# Hướng dẫn cài đặt

## Yêu cầu
- Python 3.10+
- OpenAI API Key
- **Java 11+** (dùng cho OpenDataLoader PDF parser — kiểm tra: `java -version`)
  - Tải tại: https://adoptium.net/

## 1. Clone repo
```bash
git clone https://github.com/your-username/chatbot-quyche-hust.git
cd chatbot-quyche-hust
```

## 2. Tạo virtual environment & cài dependencies
```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## 3. Cấu hình biến môi trường
```bash
# Copy file mẫu rồi điền giá trị thật vào
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux
```

Nội dung `.env`:
```env
OPENAI_API_KEY=sk-...

DATABASE_URL=sqlite:///./chatbot.db
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4.1-mini
```

## 4. Xử lý dữ liệu (nếu có PDF mới)
```bash
# Bước 1: Chuyển PDF → Markdown
cd data
python parse_pdf.py

# Bước 2: Chunking theo cấu trúc Chương/Điều/Khoản
python chunking.py
cd ..
```

## 5. Build Chroma Index
```bash
python -m rag.build_index
# → Tạo Chroma index tại rag/vector_store/
```

> Chạy lại bước này mỗi khi dữ liệu trong `data/chunks/` thay đổi.

## 6. Chạy Backend
```bash
cd backend
uvicorn main:app --reload --port 8001
# → Chạy tại: http://localhost:8001
# → Swagger docs: http://localhost:8001/docs
```

## 7. Chạy Frontend
Dùng **Live Server** (VS Code extension) để mở `frontend/index.html` và tránh lỗi CORS.

## Tham số pipeline (`rag/config.py`)
| Tham số | Giá trị | Mô tả |
|---|---|---|
| `CHUNK_SIZE` | 500 | Kích thước chunk (tokens) |
| `TOP_K_RETRIEVE` | 10 | Số chunk lấy từ Chroma |
| `TOP_N_RERANK` | 4 | Số chunk giữ lại sau LLM Reranker |
| `MAX_HISTORY_TURNS` | 5 | Số lượt hội thoại dùng cho Query Rewriting |

## Đánh giá (RAGAS)
```bash
python data/evaluation/ragas_eval.py
# → Kết quả lưu tại data/evaluation/eval_results_<timestamp>.csv
```

## Lưu ý
- **KHÔNG** commit file `.env` lên Git
- **KHÔNG** commit `rag/vector_store/` lên Git (đã có trong `.gitignore`)
- Khi cài thêm thư viện mới: cập nhật vào `requirements.txt`
