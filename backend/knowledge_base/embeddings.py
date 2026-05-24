"""Embedding service — downloads models via ModelScope (faster in China)."""
import os
from sentence_transformers import SentenceTransformer
from config import settings

_model = None

# ModelScope cache — ensure writable dir even when HOME is /nonexistent (Docker system user)
MODELSCOPE_CACHE = os.environ.get("MODELSCOPE_CACHE", os.path.expanduser("~/.cache/modelscope"))
os.environ["MODELSCOPE_CACHE"] = MODELSCOPE_CACHE
_home = os.environ.get("HOME", "")
if not _home or not os.path.isdir(_home) or not os.access(_home, os.W_OK):
    os.environ["HOME"] = os.path.dirname(MODELSCOPE_CACHE)


def _get_model():
    global _model
    if _model is not None:
        return _model

    model_name = settings.embedding_model  # "BAAI/bge-large-zh-v1.5"

    # Try ModelScope (handles caching internally — returns cached path if exists)
    try:
        from modelscope import snapshot_download

        print(f"Loading embedding model via ModelScope: {model_name}")
        model_dir = snapshot_download(model_name, cache_dir=MODELSCOPE_CACHE)
        print(f"Model path: {model_dir}")
        _model = SentenceTransformer(model_dir, device="cpu")
        return _model
    except Exception as e:
        print(f"ModelScope failed: {e}")
        print("Falling back to HuggingFace (may be slow in China)...")
        _model = SentenceTransformer(model_name, device="cpu")
        return _model


class EmbeddingWrapper:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return _get_model().encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return _get_model().encode([text], normalize_embeddings=True)[0].tolist()


embedding_model = EmbeddingWrapper()
