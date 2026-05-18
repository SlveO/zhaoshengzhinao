"""Verify SCNU data import — database counts and ChromaDB index status."""
import asyncio
import os
import sys
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

from sqlalchemy import text, select  # noqa: E402
from models import async_session  # noqa: E402
from tenants.models import Tenant  # noqa: E402


async def verify():
    async with async_session() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == "scnu"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("SCNU tenant not found — run create_scnu_tenant.py first")
            return

        print(f"SCNU Tenant: {tenant.name}")
        print(f"  Slug: {tenant.slug}")
        print(f"  Tier: {tenant.subscription_tier}")
        print(f"  Status: {tenant.status}")
        print()

        result = await db.execute(
            text("""
                SELECT data_type, COUNT(*), COUNT(*) FILTER (WHERE indexed_at IS NOT NULL)
                FROM tenant_data
                WHERE tenant_id = :tid
                GROUP BY data_type
                ORDER BY data_type
            """),
            {"tid": tenant.id},
        )

        print(f"{'Data Type':<20s} {'Total':>6s} {'Indexed':>8s}")
        print("-" * 36)
        total_rows = 0
        total_indexed = 0
        for row in result:
            print(f"{row[0]:<20s} {row[1]:>6d} {row[2]:>8d}")
            total_rows += row[1]
            total_indexed += row[2]
        print("-" * 36)
        print(f"{'TOTAL':<20s} {total_rows:>6d} {total_indexed:>8d}")

    # Check ChromaDB
    try:
        from backend.knowledge.client import get_chroma_client
        client = get_chroma_client()
        collection_name = "scnu_colleges"
        try:
            coll = client.get_collection(collection_name)
            count = coll.count()
            print(f"\nChromaDB '{collection_name}' collection: {count} documents")
        except Exception:
            print(f"\nChromaDB '{collection_name}' collection: NOT FOUND")
    except Exception as e:
        print(f"\nChromaDB check skipped (not running?): {e}")

    # Summary
    print()
    if total_rows > 0 and total_indexed > 0:
        print("Data import verified successfully.")
    elif total_rows > 0:
        print("Data imported but indexing incomplete — check ChromaDB.")
    else:
        print("No data imported — run import_scnu_data.py first.")


if __name__ == "__main__":
    asyncio.run(verify())
