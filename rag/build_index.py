"""
Build Chroma index từ data/chunks/
Chạy 1 lần, hoặc khi dữ liệu thay đổi:
    python -m rag.build_index
"""
import os
import json
import glob
from langchain_chroma import Chroma
from langchain_core.documents import Document
from rag.config import VECTOR_STORE_DIR, CHUNKS_DIR
from rag.embedder import get_embedder


def load_all_chunks() -> list[dict]:
    chunks = []
    json_files = glob.glob(os.path.join(CHUNKS_DIR, "*.json"))
    if not json_files:
        raise FileNotFoundError(f"Không tìm thấy file JSON nào trong {CHUNKS_DIR}")
    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            chunks.extend(json.load(f))
    return chunks


def build_docs(chunks: list[dict]) -> list[Document]:
    docs = []
    for chunk in chunks:
        meta = chunk["metadata"]
        docs.append(Document(
            page_content=chunk["text"],
            metadata={
                "chunk_id": str(chunk.get("chunk_id", 0)),
                "dieu": meta.get("Điều", ""),
                "source": meta.get("Source", "unknown"),
                "chuong": meta.get("Chương", ""),
                "muc": meta.get("Mục", ""),
            }
        ))
    return docs


def main():
    print("Đang tải chunks từ data/chunks/ ...")
    chunks = load_all_chunks()
    print(f"  Tổng: {len(chunks)} chunks")

    print("Đang tạo documents ...")
    docs = build_docs(chunks)
    print(f"  Tổng: {len(docs)} documents để embedding")

    print("Đang embed và lưu vào Chroma ...")
    Chroma.from_documents(
        documents=docs,
        embedding=get_embedder(),
        persist_directory=VECTOR_STORE_DIR,
        collection_name="law_chunks",
    )
    print(f"  Chroma index lưu tại: {VECTOR_STORE_DIR}")
    print("\nHoàn tất! Index đã sẵn sàng.")


if __name__ == "__main__":
    main()
