"""
Hybrid retriever: kết hợp Semantic Search (Chroma) + BM25 keyword search
bằng EnsembleRetriever với Reciprocal Rank Fusion (RRF).
"""
import json
import glob
import os
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from rag.config import VECTOR_STORE_DIR, TOP_K_RETRIEVE, CHUNKS_DIR
from rag.embedder import get_embedder

_ensemble_retriever = None


def _load_all_docs() -> list[Document]:
    docs = []
    for path in glob.glob(os.path.join(CHUNKS_DIR, "*.json")):
        with open(path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        for c in chunks:
            meta = c["metadata"]
            docs.append(Document(
                page_content=c["text"],
                metadata={
                    "dieu": meta.get("Điều", ""),
                    "source": meta.get("Source", "unknown"),
                    "chuong": meta.get("Chương", ""),
                    "muc": meta.get("Mục", ""),
                }
            ))
    return docs


def _get_ensemble_retriever() -> EnsembleRetriever:
    global _ensemble_retriever
    if _ensemble_retriever is not None:
        return _ensemble_retriever

    # Mỗi retriever lấy TOP_K_RETRIEVE//2 
    k_each = max(TOP_K_RETRIEVE // 2, 10)

    # Semantic retriever (Chroma)
    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_DIR,
        embedding_function=get_embedder(),
        collection_name="law_chunks",
    )
    semantic = vectorstore.as_retriever(search_kwargs={"k": k_each})

    # BM25 keyword retriever
    docs = _load_all_docs()
    bm25 = BM25Retriever.from_documents(docs, k=k_each)

    # Ensemble: 60% semantic + 40% BM25, RRF fusion
    _ensemble_retriever = EnsembleRetriever(
        retrievers=[semantic, bm25],
        weights=[0.6, 0.4],
    )
    return _ensemble_retriever


def retrieve(query: str) -> list[dict]:
    retriever = _get_ensemble_retriever()
    results = retriever.invoke(query)
    # Giới hạn tổng chunk truyền vào reranker
    results = results[:TOP_K_RETRIEVE]
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
