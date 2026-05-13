import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.deps import get_current_user
from services.chat_service import get_dialog_state, save_dialog_state, create_session, delete_dialog_state
from agents.conversation.state import ConversationState, Stage
from agents.conversation.agent import agent as conv_agent
from agents.conversation.slot_filler import slots_summary
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

@router.websocket("/session/{session_id}")
async def chat_websocket(ws: WebSocket, session_id: str):
    await ws.accept()
    state_data = await get_dialog_state(session_id)
    if not state_data:
        await ws.send_json({"type": "error", "content": "Session not found"})
        await ws.close()
        return

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            user_content = msg.get("content", "")

            await ws.send_json({"type": "thinking", "message": "正在分析你的回答..."})

            history = []
            for m in state_data.get("messages", []):
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            history.append(HumanMessage(content=user_content))

            initial_state: ConversationState = {
                "messages": history,
                "stage": Stage(state_data.get("stage", "open")),
                "slots": state_data.get("slots", {}),
                "stage_complete": False,
                "summary_pending": False,
            }

            result = await conv_agent.ainvoke(initial_state, config={"configurable": {"thread_id": session_id}})

            ai_msg = result["messages"][-1].content if result["messages"] else ""
            new_stage = result["stage"].value if isinstance(result["stage"], Stage) else str(result["stage"])
            new_slots = result.get("slots", {})

            state_data["messages"].append({"role": "user", "content": user_content})
            state_data["messages"].append({"role": "assistant", "content": ai_msg})
            state_data["stage"] = new_stage
            state_data["slots"] = new_slots

            await save_dialog_state(session_id, state_data)

            await ws.send_json({"type": "message", "role": "assistant", "content": ai_msg, "stage": new_stage})

            if result.get("summary_pending"):
                summary = f"阶段小结：{slots_summary(new_slots)}"
                await ws.send_json({"type": "summary", "stage": new_stage, "content": summary, "profile_snapshot": new_slots})

            if result.get("stage") == Stage.DONE:
                await ws.send_json({"type": "stage_change", "from": new_stage, "to": "done"})

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
    return {"session_id": session_id, "stage": state.get("stage"), "slots": state.get("slots"), "messages": state.get("messages", [])}

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    await delete_dialog_state(session_id)
    return {"status": "deleted"}
