import streamlit as st
import re
from docx import Document
import math

# =========================
# ⚙️ Giao diện và CSS
# =========================
st.set_page_config(page_title="Ngân hàng câu hỏi luật", page_icon="⚖️", layout="wide")
st.markdown("""
    <style>
    .main { display: flex; justify-content: center; }
    div.block-container {
        text-align: center;
        max-width: 900px;
        padding-top: 1rem;
    }
    h1 {
        font-size: 28px !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }
    .question-text {
        font-size: 18px !important;
        font-weight: 500 !important;
        text-align: left;
        margin-top: 1rem;
    }
    .stRadio > label { font-weight: normal; }
    .stButton>button {
        width: 60%;
        margin: 10px auto;
        display: block;
        border-radius: 10px;
        font-size: 18px;
        padding: 0.6rem 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>⚖️ Ngân hàng câu hỏi kiểm tra luật (SOP)</h1>", unsafe_allow_html=True)

# =========================
# 📘 HÀM ĐỌC FILE WORD
# =========================
def load_questions(docx_path):
    try:
        doc = Document(docx_path)
    except Exception as e:
        st.error(f"❌ Không thể đọc file Word: {e}")
        return []

    paragraphs = [p.text.rstrip() for p in doc.paragraphs if p.text and p.text.strip()]

    questions = []
    current = {"question": "", "options": [], "answer": None}

    opt_re = re.compile(r'^\s*(?:\d+\.\s*)?([\*]?)\s*([a-zA-Z])[\.\)\-–:]\s*(.*)$')

    for line in paragraphs:
        # Bỏ dòng bắt đầu bằng Ref.
        if re.match(r'^\s*Ref[:\.]\s*', line, re.IGNORECASE):
            continue

        m = opt_re.match(line)
        if m:
            star = m.group(1)
            text = m.group(3).strip()
            if not text:
                continue

            current["options"].append(text)
            if star:
                current["answer"] = text
        else:
            if current["options"]:
                # nếu chỉ có 1 đáp án và chưa có answer, gán luôn
                if not current["answer"] and len(current["options"]) == 1:
                    current["answer"] = current["options"][0]
                current["question"] = re.sub(r'^\s*\d+\.\s*', '', current["question"]).strip()
                if current["question"] and current["options"]:
                    questions.append(current)
                current = {"question": "", "options": [], "answer": None}

            if current["question"]:
                current["question"] += " " + line.strip()
            else:
                current["question"] = line.strip()

    # Câu cuối cùng
    if current["options"]:
        if not current["answer"] and len(current["options"]) == 1:
            current["answer"] = current["options"][0]
        current["question"] = re.sub(r'^\s*\d+\.\s*', '', current["question"]).strip()
        if current["question"] and current["options"]:
            questions.append(current)

    # Dọn final: bỏ sót Ref trong question nếu còn
    for q in questions:
        q["question"] = re.sub(r'\bRef[:\.].*$', '', q["question"], flags=re.IGNORECASE).strip()

    return [q for q in questions if q["question"] and q["options"]]

# =========================
# 🧩 TẢI DỮ LIỆU
# =========================
questions = load_questions("bank.docx")
TOTAL = len(questions)

if TOTAL == 0:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại file bank.docx.")
    st.stop()

# =========================
# 🧮 CHIA NHÓM 20 CÂU
# =========================
group_size = 20
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

if "last_group" not in st.session_state:
    st.session_state.last_group = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False

selected_group = st.selectbox("📋 Bạn muốn làm nhóm câu nào?", group_labels, index=0)

if st.session_state.last_group != selected_group:
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]
    st.session_state.submitted = False
    st.session_state.last_group = selected_group

start_idx = group_labels.index(selected_group) * group_size
end_idx = min(start_idx + group_size, TOTAL)
batch = questions[start_idx:end_idx]

# =========================
# 📄 HIỂN THỊ CÂU HỎI
# =========================
if not st.session_state.submitted:
    st.markdown(f"### 🧩 Nhóm {selected_group}")

    for i, q in enumerate(batch, start=start_idx + 1):
        st.markdown(f"<div class='question-text'><b>{i}. {q['question']}</b></div>", unsafe_allow_html=True)
        opts = ["(Chưa chọn)"] + q["options"]
        st.radio("", opts, index=0, key=f"q_{i}")
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("✅ Nộp bài và xem kết quả"):
        st.session_state.submitted = True
        st.rerun()

else:
    # Hiển thị kết quả
    score = 0
    for i, q in enumerate(batch, start=start_idx + 1):
        selected = st.session_state.get(f"q_{i}", "(Chưa chọn)")
        correct = q["answer"]
        is_correct = selected == correct
        if is_correct:
            score += 1
            st.success(f"{i}. {q['question']}\n\n✅ Đúng ({correct})")
        else:
            st.error(f"{i}. {q['question']}\n\n❌ Sai. Đáp án đúng: **{correct}**")
        st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader(f"🎯 Kết quả: {score}/{len(batch)} câu đúng")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start_idx + 1, end_idx + 1):
                key = f"q_{i}"
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.submitted = False
            st.rerun()
    with col2:
        if st.button("➡️ Sang nhóm khác"):
            for i in range(start_idx + 1, end_idx + 1):
                key = f"q_{i}"
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.submitted = False
            st.rerun()
