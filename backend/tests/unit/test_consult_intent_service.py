"""consult_intent_service 单元测试。

测试契约（纯函数，不依赖真实 DB/LLM）：
- _rule_extract_intent: 规则提取数字/关键词/专业名
- _parse_llm_intent: LLM JSON 解析与专业名校验
- _fuse_intent: 融合规则与 LLM 结果
- _format_conversation_history / _format_slots_summary / _format_tenant_majors: 格式化器
"""
import pytest
from services.consult_intent_service import (
    Intent,
    _rule_extract_intent,
    _parse_llm_intent,
    _fuse_intent,
    _format_conversation_history,
    _format_slots_summary,
    _format_tenant_majors,
)


# 测试用专业词典
MAJORS_DICT = {
    "人工智能", "计算机科学与技术", "软件工程", "应用心理学",
    "数学与应用数学", "物理学", "汉语言文学", "英语", "金融学",
}


class TestRuleExtractIntent:
    """阶段 A：规则前置意图提取。"""

    def test_data_query_with_score(self):
        intent = _rule_extract_intent("人工智能专业多少分能上", MAJORS_DICT, {})
        assert intent.intent_type == "data_query"
        assert "人工智能" in intent.majors
        assert intent.need_admission_data is True

    def test_data_query_with_explicit_score(self):
        intent = _rule_extract_intent("我考了585分能上计算机科学与技术吗", MAJORS_DICT, {})
        assert intent.intent_type == "data_query"
        assert intent.score_query == 585
        assert "计算机科学与技术" in intent.majors

    def test_data_query_with_rank(self):
        intent = _rule_extract_intent("位次30000名能上软件工程吗", MAJORS_DICT, {})
        assert intent.intent_type == "data_query"
        assert intent.rank_query == 30000

    def test_policy_query(self):
        intent = _rule_extract_intent("招生章程里选科要求是什么", MAJORS_DICT, {})
        assert intent.intent_type == "policy_query"

    def test_major_intro(self):
        intent = _rule_extract_intent("心理学学什么课程", MAJORS_DICT, {})
        assert intent.intent_type == "major_intro"
        assert "应用心理学" in intent.majors  # 别名映射

    def test_chitchat(self):
        intent = _rule_extract_intent("你好，谢谢", MAJORS_DICT, {})
        assert intent.intent_type == "chitchat"

    def test_year_extraction(self):
        intent = _rule_extract_intent("2024年人工智能录取分数", MAJORS_DICT, {})
        assert intent.year == 2024

    def test_province_from_slots(self):
        intent = _rule_extract_intent("多少分", MAJORS_DICT, {"province": "湖南"})
        assert intent.province == "湖南"

    def test_province_from_region_pref_dict(self):
        intent = _rule_extract_intent("多少分", MAJORS_DICT, {"region_pref": {"regions": ["北京"]}})
        assert intent.province == "北京"

    def test_default_province(self):
        intent = _rule_extract_intent("你好", MAJORS_DICT, {})
        assert intent.province == "广东"

    def test_major_alias_matching(self):
        """用户说简称'计科'应映射到'计算机科学与技术'。"""
        intent = _rule_extract_intent("计科多少分", MAJORS_DICT, {})
        assert "计算机科学与技术" in intent.majors

    def test_rewritten_query_defaults_to_user_content(self):
        intent = _rule_extract_intent("人工智能怎么样", MAJORS_DICT, {})
        assert intent.rewritten_query == "人工智能怎么样"


class TestParseLlmIntent:
    """阶段 B：LLM JSON 解析。"""

    def test_valid_json(self):
        raw = '{"intent_type":"data_query","majors":["人工智能"],"province":"广东","year":null,"score_query":585,"rank_query":null,"need_admission_data":true,"rewritten_query":"人工智能专业录取分数"}'
        intent = _parse_llm_intent(raw, MAJORS_DICT)
        assert intent is not None
        assert intent.intent_type == "data_query"
        assert intent.majors == ["人工智能"]
        assert intent.score_query == 585
        assert intent.need_admission_data is True
        assert intent.rewritten_query == "人工智能专业录取分数"

    def test_markdown_code_block(self):
        raw = '```json\n{"intent_type":"chitchat","majors":[],"rewritten_query":""}\n```'
        intent = _parse_llm_intent(raw, MAJORS_DICT)
        assert intent is not None
        assert intent.intent_type == "chitchat"

    def test_json_with_extra_text(self):
        raw = '好的，分析结果如下：\n{"intent_type":"policy_query","majors":[],"rewritten_query":"招生政策"}\n以上是分析。'
        intent = _parse_llm_intent(raw, MAJORS_DICT)
        assert intent is not None
        assert intent.intent_type == "policy_query"

    def test_invalid_json_returns_none(self):
        assert _parse_llm_intent("这不是JSON", MAJORS_DICT) is None

    def test_empty_returns_none(self):
        assert _parse_llm_intent("", MAJORS_DICT) is None

    def test_major_normalization_in_parser(self):
        """LLM 返回的别名应被标准化为词典中的标准名。"""
        raw = '{"intent_type":"major_intro","majors":["计科"],"rewritten_query":"计算机专业介绍"}'
        intent = _parse_llm_intent(raw, MAJORS_DICT)
        assert intent is not None
        assert "计算机科学与技术" in intent.majors

    def test_invalid_intent_type_falls_back_to_chitchat(self):
        raw = '{"intent_type":"unknown_type","majors":[]}'
        intent = _parse_llm_intent(raw, MAJORS_DICT)
        assert intent is not None
        assert intent.intent_type == "chitchat"

    def test_string_year_converted_to_int(self):
        raw = '{"intent_type":"data_query","majors":[],"year":"2024"}'
        intent = _parse_llm_intent(raw, MAJORS_DICT)
        assert intent is not None
        assert intent.year == 2024


class TestFuseIntent:
    """阶段 C：融合校验。"""

    def test_llm_none_falls_back_to_rule(self):
        rule = Intent(intent_type="data_query", majors=["人工智能"], need_admission_data=True)
        merged = _fuse_intent(rule, None)
        assert merged.intent_type == "data_query"
        assert merged.majors == ["人工智能"]

    def test_llm_takes_priority(self):
        rule = Intent(intent_type="chitchat", majors=[], score_query=585)
        llm = Intent(intent_type="data_query", majors=["软件工程"], score_query=None)
        merged = _fuse_intent(rule, llm)
        assert merged.intent_type == "data_query"
        assert merged.majors == ["软件工程"]

    def test_rule_fills_llm_gaps(self):
        """LLM 漏掉 score_query 时用规则补全。"""
        rule = Intent(intent_type="data_query", majors=["人工智能"], score_query=585)
        llm = Intent(intent_type="data_query", majors=["人工智能"], score_query=None)
        merged = _fuse_intent(rule, llm)
        assert merged.score_query == 585

    def test_need_admission_data_or_logic(self):
        """规则命中分数关键词时强制 need_admission_data=true。"""
        rule = Intent(intent_type="data_query", majors=[], need_admission_data=True)
        llm = Intent(intent_type="data_query", majors=[], need_admission_data=False)
        merged = _fuse_intent(rule, llm)
        assert merged.need_admission_data is True

    def test_data_query_no_majors_fills_from_rule(self):
        """LLM 判定 data_query 但漏提取 majors，规则补回。"""
        rule = Intent(intent_type="data_query", majors=["人工智能"])
        llm = Intent(intent_type="data_query", majors=[])
        merged = _fuse_intent(rule, llm)
        assert merged.majors == ["人工智能"]

    def test_llm_empty_majors_filled_by_rule(self):
        rule = Intent(intent_type="major_intro", majors=["应用心理学"])
        llm = Intent(intent_type="major_intro", majors=[])
        merged = _fuse_intent(rule, llm)
        assert merged.majors == ["应用心理学"]


class TestFormatters:
    """格式化器测试。"""

    def test_format_history_empty(self):
        result = _format_conversation_history([])
        assert "无历史" in result

    def test_format_history_with_messages(self):
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮你"},
        ]
        result = _format_conversation_history(history)
        assert "学生: 你好" in result
        assert "助手: 你好" in result

    def test_format_history_limit(self):
        """超过 limit*2 条只取最近的。"""
        history = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
        result = _format_conversation_history(history, limit=4)
        assert "msg19" in result
        assert "msg0" not in result

    def test_format_slots_empty(self):
        result = _format_slots_summary({})
        assert "暂无" in result

    def test_format_slots_with_data(self):
        slots = {"province": "广东", "score": 585, "rank": 30000, "intent_majors": ["人工智能"]}
        result = _format_slots_summary(slots)
        assert "广东" in result
        assert "585" in result
        assert "30000" in result
        assert "人工智能" in result

    def test_format_majors_empty(self):
        result = _format_tenant_majors(set())
        assert "词典为空" in result

    def test_format_majors_with_data(self):
        result = _format_tenant_majors({"人工智能", "软件工程"})
        assert "人工智能" in result
        assert "软件工程" in result

    def test_format_majors_limit_80(self):
        """超过 80 个专业只显示前 80 个。"""
        big_dict = {f"专业{i}" for i in range(100)}
        result = _format_tenant_majors(big_dict)
        assert "专业79" in result
        assert "专业99" not in result


class TestIntentDataclass:
    def test_to_dict_roundtrip(self):
        intent = Intent(
            intent_type="data_query",
            majors=["人工智能"],
            province="广东",
            year=2024,
            score_query=585,
            rank_query=None,
            need_admission_data=True,
            rewritten_query="人工智能录取分数",
        )
        d = intent.to_dict()
        assert d["intent_type"] == "data_query"
        assert d["majors"] == ["人工智能"]
        assert d["year"] == 2024
        assert d["score_query"] == 585
        assert d["need_admission_data"] is True
        assert d["rewritten_query"] == "人工智能录取分数"

    def test_defaults(self):
        intent = Intent()
        assert intent.intent_type == "chitchat"
        assert intent.majors == []
        assert intent.province == "广东"
        assert intent.need_admission_data is False
