"""
Bước 1: Chuyển PDF → Markdown bằng OpenDataLoader PDF.
Yêu cầu: Java 11+ và opendataloader-pdf

Chạy:
    python data/parse_pdf.py
"""
import os

try:
    import opendataloader_pdf
except ImportError:
    print("Vui lòng cài: pip install opendataloader-pdf")
    print("Yêu cầu: Java 11+  (kiểm tra: java -version)")
    exit(1)


def parse_all_pdfs(raw_dir: str = 'raw', processed_dir: str = 'processed') -> None:
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir)
        print(f"Đã tạo thư mục '{raw_dir}'. Vui lòng copy các file PDF quy chế HUST vào đây.")
        return

    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)

    pdf_files = [f for f in os.listdir(raw_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"Không tìm thấy file PDF nào trong '{raw_dir}'.")
        return

    print(f"Tìm thấy {len(pdf_files)} file PDF. Đang chuyển đổi sang Markdown bằng OpenDataLoader...")
    print("(Lưu ý: OpenDataLoader khởi động JVM lần đầu có thể mất vài giây)\n")

    # Batch convert tất cả trong một lần gọi (mỗi lần gọi convert() tạo một JVM process)
    opendataloader_pdf.convert(
        input_path=[raw_dir],
        output_dir=processed_dir,
        format="markdown"
    )

    print(f"\nHoàn tất! Markdown đã lưu tại: {processed_dir}/")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parse_all_pdfs()
