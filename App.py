import streamlit as st
from docx import Document
import re
import math

# =====================================
# ⚙️ HÀM ĐỌC FILE WORD CHUNG
# =====================================
def load_questions(docx_file, remove_ref=False):
    """Đọc câu hỏi từ file Word, định dạng:
    Câu hỏi
    a. ...
    b. ...
    *c. ...
    Ref: ...
    """

    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    # Lấy tất cả đoạn có text
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    # Chèn xuống dòng trước các đáp án nếu dính liền
    text = re.sub(r'(?<!\n)(?=[a-d]\s*\.)', '\n', text, flags=re.I)

    # Nếu là lawbank thì bỏ tất cả dòng REF
    if remove_ref:
        text = re.sub(r'(?i)\n*Ref.*', '', text)

    # Chia dòng
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    questions = []
    current_q = {"question": "", "options": [], "answer": ""}

    for line in lines:
        # Nếu là dòng đáp án
        if re.match(r"^[a-d]\s*\.", line, re.I) or re.match(r"^\*[a-d]\s*\.", line, re.I):
            is_correct = line.strip().startswith("*")
            line_clean = line.replace("*", "").strip()
            label = line_clean[:2].strip()  # "a."
            option_text = line_clean[2:].strip()

            if is_correct:
                current_q["answer"] = option_text

            current_q["options"].append(option_text)

        # Nếu là dòng câu hỏi (không bắt đầu bằng a/b/c/d)
        else:
            # Nếu đang có câu hỏi cũ thì lưu lại
            if current_q["question"] and current_q["options"]:
                questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": ""}

            current_q["question"] = line

    # Thêm câu cuối cùng
    if current_q["question"] and current_q["options"]:
        questions.append(current_q)

    # Làm sạch
    for q in questions:
        q["question"] = q["question"].strip()
        q["options"] = [o.strip() for o in q["options"] if o.strip()]
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

file_path = "lawbank.docx" if "Luật" in bank_choice else "cabbank.docx"
remove_ref = "Luật" in bank_choice

# =====================================
# 🧮 ĐỌC CÂU HỎI
# =====================================
questions = load_questions(file_path, remove_ref=remove_ref)
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
