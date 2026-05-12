"""Run once to load seed data into PostgreSQL."""
import asyncio, json, uuid
from sqlalchemy import select
from backend.models import engine, async_session, init_db
from backend.models.college import College
from backend.models.admission import AdmissionData

async def seed():
    await init_db()
    async with async_session() as db:
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Already seeded, skipping.")
            return
        with open("data/seed/schools.json", encoding="utf-8") as f:
            schools = json.load(f)
        with open("data/seed/scores.json", encoding="utf-8") as f:
            scores = json.load(f)
        name_to_id = {}
        for s in schools:
            c = College(id=uuid.uuid4(), **s)
            db.add(c)
            name_to_id[s["name"]] = c.id
        for r in scores:
            cn = r.pop("college_name")
            db.add(AdmissionData(id=uuid.uuid4(), college_id=name_to_id[cn], **r))
        await db.commit()
        print(f"Seeded {len(schools)} colleges, {len(scores)} admission records.")

if __name__ == "__main__":
    asyncio.run(seed())
