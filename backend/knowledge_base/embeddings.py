"""Embedding service — downloads models via ModelScope (faster in China)."""
import os
from sentence_transformers import SentenceTransformer
from config import settings

_model = None

# ModelScope cache in persistent Docker volume
MODELSCOPE_CACHE = os.environ.get("MODELSCOPE_CACHE", "/root/.cache/modelscope")
os.environ["MODELSCOPE_CACHE"] = MODELSCOPE_CACHE


def _get_model():
    global _model
    if _model is not None:
        return _model

    model_name = settings.embedding_model  # "BAAI/bge-large-zh-v1.5"
    local_path = os.path.join(MODELSCOPE_CACHE, "hub", model_name.replace("/", "__"))

    # Try loading from local ModelScope cache first
    if os.path.exists(local_path) and os.path.isdir(local_path):
        print(f"Loading embedding model from local cache: {local_path}")
        _model = SentenceTransformer(local_path, device="cpu")
        return _model

    # Download from ModelScope
    print(f"Downloading embedding model via ModelScope: {model_name}")
    try:
        from modelscope import snapshot_download

        model_dir = snapshot_download(model_name, cache_dir=MODELSCOPE_CACHE)
        print(f"Model downloaded to: {model_dir}")
        _model = SentenceTransformer(model_dir, device="cpu")
        return _model
    except Exception as e:
        print(f"ModelScope download failed: {e}")
        print("Falling back to HuggingFace (may be slow)...")
        _model = SentenceTransformer(model_name, device="cpu")
        return _model


class EmbeddingWrapper:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return _get_model().encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return _get_model().encode([text], normalize_embeddings=True)[0].tolist()


embedding_model = EmbeddingWrapper()
