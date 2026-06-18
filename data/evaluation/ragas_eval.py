import os
import sys
import json
import pandas as pd
from datetime import datetime
from datasets import Dataset
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rag.pipeline import answer

from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness, context_recall, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()


def main():
    print("🚀 Bắt đầu quá trình Evaluation bằng RAGAS...")

    test_file = os.path.join(os.path.dirname(__file__), 'test_questions.json')
    with open(test_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    questions, ground_truths, answers, contexts_list = [], [], [], []

    print(f"✅ Đã tải {len(test_data)} câu hỏi kiểm thử.")
    print("⏳ Đang gọi RAG Pipeline để lấy câu trả lời (Có thể mất vài phút)...")

    for i, item in enumerate(test_data):
        q = item['question']
        gt = item['ground_truth']
        print(f"   [{i+1}/{len(test_data)}] Đang xử lý: {q}")

        result = answer(query=q)
        ans = result.get('answer', '')
        # Dùng raw contexts (luôn có) thay vì sources (có thể rỗng khi không cite)
        ctxs = [t for t in result.get('contexts', []) if t]

        questions.append(q)
        ground_truths.append(gt)
        answers.append(ans)
        contexts_list.append(ctxs if ctxs else [''])

    # RAGAS 0.1.14 — column names: question / answer / contexts / ground_truth
    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
    })

    print("🔥 Đang khởi tạo LLM và Embeddings (RAGAS 0.1.14)...")
    llm = LangchainLLMWrapper(ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4.1-mini"), temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")))

    metrics = [answer_relevancy, faithfulness, context_recall, context_precision]
    # metrics = [answer_relevancy]
    for m in metrics:
        m.llm = llm
    answer_relevancy.embeddings = embeddings

    print("🔥 Đang gửi dữ liệu lên RAGAS để chấm điểm...")
    result_eval = evaluate(dataset=dataset, metrics=metrics)

    print("\n==============================")
    print("📊 KẾT QUẢ ĐÁNH GIÁ TỔNG QUAN")
    print("==============================")
    print(result_eval)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    df = result_eval.to_pandas()
    output_file = os.path.join(os.path.dirname(__file__), f'eval_results_{timestamp}.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 Đã lưu chi tiết điểm số vào: {output_file}")

    history_file = os.path.join(os.path.dirname(__file__), 'evaluation_history.log')
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] Metrics: {result_eval}\n")
        f.write(f"             Chi tiết tại: eval_results_{timestamp}.csv\n")
        f.write("-" * 50 + "\n")
    print(f"📝 Đã ghi nhận lịch sử vào: {history_file}")


if __name__ == "__main__":
    main()
