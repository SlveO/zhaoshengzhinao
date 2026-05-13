"""LangGraph-based conversation agent — 1 LLM call per turn."""
import json, re
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.state import ConversationState
from agents.conversation.prompts import SYSTEM_PROMPT
from agents.conversation.slot_filler import merge_slots, slots_summary

llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.7)

_SLOT_PATTERN = re.compile(r'<!--SLOTS-->\s*(\{.*?\})\s*<!--/SLOTS-->', re.DOTALL)

def _parse_response(text: str, current_slots: dict) -> tuple[str, dict]:
    """Parse AI response, extracting embedded slot JSON if present."""
    match = _SLOT_PATTERN.search(text)
    if match:
        try:
            update = json.loads(match.group(1))
            clean_text = _SLOT_PATTERN.sub('', text).strip()
            return clean_text, merge_slots(current_slots, update)
        except (json.JSONDecodeError, TypeError):
            pass
    return text.strip(), current_slots


async def conversation_node(state: ConversationState) -> dict:
    """Generate AI response and extract slots in a single LLM call."""
    summary = slots_summary(state["slots"])
    system = SystemMessage(content=SYSTEM_PROMPT.format(stage=state["stage"].value, slots_summary=summary))
    msgs = [system] + state["messages"]
    response = await llm.ainvoke(msgs)
    clean_text, new_slots = _parse_response(response.content, state["slots"])
    response.content = clean_text
    return {"messages": [response], "slots": new_slots}


def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("conversation", conversation_node)
    graph.set_entry_point("conversation")
    graph.add_edge("conversation", END)
    return graph.compile(checkpointer=MemorySaver())


agent = build_conversation_graph()
