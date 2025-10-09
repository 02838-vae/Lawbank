import streamlit as st
from docx import Document
import re
import math

# =====================
# ⚙️ HÀM ĐỌC FILE WORD
# =====================
def load_questions(docx_file):
    """Đọc câu hỏi từ file Word có định dạng:
    # Câu hỏi
    a. ...
    b. ...
    c. ...*
    d. ...
    """

    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    # Lấy tất cả đoạn text không rỗng
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # Gộp các dòng lại để xử lý dễ hơn (vì đôi khi Word nối các đáp án lại)
    text = "\n".join(paragraphs)

    # Tách riêng từng dòng nếu bị dính, ví dụ "a....b...."
    # Regex này sẽ chèn xuống dòng trước a./b./c./d. nếu bị dính
    text = re.sub(r'(?<!\n)(?=[a-d]\.)', '\n', text, flags=re.I)

    # Chia lại thành danh sách dòng
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # 🧩 DEBUG — xem trước 30 dòng
    with st.expander("📋 Xem nội dung gốc từ Word (debug)"):
        for i, line in enumerate(lines[:30], 1):
            st.write(f"{i:03d}: {line}")

    questions = []
    current_q = {"question": "", "options": [], "answer": ""}

    for line in lines:
        # Nếu là dòng câu hỏi (bắt đầu bằng #)
        if line.startswith("#"):
            # Nếu đã có câu trước thì lưu lại
            if current_q["question"] and current_q["options"]:
                questions.append(current_q)
            # Bắt đầu câu mới
            current_q = {"question": line[1:].strip(), "options": [], "answer": ""}

        # Nếu là đáp án (a., b., c., d.)
        elif re.match(r"^[a-d]\.", line, re.I):
            option_text = line[2:].strip()
            if "*" in option_text:
                option_text = option_text.replace("*", "").strip()
                current_q["answer"] = option_text
            current_q["options"].append(option_text)

        # Nếu là dòng rác hoặc nối tiếp (hiếm)
        else:
            # Nối thêm vào câu hỏi
            if current_q["question"]:
                current_q["question"] += " " + line

    # Thêm câu cuối cùng
    if current_q["question"] and current_q["options"]:
        if not current_q["answer"]:
            current_q["answer"] = current_q["options"][0]  # nếu thiếu dấu *
        questions.append(current_q)

    # Làm sạch dữ liệu
    for q in questions:
        q["question"] = q["question"].strip()
        q["options"] = [opt.strip() for opt in q["options"] if opt.strip()]

    return questions


# =====================
# ⚙️ GIAO DIỆN APP
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
        line-height: 1.6;
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
# 🧩 CHỌN NGÂN HÀNG
# =====================
bank_choice = st.selectbox(
    "Chọn ngân hàng muốn làm:",
    ["Ngân hàng Luật", "Ngân hàng Kỹ thuật"],
    index=0
)

file_path = "bank.docx" if "Luật" in bank_choice else "cabbank.docx"

# =====================
# 🧮 ĐỌC CÂU HỎI
# =====================
questions = load_questions(file_path)
if not questions:
    st.error(f"❌ Không đọc được câu hỏi nào trong file {file_path}. Kiểm tra định dạng trong Word.")
    st.stop()

TOTAL = len(questions)
group_size = 10
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

# =====================
# ⚙️ TRẠNG THÁI
# =====================
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

# =====================
# 📋 CHỌN NHÓM CÂU
# =====================
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

# =====================
# 📄 HIỂN THỊ CÂU HỎI
# =====================
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
