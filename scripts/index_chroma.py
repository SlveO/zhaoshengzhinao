"""Index seed data into Chroma for RAG."""
import asyncio
from collections import defaultdict
from sqlalchemy import select
from backend.models import async_session
from backend.models.college import College
from backend.models.admission import AdmissionData
from backend.models.industry import IndustryAnalysis
from backend.models.mapping import MajorIndustryMapping
from backend.knowledge_base.chroma_client import index_documents, collection

async def index():
    async with async_session() as db:
        colleges = {str(c.id): c for c in (await db.execute(select(College))).scalars().all()}
        admissions = (await db.execute(select(AdmissionData))).scalars().all()

        # Build major → industry lookup for enrichment
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

            # Enriched document text for semantic search
            industry_info = ""
            industries = major_to_industry.get(a.major_name, [])
            if industries:
                industry_info = " 就业方向:" + " ".join(industries)

            doc = (
                f"{c.name} {a.major_name} {c.level} "
                f"{c.province}{c.city} "
                f"录取位次{a.min_rank or '未知'} 分数{a.min_score} "
                f"选科:{a.subject_requirements} "
                f"985:{c.is_985} 211:{c.is_211} "
                f"{industry_info} "
                f"{c.intro}"
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
                "industries": ", ".join(industries) if industries else "",
            })
            ids.append(str(a.id))

        if docs:
            print(f"Preparing to index {len(docs)} documents...")
            # Batch indexing to avoid memory issues with 64K docs
            BATCH = 10000
            for i in range(0, len(docs), BATCH):
                batch_docs = docs[i:i+BATCH]
                batch_metas = metas[i:i+BATCH]
                batch_ids = ids[i:i+BATCH]
                index_documents(batch_docs, batch_metas, batch_ids)
                print(f"  Batch {i//BATCH + 1}: {i+len(batch_docs)}/{len(docs)} indexed")

        print(f"Chroma collection size: {collection.count()} documents")

if __name__ == "__main__":
    asyncio.run(index())

