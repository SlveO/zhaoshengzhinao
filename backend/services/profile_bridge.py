"""Profile Bridge - wire C-end LLM extraction results into session_profiles table + JSON backup.

Called from miniapp.py after each SSE response completes. Extraction fires every 3 turns.
Bridge failures MUST NOT block the SSE response - all operations are try/except guarded.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func

from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage
from tenants.models import SessionProfile
from core.event_writer import write_event
from services.cend_profile_analyzer import (
    analyze_cend_turn,
    merge_extraction_results,
    CendExtractionResult,
    RIASEC_KEYS,
)
from services.consult_service import update_session_profile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "extracted_profiles"
)


def _compute_confidence(result: CendExtractionResult) -> dict:
    """Derive a confidence score from extraction completeness.

    Returns a dict with per-layer confidence suitable for SessionProfile.confidence_json.
    """
    riasec_count = sum(1 for v in result.riasec.values() if v > 0)
    basic_count = sum(1 for v in result.basic.values() if v)
    has_values = 1 if result.values else 0
    has_concerns = 1 if result.concerns else 0
    has_interests = 1 if any(result.interests.get(k, []) for k in ("preferred_subjects", "strong_subjects", "hobbies")) else 0

    layers_filled = basic_count + has_interests + has_concerns + riasec_count + has_values
    # Max possible: basic(3) + interests(1) + concerns(1) + riasec(6) + values(1) = 12
    overall = round(min(layers_filled / 12, 1.0), 2)

    return {
        "overall": overall,
        "basic": round(basic_count / 3, 2),
        "interests": 1.0 if has_interests else 0.0,
        "concerns": 1.0 if has_concerns else 0.0,
        "riasec": round(riasec_count / 6, 2),
        "values": 1.0 if has_values else 0.0,
        "completeness": result.completeness,
    }


def _ensure_backup_dir() -> None:
    """Create the JSON backup directory if it doesn't exist."""
    os.makedirs(_JSON_BACKUP_DIR, exist_ok=True)


def _dict_to_extraction_result(data: Optional[dict]) -> CendExtractionResult:
    """Convert a profile_json dict (from DB/backup) into a CendExtractionResult."""
    if not data or not isinstance(data, dict):
        return CendExtractionResult()

    result = CendExtractionResult()

    basic = data.get("basic", {})
    if isinstance(basic, dict):
        if basic.get("province"):
            result.basic["province"] = basic["province"]
        if basic.get("subject_type"):
            result.basic["subject_type"] = basic["subject_type"]
        if basic.get("score"):
            result.basic["score"] = basic["score"]

    interests = data.get("interests", {})
    if isinstance(interests, dict):
        for key in ("preferred_subjects", "strong_subjects", "hobbies"):
            val = interests.get(key, [])
            if isinstance(val, list):
                result.interests[key] = [str(v) for v in val if v]

    concerns = data.get("concerns", [])
    if isinstance(concerns, list):
        result.concerns = [str(c) for c in concerns if c]

    riasec = data.get("riasec", {})
    if isinstance(riasec, dict):
        for k in RIASEC_KEYS:
            v = riasec.get(k, 0)
            try:
                vi = int(v)
                if 1 <= vi <= 10:
                    result.riasec[k] = vi
            except (ValueError, TypeError):
                pass

    values = data.get("values", [])
    if isinstance(values, list):
        result.values = [str(v) for v in values if v]

    region = data.get("region_pref", {})
    if isinstance(region, dict):
        if region.get("province"):
            result.region_pref["province"] = region["province"]
        if region.get("city"):
            result.region_pref["city"] = region["city"]

    extra = data.get("extra", {})
    if isinstance(extra, dict):
        result.extra = dict(extra)

    result.completeness = data.get("completeness", "L1")
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_chat_message_count(session_id: str) -> int:
    """Count user messages for a session from the ChatMessage table."""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "user",
                )
            )
            count = result.scalar() or 0
            return count
    except Exception as exc:
        logger.error(f"get_chat_message_count failed for session={session_id}: {exc}")
        return 0


async def should_extract(session_id: str) -> bool:
    """Return True if user message count > 0 AND count % 3 == 0 (every 3rd turn).

    get_chat_message_count handles its own exceptions internally, so no
    try/except is needed here.
    """
    count = await get_chat_message_count(session_id)
    return count > 0 and count % 3 == 0


async def load_existing_profile_json(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Optional[dict]:
    """Load existing SessionProfile.profile_json from the database.

    Args:
        tenant_id: UUID of the tenant.
        session_id: UUID of the consult session (ConsultSession.id, not session_id string).

    Returns:
        The profile_json dict if found, None otherwise.
    """
    try:
        async with async_session() as db:
            result = await db.execute(
                select(SessionProfile.profile_json).where(
                    SessionProfile.tenant_id == tenant_id,
                    SessionProfile.session_id == session_id,
                )
            )
            row = result.first()
            if row:
                return row[0] if isinstance(row[0], dict) else {}
            return None
    except Exception as exc:
        logger.error(
            f"load_existing_profile_json failed for tenant={tenant_id} session={session_id}: {exc}"
        )
        return None


async def bridge_profile_to_session_profiles(
    session: ConsultSession,
    tenant_id: uuid.UUID,
    user_content: str,
    assistant_content: str,
) -> bool:
    """Main bridge: extract profile from turn, merge into session_profiles + JSON backup.

    This function must NEVER raise - failures are logged and swallowed so the
    SSE response stream is not blocked.

    Steps:
        a. Load existing profile_json from session_profiles table.
        b. Call analyze_cend_turn to extract new data.
        c. Merge existing + new extraction results.
        d. If nothing was extracted -> return False.
        e. Update consult_sessions basic fields (province, subject_type, score, intent_majors).
        f. Upsert session_profiles row.
        g. Write JSON backup to data/extracted_profiles/{session_id}.json.
        h. Write analytics event "profile_extracted".

    Returns:
        True if profile was updated, False otherwise.
    """
    session_uuid = session.id  # ConsultSession primary key (UUID)
    session_id_str = session.session_id  # string session_id for chat messages / consult_service

    try:
        # --- a. Load existing profile from session_profiles ---
        existing_json = await load_existing_profile_json(tenant_id, session_uuid) or {}

        # --- b. Extract new profile data from the turn ---
        new_extraction = await analyze_cend_turn(
            user_msg=user_content,
            ai_reply=assistant_content,
            existing_profile=existing_json,
        )

        # --- c. Merge with existing ---
        existing_result = _dict_to_extraction_result(existing_json)
        merged_result = merge_extraction_results(existing_result, new_extraction)

        # --- d. Nothing extracted -> early return ---
        if not merged_result.has_any_data():
            return False

        merged_json = merged_result.to_profile_json()

        # --- e. Update consult_sessions basic fields ---
        # Note: province/subjects/score/rank come from the mini-app form, not from AI extraction.
        # Only intent_majors (derived from preferred_subjects) is written here.
        consult_updates = {}
        if merged_result.interests.get("preferred_subjects"):
            consult_updates["intent_majors"] = merged_result.interests.get("preferred_subjects", [])[:10]
        if consult_updates:
            try:
                await update_session_profile(session_id_str, consult_updates)
            except Exception as exc:
                logger.error(f"update_session_profile failed for session={session_id_str}: {exc}")

        # --- f. Upsert session_profiles row ---
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(SessionProfile).where(
                        SessionProfile.tenant_id == tenant_id,
                        SessionProfile.session_id == session_uuid,
                    )
                )
                profile_row = result.scalar_one_or_none()

                if profile_row:
                    profile_row.profile_json = merged_json
                    profile_row.confidence_json = _compute_confidence(merged_result)
                    profile_row.completeness = merged_result.completeness
                else:
                    profile_row = SessionProfile(
                        tenant_id=tenant_id,
                        session_id=session_uuid,
                        user_id=session.user_id,
                        profile_json=merged_json,
                        confidence_json=_compute_confidence(merged_result),
                        completeness=merged_result.completeness,
                    )
                    db.add(profile_row)

                await db.commit()
        except Exception as exc:
            logger.error(f"session_profiles upsert failed for session={session_uuid}: {exc}")

        # --- g. Write JSON backup ---
        try:
            _ensure_backup_dir()
            backup_path = os.path.join(_JSON_BACKUP_DIR, f"{session_uuid}.json")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(merged_json, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"JSON backup write failed for session={session_uuid}: {exc}")

        # --- h. Write analytics event ---
        try:
            await write_event(
                tenant_id=tenant_id,
                event_type="profile_extracted",
                user_id=session.user_id,
                session_id=session_uuid,
                payload={
                    "completeness": merged_result.completeness,
                    "turn_count": await get_chat_message_count(session_id_str),
                },
            )
        except Exception as exc:
            logger.error(f"write_event profile_extracted failed for session={session_uuid}: {exc}")

        return True

    except Exception as exc:
        logger.error(
            f"bridge_profile_to_session_profiles failed for session={session_id_str}: {exc}",
            exc_info=True,
        )
        return False
