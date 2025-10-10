# app.py
import streamlit as st
from docx import Document
import re
import pandas as pd
import math

# --------------------------
# Helpers
# --------------------------
def clean_text(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def is_ref_paragraph(text: str) -> bool:
    # Xác định paragraph chỉ chứa Ref hoặc bắt đầu bằng Ref:
    return bool(re.match(r'(?i)^\s*ref[:.]', text)) or bool(re.match(r'(?i)^ref\b', text))

# --------------------------
# Parse CABBANK (đã ổn)
# --------------------------
def parse_cabbank(source):
    doc = Document(source)
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    questions = []
    current = {"question": "", "options": [], "answer": ""}

    # Match options only when marker appears at start or after whitespace (avoid A/C...)
    opt_pat = re.compile(r'(?<!\S)(?P<star>\*)?(?P<letter>[A-Da-d])\s*(?:[.\)])\s*')

    for p in paras:
        text = p
        if is_ref_paragraph(text):
            # bỏ qua dòng Ref
            continue
        matches = list(opt_pat.finditer(text))
        if not matches:
            # không phải đoạn option => câu hỏi (hoặc nối tiếp)
            if current["options"]:
                # đã có options → bắt đầu câu mới
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": text, "options": [], "answer": ""}
            else:
                # nối tiếp câu hỏi
                current["question"] = (current["question"] + " " + text).strip() if current["question"] else text
            continue

        # Có ít nhất 1 marker trong paragraph
        pre = text[:matches[0].start()].strip()
        if pre:
            # pre có thể là phần câu hỏi (hoặc nếu đã có options thì pre là câu mới)
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": pre, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre).strip() if current["question"] else pre

        # Lấy từng option theo các matches
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(text)
            body = clean_text(text[start:end])
            letter = m.group("letter").lower()
            opt_text = f"{letter}. {body}" if body else f"{letter}."
            current["options"].append(opt_text)
            if m.group("star"):
                current["answer"] = opt_text

    # finalize last
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    return questions

# --------------------------
# Parse LAWBANK (robust)
# --------------------------
def parse_lawbank(source):
    """
    - Duyệt paragraph tuần tự.
    - Xác định paragraph bắt đầu câu hỏi khi:
        * paragraph văn bản bắt đầu bằng '^\d+.'  (ví dụ "1. Who ...")
      OR
        * paragraph có numPr (auto-numbering) với ilvl == 0 (top-level list)
    - Bỏ qua các paragraph Ref...
    - Ghép các paragraph không phải question-start vào block hiện tại.
    - Sau khi có block, trích đáp án bằng regex an toàn.
    """
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file {source}: {e}")
        return []

    blocks = []
    current_block = None
    question_counter = 1

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        # Bỏ qua paragraph ref
        if is_ref_paragraph(text):
            continue

        # Kiểm tra numPr và ilvl (nếu có)
        numPr_nodes = p._element.xpath(".//w:numPr")
        ilvl = None
        if numPr_nodes:
            ilvl_nodes = p._element.xpath(".//w:numPr/w:ilvl")
            if ilvl_nodes and ilvl_nodes[0].text is not None:
                try:
                    ilvl = int(ilvl_nodes[0].text)
                except:
                    ilvl = None

        starts_with_number = bool(re.match(r'^\d+\.\s+', text))
        is_question_start = False

        # Nếu paragraph có numPr và là level 0 => coi là bắt đầu câu hỏi
        if numPr_nodes and ilvl == 0:
            is_question_start = True
        # Nếu văn bản bắt đầu bằng digit + '.' => cũng coi là question start
        if starts_with_number:
            is_question_start = True

        if is_question_start:
            # Lấy số nếu có trong text để đồng bộ counter
            if starts_with_number:
                m = re.match(r'^(\d+)\.\s*(.*)$', text)
                if m:
                    num = int(m.group(1))
                    rest = m.group(2).strip()
                    # đồng bộ counter (tránh sai lệch nếu doc có jump)
                    question_counter = num + 1
                    block_text = f"{num}. {rest}" if rest else f"{num}."
                else:
                    # đánh số thủ công
                    block_text = f"{question_counter}. {text}"
                    question_counter += 1
            else:
                # paragraph có numPr level 0 nhưng không chứa số literal -> thêm số do chúng ta đoán
                block_text = f"{question_counter}. {text}"
                question_counter += 1

            # finalize previous block nếu có
            if current_block:
                blocks.append(current_block)
            current_block = block_text
        else:
            # đoạn không phải bắt đầu câu hỏi: nối vào block hiện tại (nếu có), hoặc tạo block mới (đề phòng file lạ)
            if current_block:
                current_block += " " + text
            else:
                # trường hợp hiếm: văn bản trước question start, tạo block tạm
                current_block = text

    # Thêm block cuối cùng
    if current_block:
        blocks.append(current_block)

    # Bây giờ xử lý từng block để tách question/options
    questions = []
    # regex option: chỉ match nếu ký tự nằm ở đầu chuỗi hoặc sau whitespace (không match A/C)
    opt_pat = re.compile(r'(?<!\S)(?P<star>\*)?(?P<letter>[A-Da-d])\s*(?:[.\)])\s*')

    for block in blocks:
        b = clean_text(block)
        # Loại bỏ những mẩu Ref còn sót trong block (nếu Ref đứng giữa)
        b = re.sub(r'(?i)\bRef[:.]\s*.*$', '', b).strip()

        # Tìm tất cả marker option
        matches = list(opt_pat.finditer(b))
        if not matches:
            # Nếu block không có options, skip (không phải câu trắc nghiệm)
            continue

        # câu hỏi là phần trước marker đầu tiên, bỏ số thứ tự ở đầu
        first = matches[0]
        qpart = b[: first.start()]
        # bỏ prefix số "N."
        qpart = re.sub(r'^\d+\.\s*', '', qpart).strip()
        qtext = clean_text(qpart)

        opts = []
        answer = ""
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(b)
            opt_body = clean_text(b[start:end])
            letter = m.group("letter").lower()
            opt_full = f"{letter}. {opt_body}" if opt_body else f"{letter}."
            opts.append(opt_full)
            if m.group("star"):
                answer = opt_full

        if not answer and opts:
            answer = opts[0]

        questions.append({"question": qtext, "options": opts, "answer": answer})

    return questions

# --------------------------
# UI chính
# --------------------------
st.set_page_config(page_title="Ngân hàng trắc nghiệm (Lawbank & Cabbank)", layout="wide")
st.title("📚 Ngân hàng câu hỏi")

# uploader (tùy chọn)
uploaded = st.file_uploader("Upload file .docx (nếu muốn test file riêng)", type=["docx"])

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])

source = uploaded if uploaded is not None else ("cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx")

# parse theo bank
if "Kỹ thuật" in bank_choice:
    questions = parse_cabbank(source)
else:
    questions = parse_lawbank(source)

# Debug: hiển thị thông tin chi tiết giúp rà lỗi
with st
