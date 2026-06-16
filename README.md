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
        │                                           │
┌───────▼──────────────────────────┐     ┌──────────▼──── ──────────────┐
│  RAG Pipeline (LangChain)        │     │     Database (SQLite)        │
│  1. Query Rewriting              │     │  conversations, messages     │
│     (lịch sử hội thoại phiên)    │     └──────────────────────────────┘
│  2. Retrieval                    │
│     - Format-aware chunks        │
│       → Chroma                   │
│       (text-embedding-3-small)   │
│  3. LLM Reranker (post-retrieval)│
│  4. Generator: GPT-4.1-mini      │
│     (trả lời + trích dẫn Điều)   │
└──────────────────────────────────┘
```

> **Format-aware chunking**: cắt văn bản theo đúng cấu trúc quy chế (Chương / Mục / Điều / Khoản / Điểm), giữ mỗi chunk trọn vẹn về ngữ nghĩa kèm metadata (số Điều, tên Điều, tên văn bản) để phục vụ trích dẫn.
>
> **Xử lý bảng biểu**: để không làm vỡ bảng khi cắt chunk, bảng trong văn bản được **tách ra và thay bằng placeholder** trước khi chunk, sau đó **chèn lại nguyên vẹn** vào đúng vị trí sau khi chunk xong.

---

##  Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Frontend | HTML + CSS + JavaScript (thuần) |
| Backend | FastAPI (Python 3.10+) |
| LLM | GPT-4.1-mini (OpenAI) |
| Embedding | `OpenAI text-embedding-3-small` |
| Vector DB | Chroma |
| RAG Framework | LangChain |
| Query Rewriting | LangChain (tích hợp lịch sử hội thoại phiên) |
| Chunking | Format-aware (theo cấu trúc văn bản: Chương / Mục / Điều / Khoản) |
| Retrieval | Similarity search trên Chroma (top_k) |
| Reranker | LLM Reranker (post-retrieval, dùng GPT-4.1-mini) |
| Database | SQLite |
| Cấu hình tham số RAG | `rag/config.py` + biến môi trường `.env` |

---

##  Interface RAG Pipeline

Backend gọi pipeline RAG qua **một hàm duy nhất** `rag.pipeline.answer()`:

**Input:**
```json
{
  "query": "Chuẩn đầu ra tiếng Anh để được xét tốt nghiệp là bao nhiêu?",
  "chat_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```
- `chat_history`: tối đa **5 lượt gần nhất** của phiên hiện tại, Backend truy xuất từ SQLite và truyền vào. Pipeline dùng để Query Rewriting, **không** tự đọc database.

**Output:**
```json
{
  "answer": "Theo Điều ... Quy chế đào tạo ĐHBK Hà Nội, sinh viên cần đạt chuẩn trình độ ngoại ngữ theo quy định hiện hành để được xét tốt nghiệp...",
  "sources": [
    {
      "dieu": "Điều X",
      "ten_dieu": "Chuẩn trình độ ngoại ngữ",
      "van_ban": "Quy chế đào tạo ĐHBK Hà Nội",
      "trich_doan": "..."
    }
  ]
}
```
- `sources` để Frontend hiển thị trích dẫn điều khoản và để RAGAS lấy `contexts` khi đánh giá.

---

##  Cấu trúc thư mục

```
chatbot-quyche-hust/
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── chat.py
│   │   └── history.py
│   ├── models/
│   │   └── conversation.py
│   └── database.py
│
├── rag/
│   ├── config.py             # Tham số: chunk size, top_k, top_n, model name...
│   ├── pipeline.py           # Hàm answer() - entry point cho Backend gọi
│   ├── embedder.py           # Khởi tạo embedding model (dùng chung cho build & query)
│   ├── retriever.py          # Similarity search trên Chroma
│   ├── reranker.py           # LLM Reranker
│   ├── generator.py          # Sinh câu trả lời + trích dẫn
│   ├── rewriter.py           # Query Rewriting từ lịch sử hội thoại
│   ├── build_index.py        # Build Chroma index từ data/chunks/
│   └── vector_store/         # Chroma index - KHÔNG commit lên Git
│
├── data/
│   ├── raw/                  # PDF quy chế/quy định HUST gốc
│   ├── processed/            # Markdown đã làm sạch
│   ├── chunks/               # chunks.json (format-aware theo Chương/Điều/Khoản)
│   ├── parse_pdf.py
│   ├── chunking.py           # Format-aware chunking (giấu/chèn lại bảng biểu)
│   └── evaluation/
│       ├── test_questions.json
│       └── ragas_eval.py
│
├── frontend/
│   ├── css/
│   ├── js/
│   └── index.html            # Giao diện chat chính
│
├── docs/
│   ├── API.md
│   └── setup.md
│
├── requirements.txt          # Dependencies Python (backend + rag + data)
├── .env.example              # Mẫu biến môi trường (copy thành .env)
├── .gitignore
└── README.md
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

### 2. Tạo virtual environment & cài dependencies (1 venv duy nhất ở thư mục gốc)
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
```bash
# Tạo file .env rồi điền giá trị thật vào
```

Nội dung `.env.example`:
```env
OPENAI_API_KEY=

DATABASE_URL=sqlite:///./chatbot.db
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4.1-mini
```

Các tham số kỹ thuật của pipeline đặt trong `rag/config.py`:
```python
CHUNK_SIZE =  2000        # tokens, ưu tiên giữ ranh giới Điều/Khoản
TOP_K_RETRIEVE = 30         # số chunk lấy từ Chroma
TOP_N_RERANK = 8             # số chunk giữ lại sau LLM Reranker
MAX_HISTORY_TURNS = 5         # số lượt hội thoại dùng cho Query Rewriting
RERANKER_MODEL = "gpt-4.1-mini"
```

### 4. Build Chroma Index (chạy 1 lần, hoặc khi dữ liệu thay đổi)
```bash
python -m rag.build_index
# → Tạo Chroma index tại rag/vector_store/
```

### 5. Chạy Backend
```bash
cd backend
uvicorn main:app --reload --port 8001
# → Chạy tại: http://localhost:8001
# → Swagger docs: http://localhost:8001/docs
```

### 6. Chạy Frontend

Dùng Live Server (VS Code extension) để tránh lỗi CORS khi gọi API.

---

##  Lưu ý quan trọng

- **KHÔNG** commit file `.env` lên Git
- **KHÔNG** commit `rag/vector_store/` lên Git (đã thêm vào `.gitignore`, build lại bằng `python -m rag.build_index`)

---

##  Liên hệ

> Hoàng Chí Phước - chiphuoc1947@gmail.com