"""Load seed data into PostgreSQL. Runs from data/seed/ (MVP) or data/approved/ (full)."""
import asyncio, json, uuid, sys
from pathlib import Path

from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from backend.models import engine, async_session, init_db
from backend.models.college import College
from backend.models.admission import AdmissionData


async def seed(data_dir: str = "data/seed"):
    await init_db()

    schools_path = Path(data_dir) / "schools.json"
    scores_path = Path(data_dir) / "scores.json"

    if not schools_path.exists() or not scores_path.exists():
        print(f"Missing seed files in {data_dir}")
        return

    async with async_session() as db:
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Already seeded. Clearing and re-seeding...")
            await db.execute(text("DELETE FROM admission_data"))
            await db.execute(text("DELETE FROM recommendations"))
            await db.execute(text("DELETE FROM user_profiles"))
            await db.execute(text("DELETE FROM colleges"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

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
                # Try fuzzy match
                for n, i in name_to_id.items():
                    if cn in n or n in cn:
                        cid = i
                        break
            if not cid:
                print(f"  WARNING: No college match for '{cn}', skipping")
                skipped += 1
                continue
            db.add(AdmissionData(id=uuid.uuid4(), college_id=cid, **r))

        await db.commit()
        print(f"Seeded {len(schools)} colleges, {len(scores)} admission records.")
        if skipped:
            print(f"  Skipped {skipped} records with unmatched college names.")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/seed"
    asyncio.run(seed(data_dir))
