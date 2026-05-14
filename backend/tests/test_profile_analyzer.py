import pytest, json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.conversation.profile_analyzer import (
    build_analysis_prompt, parse_analysis_response
)
from agents.conversation.evidence_accumulator import EvidenceAccumulator


class TestParseAnalysisResponse:
    def test_parse_valid_evidence_extraction(self):
        response_text = json.dumps({
            "new_evidence": [
                {
                    "dimension": "riasec_I",
                    "user_quote": "我喜欢研究数学题",
                    "inferred_score": 8,
                    "rationale": "学生表达了对分析和研究的兴趣",
                    "confidence": 0.75
                }
            ],
            "values_hint": "个人成长",
            "region_mentioned": None,
            "engagement_assessment": {
                "trust_level": "medium",
                "willingness_to_share": 0.6,
                "indicators": ["学生主动分享了个人经历"]
            }
        })
        result = parse_analysis_response(response_text)
        assert len(result["new_evidence"]) == 1
        assert result["new_evidence"][0]["dimension"] == "riasec_I"
        assert result["engagement_assessment"]["trust_level"] == "medium"

    def test_parse_empty_response(self):
        response_text = json.dumps({
            "new_evidence": [],
            "values_hint": None,
            "region_mentioned": None,
            "engagement_assessment": {
                "trust_level": "low",
                "willingness_to_share": 0.3,
                "indicators": []
            }
        })
        result = parse_analysis_response(response_text)
        assert len(result["new_evidence"]) == 0

    def test_parse_malformed_json_returns_empty(self):
        result = parse_analysis_response("not valid json {{")
        assert len(result["new_evidence"]) == 0
        assert result["engagement_assessment"]["trust_level"] == "low"

    def test_parse_json_inside_markdown(self):
        inner = json.dumps({"new_evidence": [], "values_hint": None, "region_mentioned": "广东",
                            "engagement_assessment": {"trust_level": "low", "willingness_to_share": 0.2, "indicators": []}})
        response_text = f"```json\n{inner}\n```"
        result = parse_analysis_response(response_text)
        assert result["region_mentioned"] == "广东"


class TestBuildAnalysisPrompt:
    def test_includes_blind_spot_hints(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "x", 7, "r", 0.5)
        blind_spots = acc.detect_blind_spots()
        prompt = build_analysis_prompt("用户说的话...", "AI的回复...", acc.to_dict(), blind_spots)
        assert "用户说的话" in prompt
        assert "riasec_R" in prompt
