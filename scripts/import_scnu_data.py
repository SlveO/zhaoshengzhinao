"""Import SCNU data from data/raw/scnu/*.json into TenantData + ChromaDB."""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Set up backend as the working directory so all imports match the FastAPI app
_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
# Inside Docker the backend code lives at /app directly, not /app/backend
if not Path(_backend_dir).is_dir():
    _backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _backend_dir)
if Path(_backend_dir).is_dir():
    os.chdir(_backend_dir)

from sqlalchemy import select, text  # noqa: E402
from models import async_session  # noqa: E402
from tenants.models import TenantData, Tenant  # noqa: E402
from knowledge.indexer import index_tenant_data  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "scnu"
TENANT_SLUG = "scnu"

DATA_TYPE_MAP = {
    "admissions.json": "admission_score",
    "curriculums.json": "curriculum",
    "employment.json": "employment",
}


def _make_title(r: dict, data_type: str) -> str:
    """Build a human-readable title from record fields."""
    major = r.get("major_name", "")
    year = r.get("year", "")
    if data_type == "admission_score":
        province = r.get("province", "")
        return f"{major} {year} {province}"
    elif data_type == "curriculum":
        return f"{major} 培养计划"
    elif data_type == "employment":
        return f"{major} {year}届 就业报告"
    return f"{major} {year}".strip()


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
                    title=_make_title(r, data_type),
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
                errors.append({"record": _make_title(r, data_type), "error": str(e)})

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
            {"cnt": str(total), "slug": TENANT_SLUG},
        )
        await db.commit()
        print(f"Updated doc_count to {total}")


if __name__ == "__main__":
    asyncio.run(main())
