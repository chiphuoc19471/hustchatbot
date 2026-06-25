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

    # Lọc error message khỏi history để rewriter không bị nhiễu
    _ERROR_PREFIXES = ("Xin lỗi, đã xảy ra lỗi", "Xin lỗi, tôi không tìm thấy")
    clean_history = [
        m for m in chat_history
        if not m["content"].startswith(_ERROR_PREFIXES)
    ]

    rewritten = rewrite_query(query, clean_history) if clean_history else query
    chunks = retrieve(rewritten)

    if not chunks:
        return _NOT_FOUND

    reranked = rerank(rewritten, chunks)
    return generate(rewritten, reranked)
