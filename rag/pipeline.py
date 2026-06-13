"""
Entry point cho Backend gọi.
Sử dụng:
    from rag.pipeline import answer
    result = answer(query="...", chat_history=[...])
"""
from rag.rewriter import rewrite_query
from rag.retriever import retrieve
from rag.reranker import rerank
from rag.generator import generate

_NOT_FOUND = {
    "answer": "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong cơ sở dữ liệu.",
    "sources": [],
}


def answer(query: str, chat_history: list[dict] | None = None) -> dict:
    """
    Args:
        query:        câu hỏi của người dùng
        chat_history: [{"role": "user"/"assistant", "content": "..."}]
                      tối đa 5 lượt gần nhất, Backend truy xuất từ SQLite và truyền vào.

    Returns:
        {
            "answer": str,
            "sources": [{"dieu", "ten_dieu", "van_ban", "trich_doan"}]
        }
    """
    if chat_history is None:
        chat_history = []

    rewritten = rewrite_query(query, chat_history)
    chunks = retrieve(rewritten)

    if not chunks:
        return _NOT_FOUND

    reranked = rerank(rewritten, chunks)
    return generate(query, reranked)
