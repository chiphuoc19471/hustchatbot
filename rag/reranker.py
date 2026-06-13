"""
LLM Reranker: dùng GPT-4.1-mini để chọn các điều khoản liên quan nhất
trong danh sách chunks sau khi retrieve.
"""
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rag.config import OPENAI_API_KEY, LLM_MODEL, TOP_N_RERANK

_llm = None

_SYSTEM = (
    "Bạn là chuyên gia về quy chế và quy định của Đại học Bách Khoa Hà Nội. "
    f"Nhiệm vụ: chọn tối đa {TOP_N_RERANK} điều khoản liên quan nhất đến câu hỏi, "
    "theo thứ tự liên quan giảm dần. "
    "Chỉ trả về JSON array chứa các index (ví dụ: [2, 0, 5, 3]), không giải thích."
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


def rerank(query: str, chunks: list[dict]) -> list[dict]:
    if len(chunks) <= TOP_N_RERANK:
        return chunks

    candidates_text = "\n\n".join(
        f"[{i}] {c.get('dieu', '')}: {c['text'][:400]}"
        for i, c in enumerate(chunks)
    )

    user_prompt = (
        f"Câu hỏi: {query}\n\n"
        f"Các điều khoản ứng viên:\n{candidates_text}\n\n"
        f"Chọn {TOP_N_RERANK} điều khoản liên quan nhất (JSON array các index):"
    )

    response = _get_llm().invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=user_prompt),
    ])

    try:
        content = response.content.strip()
        start, end = content.find("["), content.rfind("]") + 1
        indices = json.loads(content[start:end])
        selected = [chunks[i] for i in indices if 0 <= i < len(chunks)]
        return selected[:TOP_N_RERANK]
    except Exception:
        return chunks[:TOP_N_RERANK]
