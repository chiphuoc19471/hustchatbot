#  Chatbot Tư Vấn Quy Chế & Quy Định Đại học Bách Khoa Hà Nội (HUST)
> Ứng dụng kỹ thuật RAG (Retrieval-Augmented Generation) và Mô hình Ngôn ngữ Lớn (LLM)

<p align="center">
  <img src="R.jpg" alt="alt text" width="300" />
</p>

##  Giới thiệu

Hệ thống chatbot hỏi đáp về **quy chế, quy định của Đại học Bách Khoa Hà Nội (HUST)**, giúp sinh viên tra cứu nhanh các nội dung như: quy chế đào tạo, **chuẩn đầu ra tiếng Anh / ngoại ngữ**, điều kiện xét tốt nghiệp, học phí – học bổng, đăng ký học phần, khen thưởng – kỷ luật,... dựa trên các văn bản quy chế chính thức của Nhà trường.

---

##  Tác giả

Đồ án cá nhân — phụ trách toàn bộ: thu thập dữ liệu, RAG pipeline, Backend, Frontend và đánh giá.

---

##  Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────┐
│              FRONTEND (HTML/CSS/JS)                 │
│                  Chat / History                     │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────▼──────────────────────────────┐
│                  BACKEND (FastAPI)                  │
│              Chat API │ History API                 │
└───────┬──────────────────────────┬──────────────────┘
        │                          │
┌───────▼──────────────────────┐  ┌▼─────────────────────────────┐
│  RAG Pipeline (LangChain)    │  │     Database (SQLite)        │
│                              │  │  conversations, messages     │
│  1. Query Rewriting          │  └──────────────────────────────┘
│     (lịch sử hội thoại,      │
│      lọc error message)      │
│                              │
│  2. Hybrid Retrieval         │
│     ├─ Semantic Search       │
│     │   (Chroma,             │
│     │    text-embedding-3)   │
│     └─ BM25 Keyword Search   │
│         → EnsembleRetriever  │
│           (RRF fusion 60/40) │
│                              │
│  3. LLM Reranker             │
│     (topic + hệ đào tạo      │
│      filtering)              │
│                              │
│  4. Generator: GPT-4.1-mini  │
│     (trả lời + trích dẫn)    │
└──────────────────────────────┘
```

> **Format-aware chunking**: cắt văn bản theo đúng cấu trúc quy chế (Chương / Mục / Điều), giữ mỗi chunk trọn vẹn về ngữ nghĩa kèm metadata (số Điều, tên Điều, tên văn bản) để phục vụ trích dẫn.
>
> **Xử lý bảng biểu**: bảng trong văn bản được **tách ra và thay bằng placeholder** trước khi chunk, chuyển sang văn xuôi theo từng hệ đào tạo riêng biệt để tăng chất lượng embedding, sau đó **chèn lại đúng vị trí** khi chunk xong.
>
> **Hybrid Retrieval**: kết hợp Semantic Search (Chroma) và BM25 keyword search qua EnsembleRetriever với Reciprocal Rank Fusion (RRF). BM25 bắt được các chunk chứa từ khóa chính xác mà semantic search bỏ sót.

---

##  Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Frontend | HTML + CSS + JavaScript (thuần) |
| Backend | FastAPI (Python 3.10+) |
| LLM | GPT-4.1-mini (OpenAI) |
| Embedding | `text-embedding-3-small` (OpenAI) |
| Vector DB | Chroma |
| RAG Framework | LangChain |
| Query Rewriting | LangChain + lọc error message khỏi history |
| Chunking | Format-aware (Chương / Mục / Điều) + bảng biểu → văn xuôi theo hệ đào tạo |
| Retrieval | **Hybrid Search**: Semantic (Chroma) + BM25 → EnsembleRetriever (RRF 60/40) |
| Reranker | LLM Reranker (GPT-4.1-mini) với topic + hệ đào tạo filtering |
| Database | SQLite |
| Cấu hình | `rag/config.py` + biến môi trường `.env` |

---

##  Interface RAG Pipeline

Backend gọi pipeline RAG qua **một hàm duy nhất** `rag.pipeline.answer()`:

**Input:**
```json
{
  "query": "Hệ cử nhân khóa 68 cần bao nhiêu tín chỉ để tốt nghiệp?",
  "chat_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```
- `chat_history`: tối đa **5 lượt gần nhất** của phiên hiện tại, Backend truy xuất từ SQLite và truyền vào. Pipeline dùng để Query Rewriting, **không** tự đọc database. Error message của assistant được **lọc tự động** trước khi rewrite để tránh nhiễu.

**Output:**
```json
{
  "answer": "Theo Điều 2, Quy chế đào tạo ĐHBK Hà Nội, hệ Cử nhân cần tích lũy tối thiểu 132 tín chỉ để tốt nghiệp...",
  "sources": [
    {
      "dieu": "Điều 2",
      "ten_dieu": "Ngành đào tạo, chương trình đào tạo",
      "van_ban": "5",
      "trich_doan": "..."
    }
  ]
}
```

---

##  Cấu trúc thư mục

```
chatbot-quyche-hust/
│
├── backend/
│   ├── main.py                     # FastAPI app: cấu hình CORS, đăng ký router, tạo DB schema
│   ├── database.py                 # SQLAlchemy engine, SessionLocal, Base, get_db() dependency
│   ├── routers/
│   │   ├── chat.py                 # POST /chat, /chat/stream: nhận câu hỏi, gọi RAG, lưu message
│   │   └── history.py              # GET /history: danh sách conversation và nội dung chat
│   └── models/
│       └── conversation.py         # ORM model: bảng Conversation và Message (SQLite)
│
├── rag/
│   ├── config.py                   # Tham số pipeline: TOP_K_RETRIEVE, TOP_N_RERANK, model, path...
│   ├── pipeline.py                 # answer(): entry point; lọc error history → rewrite → retrieve → rerank → generate
│   ├── embedder.py                 # Khởi tạo OpenAI embedding model (singleton, dùng chung build & query)
│   ├── retriever.py                # Hybrid Search: BM25 + Chroma EnsembleRetriever (RRF 60/40)
│   ├── reranker.py                 # LLM Reranker: chọn top-N chunk theo đúng chủ đề và hệ đào tạo
│   ├── generator.py                # Sinh câu trả lời + trích dẫn Điều; nhận rewritten query, không lan man
│   ├── rewriter.py                 # Query Rewriting: tái tạo câu hỏi đầy đủ từ history, bỏ qua lượt nhiễu
│   ├── build_index.py              # Đọc data/chunks/*.json, embed và lưu vào Chroma vector store
│   └── vector_store/               # Chroma DB (tự sinh khi build_index) — KHÔNG commit lên Git
│
├── data/
│   ├── raw/                        # PDF văn bản quy chế/quy định HUST gốc
│   ├── processed/                  # Markdown parse lần đầu từ PDF (chưa làm sạch)
│   ├── processed_2/                # Markdown đã chuẩn hóa heading (Chương/Mục/Điều), bảng → văn xuôi
│   ├── chunks/                     # JSON chunks cho từng file (format-aware, metadata Điều/Chương)
│   ├── parse_pdf.py                # Bước 1 — Parse PDF → Markdown thô
│   ├── clean_md.py                 # Bước 2 — Làm sạch Markdown: chuẩn hóa heading, xóa ký tự lỗi
│   ├── chunking.py                 # Bước 3 — Format-aware chunking: cắt theo Điều, bảng → văn xuôi riêng từng hệ
│   └── evaluation/
│       ├── ragas_eval.py           # Đánh giá RAG pipeline bằng RAGAS (faithfulness, answer relevancy...)
│       └── evaluation_history.log  # Lịch sử kết quả các lần đánh giá
│
├── frontend/
│   ├── index.html                  # Giao diện chat chính (HTML structure)
│   ├── css/
│   │   └── chat.css                # Style toàn bộ giao diện: chat bubble, sidebar, source chip...
│   └── js/
│       ├── config.js               # Cấu hình BASE_URL trỏ tới Backend API
│       ├── api.js                  # Fetch wrapper: sendMessage(), streamMessage(), loadHistory()...
│       ├── utils.js                # Hàm tiện ích: showLoading(), hideLoading(), formatTime()...
│       └── chat-ui.js              # Logic UI chính: render message, quản lý conversation, event handler
│
├── run.py                          # Script khởi động: chạy Backend FastAPI + mở Frontend trên trình duyệt
├── requirements.txt                # Dependencies Python (backend + rag + data + evaluation)
├── .env.example                    # Mẫu biến môi trường — copy thành .env và điền giá trị thật
├── .gitignore                      # Loại trừ .env, vector_store/, *.db, __pycache__...
└── README.md                       # Tài liệu dự án
```

---

##  Setup môi trường

### Yêu cầu
- Python 3.10+
- OpenAI API Key

### 1. Clone repo
```bash
git clone https://github.com/your-username/chatbot-quyche-hust.git
cd chatbot-quyche-hust
```

### 2. Tạo virtual environment & cài dependencies
```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

> Khi cài thêm thư viện mới: `pip install <tên>` xong phải cập nhật vào `requirements.txt`.

### 3. Cấu hình biến môi trường

Tạo file `.env` từ `.env.example` rồi điền giá trị thật:

```env
OPENAI_API_KEY=sk-...

DATABASE_URL=sqlite:///./chatbot.db
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4.1-mini
```

Các tham số kỹ thuật của pipeline đặt trong `rag/config.py`:
```python
TOP_K_RETRIEVE = 30   # tổng chunk sau RRF (mỗi retriever lấy TOP_K//2)
TOP_N_RERANK   = 8    # số chunk giữ lại sau LLM Reranker
MAX_HISTORY_TURNS = 5 # số lượt hội thoại dùng cho Query Rewriting
```

### 4. Chuẩn bị dữ liệu & Build Index

```bash
# (Nếu có PDF mới) Parse PDF → Markdown
python data/parse_pdf.py

# Làm sạch Markdown
python data/clean_md.py

# Chunking (tạo/cập nhật data/chunks/*.json)
python data/chunking.py

# Build Chroma index (chạy lại mỗi khi chunks thay đổi)
python -m rag.build_index
```

> Lần khởi động đầu tiên sau khi build index sẽ **chậm hơn bình thường** do BM25Retriever load và index toàn bộ chunks vào RAM. Từ lần sau cache lại trong phiên.

### 5. Chạy server

```bash
python run.py
# hoặc
cd backend && uvicorn main:app --reload --port 8001
```

- API: `http://localhost:8001`
- Swagger docs: `http://localhost:8001/docs`

### 6. Chạy Frontend

Dùng **Live Server** (VS Code extension) để tránh lỗi CORS khi gọi API.

---

##  Lưu ý quan trọng

- **KHÔNG** commit file `.env` lên Git
- **KHÔNG** commit `rag/vector_store/` lên Git (build lại bằng `python -m rag.build_index`)
- Sau khi sửa bất kỳ file nào trong `data/processed_2/` hoặc `data/chunks/`, phải **re-chunk** và **rebuild index** để thay đổi có hiệu lực

---

##  Liên hệ

> Hoàng Chí Phước — chiphuoc1947@gmail.com
