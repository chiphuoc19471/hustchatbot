import os
import sys
import json
import pandas as pd
from datetime import datetime
from datasets import Dataset
from dotenv import load_dotenv

# Thêm thư mục gốc vào sys.path để import rag.pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rag.pipeline import answer

# --- PATCH FOR RAGAS ON LANGCHAIN >= 0.2.0 ---
import sys
try:
    import langchain_google_vertexai
    sys.modules['langchain_community.chat_models.vertexai'] = langchain_google_vertexai
except ImportError:
    pass
# ----------------------------------------------------

from ragas import evaluate
from ragas.metrics import (
    AnswerRelevancy,
    Faithfulness,
    ContextPrecision,
    ContextRecall
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

load_dotenv()

def main():
    print("🚀 Bắt đầu quá trình Evaluation bằng RAGAS...")
    
    # 1. Đọc dữ liệu test
    test_file = os.path.join(os.path.dirname(__file__), 'test_questions.json')
    with open(test_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
        
    questions = []
    ground_truths = []
    answers = []
    contexts_list = []
    
    print(f"✅ Đã tải {len(test_data)} câu hỏi kiểm thử.")
    print("⏳ Đang gọi RAG Pipeline để lấy câu trả lời (Có thể mất vài phút)...")
    
    # 2. Lấy câu trả lời từ hệ thống RAG
    for i, item in enumerate(test_data):
        q = item['question']
        gt = item['ground_truth']
        print(f"   [{i+1}/{len(test_data)}] Đang xử lý: {q}")
        
        # Gọi RAG pipeline
        result = answer(query=q)
        ans = result.get('answer', '')
        
        # Trích xuất đoạn văn bản từ các source để làm context
        ctxs = [s.get('full_text', s.get('trich_doan', '')) for s in result.get('sources', [])]
        
        questions.append(q)
        ground_truths.append(gt)
        answers.append(ans)
        contexts_list.append(ctxs)
        
    # 3. Chuyển sang định dạng của HuggingFace Dataset (theo API của RAGAS 0.2.2)
    dataset_dict = {
        "user_input": questions,
        "response": answers,
        "retrieved_contexts": contexts_list,
        "reference": ground_truths
    }
    dataset = Dataset.from_dict(dataset_dict)
    
    print("🔥 Đang khởi tạo LLM và Embeddings model (chuẩn RAGAS 0.2.2)...")
    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
    evaluator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

    print("🔥 Đang gửi dữ liệu lên RAGAS để chấm điểm...")
    # 4. Chạy evaluate
    # Chú ý: RAGAS 0.2.2 yêu cầu truyền rõ ràng llm và embeddings đã được wrap
    result_eval = evaluate(
        dataset=dataset,
        metrics=[
            ContextPrecision(),
            ContextRecall(),
            Faithfulness(),
            AnswerRelevancy(),
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings
    )
    
    print("\n==============================")
    print("📊 KẾT QUẢ ĐÁNH GIÁ TỔNG QUAN")
    print("==============================")
    print(result_eval)
    
    # Tạo timestamp cho tên file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 5. Lưu kết quả chi tiết với timestamp
    df = result_eval.to_pandas()
    output_file = os.path.join(os.path.dirname(__file__), f'eval_results_{timestamp}.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 Đã lưu chi tiết điểm số vào: {output_file}")
    
    # 6. Ghi chú log lịch sử để dễ so sánh
    history_file = os.path.join(os.path.dirname(__file__), 'evaluation_history.log')
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] Metrics: {result_eval}\n")
        f.write(f"             Chi tiết tại: eval_results_{timestamp}.csv\n")
        f.write("-" * 50 + "\n")
    print(f"📝 Đã ghi nhận lịch sử vào: {history_file}")

if __name__ == "__main__":
    main()
