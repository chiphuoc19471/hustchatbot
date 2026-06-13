"""
Query Rewriting: viết lại câu hỏi người dùng thành câu hỏi độc lập,
bổ sung ngữ cảnh từ lịch sử hội thoại của phiên hiện tại.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rag.config import OPENAI_API_KEY, LLM_MODEL, MAX_HISTORY_TURNS

_llm = None

_SYSTEM = (
    "Bạn hỗ trợ hệ thống RAG về quy chế và quy định của Đại học Bách Khoa Hà Nội. "
    "Nhiệm vụ: viết lại câu hỏi mới nhất thành câu hỏi độc lập, rõ ràng, "
    "bổ sung đủ ngữ cảnh từ lịch sử hội thoại để có thể tìm kiếm mà không cần ngữ cảnh thêm. "
    "Chỉ trả về câu hỏi đã viết lại, không giải thích."
)


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0,
        )
    return _llm


def rewrite_query(query: str, chat_history: list[dict]) -> str:
    if not chat_history:
        return query

    recent = chat_history[-(MAX_HISTORY_TURNS * 2):]
    history_text = "".join(
        f"{'Người dùng' if m['role'] == 'user' else 'Trợ lý'}: {m['content']}\n"
        for m in recent
    )

    user_prompt = (
        f"Lịch sử hội thoại:\n{history_text}\n"
        f"Câu hỏi mới nhất: {query}\n\n"
        "Câu hỏi viết lại:"
    )

    response = _get_llm().invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=user_prompt),
    ])
    return response.content.strip() or query
