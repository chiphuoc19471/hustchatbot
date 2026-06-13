"""
Bước 2: Format-aware chunking — cắt theo cấu trúc Chương/Mục/Điều/Khoản.
Xử lý bảng biểu: tách bảng → placeholder trước khi chunk → chèn lại sau khi chunk.

Chạy:
    python data/chunking.py
"""
import os
import glob
import json
import re

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


# ===== XỬ LÝ BẢNG BIỂU =====

def _fill_merged_cells(table_text: str) -> str:
    """
    Điền giá trị ô trống từ hàng trên xuống để phục hồi merged cells.
    Bỏ qua dòng phân cách (chứa ---).
    """
    lines = table_text.split('\n')
    prev_cells: list[str] = []
    result = []
    for line in lines:
        if not line.startswith('|'):
            result.append(line)
            continue
        cells = [c.strip() for c in line.split('|')]
        # Dòng phân cách |---|---|
        if all(re.match(r'^[-:]+$', c) or c == '' for c in cells if c):
            prev_cells = []
            result.append(line)
            continue
        if prev_cells:
            filled = list(cells)
            for i, cell in enumerate(cells):
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
    Chuyển markdown table thành câu văn xuôi dạng "header: value".
    Mỗi hàng dữ liệu → 1 câu, giúp embedding và LLM đọc tốt hơn raw markdown.
    Hỗ trợ bảng có nhiều dòng header (multi-level): ghép các header lại bằng ' / '.
    """
    def parse_row(line: str) -> list[str]:
        cells = line.split('|')
        if cells and cells[0].strip() == '':
            cells = cells[1:]
        if cells and cells[-1].strip() == '':
            cells = cells[:-1]
        return [c.strip() for c in cells]

    def is_separator(cells: list[str]) -> bool:
        return bool(cells) and all(re.match(r'^[-:]+$', c) or c == '' for c in cells)

    rows = [parse_row(l) for l in table_text.strip().split('\n')
            if l.strip().startswith('|')]

    if not rows:
        return table_text

    # Tìm vị trí dòng phân cách |---|
    sep_idx = next((i for i, r in enumerate(rows) if is_separator(r)), -1)

    if sep_idx == -1:
        header_rows, data_rows = rows[:1], rows[1:]
    else:
        header_rows, data_rows = rows[:sep_idx], rows[sep_idx + 1:]

    if not header_rows or not data_rows:
        return table_text

    # Ghép nhiều dòng header thành 1 dòng (multi-level header)
    num_cols = max(len(r) for r in header_rows + data_rows)
    merged_headers: list[str] = []
    for col in range(num_cols):
        parts = [hr[col] for hr in header_rows if col < len(hr) and hr[col]]
        merged_headers.append(' / '.join(parts) if parts else f'Cột {col + 1}')

    # Sinh câu văn xuôi cho từng hàng dữ liệu
    sentences: list[str] = []
    for row in data_rows:
        parts = []
        for i, cell in enumerate(row):
            if not cell:
                continue
            header = merged_headers[i] if i < len(merged_headers) else f'Cột {i + 1}'
            parts.append(f'{header}: {cell}')
        if parts:
            sentences.append(', '.join(parts) + '.')

    return '\n'.join(sentences) if sentences else table_text


def extract_tables(md_text: str) -> tuple[str, dict]:
    """
    Tách các bảng markdown ra khỏi văn bản, thay bằng placeholder {{TABLE_N}}.
    Pipeline xử lý bảng: fill merged cells → chuyển sang văn xuôi → lưu vào dict.

    Returns:
        text_with_placeholders: văn bản đã thay bảng bằng placeholder
        tables: dict ánh xạ placeholder → nội dung bảng dạng văn xuôi
    """
    tables: dict[str, str] = {}
    table_idx = 0

    # Match các dòng liên tiếp bắt đầu bằng |
    table_pattern = re.compile(r'(?:^\|[^\n]*\n)+', re.MULTILINE)

    def replace_table(match: re.Match) -> str:
        nonlocal table_idx
        key = f'{{{{TABLE_{table_idx}}}}}'
        filled = _fill_merged_cells(match.group(0).rstrip('\n'))
        tables[key] = _table_to_prose(filled)
        table_idx += 1
        return f'\n{key}\n'

    text_with_placeholders = table_pattern.sub(replace_table, md_text)
    return text_with_placeholders, tables


def restore_tables(text: str, tables: dict) -> str:
    """Chèn lại bảng vào đúng vị trí placeholder trong chunk."""
    for key, table in tables.items():
        text = text.replace(key, table)
    return text


# ===== CHUẨN HÓA CẤU TRÚC HEADING =====

def strip_images(md_text: str) -> str:
    """Xóa tất cả markdown image references vì LLM không đọc được file ảnh từ path."""
    return re.sub(r'!\[.*?\]\(.*?\)', '', md_text)


def fix_markdown_hierarchy(md_text: str) -> str:
    """
    Chuẩn hóa heading levels từ output của OpenDataLoader:
      # Chương  →  # Chương
      ## Mục    →  ## Mục
      ### Điều  →  ### Điều
    """
    md_text = re.sub(
        r'^(#+)\s*\**\s*(Chương\s+[IVXLCDM\d]+)\s*\**',
        r'# \2', md_text, flags=re.MULTILINE | re.IGNORECASE
    )
    md_text = re.sub(
        r'^(#+)\s*\**\s*(Mục\s+\d+)\s*\**',
        r'## \2', md_text, flags=re.MULTILINE | re.IGNORECASE
    )
    md_text = re.sub(
        r'^(#+)\s*\**\s*(Điều\s+\d+\.?)\s*\**',
        r'### \2', md_text, flags=re.MULTILINE | re.IGNORECASE
    )
    return md_text


# ===== CHUNKING CHÍNH =====

def chunk_markdown_files(processed_dir: str = 'processed', chunk_dir: str = 'chunks') -> None:
    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)

    md_files = glob.glob(os.path.join(processed_dir, '*.md'))
    if not md_files:
        print(f"Không tìm thấy file .md nào trong '{processed_dir}'.")
        return

    headers_to_split_on = [
        ("#",   "Chương"),
        ("##",  "Mục"),
        ("###", "Điều"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    # Fallback chunker cho các Điều quá dài
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", "?", "!", " ", ""],
        length_function=len,
    )

    for md_path in md_files:
        filename = os.path.basename(md_path)
        print(f"Đang chunking: {filename}...")

        with open(md_path, 'r', encoding='utf-8') as f:
            raw_md = f.read()

        # Bước 1: Chuẩn hóa heading
        fixed_md = fix_markdown_hierarchy(raw_md)

        # Bước 1b: Xóa ảnh (không hữu ích với RAG text-only)
        fixed_md = strip_images(fixed_md)

        # Bước 2: Tách bảng ra, thay bằng placeholder
        md_no_tables, tables = extract_tables(fixed_md)

        # Bước 3: Chunking theo heading Chương/Mục/Điều
        md_header_splits = markdown_splitter.split_text(md_no_tables)

        # Bước 4: Cắt nhỏ tiếp các đoạn quá dài
        final_splits = text_splitter.split_documents(md_header_splits)

        # Bước 5: Chèn lại bảng vào từng chunk
        chunks_data = []
        for i, doc in enumerate(final_splits):
            text_with_tables = restore_tables(doc.page_content, tables)
            chunk_metadata = dict(doc.metadata)
            chunk_metadata["Source"] = filename
            chunk_metadata["Chunk_ID"] = i + 1

            chunks_data.append({
                "chunk_id": i + 1,
                "text": text_with_tables,
                "metadata": chunk_metadata
            })

        json_filename = filename.replace('.md', '.json')
        json_path = os.path.join(chunk_dir, json_filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=4)

        print(f"  [OK] {len(chunks_data)} chunks → {json_path}")
        if tables:
            print(f"       (Đã xử lý {len(tables)} bảng biểu)")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    chunk_markdown_files()
