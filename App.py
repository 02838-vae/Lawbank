import streamlit as st
from docx import Document
import re
import math

# =====================
# ⚙️ HÀM ĐỌC FILE LAW BANK
# =====================
def load_lawbank(docx_file):
    """Đọc câu hỏi từ lawbank.docx — có đánh số, đáp án có dấu *, kết thúc bằng Ref."""
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    # Lấy toàn bộ nội dung
    text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

    # Cắt câu hỏi theo mẫu số thứ tự (1. , 2. , 3. ...)
    parts = re.split(r'\n?\d+\.\s+', text)
    questions = []

    for part in parts:
        if not part.strip():
            continue

        # Cắt phần sau "Ref" (không cần)
        part = re.split(r'Ref\.:?', part, flags=re.I)[0].strip()

        # Chèn xuống dòng trước a./b./c./d. nếu bị dính
        part = re.sub(r'(?<!\n)(?=[*]?[a-d]\s*\.)', '\n', part)

        lines = [l.strip() for l in part.split("\n") if l.strip()]
        if not lines:
            continue

        question_line = lines[0]
        options = []
        correct = ""

        for l in lines[1:]:
            if re.match(r'^[*]?[a-d]\s*\.', l, re.I):
                opt_text = re.sub(r'^[*]?[a-d]\s*\.', '', l).strip()
                if l.strip().startswith('*'):
                    correct = opt_text
                options.append(opt_text)

        if question_line and options:
            questions.append({
                "question": question_line,
                "options": options,
                "answer": correct or options[0],
            })

    return questions


# =====================
# ⚙️ HÀM ĐỌC FILE CAB BANK
# =====================
def load_cabbank(docx_file):
    """Đọc câu hỏi từ cabbank.docx — không đánh số, đáp án có thể dính liền trên cùng dòng."""
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    # Thêm xuống dòng trước a./b./c./d. nếu dính
    text = re.sub(r'(?<!\n)(?=[*]?[a-d]\s*\.)', '\n', text, flags=re.I)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    questions = []
    current_q = {"question": "", "options": [], "answer": ""}

    for line in lines:
        # Nếu là đáp án
        if re.match(r"^[*]?[a-d]\s*\.", line, re.I):
            opt = re.sub(r"^[*]?[a-d]\s*\.", "", line).strip()
            if line.strip().startswith("*"):
                current_q["answer"] = opt
            current_q["options"].append(opt)
        else:
            # Nếu có câu hỏi trước đó → lưu lại
            if current_q["question"] and current_q["options"]:
                if not current_q["answer"]:
                    current_q["answer"] = current_q["options"][0]
                questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": ""}
            current_q["question"] = line

    # Thêm câu cuối cùng
    if current_q["question"] and current_q["options"]:
        if not current_q["answer"]:
            current_q["answer"] = current_q["options"][0]
        questions.append(current_q)

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

file_path = "lawbank.docx" if "Luật" in bank_choice else "cabbank.docx"


# =====================
# 🧮 ĐỌC CÂU HỎI
# =====================
if "Luật" in bank_choice:
    questions = load_lawbank(file_path)
else:
    questions = load_cabbank(file_path)

if not questions:
    st.error(f"❌ Không đọc được câu hỏi nào trong file {file_path}. Kiểm tra định dạng trong Word.")
    st.stop()

TOTAL = len(questions)
group_size = 10
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]


# =====================
# ⚙️ SESSION STATE
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
        st.radio("", q["options"], index=None, key=f"q_{i}")
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("✅ Nộp bài và xem kết quả"):
        unanswered = [i for i in range(start + 1, end + 1) if st.session_state.get(f"q_{i}") is None]
        if unanswered:
            st.warning(f"⚠️ Bạn chưa chọn đáp án cho {len(unanswered)} câu: {', '.join(map(str, unanswered))}")
        else:
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
