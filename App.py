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

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    questions = []

    current_q = {"question": "", "options": [], "answer": None}

    for line in paragraphs:
        # Nếu dòng bắt đầu bằng đáp án (a/b/c/d, có thể * hoặc khoảng trắng trước)
        if re.match(r"^\s*\*?\s*[a-dA-D]\.\s", line):
            match = re.match(r"^\s*(\*?)\s*([a-dA-D])\.\s*(.*)", line)
            if match:
                is_correct = bool(match.group(1))
                text = match.group(3).strip()
                current_q["options"].append(text)
                if is_correct:
                    current_q["answer"] = text
        else:
            # Nếu gặp dòng mới sau khi có đáp án => lưu câu trước
            if current_q["options"]:
                if current_q["question"] and current_q["answer"]:
                    questions.append(current_q)
                current_q = {"question": "", "options": [], "answer": None}

            # Gộp dòng vào nội dung câu hỏi
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
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại file bank.docx hoặc cấu trúc file.")
    st.stop()

st.success(f"📘 Đã tải thành công {TOTAL} câu hỏi.")

# =========================
# 🎮 LOGIC THI 20 CÂU MỖI LƯỢT
# =========================
if "remaining" not in st.session_state:
    st.session_state.remaining = list(range(TOTAL))
if "batch" not in st.session_state:
    st.session_state.batch = random.sample(st.session_state.remaining, min(20, len(st.session_state.remaining)))
    for i in st.session_state.batch:
        st.session_state.remaining.remove(i)
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

batch = st.session_state.batch

# =========================
# 📄 HIỂN THỊ 20 CÂU CÙNG LÚC
# =========================
if not st.session_state.submitted:
    st.markdown("### 📘 Trả lời 20 câu hỏi dưới đây:")

    for idx, q_index in enumerate(batch):
        q = questions[q_index]
        st.markdown(f"**{idx+1}. {q['question']}**")
        st.session_state.answers[q_index] = st.radio(
            "",
            q["options"],
            index=None,
            key=f"q_{q_index}"
        )
        st.divider()

    if st.button("✅ Xem kết quả"):
        st.session_state.submitted = True
        st.rerun()

else:
    # Tính điểm và hiển thị kết quả
    score = 0
    for q_index in batch:
        q = questions[q_index]
        selected = st.session_state.answers.get(q_index)
        correct = q["answer"]
        is_correct = selected == correct
        if is_correct:
            score += 1

        st.markdown(
            f"**{q['question']}**  \n"
            f"👉 Bạn chọn: {selected if selected else '—'}  \n"
            f"✅ Đáp án đúng: **{correct}**"
        )
        st.markdown("---")

    st.success(f"🎯 Điểm của bạn: {score}/20")

    if len(st.session_state.remaining) > 0:
        if st.button("➡️ Làm 20 câu tiếp theo"):
            st.session_state.batch = random.sample(
                st.session_state.remaining,
                min(20, len(st.session_state.remaining))
            )
            for i in st.session_state.batch:
                st.session_state.remaining.remove(i)
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()
    else:
        st.info("✅ Bạn đã hoàn thành toàn bộ câu hỏi!")
        if st.button("🔄 Làm lại từ đầu"):
            st.session_state.remaining = list(range(TOTAL))
            st.session_state.batch = random.sample(st.session_state.remaining, 20)
            for i in st.session_state.batch:
                st.session_state.remaining.remove(i)
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()
