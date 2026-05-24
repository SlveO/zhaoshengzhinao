from fastapi import APIRouter, Depends, Query

from core.tenant_context import get_current_tenant
from knowledge.client import get_chroma_client
from knowledge_base.embeddings import embedding_model

router = APIRouter()


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1, max_length=500),
    k: int = Query(default=5, ge=1, le=20),
    data_type: str | None = Query(default=None),
    tenant=Depends(get_current_tenant),
):
    """Search the current tenant knowledge base for RAG callers.

    Call with X-Tenant or ?tenant=. Returns short document chunks with metadata
    and source URLs. The response shape is intentionally simple for LLM tools.
    """
    collection_name = f"{tenant.slug}_colleges"
    client = get_chroma_client()
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return {"query": q, "tenant": tenant.slug, "results": []}

    query_kwargs = {"query_embeddings": [embedding_model.embed_query(q)], "n_results": k}
    if data_type:
        query_kwargs["where"] = {"data_type": data_type}
    results = collection.query(**query_kwargs)
    items = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []

    for idx, doc_id in enumerate(ids):
        meta = metas[idx] if idx < len(metas) else {}
        items.append(
            {
                "id": doc_id,
                "text": docs[idx] if idx < len(docs) else "",
                "metadata": meta,
                "score": None if idx >= len(distances) else round(1 - float(distances[idx]), 4),
                "source_url": meta.get("source_url", ""),
                "source_title": meta.get("source_title", ""),
            }
        )

    return {"query": q, "tenant": tenant.slug, "results": items}
