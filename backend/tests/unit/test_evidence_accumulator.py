"""Unit tests for EvidenceAccumulator — actual API."""
import pytest
from agents.conversation.evidence_accumulator import (
    EvidenceAccumulator, compute_completeness,
)

RIASEC_KEYS = ["riasec_R", "riasec_I", "riasec_A", "riasec_S", "riasec_E", "riasec_C"]


def _empty_acc():
    return EvidenceAccumulator()


def _add(d, name, score=6, turn=1, conf=0.6):
    """Shorthand: add_evidence with minimal required positional args."""
    return d.add_evidence(d, name, turn, f"quote_{name}", score, f"rationale_{name}", conf)


class TestInitialState:
    def test_all_dims_empty(self):
        acc = _empty_acc()
        d = acc.to_dict()
        for key in RIASEC_KEYS:
            assert d[key]["evidence_count"] == 0
            assert d[key]["confidence"] == 0.0

    def test_completeness_is_L1_initially(self):
        snap = _empty_acc().export_snapshot()
        assert snap["completeness"] == "L1"


class TestConfidence:
    def test_never_exceeds_095(self):
        acc = _empty_acc()
        for i in range(20):
            acc.add_evidence("riasec_R", i + 1, f"q_{i}", 8, f"r_{i}", 0.9)
        assert acc.to_dict()["riasec_R"]["confidence"] <= 0.95

    def test_increases_with_more_evidence(self):
        acc = _empty_acc()
        acc.add_evidence("riasec_R", 1, "q1", 7, "r1", 0.5)
        first = acc.to_dict()["riasec_R"]["confidence"]
        acc.add_evidence("riasec_R", 2, "q2", 8, "r2", 0.5)
        assert acc.to_dict()["riasec_R"]["confidence"] > first


class TestBlindSpots:
    def test_detects_unexplored(self):
        acc = _empty_acc()
        acc.add_evidence("riasec_R", 1, "q1", 8, "r1", 0.6)
        acc.add_evidence("riasec_I", 2, "q2", 7, "r2", 0.6)
        acc.add_evidence("riasec_A", 3, "q3", 6, "r3", 0.6)
        blinds = acc.detect_blind_spots()
        for dim in ["riasec_S", "riasec_E", "riasec_C"]:
            assert dim in blinds

    def test_no_blind_spots_when_all_covered(self):
        acc = _empty_acc()
        for key in RIASEC_KEYS:
            acc.add_evidence(key, 1, "q", 7, "r", 0.6)
        assert acc.detect_blind_spots() == []


class TestCompleteness:
    def test_L1_to_L2(self):
        acc = _empty_acc()
        acc.add_evidence("riasec_R", 1, "q1", 7, "r1", 0.6)
        acc.add_evidence("riasec_I", 2, "q2", 6, "r2", 0.6)
        acc._evidence["region_pref"]["regions"] = ["广东"]
        assert acc.export_snapshot()["completeness"] == "L2"

    def test_L2_to_L3(self):
        acc = _empty_acc()
        acc.add_evidence("riasec_R", 1, "q1", 7, "r1", 0.6)
        acc.add_evidence("riasec_I", 2, "q2", 6, "r2", 0.6)
        acc.add_evidence("riasec_A", 3, "q3", 5, "r3", 0.6)
        acc.add_evidence("riasec_S", 4, "q4", 6, "r4", 0.6)
        acc.set_values(["社会贡献"])
        assert acc.export_snapshot()["completeness"] == "L3"


class TestValues:
    def test_set_values(self):
        acc = _empty_acc()
        acc.set_values(["社会贡献", "个人成长"])
        vals = acc.to_dict()["values"]["ranked"]
        assert vals == ["社会贡献", "个人成长"]

    def test_overwrite_values(self):
        acc = _empty_acc()
        acc.set_values(["社会贡献"])
        acc.set_values(["薪资水平", "个人成长"])
        assert acc.to_dict()["values"]["ranked"] == ["薪资水平", "个人成长"]


class TestSnapshot:
    def test_contains_expected_keys(self):
        acc = _empty_acc()
        acc.add_evidence("riasec_R", 1, "q1", 7, "r1", 0.6)
        acc.set_values(["社会贡献"])
        acc._evidence["region_pref"]["regions"] = ["广东"]
        snap = acc.export_snapshot()
        for k in ["riasec", "values", "completeness", "score", "subjects"]:
            assert k in snap
