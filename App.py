# app.py
import streamlit as st
from docx import Document
import re
import math
import io
import csv

st.set_page_config(page_title="Ngân hàng câu hỏi (Lawbank & Cabbank)", layout="wide")

# ---------------------------
# HÀM GIÚP
# ---------------------------
def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def is_ref_line(text: str) -> bool:
    return bool(re.match(r'(?i)^\s*ref[:.\s]', text)) or bool(re.match(r'(?i)^ref\b', text))

# ---------------------------
# PARSER CABBANK (GIỮ NGUYÊN, KHÔNG SỬA LOGIC)
# Parser đơn giản, tương tự bản bạn nói là đã chạy OK.
# ---------------------------
def load_cabbank(path_or_file):
    try:
        doc = Document(path_or_file)
    except Exception as e:
        st.error(f"Không thể đọc file cabbank: {e}")
        return []

    # Gộp các paragraph không rỗng
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    # Chèn newline trước marker đáp án (nếu dính liền)
    text = "\n".join(paras)
    text = re.sub(r'(?<!\n)(?=\*?\s*[A-Da-d]\s*(?:[.\)]))', '\n', text, flags=re.I)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    questions = []
    current = {"question": "", "options": [], "answer": ""}

    opt_re = re.compile(r'^\*?\s*([A-Da-d])\s*(?:[.\)])\s*(.*)$', flags=re.S)
    for line in lines:
        # skip REF lines if any
        if is_ref_line(line):
            continue

        m = opt_re.match(line)
        if m:
            # option line
            letter = m.group(1).lower()
            body = clean_text(m.group(2))
            opt_text = f"{letter}. {body}" if body else f"{letter}."
            if line.lstrip().startswith("*"):
                current["answer"] = opt_text
            current["options"].append(opt_text)
        else:
            # question or continuation
            # if we already have a question + options, then this starts a new question
            if current["question"] and current["options"]:
                # finalize previous
                if not current["answer"] and current["options"]:
                    current["answer"] = current["options"][0]
                questions.append(current)
                current = {"question": line, "options": [], "answer": ""}
            else:
                # append to current question (may be multi-line)
                current["question"] = (current["question"] + " " + line).strip() if current["question"] else line

    # finalize last
    if current["question"] and current["options"]:
        if not current["answer"] and current["options"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    return questions

# ---------------------------
# PARSER LAWBANK (RIÊNG BIỆT, TẬP TRUNG SỬA LỖI)
# - Xử lý khi lawbank đã được chuyển về cấu trúc giống cabbank:
#   câu hỏi (một hoặc nhiều dòng), sau đó đáp án a., b., c., d. (có thể có * trước ký tự)
# - Loại bỏ hoàn toàn dòng REF...
# - Đảm bảo không mất câu hỏi, không tách đáp án sang câu khác
# ---------------------------
def load_lawbank(path_or_file):
    try:
        doc = Document(path_or_file)
    except Exception as e:
        st.error(f"Không thể đọc file lawbank: {e}")
        return []

    # Lấy paragraphs non-empty, bỏ hoàn toàn những paragraph bắt đầu bằng Ref
    paras = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if is_ref_line(t):
            continue
        paras.append(t)

    # Nếu file có một đoạn lớn (một paragraph chứa nhiều đáp án dính liền),
    # chèn newline trước các marker đáp án để tách chúng ra. Nhưng tránh bắt nhầm A/C hoặc các ký hiệu khác.
    joined = "\n".join(paras)

    # Insert newline before an answer marker when it's not already at line start.
    # Conditions: not preceded by newline, and not inside a word or slash (avoid A/C)
    # Use lookahead to insert newline before optional '*' and letter a-d + '.' or ')'
    joined = re.sub(r'(?<!\n)(?<![A-Za-z0-9/])(?=\*?\s*[A-Da-d]\s*(?:[.\)]))', '\n', joined, flags=re.I)

    # Now split into lines
    lines = [ln.strip() for ln in joined.splitlines() if ln.strip()]

    questions = []
    current = {"question": "", "options": [], "answer": ""}
    last_non_option = None  # remember last seen non-option line (to recover missing question)

    # Option regex: starts with optional '*' then letter a-d then '.' or ')'
    opt_re = re.compile(r'^\*?\s*([A-Da-d])\s*(?:[.\)])\s*(.*)$', flags=re.S)

    for line in lines:
        # skip leftover Ref lines just in case
        if is_ref_line(line):
            continue

        m = opt_re.match(line)
        if m:
            # it's an option line
            letter = m.group(1).lower()
            body = clean_text(m.group(2))
            opt_text = f"{letter}. {body}" if body else f"{letter}."

            # If we don't currently have a question text, try to use last_non_option as question
            if not current["question"]:
                if last_non_option:
                    current["question"] = last_non_option
                    last_non_option = None
                else:
                    # No question context: create placeholder so options aren't lost
                    current["question"] = "(Không có đề bài - kiểm tra file gốc)"

            current["options"].append(opt_text)
            if line.lstrip().startswith("*"):
                current["answer"] = opt_text
            # continue
        else:
            # non-option line -> likely a question or continuation
            # if we already have options collected for current, this marks next question
            if current["question"] and current["options"]:
                # finalize previous question
                if not current["answer"] and current["options"]:
                    current["answer"] = current["options"][0]
                questions.append(current)
                current = {"question": line, "options": [], "answer": ""}
                last_non_option = line
            else:
                # accumulate into current question (multi-line)
                if current["question"]:
                    current["question"] = (current["question"] + " " + line).strip()
                else:
                    current["question"] = line
                last_non_option = line

    # finalize final question
    if current["question"] and current["options"]:
        if not current["answer"] and current["options"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    # cleanup: strip fields
    for q in questions:
        q["question"] = clean_text(q["question"])
        q["options"] = [clean_text(o) for o in q["options"] if clean_text(o)]
        if not q["answer"] and q["options"]:
            q["answer"] = q["options"][0]

    return questions

# ---------------------------
# UI chính
# ---------------------------
st.title("📚 Ngân hàng câu hỏi — Lawbank (ưu tiên) & Cabbank (giữ nguyên)")

uploaded = st.file_uploader("Upload file .docx (nếu muốn test file mới) — chọn đúng file cho mỗi ngân hàng", type=["docx"])

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Luật (Lawbank)", "Ngân hàng Kỹ thuật (Cabbank)"])

# chọn nguồn
if uploaded:
    source = uploaded
else:
    source = "lawbank.docx" if "Luật" in bank_choice else "cabbank.docx"

# parse tương ứng
if "Luật" in bank_choice:
    questions = load_lawbank(source)
else:
    questions = load_cabbank(source)

# debug preview
with st.expander("🔧 Thông tin debug & preview (mở ra kiểm tra)"):
    st.write(f"Nguồn: {'uploaded file' if uploaded else source}")
    st.write(f"Số câu parse được: {len(questions)}")
    if len(questions) > 0:
        st.write("3 câu đầu (full):")
        for i, q in enumerate(questions[:3], 1):
            st.write(f"{i}. Q: {q['question']}")
            for o in q['options']:
                st.write(f"  - {o} {'✅' if o == q['answer'] else ''}")

if not questions:
    st.error("Không đọc được câu hỏi nào. Nếu bạn đã upload file lawbank, hãy đảm bảo file đã lưu với cấu trúc: câu hỏi (line) → *a. ... b. ... c. ... → Ref: ... (bị loại bỏ).")
    st.stop()

st.success(f"Đã đọc được {len(questions)} câu hỏi từ ngân hàng.")

# Cho phép tra cứu/export
st.markdown("## 🔎 Tra cứu & Xuất")
keyword = st.text_input("Tìm kiếm (từ khoá trong câu hỏi hoặc đáp án):").strip().lower()
filtered = []
for q in questions:
    hay = (keyword in q["question"].lower()) or any(keyword in opt.lower() for opt in q["options"])
    if not keyword or hay:
        filtered.append(q)

st.write(f"Hiển thị {len(filtered)} / {len(questions)} câu")

# hiển thị table-like + tải CSV
if len(filtered):
    # show simple list
    for idx, q in enumerate(filtered, start=1):
        st.markdown(f"**{idx}. {q['question']}**")
        for o in q["options"]:
            st.write(f"- {o} {'✅' if o == q['answer'] else ''}")
        st.markdown("---")

    # prepare CSV
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["STT", "Câu hỏi", "Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D", "Đáp án đúng"])
    for i, q in enumerate(filtered, start=1):
        row = [i, q["question"]]
        row += [q["options"][j] if j < len(q["options"]) else "" for j in range(4)]
        row.append(q["answer"])
        writer.writerow(row)
    st.download_button("⬇️ Tải CSV", data=csv_buf.getvalue(), file_name="ngan_hang_cauhoi.csv", mime="text/csv")
else:
    st.info("Không có câu nào khớp từ khoá.")

# Nếu muốn làm bài -> nhóm
st.markdown("## 🧠 Làm bài (theo nhóm)")
group_size = 10
TOTAL = len(questions)
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

selected_group = st.selectbox("Chọn nhóm câu:", group_labels, index=0)
start = group_labels.index(selected_group) * group_size
end = min(start + group_size, TOTAL)
batch = questions[start:end]

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if not st.session_state.submitted:
    st.markdown(f"### Nhóm {selected_group} ({len(batch)} câu)")
    for i, q in enumerate(batch, start=start + 1):
        st.markdown(f"**{i}. {q['question']}**")
        st.radio("", q["options"], key=f"q_{i}")
        st.markdown("---")
    if st.button("✅ Nộp bài"):
        st.session_state.submitted = True
        st.experimental_rerun()
else:
    score = 0
    for i, q in enumerate(batch, start=start + 1):
        selected = st.session_state.get(f"q_{i}")
        if clean_text(selected) == clean_text(q["answer"]):
            score += 1
            st.success(f"{i}. ✅ {q['question']} — {q['answer']}")
        else:
            st.error(f"{i}. ❌ {q['question']} — Bạn: {selected} — Đúng: {q['answer']}")
        st.markdown("---")
    st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")
    if st.button("🔁 Làm lại nhóm này"):
        for i in range(start + 1, end + 1):
            st.session_state.pop(f"q_{i}", None)
        st.session_state.submitted = False
        st.experimental_rerun()
