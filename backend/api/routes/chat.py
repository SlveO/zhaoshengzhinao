import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.deps import get_current_user
from services.chat_service import get_dialog_state, save_dialog_state, create_session, delete_dialog_state
from agents.conversation.state import Stage, STAGE_ORDER
from agents.conversation.agent import agent as conv_agent
from agents.conversation.slot_filler import slots_summary
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

def _determine_next_stage(slots: dict, current_stage: Stage) -> Stage:
    """Deterministic stage progression based on slot completeness."""
    idx = STAGE_ORDER.index(current_stage)
    if idx >= len(STAGE_ORDER) - 1:
        return current_stage

    riasec = slots.get("riasec") or {}
    values = slots.get("values") or []
    region = slots.get("region_pref") or []

    checks = {
        Stage.OPEN: bool(slots.get("score")),
        Stage.EXPLORE: (len(riasec) >= 2 or len(values) >= 2) and bool(region),
        Stage.FOCUS: len(riasec) >= 3 and len(values) >= 2 and bool(region),
        Stage.CONFIRM: len(riasec) >= 3 and len(values) >= 2 and bool(region),
    }

    if checks.get(current_stage, False):
        return STAGE_ORDER[idx + 1]
    return current_stage


@router.websocket("/session/{session_id}")
async def chat_websocket(ws: WebSocket, session_id: str):
    await ws.accept()
    state_data = await get_dialog_state(session_id)
    if not state_data:
        await ws.send_json({"type": "error", "content": "Session not found"})
        await ws.close()
        return

    # Send initial state sync
    await ws.send_json({
        "type": "profile_update",
        "field": "slots",
        "value": state_data.get("slots", {}),
        "confidence": 0.7,
    })
    await ws.send_json({
        "type": "stage_change",
        "from": "none",
        "to": state_data.get("stage", "open"),
    })

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            user_content = msg.get("content", "")

            await ws.send_json({"type": "thinking", "message": "正在分析你的回答..."})

            # Build LangGraph state
            history = []
            for m in state_data.get("messages", []):
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            history.append(HumanMessage(content=user_content))

            current_stage = Stage(state_data.get("stage", "open"))
            old_slots = state_data.get("slots", {})

            initial_state = {
                "messages": history,
                "stage": current_stage,
                "slots": old_slots,
                "stage_complete": False,
                "summary_pending": False,
            }

            result = await conv_agent.ainvoke(initial_state, config={"configurable": {"thread_id": session_id}})

            ai_msg = result["messages"][-1].content if result["messages"] else ""
            new_slots = result.get("slots", old_slots)

            # Deterministic stage progression
            next_stage = _determine_next_stage(new_slots, current_stage)
            stage_changed = next_stage != current_stage and next_stage != Stage.DONE

            # Update state
            state_data["messages"].append({"role": "user", "content": user_content})
            state_data["messages"].append({"role": "assistant", "content": ai_msg})
            state_data["stage"] = next_stage.value
            state_data["slots"] = new_slots

            await save_dialog_state(session_id, state_data)

            # Send AI response
            await ws.send_json({
                "type": "message",
                "role": "assistant",
                "content": ai_msg,
                "stage": next_stage.value,
            })

            # Always send profile update so sidebar stays in sync
            await ws.send_json({
                "type": "profile_update",
                "field": "slots",
                "value": new_slots,
                "confidence": 0.7,
            })

            # Stage transition -> send stage_change and summary
            if stage_changed:
                await ws.send_json({
                    "type": "stage_change",
                    "from": current_stage.value,
                    "to": next_stage.value,
                })
                summary_text = slots_summary(new_slots)
                await ws.send_json({
                    "type": "summary",
                    "stage": next_stage.value,
                    "content": summary_text,
                    "profile_snapshot": new_slots,
                })

            # All stages complete
            if next_stage == Stage.DONE:
                await ws.send_json({
                    "type": "stage_change",
                    "from": current_stage.value,
                    "to": "done",
                })

    except WebSocketDisconnect:
        pass


@router.post("/session")
async def new_session(user: dict = Depends(get_current_user)):
    sid = await create_session(user["user_id"])
    return {"session_id": sid}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    state = await get_dialog_state(session_id)
    if not state:
        return {"error": "not found"}
    return {
        "session_id": session_id,
        "stage": state.get("stage"),
        "slots": state.get("slots"),
        "messages": state.get("messages", []),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    await delete_dialog_state(session_id)
    return {"status": "deleted"}
