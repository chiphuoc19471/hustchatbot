"""
Similarity search trên Chroma (top_k).
"""
from langchain_chroma import Chroma
from rag.config import VECTOR_STORE_DIR, TOP_K_RETRIEVE
from rag.embedder import get_embedder

_vectorstore = None


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=get_embedder(),
            collection_name="law_chunks",
        )
    return _vectorstore


def retrieve(query: str) -> list[dict]:
    vs = _get_vectorstore()
    results = vs.similarity_search(query, k=TOP_K_RETRIEVE)
    chunks = []
    for doc in results:
        meta = doc.metadata
        chunks.append({
            "text": doc.page_content,
            "dieu": meta.get("dieu", ""),
            "source": meta.get("source", ""),
            "chuong": meta.get("chuong", ""),
            "muc": meta.get("muc", ""),
        })
    return chunks
