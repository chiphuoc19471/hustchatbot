import os
import glob
import json
import re

# Thư viện của Langchain dùng để cắt văn bản
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# XỬ LÝ BẢNG BIỂU 
# LLM đọc Markdown Table thuần túy rất kém. Nếu bảng bị cắt đôi giữa 2 chunk, LLM sẽ hoàn toàn mù tịt. Giải pháp ở đây là biến bảng thành các câu văn xuôi, cất đi, cắt chunk xong mới nhét lại.

def _fill_merged_cells(table_text: str) -> str:
    """
    Hàm này "kéo" giá trị từ hàng trên xuống ô rỗng bên dưới để khôi phục dữ liệu bảng.
    """
    lines = table_text.split('\n')
    prev_cells: list[str] = [] # Lưu lại giá trị của hàng liền trước
    result = []
    
    for line in lines:
        if not line.startswith('|'):
            result.append(line)
            continue
            
        # Tách hàng thành các ô 
        cells = [c.strip() for c in line.split('|')]
        
        # Bỏ qua dòng phân cách của Markdown table 
        if all(re.match(r'^[-:]+$', c) or c == '' for c in cells if c):
            prev_cells = []
            result.append(line)
            continue
            
        # Nếu có hàng trước đó, bắt đầu điền vào ô trống
        if prev_cells:
            filled = list(cells)
            for i, cell in enumerate(cells):
                # Nếu ô hiện tại rỗng và ô phía trên có chữ -> Lấy chữ phía trên đắp xuống
                if cell == '' and i < len(prev_cells) and prev_cells[i]:
                    filled[i] = prev_cells[i]
            prev_cells = filled
            result.append('|' + '|'.join(filled[1:-1]) + '|')
        else:
            prev_cells = cells
            result.append(line)
            
    return '\n'.join(result)

def _table_to_prose(table_text: str) -> str:
    """
    Biến bảng thành văn xuôi do LLM sẽ đọc tốt hơn. 
    Thay vì để: | HP lý thuyết | 3(2-1) |
    Sẽ biến thành: "Cột 1: HP lý thuyết, Cột 2: 3(2-1)."
    """
    # Hàm phụ để tách các ô trong 1 hàng
    def parse_row(line: str) -> list[str]:
        cells = line.split('|')
        if cells and cells[0].strip() == '': cells = cells[1:]
        if cells and cells[-1].strip() == '': cells = cells[:-1]
        return [c.strip() for c in cells]

    # Hàm phụ kiểm tra xem có phải dòng gạch ngang |---| không
    def is_separator(cells: list[str]) -> bool:
        return bool(cells) and all(re.match(r'^[-:]+$', c) or c == '' for c in cells)

    # Lọc lấy tất cả các hàng có chứa dữ liệu
    rows = [parse_row(l) for l in table_text.strip().split('\n') if l.strip().startswith('|')]
    if not rows: return table_text

    # Tìm vị trí của dòng phân cách để biết đâu là Header, đâu là Data
    sep_idx = next((i for i, r in enumerate(rows) if is_separator(r)), -1)
    if sep_idx == -1:
        header_rows, data_rows = rows[:1], rows[1:]
    else:
        header_rows, data_rows = rows[:sep_idx], rows[sep_idx + 1:]

    if not header_rows or not data_rows: return table_text

    # Xử lý Header: Nếu bảng có nhiều dòng tiêu đề, nó sẽ ghép lại
    num_cols = max(len(r) for r in header_rows + data_rows)
    merged_headers: list[str] = []
    for col in range(num_cols):
        parts = [hr[col] for hr in header_rows if col < len(hr) and hr[col]]
        merged_headers.append(' / '.join(parts) if parts else f'Cột {col + 1}')

    # Nối từng hàng dữ liệu thành 1 câu hoàn chỉnh
    sentences: list[str] = []
    for row in data_rows:
        parts = []
        for i, cell in enumerate(row):
            if not cell: continue
            header = merged_headers[i] if i < len(merged_headers) else f'Cột {i + 1}'
            parts.append(f'{header}: {cell}')
        # Gộp lại bằng dấu phẩy và kết thúc bằng dấu chấm
        if parts: sentences.append(', '.join(parts) + '.')

    return '\n'.join(sentences) if sentences else table_text

def extract_tables(md_text: str) -> tuple[str, dict]:
    """
    Kỹ thuật "Placeholder". 
    Hàm này cho các bảng ra khỏi text, thay thế nó bằng dòng chữ như {{TABLE_0}}.
    Mục đích: Không cho Langchain cắt đứt đôi cái bảng. Bảng được cất an toàn trong biến `tables`.
    """
    tables: dict[str, str] = {}
    table_idx = 0
    # Dùng regex tìm các đoạn text bắt đầu bằng dấu | (tức là bảng Markdown)
    table_pattern = re.compile(r'(?:^\|[^\n]*\n)+', re.MULTILINE)

    def replace_table(match: re.Match) -> str:
        nonlocal table_idx
        key = f'{{{{TABLE_{table_idx}}}}}' # Tạo placeholder, vd: {{TABLE_0}}
        # Điền ô trống -> Chuyển thành văn xuôi -> Lưu vào từ điển `tables`
        filled = _fill_merged_cells(match.group(0).rstrip('\n'))
        tables[key] = _table_to_prose(filled)
        table_idx += 1
        return f'\n{key}\n' # Trả về placeholder đặt vào chỗ cũ

    text_with_placeholders = table_pattern.sub(replace_table, md_text)
    return text_with_placeholders, tables

def restore_tables(text: str, tables: dict) -> str:
    """
    Sau khi Langchain cắt chunk xong, hàm này tìm lại các chữ {{TABLE_0}}
    và nhét nội dung văn xuôi của bảng trả lại vào đúng vị trí đó.
    """
    for key, table in tables.items():
        text = text.replace(key, table)
    return text

#CHUẨN HÓA HEADING & ẢNH
def strip_images(md_text: str) -> str:
    return re.sub(r'!\[.*?\]\(.*?\)', '', md_text)

def fix_markdown_hierarchy(md_text: str) -> str:
    """
    Langchain chia chunk dựa vào số lượng dấu #.
    Hàm này đảm bảo mọi "Chương" đều là H1 (#), "Mục" là H2 (##), "Điều" là H3 (###).
    """
    md_text = re.sub(r'^(#+)\s*\**\s*(Chương\s+[IVXLCDM\d]+)\s*\**', r'# \2', md_text, flags=re.MULTILINE | re.IGNORECASE)
    md_text = re.sub(r'^(#+)\s*\**\s*(Mục\s+\d+)\s*\**', r'## \2', md_text, flags=re.MULTILINE | re.IGNORECASE)
    md_text = re.sub(r'^(#+)\s*\**\s*(Điều\s+\d+\.?)\s*\**', r'### \2', md_text, flags=re.MULTILINE | re.IGNORECASE)
    return md_text

#HÀM CHUNKING 
def chunk_markdown_files(processed_dir: str = 'processed_2', chunk_dir: str = 'chunks') -> None:
    # 1. Khởi tạo thư mục đầu ra
    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)

    # 2. Tìm tất cả file .md cần cắt
    md_files = glob.glob(os.path.join(processed_dir, '*.md'))
    if not md_files:
        print(f"Không tìm thấy file .md nào trong '{processed_dir}'.")
        return

    # 3. Cấu hình Langchain Chunker
    # Định nghĩa cấu trúc phân cấp: Cứ gặp # thì Langchain gom vào thuộc tính "Chương" trong Metadata
    headers_to_split_on = [
        ("#",   "Chương"),
        ("##",  "Mục"),
        ("###", "Điều"),
    ]
    # Chunker 1: Chuyên cắt theo dấu # (Giúp 1 quy định luôn nằm trọn trong 1 chunk, không bị cắt ngang câu)
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
    
    # Chunker 2: Nếu có 1 Điều luật dài quá 2000 ký tự, Chunker 1 sẽ thất bại. 
    # Ta dùng Chunker 2 để cắt nhỏ tiếp theo dấu chấm câu, dấu xuống dòng.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200, separators=["\n\n", "\n", ".", "?", "!", " ", ""], length_function=len)

    # 4. Vòng lặp xử lý từng file
    for md_path in md_files:
        filename = os.path.basename(md_path)
        print(f"Đang chunking: {filename}...")

        # Đọc text trong file
        with open(md_path, 'r', encoding='utf-8') as f:
            raw_md = f.read()

        # Áp dụng các bộ lọc làm sạch
        fixed_md = fix_markdown_hierarchy(raw_md)
        fixed_md = strip_images(fixed_md)
        
        # cấ3t bảng đi
        md_no_tables, tables = extract_tables(fixed_md)
        
        # Thực hiện việc cắt (Cắt theo # trước, sau đó cắt theo số lượng ký tự)
        md_header_splits = markdown_splitter.split_text(md_no_tables)
        final_splits = text_splitter.split_documents(md_header_splits)

        chunks_data = []
        # Duyệt qua từng Chunk đã cắt thành công
        for i, doc in enumerate(final_splits):
            # Nhét lại các bảng biểu
            text_with_tables = restore_tables(doc.page_content, tables)
            
            # meta data
            chunk_metadata = dict(doc.metadata) # Lấy meta có sẵn của Langchain (như Chương mấy, Điều mấy)
            chunk_metadata["Source"] = filename # Ghi chú Chunk này xuất phát từ file nào
            chunk_metadata["Chunk_ID"] = i + 1  # Đánh số thứ tự Chunk
            

            # Đóng gói dữ liệu thành 1 object
            chunks_data.append({
                "chunk_id": i + 1,
                "text": text_with_tables,
                "metadata": chunk_metadata
            })

        # 5. Lưu toàn bộ các chunk của file hiện tại thành file JSON
        json_filename = filename.replace('.md', '.json')
        json_path = os.path.join(chunk_dir, json_filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=4)

        print(f"  [OK] {len(chunks_data)} chunks → {json_path}")
        if tables: print(f"       (Đã xử lý {len(tables)} bảng biểu)")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    chunk_markdown_files()