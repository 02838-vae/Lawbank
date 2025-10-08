import streamlit as st
import random
import re
from docx import Document

# ===============================
# ⚙️ Cấu hình giao diện
# ===============================
st.set_page_config(page_title="Ngân hàng câu hỏi luật", page_icon="⚖️", layout="wide")

st.title("⚖️ NGÂN HÀNG CÂU HỎI KIỂM TRA LUẬT (SOP)")

# ===============================
# 🧩 HÀM ĐỌC FILE WORD
# ===============================
def load_questions(docx_path):
    try:
        doc = Document(docx_path)
    except Exception as e:
        st.error(f"❌ Lỗi khi đọc file Word: {e}")
        return []

    # Gộp toàn bộ nội dung thành 1 chuỗi duy nhất
    text = " ".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

    # Nếu không có chữ nào, trả về lỗi
    if not text:
        st.warning("⚠️ File Word trống hoặc không đọc được nội dung.")
        return []

    # ✅ Tách câu hỏi dựa trên pattern: số + dấu chấm + khoảng trắng (có thể có tab hoặc ký tự đặc biệt)
    # Ví dụ: "3. ", "29. ", "100. "
    raw_questions = re.split(r'(?:(?<=\s)|^)(\d{1,3})\.\s+', text)

    # Vì re.split giữ lại nhóm số thứ tự nên cần lọc lại
    merged = []
    buffer = ""
    for part in raw_questions:
        if re.match(r"^\d{1,3}$", part.strip()):
            if buffer:
                merged.append(buffer.strip())
            buffer = part + ". "
        else:
            buffer += part
    if buffer:
        merged.append(buffer.strip())

    questions = []
    for q in merged:
        q = q.strip()
        if not q:
            continue

        # Tách phần câu hỏi và các đáp án
        parts = re.split(r'(?=[a-zA-Z]\.\s|\*[a-zA-Z]\.\s)', q)
        if len(parts) < 2:
            continue

        question_text = parts[0].strip()
        options = []
        correct = None

        for opt in parts[1:]:
            opt = opt.strip()
            match = re.match(r"(\*?)([a-zA-Z])\.\s*(.*)", opt)
            if match:
                is_correct = bool(match.group(1))
                option_text = match.group(3).strip()
                options.append(option_text)
                if is_correct:
                    correct = option_text
            else:
                # Nếu là dòng Ref hoặc phụ chú
                question_text += " " + opt

        if options and correct:
            questions.append({
                "question": question_text,
                "options": options,
                "answer": correct
            })

    return questions


# ===============================
# 🔹 TẢI DỮ LIỆU
# ===============================
questions = load_questions("bank.docx")

if len(questions) == 0:
    st.error("❌ Không đọc được câu hỏi nào từ file Word. Hãy kiểm tra lại định dạng hoặc ký tự đặc biệt trong file.")
    st.stop()

# ===============================
# 🎮 LOGIC KIỂM TRA
# ===============================
if "index" not in st.session_state:
    st.session_state.index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "answered" not in st.session_state:
    st.session_state.answered = False

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

if st.session_state.answered and st.button("➡️ Tiếp theo"):
    st.session_state.index += 1
    st.session_state.answered = False

    if st.session_state.index >= len(questions):
        st.balloons()
        st.success(f"🎉 Bạn đã hoàn thành {len(questions)} câu hỏi!")
        st.info(f"Điểm của bạn: **{st.session_state.score} / {len(questions)}**")
        if st.button("🔁 Làm lại từ đầu"):
            st.session_state.index = 0
            st.session_state.score = 0
    st.rerun()
