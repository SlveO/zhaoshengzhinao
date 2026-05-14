"""Evidence-driven profile building — stores evidence entries, computes confidence, detects blind spots."""
import uuid
from typing import Optional

RIASEC_DIMS = {
    "riasec_R": "动手操作",
    "riasec_I": "研究思考",
    "riasec_A": "艺术创造",
    "riasec_S": "帮助他人",
    "riasec_E": "领导说服",
    "riasec_C": "规范有序",
}

VALUES_CATEGORIES = ["社会贡献", "个人成长", "工作稳定", "薪资水平"]

RIASEC_KEYS = list(RIASEC_DIMS.keys())


class EvidenceAccumulator:
    def __init__(self, seed: Optional[dict] = None):
        self._evidence: dict = {}
        for k in RIASEC_KEYS:
            self._evidence[k] = {"evidence": [], "evidence_count": 0, "confidence": 0.0}
        self._evidence["values"] = {"evidence": [], "evidence_count": 0, "ranked": []}
        self._evidence["region_pref"] = {"regions": []}
        self._evidence["score"] = {"value": None}
        self._evidence["subjects"] = {"value": None}
        self._evidence["engagement"] = {"trust_level": "low", "willingness_to_share": 0.0, "indicators": []}
        if seed:
            self.seed_basics(**seed)

    def seed_basics(self, score: Optional[int] = None, subjects: Optional[str] = None, region: Optional[list] = None):
        if score:
            self._evidence["score"] = {"value": score, "evidence_count": 1, "confidence": 1.0}
        if subjects:
            self._evidence["subjects"] = {"value": subjects, "evidence_count": 1, "confidence": 1.0}
        if region:
            self._evidence["region_pref"]["regions"] = region

    def add_evidence(self, dimension: str, source_turn: int, user_quote: str,
                     inferred_score: int, rationale: str, confidence: float) -> dict:
        item = {
            "id": f"evt_{uuid.uuid4().hex[:8]}",
            "dimension": dimension,
            "source_turn": source_turn,
            "user_quote": user_quote,
            "inferred_value": {"dimension": dimension, "score": inferred_score, "rationale": rationale},
            "confidence": confidence,
        }
        self._evidence[dimension]["evidence"].append(item)
        self._evidence[dimension]["evidence_count"] = len(self._evidence[dimension]["evidence"])
        self._recalc_dimension(dimension)
        return item

    def _recalc_dimension(self, dimension: str):
        items = self._evidence[dimension]["evidence"]
        if not items:
            return
        total_weight = sum(e["confidence"] for e in items)
        if total_weight > 0:
            weighted_score = sum(e["inferred_value"]["score"] * e["confidence"] for e in items) / total_weight
        else:
            weighted_score = sum(e["inferred_value"]["score"] for e in items) / len(items)
        self._evidence[dimension]["score"] = round(weighted_score, 1)
        n = len(items)
        if n == 1:
            agg_conf = items[0]["confidence"]
        else:
            agg_conf = min(0.5 + n * 0.08, 0.95)
        self._evidence[dimension]["confidence"] = round(agg_conf, 2)

    def get_dimension_state(self, dimension: str) -> dict:
        entry = self._evidence.get(dimension, {})
        return {
            "dimension": dimension,
            "label": RIASEC_DIMS.get(dimension, ""),
            "score": entry.get("score"),
            "evidence_count": entry.get("evidence_count", 0),
            "confidence": entry.get("confidence", 0.0),
            "evidence": entry.get("evidence", []),
        }

    def detect_blind_spots(self) -> list[str]:
        hints = []
        for dim_key, label in RIASEC_DIMS.items():
            if self._evidence[dim_key]["evidence_count"] == 0:
                hints.append(dim_key)
        return hints

    def set_engagement(self, trust_level: str, willingness: float, indicators: list[str]):
        self._evidence["engagement"] = {
            "trust_level": trust_level,
            "willingness_to_share": willingness,
            "indicators": indicators,
        }

    def set_values(self, ranked: list[str]):
        self._evidence["values"]["ranked"] = ranked
        self._evidence["values"]["evidence_count"] = len(ranked)

    def export_snapshot(self) -> dict:
        riasec = {}
        for k in RIASEC_KEYS:
            state = self.get_dimension_state(k)
            if state["score"] is not None:
                riasec[k.replace("riasec_", "")] = state["score"]
        return {
            "score": self._evidence["score"].get("value"),
            "subjects": self._evidence["subjects"].get("value"),
            "region_pref": self._evidence["region_pref"].get("regions", []),
            "riasec": riasec,
            "values": self._evidence["values"].get("ranked", []),
            "completeness": compute_completeness(self._evidence),
            "engagement": self._evidence.get("engagement", {}),
        }

    def to_dict(self) -> dict:
        return self._evidence

    @classmethod
    def from_dict(cls, data: dict) -> "EvidenceAccumulator":
        acc = cls()
        for k in RIASEC_KEYS:
            if k in data:
                acc._evidence[k] = data[k]
        for k in ["values", "region_pref", "score", "subjects", "engagement"]:
            if k in data:
                acc._evidence[k] = data[k]
        return acc


def compute_completeness(evidence: dict) -> str:
    riasec_covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
    has_values = evidence.get("values", {}).get("evidence_count", 0) >= 1
    has_region = bool(evidence.get("region_pref", {}).get("regions"))

    if riasec_covered >= 4 and has_values:
        return "L3"
    elif riasec_covered >= 2 and has_region:
        return "L2"
    return "L1"
