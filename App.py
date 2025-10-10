# app.py
import streamlit as st
from docx import Document
import re
import math

# -------------------------
# Utility
# -------------------------
def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def is_ref_paragraph(text: str) -> bool:
    return bool(re.match(r'(?i)^\s*ref[:.]?', text))


# -------------------------
# CABBANK (GIỮ NGUYÊN - OK)
# -------------------------
def parse_cabbank(source):
    doc = Document(source)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?<!\S)(?P<star>\*)?(?P<letter>[A-Da-d])\s*(?:[.)])')

    for p in paras:
        text = p
        if is_ref_paragraph(text):
            continue
        matches = list(opt_pat.finditer(text))
        if not matches:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": text, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + text).strip() if current["question"] else text
            continue
        pre = text[:matches[0].start()].strip()
        if pre:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": pre, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre).strip() if current["question"] else pre
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(text)
            opt_body = clean_text(text[start:end])
            letter = m.group("letter").lower()
            opt_text = f"{letter}. {opt_body}" if opt_body else f"{letter}."
            current["options"].append(opt_text)
            if m.group("star"):
                current["answer"] = opt_text
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)
    return questions


# -------------------------
# LAWBANK (FIX CHUẨN THEO LEVEL)
# -------------------------
def parse_lawbank(source):
    """
    Parser chính xác cho ngân hàng Luật:
    - Cấp numbering (ilvl = 0): câu hỏi (1., 2., 3.…)
    - Cấp numbering (ilvl = 1): đáp án (a., b., c., d.)
    - Các paragraph khác (không có numPr): nối thêm vào câu hỏi hiện tại
    - Dấu * trước đáp án đúng
    - Loại bỏ dòng bắt đầu bằng Ref.
    """
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Lỗi đọc file {source}: {e}")
        return []

    questions = []
    current_q = None

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        if is_ref_paragraph(text):
            continue

        # Xác định cấp numbering (nếu có)
        ilvl = None
        ilvl_nodes = p._element.xpath(".//w:numPr/w:ilvl")
        if ilvl_nodes and ilvl_nodes[0].text is not None:
            try:
                ilvl = int(ilvl_nodes[0].text)
            except:
                ilvl = None

        # Nếu paragraph là câu hỏi (level 0 hoặc bắt đầu bằng số)
        if (ilvl == 0) or re.match(r"^\d+\.", text):
            # Lưu câu trước
            if current_q and current_q["options"]:
                if not current_q["answer"] and current_q["options"]:
                    current_q["answer"] = current_q["options"][0]
                questions.append(current_q)
            # Bắt đầu câu mới
            q_text = re.sub(r"^\d+\.\s*", "", text).strip()
            current_q = {"question": q_text, "options": [], "answer": ""}

        # Nếu là đáp án (level 1 hoặc bắt đầu bằng chữ cái)
        elif (ilvl == 1) or re.match(r"^\*?[A-Da-d][\.\)]\s+", text):
            if not current_q:
                continue
            # Xác định đáp án đúng
            m = re.match(r"(?P<star>\*)?(?P<letter>[A-Da-d])[\.\)]\s*(.*)", text)
            if m:
                opt_text = f"{m.group('letter').lower()}. {m.group(3).strip()}"
                current_q["options"].append(opt_text)
                if m.group("star"):
                    current_q["answer"] = opt_text

        # Nếu không có numbering, nối vào câu hỏi hiện tại
        else:
            if current_q:
                current_q["question"] += " " + text

    # Lưu câu cuối
    if current_q and current_q["options"]:
        if not current_q["answer"] and current_q["options"]:
            current_q["answer"] = current_q["options"][0]
        questions.append(current_q)

    return questions


# -------------------------
# STREAMLIT APP
# -------------------------
st.set_page_config(page_title="Dò câu - Lawbank", layout="wide")
st.title("📘 Dò câu — Ưu tiên Ngân hàng Luật (Lawbank)")

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Luật (Lawbank)", "Ngân hàng Kỹ thuật (Cabbank)"])

uploaded = st.file_uploader("📂 Upload .docx (hoặc để trống nếu đã có sẵn)", type=["docx"])

source = uploaded or ("lawbank.docx" if "Luật" in bank_choice else "cabbank.docx")

# Parse
if "Luật" in bank_choice:
    questions = parse_lawbank(source)
else:
    questions = parse_cabbank(source)

# Debug
with st.expander("🧩 Debug thông tin"):
    st.write(f"Số câu parse được: {len(questions)}")
    for i, q in enumerate(questions[:5], 1):
        st.markdown(f"**{i}. {q['question']}**")
        for o in q["options"]:
            mark = "✅" if o == q["answer"] else ""
            st.write(f"- {o} {mark}")

if not questions:
    st.error("❌ Không đọc được câu hỏi nào — kiểm tra lại file hoặc cấu trúc numbering.")
    st.stop()

# Tra cứu
st.markdown("## 🔍 Tra cứu câu hỏi")
search = st.text_input("Nhập từ khóa tìm kiếm:").strip().lower()
limit = st.number_input("Hiển thị tối đa:", min_value=0, value=0)

count = 0
for idx, q in enumerate(questions, start=1):
    if search and search not in q["question"].lower() and search not in " ".join(q["options"]).lower():
        continue
    if limit and count >= limit:
        break
    st.markdown(f"### {idx}. {q['question']}")
    for o in q["options"]:
        mark = "✅" if o == q["answer"] else ""
        st.write(f"- {o} {mark}")
    st.markdown("---")
    count += 1

st.success(f"Đang hiển thị {count}/{len(questions)} câu hỏi.")
