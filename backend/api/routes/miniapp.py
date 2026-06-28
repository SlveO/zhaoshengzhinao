"""
C端小程序 REST API — 5 个端点。
所有端点使用统一响应格式: {data: T | null, error: {code, message} | null}
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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
from services.consult_context_service import build_consult_context
from services.profile_bridge import should_extract, bridge_profile_to_session_profiles
from tenants.service import resolve_tenant
from core.event_writer import write_event
from utils.jwt import decode_token

router = APIRouter(prefix="/api/v1", tags=["miniapp"])


def ok(data: dict) -> dict:
    return {"data": data, "error": None}


def err(code: str, message: str) -> dict:
    return {"data": None, "error": {"code": code, "message": message}}


# ─── 选科要求解析与匹配（硬过滤） ───

# 科目全称 → 单字缩写映射
_SUBJECT_MAP = {
    "物理": "物", "化学": "化", "生物": "生",
    "政治": "政", "思想政治": "政", "历史": "史",
    "地理": "地", "技术": "技",
}


def _to_abbr(name: str) -> str:
    """科目全称转单字缩写。"""
    name = name.strip()
    for full, abbr in _SUBJECT_MAP.items():
        if full in name:
            return abbr
    return name[:1] if name else ""


def parse_subject_requirement(req: str) -> dict:
    """解析专业选科要求字符串。

    返回:
        {
            'required': set[str],   # 必选科目（学生必须都选）
            'pick_one': list[set],  # 多组"N选1"，每组学生至少选一个
        }

    支持的格式（基于 admission_data 实际数据）:
        - "" / "不限"                              → 无要求
        - "首选物理，再选不限"                       → 必选物理
        - "首选物理，再选化学"                       → 必选物理+化学
        - "首选物理，再选化学/生物(2选1)"            → 必选物理，且化/生二选一
        - "物理必选"                                → 必选物理
        - "物理、化学(2科必选)"                     → 必选物理+化学
        - "物/化/生(3选1)"                          → 物/化/生三选一
        - "物理/化学(2选1)"                         → 物/化二选一
    """
    if not req or not req.strip() or "不限" in req:
        return {"required": set(), "pick_one": []}

    required: set = set()
    pick_one: list = []
    text = req.strip()

    # 模式1: "首选X，再选Y" 或 "首选X，再选Y/Z(2选1)"
    if "首选" in text:
        parts = text.split("，")
        for part in parts:
            part = part.strip()
            if part.startswith("首选"):
                for full, abbr in _SUBJECT_MAP.items():
                    if full in part:
                        required.add(abbr)
                        break
            elif part.startswith("再选"):
                if "不限" in part:
                    continue
                if "(2选1)" in part or "(3选1)" in part:
                    before_paren = part.split("(")[0].replace("再选", "")
                    subjects = [_to_abbr(s) for s in before_paren.split("/") if s.strip()]
                    if subjects:
                        pick_one.append(set(subjects))
                else:
                    for full, abbr in _SUBJECT_MAP.items():
                        if full in part:
                            required.add(abbr)
                            break

    # 模式2: "X必选"
    elif "必选" in text and "科必选" not in text:
        for full, abbr in _SUBJECT_MAP.items():
            if full in text:
                required.add(abbr)

    # 模式3: "X、Y(2科必选)"
    elif "科必选" in text:
        before_paren = text.split("(")[0]
        for full, abbr in _SUBJECT_MAP.items():
            if full in before_paren:
                required.add(abbr)

    # 模式4: "X/Y/Z(N选1)"
    elif "选1" in text:
        before_paren = text.split("(")[0]
        subjects = [_to_abbr(s) for s in before_paren.split("/") if s.strip()]
        if subjects:
            pick_one.append(set(subjects))

    return {"required": required, "pick_one": pick_one}


def check_subject_match(student_subjects: str, req: str) -> bool:
    """检查学生选科是否满足专业选科要求（硬过滤）。"""
    if not req or not req.strip() or "不限" in req:
        return True

    parsed = parse_subject_requirement(req)
    if not parsed["required"] and not parsed["pick_one"]:
        # 解析失败，宽松通过（避免误过滤）
        return True

    student_set = set(student_subjects or "")

    # 必选科目必须全部满足
    if not parsed["required"].issubset(student_set):
        return False

    # N选1 约束：每组至少选一个
    for group in parsed["pick_one"]:
        if not (group & student_set):
            return False

    return True


def calc_rank_score(student_rank: int, min_rank: int) -> float:
    """位次匹配评分 (0-100)。
    rank_diff = student_rank - min_rank（负数表示学生位次优于最低位次）。
    """
    if not student_rank or not min_rank:
        return 50.0  # 无位次数据，中性评分
    diff = student_rank - min_rank
    if diff <= 0:
        return 100.0
    elif diff <= 5000:
        return 80.0 + (5000 - diff) / 5000 * 20.0  # 80-100 线性
    elif diff <= 20000:
        return 50.0 + (20000 - diff) / 15000 * 30.0  # 50-80 线性
    else:
        return 30.0


def calc_rank_risk(student_rank: int, min_rank: int) -> tuple[str, str]:
    """根据位次差判定风险等级。返回 (risk_level, risk_label)。"""
    if not student_rank or not min_rank:
        return "match", "参考"
    diff = student_rank - min_rank
    if diff <= -5000:
        return "safe", "保底"
    elif diff <= 5000:
        return "match", "匹配"
    else:
        return "reach", "冲刺"


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

    session, is_new = await get_or_create_session(
        body.session_id, tenant_slug, user_id, module_type=body.module_type
    )
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

    # 首轮提问时 session 快照为空，用 users 表注册信息兜底 profile_summary
    # 让前端能立即显示画像条，回答也能引用注册信息
    if not profile_summary and session.user_id:
        try:
            from models.user import User
            async with async_session() as db:
                u_result = await db.execute(select(User).where(User.id == session.user_id))
                u = u_result.scalar_one_or_none()
                if u and (u.region or u.subjects or u.score or u.rank):
                    profile_summary = {
                        "province": u.region or "",
                        "subjects": u.subjects or "",
                        "score": u.score or 0,
                        "rank": u.rank or 0,
                    }
        except Exception as e:
            logging.warning(f"Failed to read user basic info on enter: {e}")

    # 返回租户 AI 形象（开场白 + 助手名），供前端展示首条消息
    greeting = None
    assistant_name = None
    if tenant and tenant.config:
        persona = tenant.config.get("ai_persona", {}) or {}
        greeting = persona.get("greeting") or None
        assistant_name = persona.get("assistant_name") or None

    return ok(EnterData(
        session_id=session.session_id,
        tenant_slug=tenant_slug,
        tenant_name=tenant_name,
        is_new_session=is_new,
        has_profile=profile_summary is not None,
        chat_history=chat_history,
        profile_summary=profile_summary,
        greeting=greeting,
        assistant_name=assistant_name,
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
                tenant_id, "chat.message_sent",
                session_id=session.id,
                payload={
                    "message_length": len(user_content),
                    "content": user_content,
                    "module": "recommend",
                    "stage": "EXPLORE",
                },
            )
        except Exception as e:
            logging.warning(f"Event chat.message_sent failed for session={body.session_id}: {e}")
    else:
        logging.debug(f"Skipped event chat.message_sent for session={body.session_id}: no tenant_id")

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

    # 优先从 users 表读取最新基本信息（解决 session 快照陈旧问题）
    # 注意：不读取 username（手机号），仅读 region/subjects/score/rank
    user_basic = {}
    if session.user_id:
        try:
            from models.user import User
            async with async_session() as db:
                u_result = await db.execute(select(User).where(User.id == session.user_id))
                u = u_result.scalar_one_or_none()
                if u:
                    user_basic = {
                        "province": u.region or "",
                        "subjects": u.subjects or "",
                        "score": u.score or 0,
                        "rank": u.rank or 0,
                    }
        except Exception as e:
            logging.warning(f"Failed to read user basic info for user_id={session.user_id}: {e}")

    province = user_basic.get("province") or existing_profile.get("province", "未知")
    subjects = user_basic.get("subjects") or existing_profile.get("subjects", "未知")
    score = user_basic.get("score") or existing_profile.get("score", "未知")
    rank = user_basic.get("rank") or existing_profile.get("rank", "未知")
    slots_text = (
        f"省份: {province}, "
        f"选科: {subjects}, "
        f"分数: {score}, "
        f"位次: {rank}"
    )

    # 构建咨询历史上下文（若推荐会话绑定了咨询会话）
    consult_context = ""
    try:
        consult_context = await build_consult_context(session)
    except Exception as e:
        logging.warning(f"build_consult_context failed for session={body.session_id}: {e}")

    # 根据已收集信息动态判定对话阶段：
    # - 基础信息（省份/选科/分数/位次）任一未知 → open（破冰，了解基本情况）
    # - 基础信息齐全但无咨询历史 → explore（探索兴趣方向）
    # - 有咨询历史 → confirm（基于画像给推荐）
    has_basic_info = (
        province and province != "未知"
        and subjects and subjects != "未知"
        and score and score != "未知"
        and rank and rank != "未知"
    )
    if not has_basic_info:
        stage = "open"
    elif consult_context and consult_context != "（无）":
        stage = "confirm"
    else:
        stage = "explore"

    system_content = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华师",
        stage=stage,
        slots_summary=slots_text,
        consult_context=consult_context or "（无）",
        knowledge_context=knowledge_context or "",
    )

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
        # Phase 1: AI 问题理解（RAG 前的轻量 LLM 调用，流式输出）
        yield f"data: {json.dumps({'type': 'thinking', 'message': '正在理解你的问题...'})}\n\n"
        yield f"data: {json.dumps({'type': 'understanding_start'})}\n\n"
        try:
            understanding_msgs = [
                SystemMessage(content="你是问题理解助手。用一句话（不超过30个字）总结用户问题的核心意图，直接输出总结内容，不加任何前缀。"),
                HumanMessage(content=user_content),
            ]
            async for chunk in llm.astream(understanding_msgs):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    yield f"data: {json.dumps({'type': 'understanding', 'text': token})}\n\n"
        except Exception as exc:
            logging.warning(f"Understanding stream failed for session={body.session_id}: {exc}")
        yield f"data: {json.dumps({'type': 'understanding_end'})}\n\n"

        # Phase 2: RAG 检索 — 逐条流式下发 source（前端单行滚动展示）
        yield f"data: {json.dumps({'type': 'search_start'})}\n\n"
        for i, src in enumerate(sources):
            yield f"data: {json.dumps({'type': 'source', 'index': i, 'total': len(sources), 'item': src})}\n\n"
        yield f"data: {json.dumps({'type': 'search_end', 'count': len(sources)})}\n\n"

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

        # B1: LLM profile extraction bridge (every 3 turns)
        profile_bridge_ran = False
        try:
            if tenant_id and await should_extract(body.session_id):
                profile_bridge_ran = await bridge_profile_to_session_profiles(
                    session, tenant_id, user_content, full_content
                )
        except Exception as e:
            logging.warning(f"Profile bridge failed for session={body.session_id}: {e}")

        # Fallback: regex extraction for basic fields
        existing_dict = {
            "province": session.province or "",
            "subjects": session.subjects or "",
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
            "profile_updated": profile_updated or profile_bridge_ran,
            "profile_summary": profile_summary,
        }
        yield f"data: {json.dumps(done_data)}\n\n"

        # Trigger consult summary generation (async, non-blocking)
        try:
            from services.consult_summary_service import maybe_generate_summary
            asyncio.create_task(maybe_generate_summary(body.session_id))
        except Exception as e:
            logging.warning(f"Summary trigger failed for session={body.session_id}: {e}")

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


# ─── API 4: 留学项目专业推荐（基于知识库 KB008-KB010） ───

# 知识库项目专业常量（KB008/KB009/KB010）
KB_PROGRAM_MAJORS = [
    {
        "major_name": "2+2 商科方向",
        "mode": "2+2 出国留学培训项目",
        "duration": "国内2年 + 国外2年",
        "credits_waiver": "豁免约1/3学分",
        "partner_majors": "会计学、金融学、经济学、管理学、市场营销、商业分析与管理、人力资源管理、数字营销、国际商务、酒店与旅游管理、会计与金融、金融经济学",
        "core_courses": "微观经济学、宏观经济学、会计学原理、财务管理、市场营销、国际金融",
        "keywords": ["商科", "经济", "会计", "金融", "市场营销", "管理", "2+2"],
        "riasec": ["E", "C", "S"],
        "description": "培养商业领袖，涵盖市场营销、财务管理等核心课程，注重实践技能培养，强调跨文化交流和国际商务。",
    },
    {
        "major_name": "2+2 新媒体方向",
        "mode": "2+2 出国留学培训项目",
        "duration": "国内2年 + 国外2年",
        "credits_waiver": "豁免约1/3学分",
        "partner_majors": "网络与新媒体、艺术与文化传播、融媒体与通信技术",
        "core_courses": "网络与新媒体概论、传播学、数字媒体技术、摄影摄像技术、新闻采访与写作、广告学概论",
        "keywords": ["新媒体", "新闻传播", "数字媒体", "平面设计", "摄影", "传媒", "2+2"],
        "riasec": ["A", "I", "S"],
        "description": "培养具备新闻传播学理论知识和新媒体技术应用能力的应用型创新人才，从事新媒体策划与运营。",
    },
    {
        "major_name": "3+1 市场营销",
        "mode": "3+1 SQA-AD 项目",
        "duration": "国内3年 + 国外1年",
        "credits_waiver": "豁免约2/3学分",
        "partner_majors": "国际时尚管理与营销、市场营销与管理、广告与数字营销、全球商务管理、时尚管理、商务与市场营销、国际市场营销、数字化营销",
        "core_courses": "市场营销原理、消费者行为学、品牌管理、数字营销、国际市场营销",
        "keywords": ["市场营销", "营销", "品牌", "数字营销", "3+1", "SQA"],
        "riasec": ["E", "S", "A"],
        "description": "培养具备市场营销理论与实务能力，掌握数字营销与品牌管理的国际化营销人才。",
    },
    {
        "major_name": "3+1 人力资源管理",
        "mode": "3+1 SQA-AD 项目",
        "duration": "国内3年 + 国外1年",
        "credits_waiver": "豁免约2/3学分",
        "partner_majors": "商务管理、商务与管理、国际商务交流、国际商务、商务管理与人力资源、国际商务与人力资源管理、国际商务管理、工商管理、商务学",
        "core_courses": "人力资源管理、组织行为学、劳动关系、薪酬管理、招聘与培训",
        "keywords": ["人力资源", "HR", "管理", "组织", "3+1", "SQA"],
        "riasec": ["S", "E", "C"],
        "description": "培养具备人力资源管理专业知识和国际商务视野的管理人才，掌握招聘、培训、绩效等核心模块。",
    },
    {
        "major_name": "3+1 商务会计",
        "mode": "3+1 SQA-AD 项目",
        "duration": "国内3年 + 国外1年",
        "credits_waiver": "豁免约2/3学分",
        "partner_majors": "会计学、会计与金融、银行与金融、国际金融与银行、国际商务会计与金融、金融管理与会计、会计与商务管理、金融经济学、会计与财务管理、财务管理",
        "core_courses": "财务会计、管理会计、财务管理、审计学、税法、会计信息系统",
        "keywords": ["会计", "商务会计", "财务", "金融", "审计", "3+1", "SQA"],
        "riasec": ["C", "E", "I"],
        "description": "培养具备会计专业知识和国际金融视野的财务管理人才，掌握会计、审计、税务等核心技能。",
    },
]


@router.post("/recommendations")
async def get_recommendations(body: RecommendationRequest):
    session = await get_session(body.session_id)
    if not session:
        return err("SESSION_NOT_FOUND", "会话不存在")

    profile_snapshot = body.profile_snapshot or build_profile_summary(session)
    if not profile_snapshot:
        profile_snapshot = {}

    # 读取学生意向专业与兴趣方向（RIASEC）
    intent_majors = profile_snapshot.get("intent_majors", []) or []
    student_riasec = profile_snapshot.get("riasec_top", "") or ""

    # 基于知识库项目专业生成推荐（自主招生项目，不依赖高考分数/位次/选科）
    items = []
    for idx, pm in enumerate(KB_PROGRAM_MAJORS):
        # 意向匹配评分
        intent_hit = False
        intent_score = 50.0
        if intent_majors:
            for intent in intent_majors:
                if not intent:
                    continue
                # 意向关键词命中项目专业关键词
                for kw in pm["keywords"]:
                    if intent in kw or kw in intent:
                        intent_hit = True
                        intent_score = 100.0
                        break
                # 意向命中对接专业
                if intent in pm["partner_majors"]:
                    intent_hit = True
                    intent_score = 100.0
                    break
                # 意向命中专业名
                if intent in pm["major_name"]:
                    intent_hit = True
                    intent_score = 100.0
                    break
            if not intent_hit:
                intent_score = 60.0

        # RIASEC 兴趣匹配评分
        riasec_score = 50.0
        if student_riasec and student_riasec in pm["riasec"]:
            riasec_score = 90.0

        # 综合分（意向 60% + 兴趣 40%）
        match_score = round(intent_score * 0.6 + riasec_score * 0.4)

        # 匹配度分级
        if match_score >= 80:
            risk_level = "match"
            risk_label = "高度匹配"
        elif match_score >= 65:
            risk_level = "reach"
            risk_label = "较匹配"
        else:
            risk_level = "safe"
            risk_label = "可考虑"

        # 动态理由生成
        reasons = [pm["description"]]
        reasons.append(f"项目模式：{pm['mode']}，{pm['duration']}，{pm['credits_waiver']}")
        reasons.append(f"核心课程：{pm['core_courses']}")
        reasons.append(f"可对接国外专业：{pm['partner_majors']}")

        if intent_hit:
            for intent in intent_majors:
                if not intent:
                    continue
                hit_kw = next((kw for kw in pm["keywords"] if intent in kw or kw in intent), None)
                if hit_kw or intent in pm["partner_majors"] or intent in pm["major_name"]:
                    reasons.append(f"符合你的意向方向「{intent}」")
                    break

        if student_riasec and student_riasec in pm["riasec"]:
            riasec_names = {"R": "实用型", "I": "研究型", "A": "艺术型", "S": "社会型", "E": "企业型", "C": "常规型"}
            reasons.append(f"契合你的兴趣类型「{riasec_names.get(student_riasec, student_riasec)}」")

        reasons.append("自主招生，不占高考志愿，文理兼收，毕业后获国外学士学位（中留服认证）")

        items.append({
            "id": f"rec_kb_{idx}",
            "college_id": f"tenant_{body.tenant_slug}",
            "college_name": "华南师范大学国际商学院",
            "major_name": pm["major_name"],
            "province": "全国招生",
            "city": "佛山南海",
            "level": "本科（出国留学项目）",
            "match_score": match_score,
            "risk_level": risk_level,
            "risk_label": risk_label,
            # 以下字段复用前端展示位：min_score→留空、min_rank→留空、subjects→项目模式
            "min_score": 0,
            "min_rank": 0,
            "subjects": pm["mode"],
            "reasons": reasons,
            # 新增字段（前端可选择性展示）
            "mode": pm["mode"],
            "duration": pm["duration"],
            "credits_waiver": pm["credits_waiver"],
            "partner_majors": pm["partner_majors"],
            "core_courses": pm["core_courses"],
        })

    # 排序：匹配度降序
    items.sort(key=lambda x: -x["match_score"])

    # 保存推荐结果（含 user_id）
    try:
        from models.recommendation import Recommendation
        async with async_session() as db:
            rec = Recommendation(
                profile_version=1,
                session_id=body.session_id,
                user_id=session.user_id,
                result_json=items,
            )
            db.add(rec)
            await db.commit()
    except Exception as e:
        logging.warning(f"Failed to save recommendation: {e}")

    return ok(RecommendationData(
        session_id=body.session_id,
        tenant_slug=body.tenant_slug,
        tenant_name="华南师范大学",
        items=items,
        disclaimer="以下建议为华南师范大学国际商学院出国留学项目专业推荐参考，自主招生不占高考志愿，最终录取以学校审核为准。",
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


# ─── API: Student basic info form (pre-chat) ───

class BasicInfoRequest(BaseModel):
    region: str
    subjects: str
    score: int
    rank: int


@router.put("/miniapp/profile/basic")
async def update_basic_info(body: BasicInfoRequest, request: Request):
    """Update student basic info (province/subjects/score/rank) before chat."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return err("AUTH_REQUIRED", "登录后才能填写基本信息")
    try:
        payload = decode_token(auth_header[7:])
        if not payload:
            return err("AUTH_REQUIRED", "无效的登录凭证")
        user_id = uuid.UUID(payload["user_id"])
    except Exception:
        return err("AUTH_REQUIRED", "无效的登录凭证")

    # Validate
    if not body.region or not body.subjects:
        return err("INVALID_INPUT", "省份和选科为必填")
    if not (0 <= body.score <= 750):
        return err("INVALID_INPUT", "分数必须在 0-750 之间")
    if body.rank <= 0:
        return err("INVALID_INPUT", "位次必须为正整数")

    from models.user import User
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return err("USER_NOT_FOUND", "用户不存在")
        user.region = body.region
        user.subjects = body.subjects
        user.score = body.score
        user.rank = body.rank
        await db.commit()
    return ok({"updated": True})


@router.get("/miniapp/profile/basic")
async def get_basic_info(request: Request):
    """Get student basic info (province/subjects/score/rank)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ok({"region": "", "subjects": "", "score": 0, "rank": None, "is_guest": True})
    try:
        payload = decode_token(auth_header[7:])
        if not payload:
            return ok({"region": "", "subjects": "", "score": 0, "rank": None, "is_guest": True})
        user_id = uuid.UUID(payload["user_id"])
    except Exception:
        return ok({"region": "", "subjects": "", "score": 0, "rank": None, "is_guest": True})

    from models.user import User
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return err("USER_NOT_FOUND", "用户不存在")
        return ok({
            "region": user.region or "",
            "subjects": user.subjects or "",
            "score": user.score or 0,
            "rank": user.rank,
            "is_guest": False,
        })
