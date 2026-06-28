"""Admin consultation workbench — list, detail, follow status, regenerate summary."""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.tenant_context import get_current_tenant, get_current_tenant_user
from models import get_db
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/consultations")
async def list_consultations(
    status: Optional[str] = Query(None),
    period: Optional[str] = Query(None),  # today / 7d / 30d
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """List consultation sessions for the current tenant."""
    stmt = select(ConsultSession).where(ConsultSession.tenant_slug == tenant.slug)

    # Status filter
    if status == "pending":
        stmt = stmt.where(ConsultSession.follow_status == "pending")
    elif status == "processed":
        stmt = stmt.where(ConsultSession.follow_status == "processed")
    elif status == "ignored":
        stmt = stmt.where(ConsultSession.follow_status == "ignored")
    elif status == "no_consult":
        stmt = stmt.where(ConsultSession.consult_started_at.is_(None))

    # Period filter
    if period == "today":
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = stmt.where(ConsultSession.consult_started_at >= start)
    elif period == "7d":
        stmt = stmt.where(ConsultSession.consult_started_at >= datetime.now(timezone.utc) - timedelta(days=7))
    elif period == "30d":
        stmt = stmt.where(ConsultSession.consult_started_at >= datetime.now(timezone.utc) - timedelta(days=30))

    # Search: match username or consult_summary
    if search:
        stmt = stmt.outerjoin(User, ConsultSession.user_id == User.id)
        stmt = stmt.where(
            or_(
                User.username.ilike(f"%{search}%"),
                ConsultSession.consult_summary.ilike(f"%{search}%"),
            )
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate
    stmt = stmt.order_by(ConsultSession.consult_started_at.desc().nullslast()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    # Fetch usernames
    user_ids = list({r.user_id for r in rows if r.user_id})
    usernames = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in user_result.scalars().all():
            usernames[str(u.id)] = u.username

    return {
        "data": [
            {
                "session_id": str(r.id),
                "session_string": r.session_id,
                "student_name": usernames.get(str(r.user_id), "游客") if r.user_id else "游客",
                "province": r.province or "",
                "subjects": r.subjects or "",
                "score": r.score or 0,
                "rank": r.rank,
                "intent_majors": r.intent_majors or [],
                "consult_summary": r.consult_summary or "",
                "consult_started_at": r.consult_started_at.isoformat() if r.consult_started_at else None,
                "follow_status": r.follow_status,
                "follow_note": r.follow_note or "",
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/consultations/stats/summary")
async def consultations_stats(
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """Quick stats for consultation workbench header."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug)
    )).scalar() or 0
    today_new = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug, ConsultSession.consult_started_at >= today_start)
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug, ConsultSession.follow_status == "pending")
    )).scalar() or 0
    processed = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug, ConsultSession.follow_status == "processed")
    )).scalar() or 0
    return {"total": total, "today_new": today_new, "pending": pending, "processed": processed}


@router.get("/consultations/{session_id}")
async def get_consultation_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """Get consultation detail with chat messages."""
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch username
    username = "游客"
    if session.user_id:
        u_result = await db.execute(select(User).where(User.id == session.user_id))
        u = u_result.scalar_one_or_none()
        if u:
            username = u.username

    # Fetch messages
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in msg_result.scalars().all()
    ]

    return {
        "session": {
            "session_id": str(session.id),
            "session_string": session.session_id,
            "student_name": username,
            "province": session.province or "",
            "subjects": session.subjects or "",
            "score": session.score or 0,
            "rank": session.rank,
            "intent_majors": session.intent_majors or [],
            "focus_points": session.focus_points or [],
            "consult_summary": session.consult_summary or "",
            "consult_started_at": session.consult_started_at.isoformat() if session.consult_started_at else None,
            "follow_status": session.follow_status,
            "follow_note": session.follow_note or "",
            "followed_at": session.followed_at.isoformat() if session.followed_at else None,
        },
        "messages": messages,
    }


class FollowStatusUpdate(BaseModel):
    status: str  # pending / processed / ignored
    note: str = ""


@router.patch("/consultations/{session_id}/follow-status")
async def update_follow_status(
    session_id: str,
    body: FollowStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_tenant_user),
):
    """Update follow-up status of a consultation."""
    if body.status not in ("pending", "processed", "ignored"):
        raise HTTPException(status_code=400, detail="Invalid status")
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.follow_status = body.status
    session.follow_note = body.note or None
    if body.status == "processed":
        session.followed_at = datetime.now(timezone.utc)
        session.followed_by = user.user_id
    await db.commit()
    return {"ok": True, "follow_status": session.follow_status}


@router.post("/consultations/{session_id}/regenerate-summary")
async def regenerate_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """Manually trigger summary regeneration."""
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    from services.consult_summary_service import generate_summary
    summary = await generate_summary(session.session_id)
    session.consult_summary = summary
    await db.commit()
    return {"consult_summary": summary}


class SummaryUpdate(BaseModel):
    summary: str


@router.patch("/consultations/{session_id}/summary")
async def update_summary(
    session_id: str,
    body: SummaryUpdate,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_tenant_user),
):
    """Manually edit consultation summary."""
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.consult_summary = body.summary.strip() or None
    await db.commit()
    return {"ok": True, "consult_summary": session.consult_summary or ""}


class FollowNoteUpdate(BaseModel):
    note: str


@router.patch("/consultations/{session_id}/follow-note")
async def update_follow_note(
    session_id: str,
    body: FollowNoteUpdate,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_tenant_user),
):
    """Save follow-up note independently (without changing status)."""
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.follow_note = body.note.strip() or None
    session.followed_at = datetime.now(timezone.utc)
    session.followed_by = user.user_id
    await db.commit()
    return {"ok": True, "follow_note": session.follow_note or ""}
