"""Import comprehensive SCNU consulting knowledge into TenantData + ChromaDB.

This complements raw admissions/curriculum/employment data with high-frequency
student consulting facts: school profile, campuses, admissions policies, fees,
financial aid, transfer restrictions, health requirements, and contact channels.
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

from sqlalchemy import select, text  # noqa: E402

from knowledge.indexer import index_tenant_data  # noqa: E402
from models import async_session  # noqa: E402
from tenants.models import Tenant, TenantData  # noqa: E402

TENANT_SLUG = "scnu"
DATASET_KEY = "scnu_comprehensive_knowledge_v2026_05_23"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "approved" / "scnu_comprehensive_knowledge.json"


def _title(record: dict) -> str:
    return f"华南师范大学 {record.get('category', '')} - {record.get('topic', '')}".strip()


async def import_knowledge(replace: bool = True) -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Knowledge file not found: {DATA_FILE}")

    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    async with async_session() as db:
        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise RuntimeError("SCNU tenant not found. Run scripts/create_scnu_tenant.py first.")

        if replace:
            try:
                client = __import__("knowledge.client", fromlist=["get_chroma_client"]).get_chroma_client()
                collection = client.get_or_create_collection(f"{TENANT_SLUG}_colleges")
                collection.delete(where={"dataset": DATASET_KEY})
            except Exception:
                pass
            await db.execute(
                text(
                    """
                    DELETE FROM tenant_data
                    WHERE tenant_id = :tenant_id
                      AND data_type = 'campus_life'
                      AND extra_meta->>'dataset' = :dataset
                    """
                ),
                {"tenant_id": tenant.id, "dataset": DATASET_KEY},
            )
            await db.commit()

        imported = 0
        errors = []
        for record in records:
            try:
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    data_type="campus_life",
                    title=_title(record),
                    content=record,
                    year=2025,
                    province="广东",
                    source_url=record.get("source_url", ""),
                    extra_meta={
                        "dataset": DATASET_KEY,
                        "category": record.get("category", ""),
                        "topic": record.get("topic", ""),
                        "source_title": record.get("source_title", ""),
                        "source_url": record.get("source_url", ""),
                    },
                )
                db.add(td)
                await db.commit()
                await index_tenant_data(TENANT_SLUG, td)
                td.indexed_at = datetime.now(timezone.utc)
                await db.commit()
                imported += 1
            except Exception as exc:
                errors.append({"title": _title(record), "error": str(exc)})

        await db.execute(
            text(
                """
                UPDATE tenants
                SET config = jsonb_set(
                    jsonb_set(config, '{knowledge_base,last_updated}', to_jsonb(CAST(:updated_at AS text)), true),
                    '{knowledge_base,scnu_comprehensive_docs}', (:count)::text::jsonb,
                    true
                )
                WHERE id = :tenant_id
                """
            ),
            {
                "tenant_id": tenant.id,
                "count": str(imported),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await db.commit()

    return {"imported": imported, "errors": errors, "dataset": DATASET_KEY}


async def main():
    result = await import_knowledge(replace=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
