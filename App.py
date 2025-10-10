import streamlit as st
from docx import Document
import re
import math

st.set_page_config(page_title="Dò câu hỏi ngân hàng", layout="wide")

# ==========================================
# ⚙️ HÀM ĐỌC CÂU HỎI — CHO NGÂN HÀNG KỸ THUẬT
# ==========================================
def load_cabbank(path):
    try:
        doc = Document(path)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {path}: {e}")
        return []

    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paras)
    text = re.sub(r'(?<!\n)(?=[a-dA-D]\s*[\.\)])', '\n', text)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    questions = []
    q = {"question": "", "options": [], "answer": ""}

    def commit():
        if q["question"] and q["options"]:
            if not q["answer"]:
                q["answer"] = q["options"][0]
            questions.append(q.copy())

    for line in lines:
        if re.match(r'^[a-dA-D]\s*[\.\)]', line):
            opt = re.sub(r'^[a-dA-D]\s*[\.\)]\s*', '', line).strip()
            if opt.startswith("*"):
                opt = opt[1:].strip()
                q["answer"] = opt
            q["options"].append(opt)
        else:
            if q["question"] and q["options"]:
                commit()
                q = {"question": line, "options": [], "answer": ""}
            else:
                q["question"] = (q["question"] + " " + line).strip()

    commit()
    return questions


# ==========================================
# ⚙️ HÀM ĐỌC CÂU HỎI — CHO NGÂN HÀNG LUẬT
# ==========================================
def load_lawbank(path):
    try:
        doc = Document(path)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {path}: {e}")
        return []

    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paras)

    # Loại bỏ REF dòng cuối mỗi câu
    text = re.sub(r'REF[\.:].*?(?=\n\d+\.)', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Tách từng câu hỏi theo số thứ tự
    raw_questions = re.split(r'\n?\s*\d+\.\s+', text)
    questions = []

    for chunk in raw_questions:
        if not chunk.strip():
            continue
        parts = re.split(r'(?<=\n)[a-dA-D]\s*[\.\)]\s*', chunk)
        q_text = parts[0].strip()
        opts = re.findall(r'([a-dA-D])[\.\)]\s*(.*?)($|\n[a-dA-D][\.\)])', chunk, flags=re.DOTALL)
        options, answer = [], ""

        for _, opt_text, _ in opts:
            clean = opt_text.replace("\n", " ").strip()
            if clean.startswith("*"):
                clean = clean[1:].strip()
                answer = clean
            options.append(clean)

        if q_text and options:
            questions.append({"question": q_text, "options": options, "answer": answer or options[0]})

    return questions


# ==========================================
# ⚙️ GIAO DIỆN CHÍNH
# ==========================================
st.title("🔍 Dò câu hỏi từ Word")

bank_choice = st.selectbox("Chọn ngân hàng cần dò:", ["Ngân hàng Kỹ thuật (cabbank)", "Ngân hàng Luật (lawbank)"])

if "Kỹ thuật" in bank_choice:
    file_path = "cabbank.docx"
    loader = load_cabbank
else:
    file_path = "lawbank.docx"
    loader = load_lawbank

questions = loader(file_path)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại định dạng file hoặc logic tách câu.")
    st.stop()

st.success(f"✅ Đọc được {len(questions)} câu hỏi từ {file_path}")

# ==========================================
# 🧾 GIAO DIỆN DÒ CÂU
# ==========================================
search = st.text_input("🔎 Tìm kiếm nội dung (tùy chọn):").strip().lower()

for i, q in enumerate(questions, 1):
    if search and search not in q["question"].lower():
        continue

    st.markdown(f"### {i}. {q['question']}")
    for opt in q["options"]:
        mark = "✅" if opt == q["answer"] else ""
        st.write(f"- {opt} {mark}")
    st.markdown("---")

# Debug số liệu
with st.expander("📊 Thông tin debug"):
    st.write(f"Số câu đọc được: {len(questions)}")
    st.write("10 câu đầu tiên:")
    for i, q in enumerate(questions[:10], 1):
        st.write(f"{i}. {q['question'][:80]}...")
