from knowledge_base.chroma_client import client as _chroma_client


def get_chroma_client():
    return _chroma_client
