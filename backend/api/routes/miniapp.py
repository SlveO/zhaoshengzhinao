"""
C端小程序 REST API — 5 个端点。
所有端点使用统一响应格式: {data: T | null, error: {code, message} | null}
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Request, Query
from starlette.responses import StreamingResponse
from sqlalchemy import select
from models import async_session
from models.admission import AdmissionData
from models.college import College
from schemas.miniapp import (
    EnterRequest, ChatMessageRequest, RecommendationRequest,
    EnterData, ChatMessageData, StudentProfileData,
    RecommendationData, MajorAnalysisData,
)
from services.consult_service import (
    get_or_create_session, get_session, get_chat_history,
    save_message, update_session_profile,
    extract_profile_from_message, build_profile_summary,
)
from tenants.service import resolve_tenant
from core.event_writer import write_event
from utils.jwt import decode_token

router = APIRouter(prefix="/api/v1", tags=["miniapp"])


def ok(data: dict) -> dict:
    return {"data": data, "error": None}


def err(code: str, message: str) -> dict:
    return {"data": None, "error": {"code": code, "message": message}}


# ─── API 1: 创建/恢复会话 ───

@router.post("/miniapp/enter")
async def miniapp_enter(body: EnterRequest, request: Request):
    tenant_slug = body.tenant_slug or "scnu"

    tenant = await resolve_tenant(tenant_slug)
    tenant_name = "华南师范大学"
    if tenant and tenant.config:
        brand = tenant.config.get("brand", {})
        tenant_name = brand.get("name", tenant_name)

    # Optional JWT parse: guest if absent or invalid
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            if payload:
                user_id = uuid.UUID(payload["user_id"])
        except Exception:
            pass

    session, is_new = await get_or_create_session(body.session_id, tenant_slug, user_id)
    if is_new and tenant:
        try:
            await write_event(
                tenant.id, "chat_session_started",
                session_id=session.id,
                payload={"user_id": str(user_id)} if user_id else None,
            )
        except Exception:
            logging.warning("Failed to write chat_session_started event")
    chat_history = await get_chat_history(session.session_id)
    profile_summary = build_profile_summary(session)

    return ok(EnterData(
        session_id=session.session_id,
        tenant_slug=tenant_slug,
        tenant_name=tenant_name,
        is_new_session=is_new,
        has_profile=profile_summary is not None,
        chat_history=chat_history,
        profile_summary=profile_summary,
    ).model_dump())


# ─── API 2: 发送聊天消息 (SSE 流式) ───

@router.post("/chat/messages")
async def send_chat_message(body: ChatMessageRequest):
    session = await get_session(body.session_id)
    if not session:
        return err("SESSION_NOT_FOUND", "会话不存在或已过期")

    # Resolve tenant for event logging
    tenant = await resolve_tenant(body.tenant_slug)
    tenant_id = tenant.id if tenant else None

    user_content = body.message.content
    await save_message(body.session_id, "user", user_content)

    # Event: user message received
    if tenant_id:
        try:
            await write_event(
                tenant_id, "chat_message_sent",
                session_id=session.id,
                payload={"message_length": len(user_content)},
            )
        except Exception as e:
            logging.warning(f"Event chat_message_sent failed for session={body.session_id}: {e}")
    else:
        logging.debug(f"Skipped event chat_message_sent for session={body.session_id}: no tenant_id")

    # 异步 RAG 检索（不阻塞事件循环）
    async def do_rag():
        knowledge_context = ""
        sources = []
        try:
            from knowledge_base.chroma_client import search_similar
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None, search_similar, user_content, 5, body.tenant_slug
            )
            if results:
                lines = ["\n## 知识库检索结果 (仅供参考)"]
                for i, r in enumerate(results[:5], 1):
                    lines.append(f"{i}. {r['document']}")
                    sources.append({
                        "text": r["document"][:200],
                        "source_title": r.get("metadata", {}).get("source_title", ""),
                        "source_url": r.get("metadata", {}).get("source_url", ""),
                        "score": round(1 - r.get("distance", 0), 4),
                    })
                knowledge_context = "\n".join(lines)
        except Exception as e:
            logging.warning(f"RAG search failed for session={body.session_id}: {e}")
        return knowledge_context, sources

    knowledge_context, sources = await do_rag()

    # Event: RAG retrieval completed
    if tenant_id:
        top_score = sources[0]["score"] if sources else 0
        try:
            await write_event(
                tenant_id, "chat_rag_completed",
                session_id=session.id,
                payload={"sources_count": len(sources), "top_score": top_score},
            )
        except Exception as e:
            logging.warning(f"Event chat_rag_completed failed for session={body.session_id}: {e}")
    else:
        logging.debug(f"Skipped event chat_rag_completed for session={body.session_id}: no tenant_id")

    # 构建 System Prompt + History
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from config import settings
    from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT

    existing_profile = build_profile_summary(session) or {}
    slots_text = (
        f"省份: {existing_profile.get('province', '未知')}, "
        f"科类: {existing_profile.get('subject_type', '未知')}, "
        f"分数: {existing_profile.get('score', '未知')}"
    )

    system_content = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华师",
        stage="open",
        slots_summary=slots_text,
    )
    if knowledge_context:
        system_content += "\n" + knowledge_context

    history_msgs = await get_chat_history(body.session_id, limit=10)
    history = []
    for m in history_msgs:
        if m["role"] == "user":
            history.append(HumanMessage(content=m["content"]))
        else:
            history.append(AIMessage(content=m["content"]))
    if history and isinstance(history[-1], HumanMessage):
        history.pop()

    msgs = [SystemMessage(content=system_content)] + history + [HumanMessage(content=user_content)]

    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )

    # SSE 流式响应
    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'message': '正在检索知识库...'})}\n\n"
        yield f"data: {json.dumps({'type': 'sources', 'items': sources})}\n\n"

        full_content = ""
        try:
            async for chunk in llm.astream(msgs):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                full_content += token
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        except Exception as exc:
            logging.error(f"LLM stream failed: {exc}")
            # Event: chat error
            try:
                if tenant_id:
                    await write_event(
                        tenant_id, "chat_error",
                        session_id=session.id,
                        payload={"error_code": "LLM_FAILED", "error_message": str(exc)[:200]},
                    )
            except Exception as e:
                    logging.warning(f"Event chat_error failed for session={body.session_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'code': 'LLM_FAILED', 'message': 'AI 服务暂时不可用'})}\n\n"
            return

        assistant_msg = await save_message(body.session_id, "assistant", full_content)

        existing_dict = {
            "province": session.province or "",
            "subject_type": session.subject_type or "",
            "score": session.score or 0,
        }
        profile_updates = await extract_profile_from_message(user_content, full_content, existing_dict)
        profile_updated = bool(profile_updates)
        updated_session = session
        if profile_updated:
            await update_session_profile(body.session_id, profile_updates)
            updated_session = await get_session(body.session_id)

        profile_summary = build_profile_summary(updated_session) if updated_session else None

        done_data = {
            "type": "done",
            "session_id": body.session_id,
            "assistant_message": assistant_msg,
            "profile_updated": profile_updated,
            "profile_summary": profile_summary,
        }
        yield f"data: {json.dumps(done_data)}\n\n"

        # Event: chat response completed
        try:
            if tenant_id:
                await write_event(
                    tenant_id, "chat_response_completed",
                    session_id=session.id,
                    payload={"response_length": len(full_content), "profile_updated": profile_updated},
                )
        except Exception as e:
            logging.warning(f"Event chat_response_completed failed for session={body.session_id}: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── API 3: 获取学生档案 ───

@router.get("/student/profile")
async def get_student_profile(session_id: str = Query(...)):
    session = await get_session(session_id)
    if not session:
        return ok(StudentProfileData(
            session_id=session_id,
            has_profile=False,
            profile=None,
        ).model_dump())

    profile_summary = build_profile_summary(session)
    profile = None
    if profile_summary:
        profile = {
            **profile_summary,
            "consult_stage": session.consult_stage or "new",
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }

    return ok(StudentProfileData(
        session_id=session_id,
        has_profile=profile is not None,
        profile=profile,
    ).model_dump())


# ─── API 4: 本校专业推荐 ───

@router.post("/recommendations")
async def get_recommendations(body: RecommendationRequest):
    session = await get_session(body.session_id)
    if not session:
        return err("SESSION_NOT_FOUND", "会话不存在")

    profile_snapshot = body.profile_snapshot or build_profile_summary(session)
    if not profile_snapshot:
        profile_snapshot = {}

    async with async_session() as db:
        result = await db.execute(
            select(College).where(College.name == "华南师范大学")
        )
        scnu = result.scalar_one_or_none()

    if not scnu:
        return err("TENANT_NOT_FOUND", "华南师范大学数据未配置")

    async with async_session() as db:
        result = await db.execute(
            select(AdmissionData).where(
                AdmissionData.college_id == scnu.id,
                AdmissionData.year == 2024,
            ).order_by(AdmissionData.min_score.desc()).limit(20)
        )
        majors = result.scalars().all()

    student_score = profile_snapshot.get("score", 0) or session.score or 0
    intent_majors = profile_snapshot.get("intent_majors", []) or []
    items = []
    for m in majors:
        if student_score > 0:
            diff = student_score - (m.min_score or 0)
            if diff >= 10:
                risk_level, risk_label = "safe", "较稳妥"
            elif diff >= -5:
                risk_level, risk_label = "match", "较匹配"
            else:
                risk_level, risk_label = "reach", "可冲"
            match_score = min(95, max(50, 70 + diff))
        else:
            risk_level, risk_label, match_score = "match", "参考", 75

        # Intent major boost
        if intent_majors and student_score > 0:
            for intent in intent_majors:
                if intent in (m.major_name or ""):
                    match_score = min(98, match_score + 8)
                    break

        reasons = [
            f"该专业{risk_label}你的分数水平" if student_score > 0 else "建议填写分数后获得更精准推荐",
            "属于华南师范大学招生专业",
        ]
        if intent_majors and student_score > 0:
            for intent in intent_majors:
                if intent in (m.major_name or ""):
                    reasons.append(f"符合你的意向方向「{intent}」")
                    break

        items.append({
            "id": f"rec_{m.id}",
            "college_id": f"tenant_{body.tenant_slug}",
            "college_name": "华南师范大学",
            "major_name": m.major_name,
            "province": m.province or "广东",
            "city": scnu.city or "广州",
            "level": scnu.level or "本科",
            "match_score": match_score,
            "risk_level": risk_level,
            "risk_label": risk_label,
            "min_score": m.min_score or 0,
            "min_rank": m.min_rank or 0,
            "subjects": m.subject_requirements or "物理+不限",
            "reasons": reasons,
        })

    # 保存推荐结果
    try:
        from models.recommendation import Recommendation
        async with async_session() as db:
            rec = Recommendation(
                profile_version=1,
                session_id=body.session_id,
                result_json=items,
            )
            db.add(rec)
            await db.commit()
    except Exception:
        pass

    return ok(RecommendationData(
        session_id=body.session_id,
        tenant_slug=body.tenant_slug,
        tenant_name="华南师范大学",
        items=items,
        disclaimer="以下建议为华南师范大学校内专业报考参考，不代表录取承诺。",
    ).model_dump())


# ─── API 5: 专业分析详情 ───

@router.get("/majors/analysis")
async def get_major_analysis(
    session_id: str = Query(...),
    major: str = Query(...),
):
    session = await get_session(session_id)
    if not session:
        return err("SESSION_NOT_FOUND", "会话不存在")

    student_score = session.score or 0
    profile_summary = build_profile_summary(session) or {}

    async with async_session() as db:
        result = await db.execute(
            select(College).where(College.name == "华南师范大学")
        )
        scnu = result.scalar_one_or_none()

    admission = None
    if scnu:
        async with async_session() as db:
            result = await db.execute(
                select(AdmissionData).where(
                    AdmissionData.college_id == scnu.id,
                    AdmissionData.major_name == major,
                ).order_by(AdmissionData.year.desc()).limit(1)
            )
            admission = result.scalar_one_or_none()

    min_score = admission.min_score if admission else 580
    min_rank = admission.min_rank if admission else 35000
    subjects = admission.subject_requirements if admission else "物理+不限"

    if student_score > 0:
        diff = student_score - min_score
        match_score = min(95, max(50, 70 + diff))
        if diff >= 10:
            risk_label = "较稳妥"
        elif diff >= -5:
            risk_label = "较匹配"
        else:
            risk_label = "可冲"
    else:
        match_score = 75
        risk_label = "参考"

    return ok(MajorAnalysisData(
        session_id=session_id,
        tenant_slug="scnu",
        tenant_name="华南师范大学",
        major={
            "name": major,
            "college_name": "华南师范大学",
            "match_score": match_score,
            "risk_label": risk_label,
            "min_score": min_score,
            "min_rank": f"{min_rank:,}" if min_rank else "暂无",
            "subjects": subjects,
        },
        analysis={
            "fit_reasons": [
                "该专业培养方向与你的意向相符" if profile_summary.get("intent_majors") else "建议在AI咨询中说明你的意向专业",
                "属于华南师范大学优势学科方向",
            ],
            "risk_desc": f"该专业参考最低分{min_score}分，你的分数{student_score}分，属于{risk_label}区间。" if student_score > 0 else "建议提供分数后获取更精准的风险评估。",
            "focus_points": ["专业课程设置", "培养方向", "近年录取趋势", "就业去向"],
            "next_consult_suggestion": "你可以继续向 AI 咨询该专业的课程设置、培养方向、近年录取参考、就业去向和所在学院情况。",
        },
    ).model_dump())
