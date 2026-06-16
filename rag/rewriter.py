"""
Query Rewriting: viết lại câu hỏi người dùng thành câu hỏi độc lập,
bổ sung ngữ cảnh từ lịch sử hội thoại của phiên hiện tại.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rag.config import OPENAI_API_KEY, LLM_MODEL, MAX_HISTORY_TURNS

_llm = None

_SYSTEM = (
    "Bạn là chuyên gia tái tạo câu hỏi (Query Rewriter) cho hệ thống RAG của Đại học Bách Khoa Hà Nội.\n"
    "Nhiệm vụ của bạn là đọc lịch sử hội thoại và câu nói mới nhất của người dùng để tạo ra MỘT câu hỏi tìm kiếm độc lập, đầy đủ ngữ cảnh.\n\n"
    "LƯU Ý ĐẶC BIỆT QUAN TRỌNG:\n"
    "1. Câu nói mới nhất của người dùng có thể KHÔNG phải là một câu hỏi, mà là một CÂU TRẢ LỜI cung cấp thêm thông tin (ví dụ: tên ngành, khóa học, hệ đào tạo) cho Trợ lý ở lượt trước.\n"
    "2. Nếu đó là câu cung cấp thông tin, bạn PHẢI tìm lại ý định hỏi ban đầu của người dùng ở các lượt trước, sau đó ghép với thông tin mới này để tạo thành một câu hỏi hoàn chỉnh.\n\n"
    "VÍ DỤ:\n"
    "- Người dùng: Bao nhiêu tín thì ra trường?\n"
    "- Trợ lý: Bạn học hệ nào?\n"
    "- Người dùng: Hệ cử nhân.\n"
    "-> KẾT QUẢ VIẾT LẠI: Hệ cử nhân cần tích lũy bao nhiêu tín chỉ để ra trường?\n\n"
    "Chỉ trả về câu hỏi đã được viết lại. TUYỆT ĐỐI không giải thích, không thêm dấu ngoặc kép hay bất kỳ văn bản nào khác."
)


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.2,
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
