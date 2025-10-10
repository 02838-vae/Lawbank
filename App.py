import streamlit as st
from docx import Document
import re
import math


# ==========================
# 🔧 HÀM XỬ LÝ CHUNG
# ==========================
def clean_text(s: str) -> str:
    """Chuẩn hóa khoảng trắng"""
    return re.sub(r'\s+', ' ', s).strip()


# ==========================
# 📘 PARSER CHO LAW BANK
# ==========================
def parse_lawbank(docx_file):
    """
    Đọc file lawbank.docx (định dạng có số thứ tự, đáp án a./b./c., Ref. ở cuối)
    """
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"Không thể đọc file lawbank.docx: {e}")
        return []

    text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    # Tách các khối câu hỏi bắt đầu bằng số thứ tự
    blocks = re.split(r'\n\s*\d+\.\s*', text)
    questions = []

    for block in blocks:
        if not block.strip():
            continue
        # Loại phần Ref.
        block = re.split(r'Ref[:.]', block, flags=re.I)[0]
        # Chèn xuống dòng trước mỗi đáp án (a., b., c., d. hoặc *a.)
        block = re.sub(r'(?<!\n)(?=[*]?\s*[A-Da-d]\s*[.\)])', '\n', block)
        lines = [clean_text(l) for l in block.split("\n") if l.strip()]

        if len(lines) < 2:
            continue

        qtext = lines[0]
        opts = []
        correct = ""

        for ln in lines[1:]:
            m = re.match(r'^[*]?\s*([A-Da-d])\s*[.\)]\s*(.*)$', ln)
            if m:
                letter = m.group(1).lower()
                body = m.group(2).strip()
                full_opt = f"{letter}. {body}"
                opts.append(full_opt)
                if ln.strip().startswith("*"):
                    correct = full_opt
            else:
                # dòng nối dài
                if opts:
                    opts[-1] += " " + ln
                    opts[-1] = clean_text(opts[-1])
                else:
                    qtext += " " + ln

        if opts:
            if not correct:
                correct = opts[0]
            questions.append({"question": qtext, "options": opts, "answer": correct})

    return questions


# ==========================
# 📗 PARSER CHO CAB BANK
# ==========================
def parse_cabbank(docx_file):
    """
    Đọc file cabbank.docx (không đánh số, đáp án có thể dính liền dòng)
    """
    try:
        doc = Document(docx_file)
    except Exception as e:
        st.error(f"Không thể đọc file cabbank.docx: {e}")
        return []

    text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    text = re.sub(r'(?<!\n)(?=[*]?\s*[A-Da-d]\s*[.\)])', '\n', text)
    lines = [clean_text(l) for l in text.split("\n") if l.strip()]

    questions = []
    current = {"question": "", "options": [], "answer": ""}

    for ln in lines:
        # dòng đáp án
        if re.match(r'^[*]?\s*[A-Da-d]\s*[.\)]', ln):
            opt_text = re.sub(r'^[*]?\s*[A-Da-d]\s*[.\)]\s*', '', ln)
            letter = ln.strip()[1].lower() if ln.strip()[0] == "*" else ln.strip()[0].lower()
            full_opt = f"{letter}. {opt_text.strip()}"
            current["options"].append(full_opt)
            if ln.strip().startswith("*"):
                current["answer"] = full_opt
        else:
            # dòng câu hỏi
            if current["options"]:
                # nếu đang có options -> lưu lại câu hỏi cũ
                if not current["answer"] and current["options"]:
                    current["answer"] = current["options"][0]
                questions.append(current)
                current = {"question": "", "options": [], "answer": ""}
            current["question"] += (" " + ln).strip()

    # thêm câu cuối
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    return questions


# ==========================
# ⚙️ GIAO DIỆN STREAMLIT
# ==========================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")
st.title("📚 Ngân hàng câu hỏi trắc nghiệm")

# --- Bước 1: chọn ngân hàng ---
bank_choice = st.selectbox(
    "Chọn ngân hàng câu hỏi:",
    ["Ngân hàng Luật", "Ngân hàng Kỹ thuật"]
)

# --- Bước 2: đọc file ---
if "Luật" in bank_choice:
    file_path = "lawbank.docx"
    questions = parse_lawbank(file_path)
else:
    file_path = "cabbank.docx"
    questions = parse_cabbank(file_path)

# --- Bước 3: kiểm tra kết quả parse ---
if not questions:
    st.error(f"❌ Không đọc được câu hỏi nào trong file {file_path}. Kiểm tra định dạng file .docx.")
    st.stop()

st.success(f"✅ Đã đọc được {len(questions)} câu hỏi từ {file_path}.")

with st.expander("🔍 Xem trước 5 câu đầu (kiểm tra parsing)"):
    for i, q in enumerate(questions[:5], 1):
        st.markdown(f"**{i}. {q['question']}**")
        for opt in q["options"]:
            mark = "✅" if opt == q["answer"] else ""
            st.write(f"- {opt} {mark}")
        st.markdown("---")

# --- Bước 4: bắt đầu làm bài ---
if st.button("🚀 Bắt đầu làm bài"):
    group_size = 10
    TOTAL = len(questions)
    group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(math.ceil(TOTAL/group_size))]
    selected_group = st.selectbox("Chọn nhóm câu hỏi:", group_labels, index=0)
    start = group_labels.index(selected_group) * group_size
    end = min(start + group_size, TOTAL)
    batch = questions[start:end]

    st.session_state.submitted = False

    placeholder_choice = "-- Chưa chọn --"
    for i, q in enumerate(batch, start=start + 1):
        st.markdown(f"### {i}. {q['question']}")
        st.radio("", [placeholder_choice] + q["options"], key=f"q_{i}", index=0)
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("✅ Nộp bài"):
        score = 0
        for i, q in enumerate(batch, start=start + 1):
            selected = st.session_state.get(f"q_{i}")
            correct = q["answer"]
            if selected == correct:
                score += 1
                st.success(f"{i}. ✅ Đúng ({correct})")
            else:
                st.error(f"{i}. ❌ Sai ({selected}) — Đúng: {correct}")
        st.subheader(f"🎯 Kết quả: {score}/{len(batch)} câu đúng")
