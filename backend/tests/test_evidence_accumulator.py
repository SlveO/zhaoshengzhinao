import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.conversation.evidence_accumulator import (
    EvidenceAccumulator, RIASEC_DIMS, VALUES_CATEGORIES, compute_completeness
)


class TestEvidenceAccumulator:
    def test_add_evidence_creates_dimension(self):
        acc = EvidenceAccumulator()
        evt = acc.add_evidence(
            dimension="riasec_I",
            source_turn=3,
            user_quote="我特别喜欢自己查资料研究不明白的东西",
            inferred_score=8,
            rationale="学生表达了对独立研究的明确兴趣",
            confidence=0.6,
        )
        assert evt["id"].startswith("evt_")
        assert evt["dimension"] == "riasec_I"
        state = acc.get_dimension_state("riasec_I")
        assert state["evidence_count"] == 1
        assert state["score"] == 8.0
        assert state["confidence"] == 0.6

    def test_multiple_evidence_weights_average(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "research stuff", 8, "reason", 0.6)
        acc.add_evidence("riasec_I", 3, "analyzes math", 6, "reason", 0.8)
        state = acc.get_dimension_state("riasec_I")
        assert state["evidence_count"] == 2
        # Weighted: (8*0.6 + 6*0.8) / (0.6+0.8) = (4.8+4.8)/1.4 = 6.86
        assert round(state["score"], 1) == 6.9
        assert state["confidence"] > 0.6

    def test_detect_blind_spots(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "x", 7, "r", 0.5)
        acc.add_evidence("riasec_S", 2, "y", 8, "r", 0.5)
        blind = acc.detect_blind_spots()
        assert "riasec_R" in blind
        assert "riasec_A" in blind
        assert "riasec_E" in blind
        assert "riasec_C" in blind
        assert "riasec_I" not in blind
        assert "riasec_S" not in blind

    def test_export_snapshot(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "x", 7, "r", 0.5)
        acc.add_evidence("riasec_S", 2, "y", 8, "r", 0.5)
        acc.seed_basics(score=620, subjects="物化生", region=["广东"])
        snap = acc.export_snapshot()
        assert snap["score"] == 620
        assert snap["subjects"] == "物化生"
        assert snap["region_pref"] == ["广东"]
        assert "I" in snap["riasec"]
        assert "S" in snap["riasec"]
        assert snap["completeness"] == "L2"


class TestComputeCompleteness:
    def test_l1_basic(self):
        evidence = make_evidence(riasec_covered=0, has_values=False, has_region=False)
        assert compute_completeness(evidence) == "L1"

    def test_l2_moderate(self):
        evidence = make_evidence(riasec_covered=2, has_values=False, has_region=True)
        assert compute_completeness(evidence) == "L2"

    def test_l3_deep(self):
        evidence = make_evidence(riasec_covered=4, has_values=True, has_region=True)
        assert compute_completeness(evidence) == "L3"


def make_evidence(riasec_covered, has_values, has_region):
    riasec_keys = ["riasec_R", "riasec_I", "riasec_A", "riasec_S", "riasec_E", "riasec_C"]
    ev = {}
    for i, k in enumerate(riasec_keys):
        ev[k] = {"evidence_count": 1 if i < riasec_covered else 0, "confidence": 0.7 if i < riasec_covered else 0}
    ev["values"] = {"evidence_count": 2 if has_values else 0}
    ev["region_pref"] = {"regions": ["广东"]} if has_region else {}
    return ev
