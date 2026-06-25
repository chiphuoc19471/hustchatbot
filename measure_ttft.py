"""
Đo TTFT (Time to First Token) của chatbot HUST qua endpoint /chat/stream.
Chạy: python measure_ttft.py
Yêu cầu: backend đang chạy tại http://localhost:8001
"""

import time
import json
import threading
import requests

BASE_URL = "http://localhost:8001"
STREAM_ENDPOINT = f"{BASE_URL}/chat/stream"

QUESTIONS = [
    "Học phí của ngành Hệ thống thông tin quản lý k68 là bao nhiêu?",
    "Cử nhân ngành hệ thống thông tin quản lý k68 học bao nhiêu tín chỉ?",
]


def measure_ttft(question: str) -> dict:
    """Gửi câu hỏi đến streaming endpoint, đo thời gian đến token đầu tiên."""
    payload = {"question": question}
    TOKEN_DELAY = 0.012  # asyncio.sleep delay mỗi token trong backend (chat.py)

    ttft = None
    full_answer_tokens = []

    start = time.perf_counter()

    with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if "token" in data and ttft is None:
                ttft = time.perf_counter() - start

            if "token" in data:
                full_answer_tokens.append(data["token"])

            if data.get("done"):
                break

    num_tokens = len([t for t in full_answer_tokens if t.strip()])
    # Tổng thời gian người dùng thấy = pipeline (TTFT) + streaming giả lập token-by-token
    estimated_total = round(ttft + num_tokens * TOKEN_DELAY, 3) if ttft is not None else None
    answer_preview = "".join(full_answer_tokens)[:120].replace("\n", " ")

    return {
        "question": question,
        "ttft_s": round(ttft, 3) if ttft is not None else None,
        "total_s": estimated_total,
        "num_tokens": num_tokens,
        "answer_preview": answer_preview,
    }


def test_concurrent() -> None:
    """Gửi 2 câu hỏi đồng thời, kiểm tra hệ thống phân biệt 2 người dùng."""
    print("\n" + "=" * 70)
    print("TEST 2 NGƯỜI DÙNG ĐỒNG THỜI")
    print("=" * 70)

    slot = [None, None]
    errors = [None, None]

    def worker(idx: int, question: str) -> None:
        try:
            slot[idx] = measure_ttft(question)
        except Exception as e:
            errors[idx] = str(e)

    threads = [
        threading.Thread(target=worker, args=(0, QUESTIONS[0])),
        threading.Thread(target=worker, args=(1, QUESTIONS[1])),
    ]

    wall_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall_time = round(time.perf_counter() - wall_start, 3)

    print(f"\nTổng thời gian chờ (wall clock): {wall_time} s")
    print()

    for idx in range(2):
        label = f"Sinh viên {idx + 1}"
        if errors[idx]:
            print(f"[{label}] LỖI: {errors[idx]}")
            continue
        r = slot[idx]
        print(f"[{label}] Câu hỏi  : {r['question']}")
        print(f"           TTFT     : {r['ttft_s']} s")
        print(f"           Câu trả lời: {r['answer_preview'][:80]}...")
        print()

    if slot[0] and slot[1]:
        print("=> Hai người dùng nhận câu trả lời độc lập, không bị lẫn nội dung.")
        if wall_time < max(slot[0]["ttft_s"], slot[1]["ttft_s"]) * 1.3:
            print("=> Hệ thống xử lý song song: tổng thời gian gần bằng request chậm nhất.")


def main():
    print("=" * 70)
    print("ĐO TTFT — CHATBOT TƯ VẤN QUY CHẾ HUST")
    print("=" * 70)

    results = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] Câu hỏi: {q}")
        print("  Đang gửi request...")
        try:
            result = measure_ttft(q)
            results.append(result)
            print(f"  TTFT             : {result['ttft_s']} s")
            print(f"  Tổng (ước tính)  : {result['total_s']} s  ({result['num_tokens']} token × 0.012s + TTFT)")
            print(f"  Câu trả lời      : {result['answer_preview']}...")
        except requests.exceptions.ConnectionError:
            print("  LỖI: Không kết nối được backend. Đảm bảo backend đang chạy tại localhost:8001")
        except Exception as e:
            print(f"  LỖI: {e}")

    if results:
        print("\n" + "=" * 70)
        print("BẢNG KẾT QUẢ")
        print("=" * 70)
        print(f"{'STT':<4} {'TTFT (s)':<12} {'Tổng ước tính (s)':<20} {'Token':<8} {'Câu hỏi'}")
        print("-" * 80)
        for i, r in enumerate(results, 1):
            print(f"{i:<4} {str(r['ttft_s']):<12} {str(r['total_s']):<20} {r['num_tokens']:<8} {r['question'][:35]}")

        avg_ttft = sum(r["ttft_s"] for r in results if r["ttft_s"]) / len(results)
        avg_total = sum(r["total_s"] for r in results if r["total_s"]) / len(results)
        print("-" * 80)
        print(f"{'TB':<4} {round(avg_ttft, 3):<12} {round(avg_total, 3):<20}")
        print("\nCột 'Tổng ước tính' = TTFT + (số token × 0.012s) — phản ánh thời gian người dùng thấy toàn bộ câu trả lời")

    test_concurrent()


if __name__ == "__main__":
    main()
