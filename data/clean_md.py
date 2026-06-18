import os
import glob
import re

def clean_hust_regulation(text: str) -> str:
    # 1. Sửa lỗi OCR 
    text = text.replace('ƣ', 'ư').replace('Ƣ', 'Ư')
    text = text.replace('QĐÐ', 'QĐ').replace('QUYÉT', 'QUYẾT').replace('ĐÓC', 'ĐỐC')
    text = text.replace('Nơinhận:', 'Nơi nhận:').replace('Nơinhận', 'Nơi nhận')
    text = text.replace('ĐẠIHỌCBÁCHKHOAHÀNỘI', 'ĐẠI HỌC BÁCH KHOA HÀ NỘI')
    text = text.replace('Độclập-Tựdo-Hạnhphúc', 'Độc lập - Tự do - Hạnh phúc')

    # 2. Xóa Mục lục, Rác hình ảnh & Số trang
    text = re.sub(r'(?i)(##\s*)?MỤC LỤC.*?((?=#\s*CHƯƠNG)|(?=CHƯƠNG\s+[IVXLCDM])|(?=###\s*Điều))', '', text, flags=re.DOTALL)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'^\s*\d{1,2}\s*$', '', text, flags=re.MULTILINE)

    # 3. Xóa Quốc hiệu & Tiêu ngữ
    noise_patterns = [
        r'BỘ GIÁO DỤC VÀ ĐÀO TẠO',
        r'ĐẠI HỌC BÁCH KHOA HÀ NỘI',
        r'TRƯỜNG ĐH BÁCH KHOA HÀ NỘI',
        r'TRƯỜNG ĐẠI HỌC BÁCH KHOA HÀ NỘI',
        r'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\s*Độc lập [–\-] Tự do [–\-] Hạnh phúc',
        r'CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\s*Độc lập [–\-] Tự do [–\-] Hạnh phúc',
        r'CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM',
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # 4. Xóa vỏ bọc Quyết định ban hành
    text = re.sub(r'(?i)(?:Căn cứ|Theo đề nghị|việc Quy định chi tiết).*?(?=QUY CHẾ|HƯỚNG DẪN|QUY ĐỊNH|###\s*Điều 1)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)(?:###\s*)?QUYẾT ĐỊNH:[\s\S]*?chịu trách nhiệm thi hành Quy[eế]t định này\./\.', '', text)
    text = re.sub(r'(?i)QUYẾT ĐỊNH Về việc ban hành[\s\S]*?chịu trách nhiệm thi hành Quy[eế]t định này\./\.', '', text)

    # 5. Xóa Chữ ký và Nơi nhận
    text = re.sub(r'(?i)Nơi\s*nhận:[\s\S]*?(?:Lưu:\s*.*?[\.\n])', '', text)
    signatures = [
        r'(?:KT\.\s*)?GIÁM ĐỐC', r'(?:KT\.\s*)?HIỆU TRƯỞNG', r'PHÓ GIÁM ĐỐC',
        r'PHÓ HIỆU TRƯỞNG', r'HÓ GIÁMĐÓC', r'(?:PGS\.TS\.|GS\.TS\.).*?\n',
        r'KT\.\s*\n', r'1T\.\s*\n'
    ]
    for sig in signatures:
        text = re.sub(sig, '', text, flags=re.IGNORECASE)

    # 6. Ép chuẩn Heading
    text = re.sub(r'^#*\s*(?:[-–—_]*\s*)?(CHƯƠNG\s+[IVXLCDM]+.*)$', r'# \1', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^#*\s*[- ]*(Điều\s+\d+\.?)(.*)$', r'### \1\2', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^#*\s*[- ]*(Phụ lục\s+[IVXLCDM]+)(.*)$', r'# \1\2', text, flags=re.MULTILINE | re.IGNORECASE)

    # 7. Dọn dẹp khoảng trắng
    text = re.sub(r'^\s*-\s*-\s*', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'^#+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def process_and_clean_files(input_dir: str = 'processed', output_dir: str = 'processed_2'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    md_files = glob.glob(os.path.join(input_dir, '*.md'))
    if not md_files:
        print(f"Không tìm thấy file .md nào trong '{input_dir}'.")
        return

    for md_path in md_files:
        filename = os.path.basename(md_path)
        print(f"Đang làm sạch: {filename}...")

        with open(md_path, 'r', encoding='utf-8') as f:
            raw_md = f.read()

        # LÀM SẠCH VÀ LƯU VÀO PROCESSED_2 
        cleaned_md = clean_hust_regulation(raw_md)
        clean_path = os.path.join(output_dir, filename)
        with open(clean_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_md)

        print(f"  [OK] Đã lưu -> {clean_path}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    process_and_clean_files(input_dir='processed', output_dir='processed_2')