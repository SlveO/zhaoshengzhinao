"""C端咨询模块 SSE 路由 — /api/v1/consult/messages。

双层检索 (SQL + RAG) + 后置校验 + 失败重生成。
会话隔离：仅接受 sess_consult_ 前缀的 session_id。
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select

from config import settings
from models import async_session
from models.college import College
from schemas.consult import ConsultMessageRequest
from services.consult_retrieval_service import (
    query_admission_data,
    build_rag_query,
    render_admission_table,
)
from services.consult_service import (
    CONSULT_SESSION_PREFIX,
    get_session,
    get_chat_history,
    save_message,
    build_profile_summary,
)
from services.consult_validator import validate_response
from services.consult_intent_service import extract_intent
from services.prompt_service import load_prompt
from services.persona_service import build_persona_greeting, apply_persona_style
from tenants.service import resolve_tenant
from core.event_writer import write_event
from utils.jwt import decode_token

router = APIRouter(prefix="/api/v1", tags=["consult"])

_logger = logging.getLogger(__name__)


def _sse(event_type: str, data: dict) -> str:
    """格式化 SSE data 行。"""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/consult/messages")
async def send_consult_message(body: ConsultMessageRequest, request: Request):
    """咨询 SSE 流式端点。

    SSE 事件序列：
      thinking → intent → admission_data → search_start → source* → search_end
      → token* → validation → [regeneration → token*] → done
    """
    # 1. 会话校验：必须是咨询会话（sess_consult_ 前缀）
    if not body.session_id.startswith(CONSULT_SESSION_PREFIX):
        return StreamingResponse(
            iter([_sse("error", {"code": "INVALID_SESSION", "message": "非咨询会话"})]),
            media_type="text/event-stream",
        )

    session = await get_session(body.session_id)
    if not session:
        return StreamingResponse(
            iter([_sse("error", {"code": "SESSION_NOT_FOUND", "message": "会话不存在或已过期"})]),
            media_type="text/event-stream",
        )

    tenant = await resolve_tenant(body.tenant_slug)
    tenant_id = tenant.id if tenant else None

    # 解析 JWT（可选）
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            if payload:
                user_id = uuid.UUID(payload["user_id"])
        except Exception:
            pass

    user_content = body.message
    await save_message(body.session_id, "user", user_content)

    if tenant_id:
        try:
            await write_event(
                tenant_id, "consult_message_sent",
                session_id=session.id,
                payload={"message_length": len(user_content)},
            )
        except Exception as e:
            _logger.warning(f"Event consult_message_sent failed: {e}")

    # 预加载 tenant college_id
    tenant_college_id = None
    if tenant:
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(College).where(College.name == tenant.config.get("brand", {}).get("name", "华南师范大学"))
                )
                college = result.scalar_one_or_none()
                if college:
                    tenant_college_id = college.id
        except Exception as e:
            _logger.warning(f"Failed to resolve college_id for tenant {body.tenant_slug}: {e}")

    async def event_stream():
        # ── Phase 1: 意图提取（三阶段管道：规则 + LLM + 融合）──
        yield _sse("thinking", {"status": "正在理解你的问题..."})

        # 获取对话历史与画像，供意图提取消解指代
        history_msgs = await get_chat_history(body.session_id, limit=8)
        slots = build_profile_summary(session) or {}

        intent_obj = await extract_intent(
            user_content=user_content,
            tenant_slug=body.tenant_slug,
            history=history_msgs,
            slots=slots,
        )
        intent = intent_obj.to_dict()

        yield _sse("intent", {"intent": intent})

        # ── Phase 2a: SQL 精确查询 admission_data ──
        admission_rows = []
        if intent.get("need_admission_data") and intent.get("majors") and tenant_college_id:
            try:
                province = intent.get("province") or session.province or "广东"
                admission_rows = await query_admission_data(
                    majors=intent["majors"],
                    province=province,
                    year=intent.get("year"),
                    tenant_college_id=tenant_college_id,
                )
            except Exception as e:
                _logger.warning(f"query_admission_data failed: {e}")

        yield _sse("admission_data", {"count": len(admission_rows), "rows": admission_rows})

        # ── Phase 2b: RAG 向量检索 ──
        sources = []
        rag_query = build_rag_query(intent, user_content)
        if rag_query:
            yield _sse("search_start", {})
            try:
                from knowledge_base.chroma_client import search_similar
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(
                    None, search_similar, rag_query, 5, body.tenant_slug
                )
                for i, r in enumerate(results[:5]):
                    src = {
                        "text": r["document"][:200],
                        "source_title": r.get("metadata", {}).get("source_title", ""),
                        "source_url": r.get("metadata", {}).get("source_url", ""),
                        "score": round(1 - r.get("distance", 0), 4),
                    }
                    sources.append(src)
                    yield _sse("source", {"index": i, "total": len(results[:5]), "item": src})
            except Exception as e:
                _logger.warning(f"RAG search failed: {e}")
            yield _sse("search_end", {"count": len(sources)})

        # ── Phase 3: 构建 system prompt + LLM 流式生成 ──
        system_template = await load_prompt("consult_system", body.tenant_slug)

        # slots_summary
        existing_profile = build_profile_summary(session) or {}
        province = existing_profile.get("province") or "未知"
        subjects = existing_profile.get("subjects") or "未知"
        score = existing_profile.get("score") or "未知"
        rank = existing_profile.get("rank") or "未知"
        slots_text = f"省份: {province}, 选科: {subjects}, 分数: {score}, 位次: {rank}"

        admission_table = render_admission_table(admission_rows)

        knowledge_context = ""
        if sources:
            lines = ["## 知识库检索结果 (仅供参考)"]
            for i, s in enumerate(sources, 1):
                lines.append(f"{i}. {s['text']}")
            knowledge_context = "\n".join(lines)

        try:
            system_content = system_template.format(
                slots_summary=slots_text,
                admission_table=admission_table,
                knowledge_context=knowledge_context,
            )
        except KeyError as e:
            _logger.warning(f"System prompt template missing placeholder: {e}")
            system_content = system_template

        # 注入租户 AI 形象（assistant_name + greeting + style）
        # 咨询模块与推荐模块共用同一份 persona 配置，确保学生侧体验一致
        if tenant and tenant.config:
            _brand = tenant.config.get("brand", {})
            _uni_short = _brand.get("short_name") or _brand.get("name", "")
            _persona = tenant.config.get("ai_persona", {})
            if _uni_short:
                system_content = build_persona_greeting(_persona, _uni_short) + "\n\n" + system_content
            system_content = apply_persona_style(system_content, _persona)

        # 历史消息
        history_msgs = await get_chat_history(body.session_id, limit=10)
        history = []
        for m in history_msgs:
            if m["role"] == "user":
                history.append(HumanMessage(content=m["content"]))
            else:
                history.append(AIMessage(content=m["content"]))
        # 移除最后一条 user 消息（避免重复）
        if history and isinstance(history[-1], HumanMessage):
            history.pop()

        msgs = [SystemMessage(content=system_content)] + history + [HumanMessage(content=user_content)]

        # LLM 流式生成（temperature=0.3 更严谨）
        llm_gen = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.3,
        )

        full_content = ""
        try:
            async for chunk in llm_gen.astream(msgs):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                full_content += token
                yield _sse("token", {"text": token})
        except Exception as exc:
            _logger.error(f"LLM stream failed: {exc}")
            yield _sse("error", {"code": "LLM_FAILED", "message": "AI 服务暂时不可用"})
            return

        # ── Phase 4: 后置校验 + 重生成 ──
        issues = []
        regenerated = False
        try:
            issues = validate_response(full_content, admission_rows)
        except Exception as e:
            _logger.warning(f"Validation failed: {e}")

        if issues and admission_rows:
            yield _sse("validation", {
                "passed": False,
                "issues_count": len(issues),
                "issues": [
                    {
                        "major": i.major_in_reply,
                        "metric": i.metric,
                        "value": i.value_in_reply,
                        "issue_type": i.issue_type,
                    }
                    for i in issues
                ],
                "regenerated": False,
            })

            # 重生成（最多 1 次）
            max_attempts = settings.consult_max_regeneration_attempts
            for attempt in range(max_attempts):
                try:
                    degraded_prompt = await load_prompt("consult_degraded", body.tenant_slug)
                    try:
                        degraded_content = degraded_prompt.format(
                            admission_table=admission_table,
                            user_content=user_content,
                        )
                    except KeyError:
                        degraded_content = degraded_prompt

                    regen_msgs = [
                        SystemMessage(content=degraded_content),
                        HumanMessage(content=user_content),
                    ]

                    full_content = ""
                    yield _sse("regeneration", {"attempt": attempt + 1})
                    async for chunk in llm_gen.astream(regen_msgs):
                        token = chunk.content if hasattr(chunk, "content") else str(chunk)
                        full_content += token
                        yield _sse("token", {"text": token})

                    regenerated = True
                    # 重新校验
                    new_issues = validate_response(full_content, admission_rows)
                    if not new_issues:
                        issues = []
                        break
                    issues = new_issues
                except Exception as e:
                    _logger.warning(f"Regeneration attempt {attempt + 1} failed: {e}")
                    break

            yield _sse("validation", {
                "passed": len(issues) == 0,
                "issues_count": len(issues),
                "issues": [
                    {
                        "major": i.major_in_reply,
                        "metric": i.metric,
                        "value": i.value_in_reply,
                        "issue_type": i.issue_type,
                    }
                    for i in issues
                ],
                "regenerated": regenerated,
            })
        else:
            yield _sse("validation", {
                "passed": True,
                "issues_count": 0,
                "issues": [],
                "regenerated": False,
            })

        # ── Phase 5: 保存 assistant 消息 + done ──
        assistant_msg = await save_message(body.session_id, "assistant", full_content)

        if tenant_id:
            try:
                await write_event(
                    tenant_id, "consult_response_completed",
                    session_id=session.id,
                    payload={
                        "response_length": len(full_content),
                        "validation_passed": len(issues) == 0,
                        "regenerated": regenerated,
                    },
                )
            except Exception as e:
                _logger.warning(f"Event consult_response_completed failed: {e}")

        yield _sse("done", {
            "session_id": body.session_id,
            "assistant_message": assistant_msg,
            "validation_passed": len(issues) == 0,
            "regenerated": regenerated,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
