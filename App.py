import streamlit as st
import random
import re
from docx import Document

st.set_page_config(page_title="Ngân hàng câu hỏi luật", page_icon="⚖️", layout="wide")

# ===============================
# 🔹 HÀM ĐỌC FILE WORD
# ===============================
def load_questions(docx_path):
    doc = Document(docx_path)
    # Gộp toàn bộ nội dung lại, bỏ đoạn rỗng
    text = " ".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

    # ✅ Tách theo số thứ tự câu hỏi (ví dụ: 1. 2. 3.)
    raw_questions = re.split(r'(?=\d+\.\s)', text)

    questions = []
    for q in raw_questions:
        q = q.strip()
        if not q or not re.match(r'^\d+\.\s', q):
            continue

        # Dòng đầu là câu hỏi, các dòng sau là đáp án
        # Tách đáp án theo a., b., c., d., e.
        parts = re.split(r'(?=[a-zA-Z]\.\s|\*[a-zA-Z]\.\s)', q)
        if len(parts) < 2:
            continue

        question_text = parts[0].strip()
        options = []
        correct = None

        for opt in parts[1:]:
            opt = opt.strip()
            if not opt:
                continue
            match = re.match(r"(\*?)([a-zA-Z])\.\s*(.*)", opt)
            if match:
                is_correct = bool(match.group(1))
                text = match.group(3).strip()
                options.append(text)
                if is_correct:
                    correct = text
            else:
                question_text += " " + opt

        if options and correct:
            questions.append({
                "question": question_text,
                "options": options,
                "answer": correct
            })

    random.shuffle(questions)
    return questions

# ===============================
# 🔹 GIAO DIỆN STREAMLIT
# ===============================
st.title("⚖️ NGÂN HÀNG CÂU HỎI KIỂM TRA LUẬT (SOP)")

questions = load_questions("Procedure Questin Bank_Final_Update_15.08.25.docx")

if "index" not in st.session_state:
    st.session_state.index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "answered" not in st.session_state:
    st.session_state.answered = False

if len(questions) == 0:
    st.error("❌ Không đọc được câu hỏi nào từ file Word. Hãy kiểm tra lại tên file hoặc đường dẫn.")
else:
    q = questions[st.session_state.index]

    st.markdown(f"### Câu {st.session_state.index + 1}: {q['question']}")
    choice = st.radio("Chọn đáp án:", q["options"], index=None)

    if st.button("Xác nhận"):
        st.session_state.answered = True
        if choice == q["answer"]:
            st.success("✅ Chính xác!")
            st.session_state.score += 1
        else:
            st.error(f"❌ Sai! Đáp án đúng là: {q['answer']}")

    if st.session_state.answered and st.button("➡️ Câu tiếp theo"):
        st.session_state.index += 1
        st.session_state.answered = False

        if st.session_state.index >= len(questions):
            st.balloons()
            st.success(f"🎉 Hoàn thành bài kiểm tra! Điểm: {st.session_state.score}/{len(questions)}")
            if st.button("🔁 Làm lại"):
                st.session_state.index = 0
                st.session_state.score = 0
        st.rerun()
