import streamlit as st
import re
from docx import Document
import math

# =========================
# ⚙️ Cấu hình giao diện
# =========================
st.set_page_config(page_title="Ngân hàng câu hỏi luật", page_icon="⚖️", layout="wide")
st.title("⚖️ NGÂN HÀNG CÂU HỎI KIỂM TRA LUẬT (SOP)")

# =========================
# 📘 HÀM ĐỌC FILE WORD
# =========================
def load_questions(docx_path):
    try:
        doc = Document(docx_path)
    except Exception as e:
        st.error(f"❌ Không thể đọc file Word: {e}")
        return []

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    questions = []
    current_q = {"question": "", "options": [], "answer": None}

    for line in paragraphs:
        # Regex nhận cả a,b,c,d (hoa/thường), có thể có *, khoảng trắng
        if re.match(r"^\s*\*?\s*[a-dA-D]\.\s", line):
            match = re.match(r"^\s*(\*?)\s*([a-dA-D])\.\s*(.*)", line)
            if match:
                is_correct = bool(match.group(1))
                text = match.group(3).strip()
                current_q["options"].append(text)
                if is_correct:
                    current_q["answer"] = text
        else:
            # Nếu gặp câu hỏi mới sau khi có đáp án => lưu câu cũ
            if current_q["options"]:
                if current_q["question"] and current_q["answer"]:
                    questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": None}

            # Thêm dòng mới vào nội dung câu hỏi
            if current_q["question"]:
                current_q["question"] += " " + line
            else:
                current_q["question"] = line

    # Thêm câu cuối cùng
    if current_q["question"] and current_q["answer"]:
        questions.append(current_q)

    return questions

# =========================
# 🧩 TẢI DỮ LIỆU
# =========================
questions = load_questions("bank.docx")
TOTAL = len(questions)

if TOTAL == 0:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại file bank.docx.")
    st.stop()

st.success(f"📘 Đã tải thành công {TOTAL} câu hỏi.")

# =========================
# 🧮 CHIA NHÓM 20 CÂU
# =========================
group_size = 20
num_groups = math.ceil(TOTAL / group_size)

group_labels = []
for i in range(num_groups):
    start = i * group_size + 1
    end = min((i + 1) * group_size, TOTAL)
    group_labels.append(f"Câu {start} - {end}")

# =========================
# 🎯 CHỌN NHÓM CÂU HỎI
# =========================
selected_group = st.selectbox("📋 Bạn muốn làm nhóm câu nào?", group_labels)

start_idx = (group_labels.index(selected_group)) * group_size
end_idx = min(start_idx + group_size, TOTAL)
batch = questions[start_idx:end_idx]

# Dùng session để lưu đáp án
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# =========================
# 📄 HIỂN THỊ 20 CÂU CÙNG LÚC
# =========================
if not st.session_state.submitted:
    st.markdown(f"### 🧩 Nhóm {selected_group}")

    for i, q in enumerate(batch, start=start_idx + 1):
        st.markdown(f"**{i}. {q['question']}**")
        st.session_state.answers[i] = st.radio(
            "",
            q["options"],
            index=None,
            key=f"q_{i}"
        )
        st.divider()

    if st.button("✅ Nộp bài và xem kết quả"):
        st.session_state.submitted = True
        st.rerun()

else:
    # Tính điểm và hiển thị kết quả
    score = 0
    for i, q in enumerate(batch, start=start_idx + 1):
        selected = st.session_state.answers.get(i)
        correct = q["answer"]
        is_correct = selected == correct
        if is_correct:
            score += 1
            st.success(f"{i}. {q['question']}\n\n✅ Đúng ({correct})")
        else:
            st.error(f"{i}. {q['question']}\n\n❌ Sai. Đáp án đúng: **{correct}**")

        st.markdown("---")

    st.subheader(f"🎯 Kết quả: {score}/{len(batch)} câu đúng")

    if st.button("🔁 Làm lại nhóm này"):
        for i in range(start_idx + 1, end_idx + 1):
            if f"q_{i}" in st.session_state:
                del st.session_state[f"q_{i}"]
        st.session_state.submitted = False
        st.rerun()

    if st.button("➡️ Sang nhóm câu khác"):
        for i in range(start_idx + 1, end_idx + 1):
            if f"q_{i}" in st.session_state:
                del st.session_state[f"q_{i}"]
        st.session_state.submitted = False
        st.rerun()
