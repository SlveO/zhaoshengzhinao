"""Per-tenant ChromaDB indexing utilities."""
from __future__ import annotations

from knowledge.client import get_chroma_client
from tenants.models import TenantData


def _build_document_text(data: TenantData) -> str:
    """Convert a TenantData record to a searchable text blob."""
    parts = [data.title]
    content = data.content or {}

    if data.data_type == "admission_score":
        parts.append(
            f"{content.get('major_name', '')} "
            f"{data.year or ''}年 "
            f"{data.province or ''} "
            f"最低分{content.get('min_score', '')} "
            f"最低位次{content.get('min_rank', '')} "
            f"选科要求{content.get('subject_requirements', '')}"
        )
    elif data.data_type == "curriculum":
        courses = content.get("core_courses", [])
        if isinstance(courses, list):
            parts.append(" ".join(str(c) for c in courses))
        else:
            parts.append(str(courses))
        obj = content.get("objective", "")
        parts.append(obj if isinstance(obj, str) else str(obj))
    elif data.data_type == "employment":
        top_ind = content.get("top_industries", [])
        ind_text = ""
        if isinstance(top_ind, list):
            ind_text = " ".join(
                f"{i.get('industry', '')}({i.get('percentage', 0)*100:.0f}%)"
                for i in top_ind[:5]
            )
        parts.append(
            f"就业率{content.get('employment_rate', '')} "
            f"月薪{content.get('avg_monthly_salary', '')} "
            f"行业: {ind_text}"
        )
    elif data.data_type == "campus_life":
        parts.append(str(content.get("text", "")))

    return " ".join(str(p) for p in parts if p)


def _sanitize_meta_val(v):
    """Replace None with empty string for ChromaDB compatibility."""
    return v if v is not None else ""


async def index_tenant_data(tenant_slug: str, data: TenantData) -> None:
    """Index a single TenantData record into the tenant's ChromaDB collection."""
    client = get_chroma_client()
    collection_name = f"{tenant_slug}_colleges"
    collection = client.get_or_create_collection(collection_name)

    doc_text = _build_document_text(data)
    raw_meta = {
        "tenant_slug": tenant_slug,
        "data_type": str(data.data_type) if hasattr(data.data_type, "value") else data.data_type,
        "year": data.year,
        "province": data.province,
        **data.extra_meta,
    }
    clean_meta = {k: _sanitize_meta_val(v) for k, v in raw_meta.items()}
    collection.add(
        ids=[str(data.id)],
        documents=[doc_text],
        metadatas=[clean_meta],
    )


async def reindex_tenant(tenant_slug: str) -> None:
    """Drop and rebuild a tenant's entire ChromaDB collection.

    Call this after bulk-importing TenantData records.
    """
    from models import async_session
    from sqlalchemy import select

    client = get_chroma_client()
    collection_name = f"{tenant_slug}_colleges"

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    async with async_session() as db:
        result = await db.execute(
            select(TenantData).where(
                TenantData.tenant.has(slug=tenant_slug)
            )
        )
        records = result.scalars().all()

    if not records:
        return

    collection = client.get_or_create_collection(collection_name)
    batch_size = 2000
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        collection.add(
            ids=[str(r.id) for r in batch],
            documents=[_build_document_text(r) for r in batch],
            metadatas=[
                {
                    "tenant_slug": tenant_slug,
                    "data_type": str(r.data_type) if hasattr(r.data_type, "value") else r.data_type,
                    "year": _sanitize_meta_val(r.year),
                    "province": _sanitize_meta_val(r.province),
                    **{k: _sanitize_meta_val(v) for k, v in r.extra_meta.items()},
                }
                for r in batch
            ],
        )
