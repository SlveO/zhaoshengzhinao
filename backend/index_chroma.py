"""Index seed data into Chroma for RAG. Works both locally and in Docker."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from models import async_session
from models.college import College
from models.admission import AdmissionData
from models.mapping import MajorIndustryMapping
from knowledge_base.chroma_client import index_documents, collection

async def index():
    async with async_session() as db:
        colleges = {str(c.id): c for c in (await db.execute(select(College))).scalars().all()}
        admissions = (await db.execute(select(AdmissionData))).scalars().all()
        mappings = (await db.execute(select(MajorIndustryMapping))).scalars().all()

        major_to_industry = {}
        for m in mappings:
            if m.primary_industries:
                major_to_industry[m.major_name] = m.primary_industries

        docs, metas, ids = [], [], []
        for a in admissions:
            c = colleges.get(str(a.college_id))
            if not c:
                continue
            inds = major_to_industry.get(a.major_name, [])
            ind_str = ", ".join(inds) if inds else ""
            doc = (
                f"{c.name} {a.major_name} {c.level} "
                f"{a.province or c.province}{c.city} "
                f"录取位次{a.min_rank or -1} 分数{a.min_score} "
                f"选科:{a.subject_requirements} "
                f"985:{c.is_985} 211:{c.is_211} 就业方向:{ind_str}"
            )
            docs.append(doc)
            metas.append({
                "college_id": str(a.college_id),
                "college_name": c.name,
                "major_name": a.major_name,
                "level": c.level or "",
                "province": a.province or c.province or "",
                "city": c.city or "",
                "min_rank": a.min_rank or 0,
                "min_score": a.min_score or 0,
                "subjects": a.subject_requirements or "",
                "source_url": a.source_url or "",
                "industries": ind_str,
            })
            ids.append(str(a.id))

        if docs:
            print(f"Indexing {len(docs)} documents in batches...")
            BATCH = 2000
            for i in range(0, len(docs), BATCH):
                index_documents(
                    docs[i:i+BATCH],
                    metas[i:i+BATCH],
                    ids[i:i+BATCH],
                )
                print(f"  {min(i+BATCH, len(docs))}/{len(docs)}")
        print(f"Chroma size: {collection.count()}")

if __name__ == "__main__":
    asyncio.run(index())
