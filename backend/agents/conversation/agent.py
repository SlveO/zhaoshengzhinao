"""LangGraph-based conversation agent with 4-stage state machine."""
import json
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.state import ConversationState, Stage, STAGE_ORDER
from agents.conversation.prompts import SYSTEM_PROMPT, STAGE_TRANSITION_PROMPT
from agents.conversation.slot_filler import extract_slots, slots_summary

llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.7)
llm_fast = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.1)

def _system_message(state: ConversationState) -> SystemMessage:
    summary = slots_summary(state["slots"])
    return SystemMessage(content=SYSTEM_PROMPT.format(stage=state["stage"].value, slots_summary=summary))

async def _should_transition(state: ConversationState) -> bool:
    """Ask LLM whether current stage is complete."""
    if len(state["messages"]) < 2:
        return False
    recent = "\n".join(m.content for m in state["messages"][-4:])
    prompt = STAGE_TRANSITION_PROMPT.format(current_stage=state["stage"].value, conversation=recent)
    resp = await llm_fast.ainvoke(prompt)
    try:
        result = json.loads(resp.content)
        return result.get("should_transition", False)
    except json.JSONDecodeError:
        return False

async def conversation_node(state: ConversationState) -> ConversationState:
    """Generate the next AI message."""
    msgs = [_system_message(state)] + state["messages"]
    response = await llm.ainvoke(msgs)
    return {"messages": [response], "stage": state["stage"], "slots": state["slots"], "stage_complete": state["stage_complete"], "summary_pending": False}

async def extract_slots_node(state: ConversationState) -> ConversationState:
    """Extract slots from the latest user message."""
    if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
        conv = "\n".join(m.content for m in state["messages"][-6:])
        new_slots = await extract_slots(conv, state["slots"])
        return {"messages": [], "stage": state["stage"], "slots": new_slots, "stage_complete": state["stage_complete"], "summary_pending": False}
    return {}

async def check_transition(state: ConversationState) -> ConversationState:
    """Check if stage should advance."""
    transitioned = await _should_transition(state)
    if transitioned:
        idx = STAGE_ORDER.index(state["stage"])
        if idx < len(STAGE_ORDER) - 1:
            new_stage = STAGE_ORDER[idx + 1]
            return {"messages": [], "stage": new_stage, "slots": state["slots"], "stage_complete": True, "summary_pending": True}
    return {"messages": [], "stage": state["stage"], "slots": state["slots"], "stage_complete": False, "summary_pending": False}

def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("extract_slots", extract_slots_node)
    graph.add_node("check_transition", check_transition)
    graph.add_node("conversation", conversation_node)

    graph.set_entry_point("extract_slots")
    graph.add_edge("extract_slots", "check_transition")
    graph.add_edge("check_transition", "conversation")
    graph.add_edge("conversation", END)

    return graph.compile(checkpointer=MemorySaver())

agent = build_conversation_graph()
