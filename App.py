import streamlit as st
import random
import re
from docx import Document

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

    # Lấy toàn bộ text (bỏ dòng trống)
    text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    # Tách thành từng khối câu hỏi theo mẫu xuất hiện của đáp án "a." hoặc "*a."
    # Regex: tìm đoạn bắt đầu trước a. hoặc *a.
    raw_blocks = re.split(r'(?=\*?a\.\s)', text)

    questions = []
    buffer = ""
    for part in raw_blocks:
        part = part.strip()
        if not part:
            continue

        # Nếu không có đáp án nào trong đoạn => gộp với đoạn trước
        if not re.search(r'[a-cA-C]\.', part):
            buffer += " " + part
            continue

        # Nếu buffer đang có nội dung, xử lý câu trước đó
        if buffer:
            questions.append(buffer.strip())
            buffer = ""
        buffer = part

    # Thêm phần cuối
    if buffer:
        questions.append(buffer.strip())

    parsed = []
    for block in questions:
        # Tách câu hỏi và đáp án
        parts = re.split(r'(?=[a-cA-C]\.\s|\*[a-cA-C]\.\s)', block)
        if len(parts) < 2:
            continue

        question_text = parts[0].strip()
        options = []
        correct = None

        for p in parts[1:]:
            match = re.match(r"(\*?)([a-cA-C])\.\s*(.*)", p.strip())
            if match:
                is_correct = bool(match.group(1))
                text = match.group(3)
                options.append(text)
                if is_correct:
                    correct = text
            else:
                question_text += " " + p.strip()

        if options and correct:
            parsed.append({
                "question": question_text,
                "options": options,
                "answer": correct
            })

    return parsed

# =========================
# 🔹 TẢI DỮ LIỆU
# =========================
questions = load_questions("bank.docx")
TOTAL = len(questions)

if TOTAL == 0:
    st.error("❌ Không đọc được câu hỏi nào. Có thể file Word dùng numbering tự động.")
    st.stop()

st.success(f"📘 Đã tải thành công {TOTAL} câu hỏi.")

# =========================
# 🎮 LOGIC THI 20 CÂU MỖI LƯỢT
# =========================
if "remaining_questions" not in st.session_state:
    st.session_state.remaining_questions = list(range(TOTAL))
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
        st.info("✅ Bạn đã hoàn thành toàn bộ câu hỏi!")
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

st.markdown(f"### 🧭 Câu {st.session_state.index + 1}/20\n\n**{q['question']}**\n\n---")
choice = st.radio("👉 Chọn đáp án của bạn:", q["options"], index=None, key=f"radio_{st.session_state.index}")

if st.button("✅ Xác nhận"):
    st.session_state.answered = True
    if choice == q["answer"]:
        st.success("🎯 Chính xác!")
        st.session_state.score += 1
    else:
        st.error(f"❌ Sai rồi — Đáp án đúng là: **{q['answer']}**")

if st.session_state.answered and st.button("➡️ Câu tiếp theo"):
    st.session_state.index += 1
    st.session_state.answered = False
    st.rerun()
