import json
import asyncio
import traceback
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, SessionLocal
from models.conversation import Conversation, Message
from rag.pipeline import answer as rag_answer

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None


class SourceInfo(BaseModel):
    dieu: str
    ten_dieu: str
    van_ban: str
    trich_doan: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    conversation_id: int
    message_id: int


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def send_question(
    chat_req: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Gửi câu hỏi và nhận trả lời từ RAG pipeline.
    Tạo hội thoại mới nếu không có conversation_id.
    """
    # 1. Resolve or Create Conversation
    if chat_req.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == chat_req.conversation_id
        ).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy hội thoại"
            )
    else:
        title = chat_req.question[:50] + "..." if len(chat_req.question) > 50 else chat_req.question
        conversation = Conversation(title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Save User's Message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=chat_req.question,
        sources=None
    )
    db.add(user_msg)

    # 3. Lấy lịch sử hội thoại (tối đa 5 lượt gần nhất)
    recent_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(10)
        .all()
    )
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent_messages)
    ]

    # 4. Gọi RAG pipeline
    rag_result = rag_answer(query=chat_req.question, chat_history=chat_history)
    answer = rag_result["answer"]
    sources = rag_result["sources"]

    # 5. Save Assistant's Message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources, ensure_ascii=False)
    )
    db.add(assistant_msg)

    # 6. Update Conversation timestamp
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)

    sources_response = [
        SourceInfo(
            dieu=s["dieu"],
            ten_dieu=s["ten_dieu"],
            van_ban=s["van_ban"],
            trich_doan=s["trich_doan"],
        )
        for s in sources
    ]

    return ChatResponse(
        answer=answer,
        sources=sources_response,
        conversation_id=conversation.id,
        message_id=assistant_msg.id
    )


@router.post("/stream")
async def send_question_stream(
    chat_req: ChatRequest,
    db: Session = Depends(get_db)
):
    """Streaming endpoint: RAG chạy trong thread, sau đó stream kết quả từng token."""
    # 1. Resolve / create conversation
    if chat_req.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == chat_req.conversation_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")
    else:
        title = chat_req.question[:50] + ("..." if len(chat_req.question) > 50 else "")
        conversation = Conversation(title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Save user message
    db.add(Message(conversation_id=conversation.id, role="user", content=chat_req.question))
    db.commit()

    # 3. Lấy lịch sử hội thoại
    recent = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.id.desc()).limit(10).all()
    chat_history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    conv_id = conversation.id
    question_copy = chat_req.question

    # 4. Chạy RAG pipeline trong thread
    def _run_rag_and_save():
        try:
            result = rag_answer(query=question_copy, chat_history=chat_history)
            answer = result["answer"]
            sources = result["sources"]
        except Exception:
            traceback.print_exc()
            answer = "Xin lỗi, đã xảy ra lỗi xử lý. Vui lòng thử lại."
            sources = []

        msg_id = None
        try:
            new_db = SessionLocal()
            try:
                msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=answer,
                    sources=json.dumps(sources, ensure_ascii=False),
                )
                new_db.add(msg)
                new_db.query(Conversation).filter(Conversation.id == conv_id).update(
                    {"updated_at": datetime.utcnow()}
                )
                new_db.commit()
                new_db.refresh(msg)
                msg_id = msg.id
            finally:
                new_db.close()
        except Exception:
            traceback.print_exc()

        return answer, sources, msg_id

    answer, sources, msg_id = await asyncio.get_running_loop().run_in_executor(
        None, _run_rag_and_save
    )

    # 5. Stream kết quả từng token
    import re
    tokens = re.split(r'(\s+)', answer)

    async def event_stream():
        yield f"data: {json.dumps({'status': 'generating'}, ensure_ascii=False)}\n\n"
        for tok in tokens:
            if tok:
                yield f"data: {json.dumps({'token': tok}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.012)
        yield f"data: {json.dumps({'done': True, 'sources': sources, 'conversation_id': conv_id, 'message_id': msg_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
