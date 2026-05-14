"""Load seed data into PostgreSQL. All data types from data/ directory."""
import asyncio, json, uuid, sys
from pathlib import Path

from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from backend.models import engine, async_session, init_db
from backend.models.college import College
from backend.models.admission import AdmissionData
from backend.models.industry import IndustryAnalysis
from backend.models.mapping import MajorIndustryMapping


async def seed_colleges_scores(db, data_dir: str):
    """Import colleges and admission scores."""
    schools_path = Path(data_dir) / "schools.json"
    scores_path = Path(data_dir) / "scores.json"

    if not schools_path.exists() or not scores_path.exists():
        print(f"Missing seed files in {data_dir}")
        return

    with open(schools_path, encoding="utf-8") as f:
        schools = json.load(f)
    with open(scores_path, encoding="utf-8") as f:
        scores = json.load(f)

    name_to_id = {}
    for s in schools:
        c = College(id=uuid.uuid4(), **s)
        db.add(c)
        name_to_id[s["name"]] = c.id

    skipped = 0
    for r in scores:
        cn = r.pop("college_name", "")
        cid = name_to_id.get(cn)
        if not cid:
            for n, i in name_to_id.items():
                if cn in n or n in cn:
                    cid = i
                    break
        if not cid:
            skipped += 1
            continue
        db.add(AdmissionData(id=uuid.uuid4(), college_id=cid, **r))

    await db.commit()
    print(f"Colleges: {len(schools)}, Admissions: {len(scores)}"
          + (f" (skipped {skipped})" if skipped else ""))


async def seed_industries(db, data_dir: str):
    """Import industry analysis data."""
    path = Path(data_dir) / "industries.json"
    if not path.exists():
        print("No industries.json found, skipping.")
        return

    with open(path, encoding="utf-8") as f:
        industries = json.load(f)

    for ind in industries:
        # Convert list/dict fields for JSONB
        for field in ("popular_positions", "pros", "cons",
                       "insider_reviews", "related_majors"):
            if not isinstance(ind.get(field), (list, dict)):
                ind[field] = []

        db.add(IndustryAnalysis(id=uuid.uuid4(), **ind))

    await db.commit()
    print(f"Industries: {len(industries)}")


async def seed_mappings(db, data_dir: str):
    """Import major-industry mappings."""
    path = Path(data_dir) / "major_industry_mapping.json"
    if not path.exists():
        print("No major_industry_mapping.json found, skipping.")
        return

    with open(path, encoding="utf-8") as f:
        mappings = json.load(f)

    for m in mappings:
        for field in ("primary_industries", "secondary_industries",
                       "typical_positions"):
            if not isinstance(m.get(field), list):
                m[field] = []
        if not isinstance(m.get("salary_range"), dict):
            m["salary_range"] = {}

        db.add(MajorIndustryMapping(id=uuid.uuid4(), **m))

    await db.commit()
    print(f"Major-industry mappings: {len(mappings)}")


async def seed(data_dir: str = "data/seed"):
    await init_db()

    async with async_session() as db:
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Already seeded. Clearing and re-seeding...")
            for table in ("major_industry_mapping", "industry_analysis",
                           "admission_data", "recommendations",
                           "user_profiles", "colleges", "users"):
                await db.execute(
                    text(f"DELETE FROM {table}"))
            await db.commit()

        await seed_colleges_scores(db, data_dir)

        # Try approved/ dir first for industry/mapping (full data)
        approved = Path(data_dir).parent / "approved"
        await seed_industries(db, str(approved) if (approved / "industries.json").exists() else data_dir)
        await seed_mappings(db, str(approved) if (approved / "major_industry_mapping.json").exists() else data_dir)


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/seed"
    asyncio.run(seed(data_dir))
