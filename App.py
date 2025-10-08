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

    text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    question_blocks = re.split(r'\n(?=\d+\.\s)', text)

    questions = []
    for block in question_blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        question_text = lines[0]
        options = []
        correct = None

        for l in lines[1:]:
            match = re.match(r"(\*?)([a-zA-Z])\.\s*(.*)", l)
            if match:
                is_correct = bool(match.group(1))
                text = match.group(3).strip()
                options.append(text)
                if is_correct:
                    correct = text
            else:
                # Gộp dòng phụ (Ref.) vào câu hỏi, trừ khi là câu kế tiếp
                if not re.match(r'^\d+\.\s', l):
                    question_text += " " + l

        if options and correct:
            questions.append({
                "question": question_text,
                "options": options,
                "answer": correct
            })

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
# 🎮 LOGIC THI 20 CÂU MỖI LƯỢT
# =========================
if "remaining_questions" not in st.session_state:
    st.session_state.remaining_questions = list(range(TOTAL))  # danh sách index câu hỏi còn lại
if "current_batch" not in st.session_state:
    st.session_state.current_batch = random.sample(st.session_state.remaining_questions, min(20, len(st.session_state.remaining_questions)))
    for i in st.session_state.current_batch:
        st.session_state.remaining_questions.remove(i)
if "index" not in st.session_state:
    st.session_state.index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "answered" not in st.session_state:
    st.session_state.answered = False

# Nếu đã hết câu trong batch
if st.session_state.index >= len(st.session_state.current_batch):
    st.balloons()
    st.success(f"🎉 Hoàn thành 20 câu! Điểm của bạn: {st.session_state.score}/20")

    if len(st.session_state.remaining_questions) > 0:
        if st.button("🔁 Làm 20 câu tiếp theo"):
            st.session_state.current_batch = random.sample(
                st.session_state.remaining_questions,
                min(20, len(st.session_state.remaining_questions))
            )
            for i in st.session_state.current_batch:
                st.session_state.remaining_questions.remove(i)
            st.session_state.index = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.rerun()
    else:
        st.info("✅ Bạn đã hoàn thành toàn bộ 502 câu hỏi!")
        if st.button("🔄 Làm lại từ đầu"):
            st.session_state.remaining_questions = list(range(TOTAL))
            st.session_state.current_batch = random.sample(st.session_state.remaining_questions, 20)
            for i in st.session_state.current_batch:
                st.session_state.remaining_questions.remove(i)
            st.session_state.index = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.rerun()

    st.stop()

# =========================
# 📄 HIỂN THỊ CÂU HỎI HIỆN TẠI
# =========================
current_q_index = st.session_state.current_batch[st.session_state.index]
q = questions[current_q_index]

# Hiển thị câu hỏi rõ ràng, tách dòng
st.markdown(f"### 🧭 Câu {st.session_state.index + 1}/20\n\n{q['question']}\n\n---")

# Hiển thị đáp án mỗi dòng tách biệt
choice = st.radio("👉 Chọn đáp án của bạn:", q["options"], index=None, key=f"radio_{st.session_state.index}")

# Nút xác nhận
if st.button("✅ Xác nhận"):
    st.session_state.answered = True
    if choice == q["answer"]:
        st.success("🎯 Chính xác!")
        st.session_state.score += 1
    else:
        st.error(f"❌ Sai rồi — Đáp án đúng là: **{q['answer']}**")

# Nút tiếp theo
if st.session_state.answered and st.button("➡️ Câu tiếp theo"):
    st.session_state.index += 1
    st.session_state.answered = False
    st.rerun()
