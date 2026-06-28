"""Import SCNU International Business College RAG knowledge base into TenantData + ChromaDB.

Handles the new RAG knowledge base format with:
- metadata: project info
- knowledge_base: array of 30 self-contained chunks (KB001-KB030)
- faq_pairs: 5 high-frequency FAQ pairs with related_chunks references
- rag_config: retrieval/generation configuration

Each chunk is stored as a TenantData record (data_type="campus_life") and indexed
into the tenant's ChromaDB collection for semantic retrieval.
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
# Inside Docker the backend code lives at /app directly, not /app/backend
if not Path(_backend_dir).is_dir():
    _backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _backend_dir)
if Path(_backend_dir).is_dir():
    os.chdir(_backend_dir)

from sqlalchemy import select, text  # noqa: E402

from knowledge.indexer import index_tenant_data, reindex_tenant  # noqa: E402
from models import async_session  # noqa: E402
from tenants.models import Tenant, TenantData  # noqa: E402

TENANT_SLUG = "scnu"
DATASET_KEY = "scnu_ibc_rag_knowledge_base_v2026_06_28"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "approved" / "scnu_ibc_rag_knowledge_base.json"


def _chunk_title(chunk: dict) -> str:
    return f"华师国际本科 {chunk.get('category', '')} - {chunk.get('sub_category', '')}".strip()


def _faq_title(faq: dict) -> str:
    q = faq.get("question", "")
    return f"华师国际本科 FAQ - {q[:60]}"


async def _cleanup_all(db, tenant_id) -> dict:
    """Thoroughly clean all local dev data: knowledge base + consultation + chat.

    Returns a dict with cleanup counts.
    """
    cleanup = {}

    # 1. Drop all ChromaDB collections (scnu_colleges + legacy colleges_majors + any others)
    try:
        from knowledge.client import get_chroma_client
        client = get_chroma_client()
        for coll_name in [f"{TENANT_SLUG}_colleges", "colleges_majors"]:
            try:
                client.delete_collection(coll_name)
                cleanup[f"chroma_{coll_name}"] = "dropped"
            except Exception:
                cleanup[f"chroma_{coll_name}"] = "not_found"
    except Exception as e:
        cleanup["chroma_error"] = str(e)

    # 2. Clean tenant_data (ALL knowledge base records)
    result = await db.execute(
        text("DELETE FROM tenant_data WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    cleanup["tenant_data_deleted"] = result.rowcount
    await db.commit()

    # 3. Clean consult_sessions (user consultation data)
    result = await db.execute(
        text("DELETE FROM consult_sessions WHERE tenant_slug = :slug"),
        {"slug": TENANT_SLUG},
    )
    cleanup["consult_sessions_deleted"] = result.rowcount
    await db.commit()

    # 4. Clean chat_messages (user chat history)
    result = await db.execute(text("DELETE FROM chat_messages"))
    cleanup["chat_messages_deleted"] = result.rowcount
    await db.commit()

    return cleanup


async def import_knowledge(replace: bool = True) -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Knowledge file not found: {DATA_FILE}")

    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    chunks = raw.get("knowledge_base", [])
    faq_pairs = raw.get("faq_pairs", [])
    meta = raw.get("metadata", {})

    async with async_session() as db:
        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise RuntimeError("SCNU tenant not found. Run scripts/create_scnu_tenant.py first.")

        cleanup_report = {}
        if replace:
            cleanup_report = await _cleanup_all(db, tenant.id)

        imported = 0
        errors = []

        # Import knowledge chunks (KB001-KB030)
        for chunk in chunks:
            try:
                chunk_meta = chunk.get("metadata", {})
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    data_type="campus_life",
                    title=_chunk_title(chunk),
                    content=chunk,
                    year=2026,
                    province="广东",
                    source_url="",
                    extra_meta={
                        "dataset": DATASET_KEY,
                        "chunk_id": chunk.get("chunk_id", ""),
                        "category": chunk.get("category", ""),
                        "sub_category": chunk.get("sub_category", ""),
                        "source": chunk.get("source", ""),
                        "priority": chunk_meta.get("priority", 3),
                        "frequently_asked": chunk_meta.get("frequently_asked", False),
                    },
                )
                db.add(td)
                await db.commit()
                await index_tenant_data(TENANT_SLUG, td)
                td.indexed_at = datetime.now(timezone.utc)
                await db.commit()
                imported += 1
            except Exception as exc:
                errors.append({"title": _chunk_title(chunk), "error": str(exc)})

        # Import FAQ pairs
        for faq in faq_pairs:
            try:
                related = faq.get("related_chunks", [])
                content = {
                    "chunk_id": f"FAQ_{imported:03d}",
                    "category": "高频FAQ",
                    "sub_category": faq.get("question", "")[:80],
                    "question_patterns": [faq.get("question", "")],
                    "answer_content": faq.get("answer", ""),
                    "keywords": ["FAQ", "高频问题"],
                    "source": "FAQ知识库构建",
                    "metadata": {"priority": 1, "frequently_asked": True},
                    "related_chunks": related,
                    "question": faq.get("question", ""),
                    "answer": faq.get("answer", ""),
                }
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    data_type="campus_life",
                    title=_faq_title(faq),
                    content=content,
                    year=2026,
                    province="广东",
                    source_url="",
                    extra_meta={
                        "dataset": DATASET_KEY,
                        "chunk_id": content["chunk_id"],
                        "category": "高频FAQ",
                        "sub_category": faq.get("question", "")[:80],
                        "source": "FAQ知识库构建",
                        "priority": 1,
                        "frequently_asked": True,
                        "is_faq": True,
                    },
                )
                db.add(td)
                await db.commit()
                await index_tenant_data(TENANT_SLUG, td)
                td.indexed_at = datetime.now(timezone.utc)
                await db.commit()
                imported += 1
            except Exception as exc:
                errors.append({"title": _faq_title(faq), "error": str(exc)})

        # Update tenant config with knowledge base metadata
        await db.execute(
            text(
                """
                UPDATE tenants
                SET config = jsonb_set(
                    jsonb_set(config, '{knowledge_base,last_updated}', to_jsonb(CAST(:updated_at AS text)), true),
                    '{knowledge_base,scnu_ibc_docs}', (:count)::text::jsonb,
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

    return {
        "imported": imported,
        "chunks": len(chunks),
        "faqs": len(faq_pairs),
        "errors": errors,
        "dataset": DATASET_KEY,
        "project": meta.get("project_name", ""),
        "cleanup": cleanup_report,
    }


async def main():
    result = await import_knowledge(replace=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
