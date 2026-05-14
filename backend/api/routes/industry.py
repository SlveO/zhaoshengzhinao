"""Industry analysis and major-industry mapping API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from models.industry import IndustryAnalysis
from models.mapping import MajorIndustryMapping

router = APIRouter()


@router.get("/industries")
async def list_industries(
    db: AsyncSession = Depends(get_db),
    year: int = Query(None),
):
    """List all industry analysis records, optionally filtered by year."""
    q = select(IndustryAnalysis)
    if year:
        q = q.where(IndustryAnalysis.year == year)
    q = q.order_by(IndustryAnalysis.avg_annual_salary.desc())
    result = await db.execute(q)
    industries = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "industry_name": i.industry_name,
            "industry_code": i.industry_code,
            "year": i.year,
            "avg_annual_salary": i.avg_annual_salary,
            "salary_growth_rate": i.salary_growth_rate,
            "employment_demand_index": i.employment_demand_index,
            "industry_growth_rate": i.industry_growth_rate,
            "entry_difficulty": i.entry_difficulty,
            "popular_positions": i.popular_positions,
            "career_path": i.career_path,
            "pros": i.pros,
            "cons": i.cons,
            "related_majors": i.related_majors,
            "outlook": i.outlook,
        }
        for i in industries
    ]


@router.get("/mappings")
async def list_mappings(
    db: AsyncSession = Depends(get_db),
    major_name: str = Query(None),
):
    """List major-industry mappings, optionally filtered by major."""
    q = select(MajorIndustryMapping)
    if major_name:
        q = q.where(MajorIndustryMapping.major_name == major_name)
    result = await db.execute(q)
    mappings = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "major_name": m.major_name,
            "primary_industries": m.primary_industries,
            "secondary_industries": m.secondary_industries,
            "typical_positions": m.typical_positions,
            "salary_range": m.salary_range,
        }
        for m in mappings
    ]


@router.get("/industries/by-major")
async def industries_by_major(
    major_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get industry information for a specific major."""
    # Find mapping for this major
    result = await db.execute(
        select(MajorIndustryMapping).where(
            MajorIndustryMapping.major_name == major_name
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        return {"error": "not found", "major_name": major_name}

    # Get industry details
    industries = []
    for ind_name in mapping.primary_industries + mapping.secondary_industries:
        result = await db.execute(
            select(IndustryAnalysis).where(
                IndustryAnalysis.industry_name == ind_name,
                IndustryAnalysis.year == 2024,
            )
        )
        ind = result.scalar_one_or_none()
        if ind:
            industries.append({
                "industry_name": ind.industry_name,
                "avg_annual_salary": ind.avg_annual_salary,
                "entry_difficulty": ind.entry_difficulty,
                "outlook": ind.outlook,
                "popular_positions": ind.popular_positions,
            })

    return {
        "major_name": major_name,
        "typical_positions": mapping.typical_positions,
        "salary_range": mapping.salary_range,
        "industries": industries,
    }
