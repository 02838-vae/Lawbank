import streamlit as st
import random
import re
from docx import Document

# --- Hàm đọc file Word ---
def load_questions(docx_path):
    doc = Document(docx_path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    # Tách các câu hỏi
    raw_questions = re.split(r'\n(?=[A-Z].+?\))', text)
    
    questions = []
    for q in raw_questions:
        lines = [l.strip() for l in q.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        question_text = lines[0]
        options = []
        correct = None
        for l in lines[1:]:
            match = re.match(r"(\*?)([a-cA-C])\.\s*(.*)", l)
            if match:
                is_correct = bool(match.group(1))
                letter = match.group(2)
                text = match.group(3)
                options.append(text)
                if is_correct:
                    correct = text
        if correct and options:
            questions.append({
                "question": question_text,
                "options": options,
                "answer": correct
            })
    return questions

# --- Tải dữ liệu ---
questions = load_questions("Procedure Questin Bank_Final_Update_15.08.25.docx")

st.title("📘 Kiểm tra trắc nghiệm SOP/Luật - Tổ bạn")

# --- Bộ nhớ session ---
if "index" not in st.session_state:
    st.session_state.index = 0
if "score" not in st.session_state:
    st.session_state.score = 0

# --- Hiển thị câu hỏi ---
q = questions[st.session_state.index]
st.write(f"### Câu {st.session_state.index + 1}: {q['question']}")
choice = st.radio("Chọn đáp án:", q["options"])

if st.button("Xác nhận"):
    if choice == q["answer"]:
        st.success("✅ Chính xác!")
        st.session_state.score += 1
    else:
        st.error(f"❌ Sai! Đáp án đúng là: {q['answer']}")
    st.session_state.index += 1
    if st.session_state.index >= len(questions):
        st.balloons()
        st.write(f"### 🎉 Hoàn thành! Điểm: {st.session_state.score}/{len(questions)}")
        st.session_state.index = 0
        st.session_state.score = 0
    st.rerun()