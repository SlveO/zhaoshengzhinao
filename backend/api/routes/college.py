from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from models.college import College

router = APIRouter()


@router.get("")
async def list_colleges(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    level: str = Query(None),
    province: str = Query(None),
):
    q = select(College)
    if level:
        q = q.where(College.level == level)
    if province:
        q = q.where(College.province == province)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    colleges = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "code": c.code,
            "type": c.type,
            "level": c.level,
            "province": c.province,
            "city": c.city,
            "is_985": c.is_985,
            "is_211": c.is_211,
            "is_double_first": c.is_double_first,
            "intro": c.intro,
        }
        for c in colleges
    ]


@router.get("/{college_id}")
async def get_college(college_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(College).where(College.id == college_id))
    c = result.scalar_one_or_none()
    if not c:
        return {"error": "not found"}
    return {
        "id": str(c.id),
        "name": c.name,
        "code": c.code,
        "type": c.type,
        "level": c.level,
        "province": c.province,
        "city": c.city,
        "is_985": c.is_985,
        "is_211": c.is_211,
        "is_double_first": c.is_double_first,
        "intro": c.intro,
    }
