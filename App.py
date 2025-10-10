# app.py
import streamlit as st
from docx import Document
import re
import pandas as pd
import math

# -------------------------
# Helpers
# -------------------------
def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def is_ref_paragraph(text: str) -> bool:
    return bool(re.match(r'(?i)^\s*ref[:.]?', text))

# -------------------------
# CABBANK parser (GIỮ NGUYÊN - không chỉnh)
# -------------------------
def parse_cabbank(source):
    """
    Parser cho ngân hàng Kỹ thuật (giữ logic giống phiên bản đã chạy OK trước đó).
    - Duyệt paragraph, tìm markers a./b./c./d. trong paragraph (finditer).
    - Gom câu hỏi và options, đánh dấu đáp án *a/*b...
    """
    doc = Document(source)
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]

    questions = []
    current = {"question": "", "options": [], "answer": ""}

    # Match option marker only when at start or after whitespace (avoid matching inside A/C etc.)
    opt_pat = re.compile(r'(?<!\S)(?P<star>\*)?(?P<letter>[A-Da-d])\s*(?:[.\)])\s*')

    for p in paras:
        text = p
        if is_ref_paragraph(text):
            continue

        matches = list(opt_pat.finditer(text))
        if not matches:
            # no option marker on this paragraph
            if current["options"]:
                # we already had options -> this paragraph is the start of next question
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": text, "options": [], "answer": ""}
            else:
                # still collecting question text
                current["question"] = (current["question"] + " " + text).strip() if current["question"] else text
            continue

        # paragraph contains one or more option markers
        pre = text[:matches[0].start()].strip()
        if pre:
            if current["options"]:
                # ambiguous: finish previous question and start new
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": pre, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre).strip() if current["question"] else pre

        # extract each option by slicing between markers
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(text)
            opt_body = clean_text(text[start:end])
            letter = m.group("letter").lower()
            opt_text = f"{letter}. {opt_body}" if opt_body else f"{letter}."
            current["options"].append(opt_text)
            if m.group("star"):
                current["answer"] = opt_text

    # finalize last
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    return questions

# -------------------------
# LAWBANK parser (TẬP TRUNG CHỈNH SỬA)
# -------------------------
def parse_lawbank(source):
    """
    Robust parser for lawbank:
    - Iterate paragraphs in order.
    - Consider a paragraph to start a question if:
        * it literally starts with '^\d+\.' OR
        * it has numbering properties (numPr) with ilvl == 0 (top-level list) OR
        * heuristic: the next paragraph(s) contain option markers (a./b./c./d.)
    - Skip/strip any paragraph that is Ref...
    - After grouping paragraphs into blocks (one block per question), extract options using safe regex.
    """
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file {source}: {e}")
        return []

    # Collect paragraphs with metadata
    paras_meta = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        # detect numbering (numPr) and ilvl
        numPr_nodes = p._element.xpath(".//w:numPr")
        ilvl = None
        if numPr_nodes:
            ilvl_nodes = p._element.xpath(".//w:numPr/w:ilvl")
            if ilvl_nodes and ilvl_nodes[0].text is not None:
                try:
                    ilvl = int(ilvl_nodes[0].text)
                except:
                    ilvl = None
        paras_meta.append({"text": text, "numpr": bool(numPr_nodes), "ilvl": ilvl})

    # Precompute which paragraphs contain any option marker
    opt_pat_detect = re.compile(r'(?<!\S)(?:\*)?[A-Da-d]\s*(?:[.\)])')
    has_option = [bool(opt_pat_detect.search(p["text"])) and not is_ref_paragraph(p["text"]) for p in paras_meta]

    # Group into blocks: rule-based
    blocks = []
    current_block = None
    n = len(paras_meta)
    for i, p in enumerate(paras_meta):
        text = p["text"]
        if is_ref_paragraph(text):
            # skip ref paragraphs (they are removed)
            continue

        starts_with_number = bool(re.match(r'^\d+\.\s+', text))
        is_top_level_num = p["numpr"] and p["ilvl"] == 0

        # Heuristic: if next para contains options, treat this para as question start
        next_has_option = (i+1 < n and has_option[i+1])

        # Also if this paragraph itself contains both question text and options (detect marker but with text before)
        own_matches = list(opt_pat_detect.finditer(text))
        own_has_pretext_and_option = False
        if own_matches:
            if own_matches[0].start() > 0 and text[:own_matches[0].start()].strip():
                # there is text before first option marker -> this paragraph likely contains q + options
                own_has_pretext_and_option = True

        is_question_start = starts_with_number or is_top_level_num or next_has_option or own_has_pretext_and_option

        if is_question_start:
            # finalize previous block
            if current_block:
                blocks.append(current_block)
            current_block = text
        else:
            # continuation paragraph -> append to current block (or create temp block)
            if current_block:
                current_block += " " + text
            else:
                # start a temp block (defensive)
                current_block = text

    if current_block:
        blocks.append(current_block)

    # Now parse each block into question + options
    questions = []
    # option regex: only match letter a-d at start or after whitespace (avoid catching A/C etc.)
    opt_pat = re.compile(r'(?<!\S)(?P<star>\*)?(?P<letter>[A-Da-d])\s*(?:[.\)])')
    for block in blocks:
        b = clean_text(block)
        # remove any Ref: ... trailing in block
        b = re.sub(r'(?i)\bRef[:.]\s*.*$', '', b, flags=re.S).strip()
        matches = list(opt_pat.finditer(b))
        if not matches:
            # no options -> not a test question
            continue

        # question text is content before first match
        first = matches[0]
        q_raw = b[: first.start()]
        # remove leading numbering like "1. "
        q_raw = re.sub(r'^\d+\.\s*', '', q_raw).strip()
        q_text = clean_text(q_raw)

        opts = []
        ans = ""
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(b)
            opt_body = clean_text(b[start:end])
            letter = m.group("letter").lower()
            opt_full = f"{letter}. {opt_body}" if opt_body else f"{letter}."
            opts.append(opt_full)
            if m.group("star"):
                ans = opt_full

        if not ans and opts:
            ans = opts[0]

        questions.append({"question": q_text, "options": opts, "answer": ans})

    return questions

# -------------------------
# Streamlit UI: Debug / Dò câu
# -------------------------
st.set_page_config(page_title="Dò câu - Lawbank", layout="wide")
st.title("🔍 Dò câu — Chỉ tập trung Lawbank (cabbank giữ nguyên)")

bank_choice = st.selectbox("Chọn ngân hàng để dò:", ["Ngân hàng Luật (focus)", "Ngân hàng Kỹ thuật (giữ nguyên)"])

# Choose source files (you can upload to test)
uploaded = st.file_uploader("Upload .docx (tùy chọn) — nếu không, app sẽ dùng lawbank.docx / cabbank.docx trong thư mục", type=["docx"])

if uploaded:
    source = uploaded
else:
    source = "lawbank.docx" if "Luật" in bank_choice else "cabbank.docx"

# Parse
if "Luật" in bank_choice:
    questions = parse_lawbank(source)
else:
    # use cabbank parser as before (kept untouched)
    questions = parse_cabbank(source)

# Debug info
with st.expander("🔧 Thông tin debug"):
    try:
        doc = Document(source)
        total_paras = len([p for p in doc.paragraphs if p.text and p.text.strip()])
        st.write(f"Số paragraph (non-empty) trong file: {total_paras}")
    except Exception as e:
        st.write("Không thể đọc số paragraph:", e)
    st.write(f"Số câu parse được: {len(questions)}")
    if len(questions) > 0:
        st.write("3 câu đầu parsed (question + options + answer):")
        for i, q in enumerate(questions[:3], 1):
            st.write(f"{i}. Q: {q['question']}")
            for o in q['options']:
                st.write("   - " + o + ("  ✅" if o == q["answer"] else ""))

if not questions:
    st.error("Không đọc được câu hỏi nào — kiểm tra file hoặc upload file để debug.")
    st.stop()

# Search + show
search = st.text_input("🔎 Tìm kiếm (nhập từ khóa, ví dụ: 'VAECO', '6020', 'placard')").strip().lower()
show_count = st.number_input("Hiển thị tối đa (0 = tất cả):", min_value=0, value=0, step=10)

displayed = 0
for idx, q in enumerate(questions, start=1):
    if search and search not in q["question"].lower() and search not in " ".join(q["options"]).lower():
        continue
    if show_count and displayed >= show_count:
        break
    st.markdown(f"### {idx}. {q['question']}")
    for o in q["options"]:
        st.write(f"- {o} {'✅' if o == q['answer'] else ''}")
    st.markdown("---")
    displayed += 1

st.success(f"Hiển thị {displayed}/{len(questions)} câu đã parse.")
