import streamlit as st
from docx import Document
import re
import math

# =====================
# ⚙️ Hàm trích xuất câu hỏi từ file Word
# =====================
def load_questions(docx_file):
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    questions = []
    current_q = {"question": "", "options": [], "answer": None}

    # Regex linh hoạt cho đáp án
    opt_re = re.compile(r"^\s*([\*]?)\s*([a-dA-D])[\.\)\-–:]\s*(.*)")

    for line in paragraphs:
        # Bỏ dòng Ref hoặc ghi chú
        if re.match(r"^\s*Ref[:\.]", line, re.IGNORECASE):
            continue

        # Nếu là đáp án
        m = opt_re.match(line)
        if m:
            is_correct = bool(m.group(1))
            label = m.group(2).upper()
            text = m.group(3).strip()
            if text:
                current_q["options"].append(f"{label}. {text}")
                if is_correct:
                    current_q["answer"] = f"{label}. {text}"
        else:
            # Nếu câu trước đã có đáp án, lưu lại
            if current_q["options"]:
                if len(current_q["options"]) >= 2:
                    if not current_q["answer"]:
                        current_q["answer"] = current_q["options"][0]
                    questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": None}

            # Câu hỏi mới
            if current_q["question"]:
                current_q["question"] += " " + line
            else:
                current_q["question"] = line

    # Thêm câu cuối
    if current_q["options"] and len(current_q["options"]) >= 2:
        if not current_q["answer"]:
            current_q["answer"] = current_q["options"][0]
        questions.append(current_q)

    return questions

# =====================
# ⚙️ Giao diện
# =====================
st.set_page_config(page_title="Ngân hàng câu hỏi", layout="wide")

st.markdown("""
    <style>
    .main { display: flex; justify-content: center; }
    div.block-container { text-align: center; max-width: 900px; padding-top: 1rem; }
    h1 {
        font-size: 28px !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    .question {
        font-size: 18px;
        font-weight: 500;
        text-align: left;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .stRadio > label { font-weight: normal; font-size: 16px; }
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

st.markdown("<h1>📚 Ngân hàng câu hỏi</h1>", unsafe_allow_html=True)

# =====================
# 📘 Chọn ngân hàng câu hỏi
# =====================
bank_choice = st.selectbox(
    "Chọn ngân hàng muốn làm:",
    ["Ngân hàng Luật (bank.docx)", "Ngân hàng Kỹ thuật (cabbank.docx)"]
)

file_path = "bank.docx" if "Luật" in bank_choice else "cabbank.docx"
questions = load_questions(file_path)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại file Word.")
    st.stop()

TOTAL = len(questions)
group_size = 10
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

# =====================
# 📋 Chọn nhóm câu hỏi
# =====================
if "last_group" not in st.session_state:
    st.session_state.last_group = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False

selected_group = st.selectbox("📘 Bạn muốn làm nhóm câu nào?", group_labels, index=0)

# Reset khi đổi nhóm hoặc ngân hàng
if st.session_state.last_group != (selected_group + file_path):
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]
    st.session_state.submitted = False
    st.session_state.last_group = selected_group + file_path

start = group_labels.index(selected_group) * group_size
end = min(start + group_size, TOTAL)
batch = questions[start:end]

# =====================
# 📄 Hiển thị câu hỏi
# =====================
if not st.session_state.submitted:
    st.markdown(f"### 🧩 Nhóm {selected_group}")

    for i, q in enumerate(batch, start=start + 1):
        st.markdown(f"<div class='question'><b>{i}. {q['question']}</b></div>", unsafe_allow_html=True)
        opts = ["(Chưa chọn)"] + q["options"]
        st.radio("", opts, index=0, key=f"q_{i}")
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("✅ Nộp bài và xem kết quả"):
        st.session_state.submitted = True
        st.rerun()

else:
    # Hiển thị kết quả
    score = 0
    for i, q in enumerate(batch, start=start + 1):
        selected = st.session_state.get(f"q_{i}", "(Chưa chọn)")
        correct = q["answer"]
        if selected == correct:
            score += 1
            st.success(f"{i}. {q['question']}\n\n✅ Đúng ({correct})")
        else:
            st.error(f"{i}. {q['question']}\n\n❌ Sai. Đáp án đúng: **{correct}**")
        st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader(f"🎯 Kết quả: {score}/{len(batch)} câu đúng")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start + 1, end + 1):
                key = f"q_{i}"
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.submitted = False
            st.rerun()
    with col2:
        if st.button("➡️ Sang nhóm khác"):
            for i in range(start + 1, end + 1):
                key = f"q_{i}"
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.submitted = False
            st.rerun()
