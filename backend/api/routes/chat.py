# backend/api/routes/chat.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.deps import get_current_user, get_optional_user
from services.chat_service import get_dialog_state, save_dialog_state, create_session, delete_dialog_state
from agents.conversation.state import Stage, STAGE_ORDER
from agents.conversation.agent import _build_system_prompt, _detect_emotion
from agents.conversation.slot_filler import slots_summary
from agents.conversation.profile_analyzer import analyze_turn
from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
from agents.conversation.evidence_accumulator import EvidenceAccumulator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings

router = APIRouter()

RIASEC_KEYS = ["riasec_R", "riasec_I", "riasec_A", "riasec_S", "riasec_E", "riasec_C"]


def _determine_next_stage(evidence: dict, current_stage: Stage, turns: int) -> Stage:
    idx = STAGE_ORDER.index(current_stage)
    if idx >= len(STAGE_ORDER) - 1:
        return current_stage

    if current_stage == Stage.CONFIRM:
        return Stage.DONE

    eng = evidence.get("engagement", {})
    region_pref = evidence.get("region_pref", {}).get("regions", [])
    values_count = evidence.get("values", {}).get("evidence_count", 0)

    if current_stage == Stage.OPEN:
        if eng.get("trust_level") in ("medium", "high"):
            return Stage.EXPLORE
        if turns >= 5:
            return Stage.EXPLORE
        return Stage.OPEN

    if current_stage == Stage.EXPLORE:
        covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
        if covered >= 3 and region_pref:
            return Stage.FOCUS
        return Stage.EXPLORE

    if current_stage == Stage.FOCUS:
        covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
        if covered >= 4 and values_count >= 1:
            return Stage.CONFIRM
        return Stage.FOCUS

    return current_stage


async def _persist_profile(user_id: str, evidence: dict):
    try:
        from services.profile_service import save_profile
        from models import async_session
        acc = EvidenceAccumulator.from_dict(evidence)
        snapshot = acc.export_snapshot()
        async with async_session() as db:
            await save_profile(db, user_id, snapshot)
    except Exception:
        pass


@router.patch("/profile")
async def update_user_profile(body: dict, user: dict = Depends(get_current_user)):
    from sqlalchemy import update
    from models import async_session
    from models.user import User

    score = body.get("score", 0)
    subjects = body.get("subjects", "")
    region = body.get("region", "")

    async with async_session() as db:
        await db.execute(
            update(User).where(User.id == user["user_id"]).values(
                score=score, subjects=subjects, region=region
            )
        )
        await db.commit()
    return {"status": "ok", "score": score, "subjects": subjects, "region": region}


@router.websocket("/session/{session_id}")
async def chat_websocket(ws: WebSocket, session_id: str):
    await ws.accept()

    # Resolve tenant from query params (middleware skips WebSocket)
    tenant_slug = ws.query_params.get("tenant", "default")
    tenant_id = None
    uni_name = ""        # university full name for B2B prompt
    uni_short = ""       # university short name for B2B prompt
    try:
        from tenants.service import resolve_tenant as _resolve
        t = await _resolve(tenant_slug)
        if t:
            tenant_id = str(t.id)
            brand = (t.config or {}).get("brand", {})
            uni_name = brand.get("name", "")
            uni_short = brand.get("short_name", uni_name)
    except Exception:
        pass

    state_data = await get_dialog_state(session_id)
    if not state_data:
        await ws.send_json({"type": "error", "content": "Session not found"})
        await ws.close()
        return

    # Store tenant_id in session state for event logging
    state_data["tenant_id"] = tenant_id

    # Initialize evidence or migrate from old slots
    if "evidence" not in state_data:
        acc = EvidenceAccumulator()
        old_slots = state_data.get("slots", {})
        if old_slots.get("score"):
            acc.seed_basics(score=old_slots["score"])
        if old_slots.get("subjects"):
            acc.seed_basics(subjects=old_slots["subjects"])
        if old_slots.get("region_pref"):
            acc.seed_basics(region=old_slots["region_pref"])
        state_data["evidence"] = acc.to_dict()
    if "turns" not in state_data:
        state_data["turns"] = 0

    # Send initial state sync
    acc_init = EvidenceAccumulator.from_dict(state_data["evidence"])
    await ws.send_json({
        "type": "profile_update",
        "field": "slots",
        "value": acc_init.export_snapshot(),
        "confidence": 0.7,
    })
    await ws.send_json({
        "type": "stage_change",
        "from": "none",
        "to": state_data.get("stage", "open"),
    })

    session_llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )

    msg_count = 0
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            # Skip ping keepalive and empty messages
            if msg.get("type") == "ping":
                continue
            user_content = (msg.get("content") or "").strip()
            if not user_content:
                continue
            msg_count += 1

            await ws.send_json({"type": "thinking", "message": "正在分析你的回答..."})

            # Build message history
            history = []
            for m in state_data.get("messages", []):
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            history.append(HumanMessage(content=user_content))

            current_stage = Stage(state_data.get("stage", "open"))
            state_data["turns"] = state_data.get("turns", 0) + 1
            acc = EvidenceAccumulator.from_dict(state_data["evidence"])
            blind_spots = acc.detect_blind_spots()

            # Build system prompt — B2B (university-specific) or B2C (generic advisor)
            slots_text = slots_summary(acc.export_snapshot())
            emotion = _detect_emotion(user_content)
            if uni_name:
                system_content = B2B_SYSTEM_PROMPT.format(
                    university_name=uni_name,
                    university_short=uni_short or uni_name,
                    stage=current_stage.value,
                    slots_summary=slots_text,
                )
            else:
                system_content = _build_system_prompt(current_stage.value, slots_text, blind_spots, emotion)
            if blind_spots:
                hint_text = "、".join(blind_spots)
                system_content += f"\n\n## 当前未探索领域\n以下维度尚无证据：{hint_text}。在后续对话中自然地引导学生谈论这些方面。"
            if emotion:
                from agents.conversation.agent import _EMOTION_HINTS
                hint = _EMOTION_HINTS.get(emotion)
                if hint:
                    system_content += f"\n\n## 情绪提示\n{hint}"
            system_msg = SystemMessage(content=system_content)
            msgs = [system_msg] + history

            # Step 1: Conversation agent (with error handling)
            try:
                ai_response = await session_llm.ainvoke(msgs)
                ai_msg = ai_response.content
            except Exception:
                await ws.send_json({"type": "error", "code": "LLM_FAILED", "message": "AI 服务暂时不可用，请稍后重试"})
                continue  # Don't kill the connection

            # Step 2: Profile analyzer (analyze this turn)
            try:
                analysis = await analyze_turn(user_content, ai_msg, acc.to_dict(), blind_spots)
            except Exception:
                analysis = {"new_evidence": [], "values_hint": None, "region_mentioned": None, "engagement_assessment": {}}

            # Apply new evidence
            for evt in analysis.get("new_evidence", []):
                acc.add_evidence(
                    dimension=evt["dimension"],
                    source_turn=state_data["turns"],
                    user_quote=evt.get("user_quote", ""),
                    inferred_score=evt.get("inferred_score", 5),
                    rationale=evt.get("rationale", ""),
                    confidence=evt.get("confidence", 0.5),
                )
            if analysis.get("values_hint"):
                existing_vals = acc.to_dict().get("values", {}).get("ranked", [])
                if analysis["values_hint"] not in existing_vals:
                    existing_vals.append(analysis["values_hint"])
                acc.set_values(existing_vals)
            if analysis.get("region_mentioned"):
                existing_regions = set(acc.to_dict().get("region_pref", {}).get("regions", []))
                existing_regions.add(analysis["region_mentioned"])
                acc.to_dict()["region_pref"]["regions"] = list(existing_regions)
            acc.set_engagement(**analysis.get("engagement_assessment", {}))

            # Determine stage
            next_stage = _determine_next_stage(acc.to_dict(), current_stage, state_data["turns"])
            stage_changed = next_stage != current_stage

            # Update state
            state_data["messages"].append({"role": "user", "content": user_content})
            state_data["messages"].append({"role": "assistant", "content": ai_msg})
            state_data["stage"] = next_stage.value
            state_data["evidence"] = acc.to_dict()

            await save_dialog_state(session_id, state_data)
            snapshot = acc.export_snapshot()
            await _persist_profile(state_data["user_id"], acc.to_dict())

            # ── Event logging ──
            try:
                from core.event_writer import write_event
                await write_event(
                    tenant_id=state_data.get("tenant_id"),
                    event_type="chat.message_sent",
                    user_id=state_data.get("user_id"),
                    session_id=session_id,
                    payload={
                        "stage": next_stage.value,
                        "turn": state_data["turns"],
                        "message_length": len(user_content),
                        "emotion": emotion,
                    },
                )
                if stage_changed:
                    await write_event(
                        tenant_id=state_data.get("tenant_id"),
                        event_type="chat.stage_changed",
                        user_id=state_data.get("user_id"),
                        session_id=session_id,
                        payload={"from_stage": current_stage.value, "to_stage": next_stage.value, "turn": state_data["turns"]},
                    )
                await write_event(
                    tenant_id=state_data.get("tenant_id"),
                    event_type="profile.updated",
                    user_id=state_data.get("user_id"),
                    session_id=session_id,
                    payload={
                        "completeness": snapshot.get("completeness"),
                        "riasec_dims": [k for k in RIASEC_KEYS if acc.to_dict()[k]["evidence_count"] > 0],
                        "confidence": snapshot.get("confidence_avg", 0),
                    },
                )
            except Exception:
                pass

            # Send AI response
            await ws.send_json({
                "type": "message",
                "role": "assistant",
                "content": ai_msg,
                "stage": next_stage.value,
            })

            # Profile update (always, keeps sidebar in sync)
            await ws.send_json({
                "type": "profile_update",
                "field": "slots",
                "value": snapshot,
                "confidence": 0.7,
            })

            # Stage transition handling
            if stage_changed:
                await ws.send_json({
                    "type": "stage_change",
                    "from": current_stage.value,
                    "to": next_stage.value,
                })
                summary_text = slots_summary(snapshot)
                await ws.send_json({
                    "type": "summary",
                    "stage": current_stage.value,
                    "content": summary_text,
                    "profile_snapshot": snapshot,
                })

            if next_stage == Stage.DONE:
                await ws.send_json({
                    "type": "stage_change",
                    "from": current_stage.value,
                    "to": "done",
                })
                # Invalidate recommendation cache
                try:
                    import redis.asyncio as aioredis
                    r = aioredis.from_url(settings.redis_url)
                    await r.delete(f"recs_cache:{state_data['user_id']}")
                except Exception:
                    pass

                # Persist session profile for analytics
                try:
                    from core.event_writer import write_event
                    await write_event(
                        tenant_id=state_data.get("tenant_id"),
                        event_type="page.intent_expressed",
                        user_id=state_data.get("user_id"),
                        session_id=session_id,
                        payload={"completeness": snapshot.get("completeness"), "riasec_dims": [k for k in RIASEC_KEYS if acc.to_dict()[k]["evidence_count"] > 0]},
                    )
                except Exception:
                    pass

    except WebSocketDisconnect:
        # Clean up on disconnect — persist final state
        try:
            await _persist_profile(state_data.get("user_id"), state_data.get("evidence", {}))
        except Exception:
            pass


@router.post("/session")
async def new_session(user: dict | None = Depends(get_optional_user)):
    """Create a new chat session. Works for both registered users and guests."""
    from sqlalchemy import select
    from models import async_session
    from models.user import User
    import uuid as uuid_mod

    user_id = user["user_id"] if user else str(uuid_mod.uuid4())

    acc = EvidenceAccumulator()
    if user:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user["user_id"]))
            u = result.scalar_one_or_none()
            if u:
                if u.score:
                    acc.seed_basics(score=u.score)
                if u.subjects:
                    acc.seed_basics(subjects=u.subjects)
                if u.region:
                    acc.seed_basics(region=[u.region])

    initial_slots = acc.export_snapshot()
    sid = await create_session(user_id, initial_slots)
    state = await get_dialog_state(sid)
    if state:
        state["evidence"] = acc.to_dict()
        await save_dialog_state(sid, state)
    return {"session_id": sid, "guest": not bool(user)}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    state = await get_dialog_state(session_id)
    if not state:
        return {"error": "not found"}
    return {
        "session_id": session_id,
        "stage": state.get("stage"),
        "slots": EvidenceAccumulator.from_dict(state.get("evidence", {})).export_snapshot() if state.get("evidence") else state.get("slots"),
        "messages": state.get("messages", []),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    await delete_dialog_state(session_id)
    return {"status": "deleted"}
