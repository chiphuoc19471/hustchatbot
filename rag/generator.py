"""
Generator: sinh câu trả lời từ các chunks đã rerank,
trả về answer + sources theo interface đã thống nhất với Backend.
"""
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rag.config import OPENAI_API_KEY, LLM_MODEL

_llm = None

_SYSTEM = (
    "Bạn là trợ lý tư vấn về quy chế và quy định của Đại học Bách Khoa Hà Nội (HUST). "
    "Phong cách của bạn là chuyên nghiệp, chính xác và tận tâm hỗ trợ sinh viên.\n\n"

    "NGUYÊN TẮC:\n"
    "- CHỈ trả lời dựa trên phần NGỮ CẢNH được cung cấp.\n"
    "- KHÔNG tự ý bịa đặt nội dung quy chế không có trong ngữ cảnh.\n"
    "- Khi trích dẫn: 'Theo Điều X [tên văn bản]...'.\n"
    "- Nếu ngữ cảnh không đủ thông tin: thành thật cho biết và hướng dẫn người dùng tra cứu thêm.\n\n"

    "CẤU TRÚC TRẢ LỜI:\n"
    "① Trả lời trực tiếp câu hỏi (1-2 câu).\n"
    "② Trích dẫn điều khoản liên quan (số Điều, tên văn bản, nội dung cốt lõi).\n"
    "③ Lưu ý thêm nếu cần (ngoại lệ, điều kiện đặc biệt...).\n\n"

    "Trả lời bằng tiếng Việt, rõ ràng, dễ hiểu."
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


def _van_ban(source: str) -> str:
    return re.sub(r"\.(md|json)$", "", source, flags=re.IGNORECASE)


def _parse_dieu(dieu_raw: str) -> tuple[str, str]:
    """Tách 'Điều 20.Điều kiện xét tốt nghiệp' → ('Điều 20', 'Điều kiện xét tốt nghiệp')"""
    clean = re.sub(r"\*+", "", dieu_raw).strip()
    parts = clean.split(".", 1)
    dieu_num = parts[0].strip()
    ten_dieu = parts[1].strip() if len(parts) == 2 else ""
    return dieu_num, ten_dieu


def _build_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"--- {re.sub(r'[*]+', '', c.get('dieu', '')).strip()} ({_van_ban(c['source'])}) ---\n{c['text']}"
        for c in chunks
    )


def _build_user_prompt(query: str, context: str) -> str:
    return (
        f"NGỮ CẢNH (chỉ được dùng thông tin trong phần này để trả lời):\n"
        f"{context}\n\n"
        f"---\n"
        f"CÂU HỎI: {query}\n\n"
        "TRẢ LỜI:"
    )


def build_sources(chunks: list[dict]) -> list[dict]:
    seen, sources = set(), []
    for c in chunks:
        dieu_num, ten_dieu = _parse_dieu(c.get("dieu", ""))
        van_ban = _van_ban(c["source"])
        key = (dieu_num, van_ban)
        if key not in seen:
            seen.add(key)
            sources.append({
                "dieu": dieu_num,
                "ten_dieu": ten_dieu,
                "van_ban": van_ban,
                "trich_doan": c["text"][:300].strip(),
                "full_text": c["text"],
            })
    return sources


def generate(query: str, chunks: list[dict]) -> dict:
    context = _build_context(chunks)
    user_prompt = _build_user_prompt(query, context)

    response = _get_llm().invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=user_prompt),
    ])

    answer_text = response.content.strip()
    keywords = ["Điều", "Khoản", "Quy chế", "Quy định", "Thông báo", "Quyết định"]
    is_cited = any(kw in answer_text for kw in keywords)
    final_sources = build_sources(chunks) if is_cited else []

    return {
        "answer": answer_text,
        "sources": final_sources,
    }


async def astream_generate(query: str, chunks: list[dict]):
    """Async generator: yield từng token string để frontend hiển thị streaming."""
    context = _build_context(chunks)
    user_prompt = _build_user_prompt(query, context)

    async for chunk in _get_llm().astream([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=user_prompt),
    ]):
        if chunk.content:
            yield chunk.content
