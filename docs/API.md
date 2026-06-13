# 📡 API Documentation
> Chatbot Tư Vấn Pháp Luật Lao Động

**Base URL:** `http://localhost:8001`  
**Format:** JSON  
**Auth:** Bearer JWT Token (trừ các API đăng ký/đăng nhập)

---

## 🔐 Authentication

### Đăng ký tài khoản
```
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "matkhau123",
  "name": "Nguyen Van A"
}
```

**Response 200:**
```json
{
  "message": "Đăng ký thành công",
  "user_id": 1
}
```

**Response 400 — Email đã tồn tại:**
```json
{
  "detail": "Email đã được sử dụng"
}
```

---

### Đăng nhập
```
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "matkhau123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "Nguyen Van A"
  }
}
```

**Response 401 — Sai mật khẩu:**
```json
{
  "detail": "Email hoặc mật khẩu không đúng"
}
```

---

## 💬 Chat

### Gửi câu hỏi
```
POST /chat
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "question": "Thử việc tối đa bao nhiêu ngày?",
  "conversation_id": null
}
```
> `conversation_id`: Truyền `null` nếu bắt đầu cuộc hội thoại mới.  
> Truyền ID có sẵn nếu muốn tiếp tục cuộc hội thoại cũ.

**Response 200:**
```json
{
  "answer": "Theo Điều 25, Bộ luật Lao động 2019, thời gian thử việc không quá 180 ngày đối với công việc của người quản lý doanh nghiệp; không quá 60 ngày đối với công việc có chức danh nghề cần trình độ cao đẳng trở lên; không quá 30 ngày đối với công việc có chức danh nghề cần trình độ trung cấp...",
  "sources": [
    {
      "law": "Bộ luật Lao động 2019",
      "article": "Điều 25",
      "chapter": "Chương III",
      "content": "Thời gian thử việc..."
    }
  ],
  "conversation_id": 5,
  "message_id": 12
}
```

**Response 401 — Chưa đăng nhập:**
```json
{
  "detail": "Token không hợp lệ hoặc đã hết hạn"
}
```

---

## 📚 Lịch sử hội thoại

### Lấy danh sách hội thoại
```
GET /history
Authorization: Bearer <token>
```

**Response 200:**
```json
[
  {
    "id": 5,
    "title": "Thử việc tối đa bao nhiêu ngày?",
    "topic": "hop-dong",
    "message_count": 4,
    "created_at": "2024-06-15T10:30:00",
    "updated_at": "2024-06-15T10:45:00"
  },
  {
    "id": 3,
    "title": "Tính trợ cấp thôi việc thế nào?",
    "topic": "luong",
    "message_count": 6,
    "created_at": "2024-06-14T09:00:00",
    "updated_at": "2024-06-14T09:20:00"
  }
]
```

---

### Xem chi tiết một hội thoại
```
GET /history/{conversation_id}
Authorization: Bearer <token>
```

**Response 200:**
```json
{
  "id": 5,
  "title": "Thử việc tối đa bao nhiêu ngày?",
  "topic": "hop-dong",
  "created_at": "2024-06-15T10:30:00",
  "messages": [
    {
      "id": 11,
      "role": "user",
      "content": "Thử việc tối đa bao nhiêu ngày?",
      "sources": null,
      "created_at": "2024-06-15T10:30:00"
    },
    {
      "id": 12,
      "role": "assistant",
      "content": "Theo Điều 25, Bộ luật Lao động 2019...",
      "sources": [
        {
          "law": "Bộ luật Lao động 2019",
          "article": "Điều 25",
          "chapter": "Chương III"
        }
      ],
      "created_at": "2024-06-15T10:30:05"
    }
  ]
}
```

**Response 404 — Không tìm thấy:**
```json
{
  "detail": "Không tìm thấy hội thoại"
}
```

---

### Xóa hội thoại
```
DELETE /history/{conversation_id}
Authorization: Bearer <token>
```

**Response 200:**
```json
{
  "message": "Đã xóa hội thoại thành công"
}
```

**Response 403 — Không có quyền:**
```json
{
  "detail": "Bạn không có quyền xóa hội thoại này"
}
```

---

## 🔧 Cách Frontend gọi API (api.js)

```javascript
const BASE_URL = "http://localhost:8001";

// Lấy token từ localStorage
const getToken = () => localStorage.getItem("access_token");

// Đăng nhập
export const login = async (email, password) => {
  const res = await axios.post(`${BASE_URL}/auth/login`, { email, password });
  localStorage.setItem("access_token", res.data.access_token);
  return res.data;
};

// Gửi câu hỏi
export const sendMessage = async (question, conversationId = null) => {
  const res = await axios.post(
    `${BASE_URL}/chat`,
    { question, conversation_id: conversationId },
    { headers: { Authorization: `Bearer ${getToken()}` } }
  );
  return res.data;
};

// Lấy danh sách lịch sử
export const getHistory = async () => {
  const res = await axios.get(`${BASE_URL}/history`, {
    headers: { Authorization: `Bearer ${getToken()}` }
  });
  return res.data;
};

// Xóa hội thoại
export const deleteConversation = async (id) => {
  const res = await axios.delete(`${BASE_URL}/history/${id}`, {
    headers: { Authorization: `Bearer ${getToken()}` }
  });
  return res.data;
};
```

---

## 📋 Mock API (Dùng khi Backend chưa xong)

```javascript
// services/mockApi.js — Người C dùng trong khi chờ Backend

export const login = async (email, password) => ({
  access_token: "mock-token-123",
  user: { id: 1, email, name: "Test User" }
});

export const sendMessage = async (question, conversationId) => ({
  answer: "Đây là câu trả lời mock. Theo Điều 25, BLLĐ 2019...",
  sources: [{ law: "Bộ luật Lao động 2019", article: "Điều 25" }],
  conversation_id: conversationId || 1,
  message_id: Math.random()
});

export const getHistory = async () => ([
  { id: 1, title: "Thử việc tối đa bao nhiêu ngày?", message_count: 2, created_at: "2024-06-15" },
  { id: 2, title: "Tính trợ cấp thôi việc?", message_count: 4, created_at: "2024-06-14" }
]);
```

> Khi Backend xong, chỉ cần đổi import từ `mockApi` sang `api` là hoạt động ngay ✅

---

## 📊 Danh sách Topic phân loại

| Topic Code | Mô tả |
|---|---|
| `hop-dong` | Hợp đồng lao động |
| `luong` | Lương, thưởng, phụ cấp |
| `nghi-phep` | Nghỉ phép, nghỉ lễ |
| `bhxh` | Bảo hiểm xã hội, y tế |
| `tranh-chap` | Tranh chấp, sa thải |
| `khac` | Các chủ đề khác |

---

## ⚠️ Mã lỗi

| HTTP Code | Ý nghĩa |
|---|---|
| 200 | Thành công |
| 400 | Dữ liệu đầu vào không hợp lệ |
| 401 | Chưa đăng nhập hoặc token hết hạn |
| 403 | Không có quyền thực hiện |
| 404 | Không tìm thấy tài nguyên |
| 500 | Lỗi server |

---

> 📌 **Lưu ý:** Mọi thay đổi API phải cập nhật file này và thông báo cho cả nhóm trước khi triển khai.
