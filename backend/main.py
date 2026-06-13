import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from models.conversation import Conversation, Message
from routers import chat, history

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Chatbot Tư Vấn Quy Chế HUST - API",
    description="Hệ thống Backend cung cấp các API hỏi đáp về quy chế, quy định Đại học Bách Khoa Hà Nội.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(history.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Chatbot Tư Vấn Quy Chế HUST API",
        "docs_url": "/docs"
    }
