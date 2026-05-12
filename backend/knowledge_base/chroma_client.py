import chromadb
from config import settings
from knowledge_base.embeddings import embedding_model

client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection(name="colleges_majors")

def index_documents(docs: list[str], metadatas: list[dict], ids: list[str]):
    embeddings = embedding_model.embed_documents(docs)
    collection.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)

def search_similar(query: str, k: int = 30) -> list[dict]:
    q_emb = embedding_model.embed_query(query)
    results = collection.query(query_embeddings=[q_emb], n_results=k)
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
