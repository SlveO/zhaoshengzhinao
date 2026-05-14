"""LangGraph-based conversation agent — 1 LLM call per turn."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.state import ConversationState
from agents.conversation.prompts import SYSTEM_PROMPT
from agents.conversation.slot_filler import slots_summary

_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.7)
    return _llm

# For backward compatibility (lazy-loaded)
llm = None

_EMOTION_KW = {
    "焦虑": ["好烦", "担心", "紧张", "不知道怎么办", "压力", "害怕", "考砸", "万一", "怎么办"],
    "迷茫": ["不知道", "随便", "都行", "没什么想法", "无所谓", "不清楚", "不太了解", "没想过"],
    "确定": ["就想学", "一定要", "必须", "确定了", "肯定是", "就是喜欢", "非它不可"],
    "烦躁": ["别问了", "不想说", "烦死了", "随便吧", "不想聊", "就这样吧"],
    "兴奋": ["特别喜欢", "超级喜欢", "太棒了", "好期待", "梦想", "真的很喜欢"],
}

_EMOTION_HINTS = {
    "焦虑": "该学生表现出焦虑情绪，请先简短安抚（1句话），再温和提问。",
    "迷茫": "该学生比较迷茫，请用具体的例子或场景来引导，避免开放式提问。",
    "确定": "该学生目标明确，可直接追问动机来源，深度挖掘为什么喜欢。",
    "烦躁": "该学生有些不耐烦，请简短回复表示理解，给对方空间，不要追问。",
    "兴奋": "该学生表现出兴奋，请鼓励ta多说，追问更多细节和感受。",
}


def _detect_emotion(user_msg: str) -> str | None:
    for emotion, keywords in _EMOTION_KW.items():
        if any(kw in user_msg for kw in keywords):
            return emotion
    return None


def _build_system_prompt(stage: str, slots_summary_text: str, blind_spot_hints: list[str], emotion: str | None) -> str:
    content = SYSTEM_PROMPT.format(stage=stage, slots_summary=slots_summary_text)
    if blind_spot_hints:
        hint_text = "、".join(blind_spot_hints)
        content += f"\n\n## 当前未探索领域\n以下维度尚无证据：{hint_text}。在后续对话中自然地引导学生谈论这些方面，避免直接提问'你喜欢动手吗'这类生硬问题。"
    if emotion:
        content += f"\n\n## 情绪提示\n{_EMOTION_HINTS.get(emotion, '')}"
    return content


async def conversation_node(state: ConversationState, blind_spot_hints: list[str] | None = None) -> dict:
    summary = slots_summary(state.get("slots", {}))
    last_user = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            last_user = m.content
            break
    emotion = _detect_emotion(last_user)
    system_content = _build_system_prompt(state["stage"].value, summary, blind_spot_hints or [], emotion)
    system = SystemMessage(content=system_content)
    msgs = [system] + state["messages"]
    response = await _get_llm().ainvoke(msgs)
    return {"messages": [response], "slots": state.get("slots", {})}


def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("conversation", conversation_node)
    graph.set_entry_point("conversation")
    graph.add_edge("conversation", END)
    return graph.compile(checkpointer=MemorySaver())


agent = build_conversation_graph()
