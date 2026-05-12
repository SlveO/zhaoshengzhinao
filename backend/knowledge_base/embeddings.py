from langchain_community.embeddings import HuggingFaceEmbeddings
from config import settings

embedding_model = HuggingFaceEmbeddings(
    model_name=settings.embedding_model,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
