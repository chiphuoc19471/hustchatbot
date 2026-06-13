import json
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from database import get_db
from models.conversation import Conversation, Message

router = APIRouter(prefix="/history", tags=["History"])


class ConversationSummaryResponse(BaseModel):
    id: int
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class MessageDetailResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[Any] = None
    created_at: datetime

    @field_validator("sources", mode="before")
    @classmethod
    def parse_sources(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageDetailResponse]


class DeleteResponse(BaseModel):
    message: str


@router.get("", response_model=List[ConversationSummaryResponse], status_code=status.HTTP_200_OK)
def get_history(db: Session = Depends(get_db)):
    """Lấy danh sách tất cả cuộc trò chuyện, sắp xếp theo thời gian gần nhất."""
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        ConversationSummaryResponse(
            id=conv.id,
            title=conv.title,
            message_count=len(conv.messages),
            created_at=conv.created_at,
            updated_at=conv.updated_at
        )
        for conv in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationDetailResponse, status_code=status.HTTP_200_OK)
def get_conversation_detail(conversation_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết một cuộc trò chuyện cùng tất cả tin nhắn."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại"
        )

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageDetailResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at
            )
            for msg in conversation.messages
        ]
    )


@router.delete("/{conversation_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Xóa một cuộc trò chuyện và tất cả tin nhắn của nó."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại"
        )

    db.delete(conversation)
    db.commit()
    return DeleteResponse(message="Đã xóa hội thoại thành công")
