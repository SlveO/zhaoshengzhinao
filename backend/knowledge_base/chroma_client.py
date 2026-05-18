import chromadb
from config import settings
from knowledge_base.embeddings import embedding_model

client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection(name="colleges_majors")

def _sanitize_meta(meta: dict) -> dict:
    """Replace None values with empty string — ChromaDB 0.5.x rejects None."""
    return {k: (v if v is not None else "") for k, v in meta.items()}


def index_documents(docs: list[str], metadatas: list[dict], ids: list[str]):
    embeddings = embedding_model.embed_documents(docs)
    clean_metas = [_sanitize_meta(m) for m in metadatas]
    collection.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=clean_metas)

_tenant_collections: dict[str, object] = {}


def get_tenant_collection(tenant_slug: str):
    """Get or create a tenant-specific ChromaDB collection."""
    if tenant_slug not in _tenant_collections:
        _tenant_collections[tenant_slug] = client.get_or_create_collection(
            name=f"{tenant_slug}_colleges"
        )
    return _tenant_collections[tenant_slug]


def search_similar(query: str, k: int = 30, tenant_slug: str | None = None) -> list[dict]:
    q_emb = embedding_model.embed_query(query)
    coll = get_tenant_collection(tenant_slug) if tenant_slug else collection
    results = coll.query(query_embeddings=[q_emb], n_results=k)
    items = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            items.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
    return items
