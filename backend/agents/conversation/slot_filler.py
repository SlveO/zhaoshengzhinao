"""Backwards-compatible wrapper — delegates to EvidenceAccumulator."""
from agents.conversation.evidence_accumulator import EvidenceAccumulator


def merge_slots(existing: dict, update: dict) -> dict:
    """DEPRECATED: Used only for old code paths. New code should use EvidenceAccumulator directly."""
    acc = EvidenceAccumulator.from_dict(existing) if existing else EvidenceAccumulator()
    riasec_update = update.get("riasec_update") or {}
    if isinstance(riasec_update, dict):
        for dim, val in riasec_update.items():
            key = f"riasec_{dim}"
            if val is not None and key in acc.to_dict():
                acc.add_evidence(key, 0, "", int(val), "keyword fallback", 0.3)
    if update.get("values_hint"):
        existing_vals = acc.to_dict().get("values", {}).get("ranked", [])
        if update["values_hint"] not in existing_vals:
            existing_vals.append(update["values_hint"])
        acc.set_values(existing_vals)
    if update.get("region_pref"):
        existing_regions = set(acc.to_dict().get("region_pref", {}).get("regions", []))
        existing_regions.update(update["region_pref"])
        acc.to_dict()["region_pref"]["regions"] = list(existing_regions)
    if update.get("score"):
        acc.seed_basics(score=update["score"])
    if update.get("subjects"):
        acc.seed_basics(subjects=update["subjects"])
    snap = acc.export_snapshot()
    # Flatten to old slot format for backwards compat
    slots = {
        "score": snap.get("score"),
        "subjects": snap.get("subjects"),
        "region_pref": snap.get("region_pref", []),
        "riasec": snap.get("riasec", {}),
        "values": snap.get("values", []),
    }
    return slots


def slots_summary(slots: dict) -> str:
    """Human-readable summary of current profile."""
    lines = []
    if slots.get("score"):
        lines.append(f"分数: {slots['score']}")
    if slots.get("subjects"):
        lines.append(f"选科: {slots['subjects']}")
    riasec = slots.get("riasec", {}) or {}
    if riasec:
        dim_names = {"R": "动手操作", "I": "研究思考", "A": "艺术创造", "S": "帮助他人", "E": "领导说服", "C": "规范有序"}
        top = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:2]
        lines.append("兴趣倾向: " + ", ".join(f"{dim_names.get(k, k)}({v})" for k, v in top))
    if slots.get("values"):
        lines.append(f"价值观: {' > '.join(slots['values'])}")
    if slots.get("region_pref"):
        lines.append(f"地域偏好: {', '.join(slots['region_pref'])}")
    return "\n".join(lines) if lines else "尚无信息"
