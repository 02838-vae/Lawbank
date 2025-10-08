import streamlit as st
import random
import re
from docx import Document

# =========================
# ⚙️ Cấu hình trang
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

    # Ghép tất cả paragraph thành chuỗi, giữ nguyên xuống dòng
    text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    # ✅ Tách theo số thứ tự đầu câu (vd: "1. ", "2. ", "99. ")
    raw_questions = re.split(r'\n(?=\d+\.\s)', text)

    questions = []
    for block in raw_questions:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        question_text = lines[0]
        options = []
        correct = None

        # Duyệt từng dòng trong khối câu hỏi
        for i, l in enumerate(lines[1:]):
            match = re.match(r"(\*?)([a-zA-Z])\.\s*(.*)", l)
            if match:
                # Đây là dòng đáp án
                is_correct = bool(match.group(1))
                text = match.group(3).strip()
                options.append(text)
                if is_correct:
                    correct = text
            else:
                # Nếu dòng không phải đáp án (vd: Ref. hoặc tiếp nối câu hỏi)
                if not re.match(r'^\d+\.\s', l):  # tránh gộp sang câu tiếp theo
                    question_text += " " + l

        if options and correct:
            questions.append({
                "question": question_text,
                "options": options,
                "answer": correct
            })

    return questions


# =========================
# 🎮 GIAO DIỆN STREAMLIT
# =========================
questions = load_questions("bank.docx")

if len(questions) == 0:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại định dạng file hoặc tên file (bank.docx).")
    st.stop()

# Bộ nhớ session
if "index" not in st.session_state:
    st.session_state.index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "answered" not in st.session_state:
    st.session_state.answered = False

# Hiển thị câu hỏi hiện tại
q = questions[st.session_state.index]
st.markdown(f"### Câu {st.session_state.index + 1}: {q['question']}")
choice = st.radio("Chọn đáp án của bạn:", q["options"], index=None)

if st.button("✅ Xác nhận"):
    st.session_state.answered = True
    if choice == q["answer"]:
        st.success("Chính xác! ✅")
        st.session_state.score += 1
    else:
        st.error(f"Sai rồi ❌ — Đáp án đúng là: {q['answer']}")

if st.session_state.answered and st.button("➡️ Câu tiếp theo"):
    st.session_state.index += 1
    st.session_state.answered = False

    if st.session_state.index >= len(questions):
        st.balloons()
        st.success(f"🎉 Hoàn thành bài kiểm tra! Tổng điểm: {st.session_state.score}/{len(questions)}")
        if st.button("🔁 Làm lại"):
            st.session_state.index = 0
            st.session_state.score = 0
    st.rerun()
