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

# Keyword-based fallback when LLM doesn't output SLOTS block
_RIASEC_KW = {
    'R': ['实验', '操作', '动手', '制作', '修理', '建造', '工具', '机械', '组装', '合成', '调试'],
    'I': ['研究', '分析', '探索', '思考', '科学', '理论', '发现', '推理', '逻辑', '钻研', '化学', '物理', '生物', '数学', '科普', '编程', '代码', '算法'],
    'A': ['艺术', '设计', '创作', '音乐', '绘画', '写作', '创意', '想象', '表达', '文学', '摄影', '表演'],
    'S': ['帮助', '教育', '服务', '社会', '志愿', '照顾', '辅导', '贡献', '有意义', '助人', '沟通', '交流', '团队', '合作'],
    'E': ['管理', '领导', '组织', '说服', '商业', '销售', '竞争', '演讲', '决策', '金融', '经济', '创业'],
    'C': ['规范', '数据', '整理', '细节', '会计', '统计', '记录', '条理', '规则', '检查', '审核', '校对'],
}
_VALUES_KW = {
    '社会贡献': ['帮助', '贡献', '社会', '有意义', '服务', '助人', '奉献', '改善', '改变'],
    '个人成长': ['成长', '学习', '发展', '进步', '探索', '提升', '突破', '挑战'],
    '工作稳定': ['稳定', '安全', '保障', '公务员', '体制'],
    '薪资水平': ['薪资', '工资', '收入', '待遇', '赚钱', '高薪'],
}
_REGIONS = ['广东', '广州', '深圳', '北京', '上海', '浙江', '江苏', '四川', '湖北', '珠海', '东莞', '佛山', '汕头']


def _fallback_extract(user_msg: str) -> dict:
    """Simple keyword-based slot extraction from user message."""
    update = {}
    riasec_update = {}
    for dim, keywords in _RIASEC_KW.items():
        hits = sum(1 for kw in keywords if kw in user_msg)
        if hits > 0:
            riasec_update[dim] = min(5 + hits * 2, 10)
    if riasec_update:
        update['riasec_update'] = riasec_update

    for value, keywords in _VALUES_KW.items():
        if any(kw in user_msg for kw in keywords):
            update['values_hint'] = value
            break

    for r in _REGIONS:
        if r in user_msg:
            update['region_pref'] = [r]
            break

    return update


def _parse_response(text: str, current_slots: dict, user_msg: str) -> tuple[str, dict]:
    """Parse AI response, extracting embedded slot JSON, with keyword fallback."""
    match = _SLOT_PATTERN.search(text)
    if match:
        try:
            update = json.loads(match.group(1))
            clean_text = _SLOT_PATTERN.sub('', text).strip()
            return clean_text, merge_slots(current_slots, update)
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: keyword extraction from user message
    fallback = _fallback_extract(user_msg)
    if fallback:
        return text.strip(), merge_slots(current_slots, fallback)

    return text.strip(), current_slots


async def conversation_node(state: ConversationState) -> dict:
    """Generate AI response and extract slots in a single LLM call."""
    summary = slots_summary(state["slots"])
    system = SystemMessage(content=SYSTEM_PROMPT.format(stage=state["stage"].value, slots_summary=summary))
    msgs = [system] + state["messages"]

    # Extract last user message for fallback slot extraction
    last_user = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            last_user = m.content
            break

    response = await llm.ainvoke(msgs)
    clean_text, new_slots = _parse_response(response.content, state["slots"], last_user)
    response.content = clean_text
    return {"messages": [response], "slots": new_slots}


def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("conversation", conversation_node)
    graph.set_entry_point("conversation")
    graph.add_edge("conversation", END)
    return graph.compile(checkpointer=MemorySaver())


agent = build_conversation_graph()
