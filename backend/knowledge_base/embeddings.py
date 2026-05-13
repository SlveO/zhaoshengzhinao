from sentence_transformers import SentenceTransformer
from config import settings

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model, device="cpu")
    return _model

class EmbeddingWrapper:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return _get_model().encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return _get_model().encode([text], normalize_embeddings=True)[0].tolist()

embedding_model = EmbeddingWrapper()
