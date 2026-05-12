"""Index seed data into Chroma for RAG."""
import asyncio
from sqlalchemy import select
from backend.models import async_session
from backend.models.college import College
from backend.models.admission import AdmissionData
from backend.knowledge_base.chroma_client import index_documents

async def index():
    async with async_session() as db:
        colleges = {str(c.id): c for c in (await db.execute(select(College))).scalars().all()}
        admissions = (await db.execute(select(AdmissionData))).scalars().all()
        docs, metas, ids = [], [], []
        for a in admissions:
            c = colleges.get(str(a.college_id))
            if not c:
                continue
            doc = f"{c.name} {a.major_name} {c.level} {c.province}{c.city} 录取位次{a.min_rank} 分数{a.min_score} {a.subject_requirements} 985:{c.is_985} 211:{c.is_211} {c.intro}"
            docs.append(doc)
            metas.append({"college_id": str(a.college_id), "college_name": c.name, "major_name": a.major_name, "level": c.level, "province": c.province, "city": c.city, "min_rank": a.min_rank, "min_score": a.min_score, "subjects": a.subject_requirements, "source_url": a.source_url})
            ids.append(str(a.id))
        if docs:
            index_documents(docs, metas, ids)
            print(f"Indexed {len(docs)} documents into Chroma.")

if __name__ == "__main__":
    asyncio.run(index())
