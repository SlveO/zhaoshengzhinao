"""Import SCNU data from data/raw/scnu/*.json into TenantData + ChromaDB."""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select, text
from backend.models import async_session
from backend.tenants.models import TenantData, Tenant
from backend.knowledge.indexer import index_tenant_data

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "scnu"
TENANT_SLUG = "scnu"

DATA_TYPE_MAP = {
    "admissions.json": "admission_score",
    "curriculums.json": "curriculum",
    "employment.json": "employment",
}


async def import_file(tenant_id, filepath, data_type):
    with open(filepath, encoding="utf-8") as f:
        records = json.load(f)

    imported = 0
    errors = []
    async with async_session() as db:
        for r in records:
            try:
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    data_type=data_type,
                    title=r.get("title", f"{r.get('major_name', '')} {r.get('year', '')}"),
                    content=r,
                    year=r.get("year"),
                    province=r.get("province"),
                    extra_meta={
                        "major_name": r.get("major_name", ""),
                        "college": r.get("college", ""),
                    },
                )
                db.add(td)
                await db.commit()
                await index_tenant_data(TENANT_SLUG, td)
                td.indexed_at = datetime.now(timezone.utc)
                await db.commit()
                imported += 1
            except Exception as e:
                errors.append({"record": r.get("title", str(r)[:100]), "error": str(e)})

    return imported, errors


async def main():
    async with async_session() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("SCNU tenant not found — run create_scnu_tenant.py first")
            return
        tenant_id = tenant.id
        print(f"Found tenant: {tenant.name} (slug={tenant.slug})")

    total = 0
    for filename, data_type in DATA_TYPE_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"SKIP {filename} — not found")
            continue
        count, errs = await import_file(tenant_id, str(filepath), data_type)
        total += count
        print(f"{filename}: {count} imported, {len(errs)} errors")
        for e in errs:
            print(f"  ERROR: {e['record']}: {e['error']}")

    print(f"\nTotal: {total} documents imported to SCNU knowledge base")

    async with async_session() as db:
        await db.execute(
            text("""
                UPDATE tenants
                SET config = jsonb_set(config, '{knowledge_base,doc_count}', (:cnt)::text::jsonb)
                WHERE slug = :slug
            """),
            {"cnt": total, "slug": TENANT_SLUG},
        )
        await db.commit()
        print(f"Updated doc_count to {total}")


if __name__ == "__main__":
    asyncio.run(main())
