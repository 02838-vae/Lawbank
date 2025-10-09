import streamlit as st
from docx import Document
import re
import math

# =====================
# ⚙️ HÀM ĐỌC FILE WORD
# =====================
def load_questions(docx_file, mode="law"):
    """Đọc câu hỏi từ file Word. mode = 'law' hoặc 'tech'."""
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"❌ Không thể đọc file {docx_file}: {e}")
        return []

    text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
    questions = []

    # ------------------------
    # 1️⃣ Dạng kỹ thuật (có dấu #)
    # ------------------------
    if mode == "tech":
        # Cắt mỗi câu bắt đầu bằng "#"
        raw_blocks = re.split(r"(?=\n?#\s*\d*\s*)", text)
        for block in raw_blocks:
            block = block.strip()
            if not block.startswith("#"):
                continue

            lines = [l.strip() for l in block.splitlines() if l.strip()]
            question_text = re.sub(r"^#+\s*\d*\s*", "", lines[0]).strip()
            rest_text = " ".join(lines[1:])

            # Tách tất cả đáp án (a., b., c., d.) kể cả dính liền hoặc không xuống dòng
            pattern = r"([\*]?)\s*([a-dA-D])[\.\)\-–:]\s*(.*?)(?=(?:[\*]?\s*[a-dA-D][\.\)\-–:])|$)"
            matches = re.findall(pattern, rest_text, re.DOTALL)

            options = []
            correct_answer = None

            for m in matches:
                is_correct = bool(m[0])
                label = m[1].upper()
                text_opt = re.sub(r"\s+", " ", m[2].strip())
                if text_opt:
                    opt = f"{label}. {text_opt}"
                    options.append(opt)
                    if is_correct:
                        correct_answer = opt

            # Thêm câu hỏi hợp lệ
            if len(options) >= 2:
                if not correct_answer:
                    correct_answer = options[0]
                questions.append({
                    "question": question_text,
                    "options": options,
                    "answer": correct_answer
                })

    # ------------------------
    # 2️⃣ Dạng luật (bình thường)
    # ------------------------
    else:
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        current_q = {"question": "", "options": [], "answer": None}
        opt_re = re.compile(r"^\s*([\*]?)\s*([a-dA-D])[\.\)\-–:]\s*(.*)")

        for line in paragraphs:
            if re.match(r"^\s*Ref[:\.]", line, re.IGNORECASE):
                continue

            m = opt_re.match(line)
            if m:
                is_correct = bool(m.group(1))
                label = m.group(2).upper()
                text_opt = m.group(3).strip()
                if text_opt:
                    current_q["options"].append(f"{label}. {text_opt}")
                    if is_correct:
                        current_q["answer"] = f"{label}. {text_opt}"
            else:
                if current_q["options"]:
                    if len(current_q["options"]) >= 2:
                        if not current_q["answer"]:
                            current_q["answer"] = current_q["options"][0]
                        questions.append(current_q)
                    current_q = {"question": "", "options": [], "answer": None}

                if current_q["question"]:
                    current_q["question"] += " " + line
                else:
                    current_q["question"] = line

        if current_q["options"] and len(current_q["options"]) >= 2:
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

file_path = "bank.docx" if "Luật" in bank_choice else "cabbank.docx"
mode = "law" if "Luật" in bank_choice else "tech"

# =====================
# 🧮 ĐỌC CÂU HỎI
# =====================
questions = load_questions(file_path, mode)
if not questions:
    st.error(f"❌ Không đọc được câu hỏi nào trong file {file_path}.")
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
        for opt in q["options"]:
            st.markdown(f"- {opt}")
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
