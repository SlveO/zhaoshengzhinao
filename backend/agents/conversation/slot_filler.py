"""Slot merging and summary utilities — used by the conversation agent."""


def merge_slots(existing: dict, update: dict) -> dict:
    """Merge new slot values into existing, preserving confidence scoring."""
    merged = dict(existing)
    for key in ["score", "subjects", "career_vision", "family_influence"]:
        if update.get(key):
            merged[key] = update[key]
    riasec = merged.get("riasec", {}) or {}
    riasec_update = update.get("riasec_update") or {}
    if isinstance(riasec_update, dict):
        for dim, val in riasec_update.items():
            if val is not None:
                riasec[dim] = round((riasec.get(dim, 5) + val) / 2, 1) if dim in riasec else val
    merged["riasec"] = riasec
    if update.get("values_hint"):
        vals = merged.get("values", [])
        if update["values_hint"] not in vals:
            vals.append(update["values_hint"])
        merged["values"] = vals
    if update.get("region_pref"):
        existing_regions = set(merged.get("region_pref", []))
        existing_regions.update(update["region_pref"])
        merged["region_pref"] = list(existing_regions)
    return merged


def slots_summary(slots: dict) -> str:
    """Human-readable summary of current slots."""
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
