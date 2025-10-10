import streamlit as st
from docx import Document
import re
import math

# =====================================
# ⚙️ HÀM ĐỌC FILE CHO CABBANK (CODE CŨ GIỮ NGUYÊN)
# =====================================
def load_cabbank(docx_file):
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    # Chèn xuống dòng trước các đáp án nếu dính liền
    text = re.sub(r'(?<!\n)(?=[a-d]\s*\.)', '\n', text, flags=re.I)
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    questions = []
    current_q = {"question": "", "options": [], "answer": ""}

    for line in lines:
        # Nếu là đáp án
        if re.match(r"^\*?[a-d]\s*\.", line, re.I):
            is_correct = line.strip().startswith("*")
            line_clean = line.replace("*", "").strip()
            option_text = re.sub(r"^[a-d]\s*\.\s*", "", line_clean, flags=re.I).strip()

            if is_correct:
                current_q["answer"] = option_text
            current_q["options"].append(option_text)
        else:
            # Nếu đang có câu hỏi và option, thì lưu lại
            if current_q["question"] and current_q["options"]:
                questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": ""}

            current_q["question"] = line

    if current_q["question"] and current_q["options"]:
        questions.append(current_q)

    for q in questions:
        q["question"] = q["question"].strip()
        q["options"] = [opt.strip() for opt in q["options"] if opt.strip()]
        if not q["answer"] and q["options"]:
            q["answer"] = q["options"][0]

    return questions


# =====================================
# ⚙️ HÀM ĐỌC FILE CHO LAWBANK (MỚI)
# =====================================
def load_lawbank(docx_file):
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # Gộp lại để xử lý, chèn xuống dòng khi gặp các đáp án
    text = "\n".join(paragraphs)
    text = re.sub(r'(?<!\n)(?=[a-d]\s*\.)', '\n', text, flags=re.I)
    text = re.sub(r'(?<!\n)(?=\*[a-d]\s*\.)', '\n', text, flags=re.I)

    # Loại bỏ dòng REF
    text = re.sub(r'(?i)\n*Ref[:.].*', '', text)

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    questions = []
    current_q = {"question": "", "options": [], "answer": ""}

    for line in lines:
        # Nếu là dòng đáp án
        if re.match(r"^\*?[a-d]\s*\.", line, re.I):
            is_correct = line.strip().startswith("*")
            line_clean = line.replace("*", "").strip()
            option_text = re.sub(r"^[a-d]\s*\.\s*", "", line_clean, flags=re.I).strip()

            if is_correct:
                current_q["answer"] = option_text
            current_q["options"].append(option_text)
        else:
            # Nếu đang có câu hỏi và option, thì lưu lại
            if current_q["question"] and current_q["options"]:
                questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": ""}

            current_q["question"] = line

    if current_q["question"] and current_q["options"]:
        questions.append(current_q)

    # Làm sạch
    for q in questions:
        q["question"] = q["question"].strip()
        q["options"] = [opt.strip() for opt in q["options"] if opt.strip()]
        if not q["answer"] and q["options"]:
            q["answer"] = q["options"][0]

    return questions


# =====================================
# ⚙️ GIAO DIỆN APP
# =====================================
st.set_page_config(page_title="Ngân hàng câu hỏi", layout="wide")

st.markdown("""
    <style>
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
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>📚 Ngân hàng câu hỏi</h1>", unsafe_allow_html=True)

# =====================================
# 🧩 CHỌN NGÂN HÀNG
# =====================================
bank_choice = st.selectbox(
    "Chọn ngân hàng muốn làm:",
    ["Ngân hàng Luật", "Ngân hàng Kỹ thuật"],
    index=0
)

# =====================================
# 🧮 ĐỌC CÂU HỎI
# =====================================
if "Luật" in bank_choice:
    file_path = "lawbank.docx"
    questions = load_lawbank(file_path)
else:
    file_path = "cabbank.docx"
    questions = load_cabbank(file_path)

if not questions:
    st.error(f"❌ Không đọc được câu hỏi nào trong file {file_path}. Kiểm tra định dạng trong Word.")
    st.stop()

TOTAL = len(questions)
group_size = 10
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

# =====================================
# ⚙️ TRẠNG THÁI
# =====================================
if "current_bank" not in st.session_state:
    st.session_state.current_bank = bank_choice
if "last_group" not in st.session_state:
    st.session_state.last_group = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.session_state.current_bank != bank_choice:
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]
    st.session_state.submitted = False
    st.session_state.current_bank = bank_choice

# =====================================
# 📋 CHỌN NHÓM CÂU
# =====================================
selected_group = st.selectbox("📘 Bạn muốn làm nhóm câu nào?", group_labels, index=0)

if st.session_state.last_group != (selected_group + file_path):
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]
    st.session_state.submitted = False
    st.session_state.last_group = selected_group + file_path

start = group_labels.index(selected_group) * group_size
end = min(start + group_size, TOTAL)
batch = questions[start:end]

# =====================================
# 📄 HIỂN THỊ CÂU HỎI
# =====================================
if not st.session_state.submitted:
    st.markdown(f"### 🧩 Nhóm {selected_group}")

    for i, q in enumerate(batch, start=start + 1):
        st.markdown(f"<div class='question'><b>{i}. {q['question']}</b></div>", unsafe_allow_html=True)
        st.radio("", q["options"], index=0, key=f"q_{i}")
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("✅ Nộp bài và xem kết quả"):
        st.session_state.submitted = True
        st.rerun()

else:
    score = 0
    for i, q in enumerate(batch, start=start + 1):
        selected = st.session_state.get(f"q_{i}")
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
