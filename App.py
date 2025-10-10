# app.py
import streamlit as st
from docx import Document
import re
import math

# ---------------------------
# Helpers
# ---------------------------
def clean_text(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r'\s+', ' ', s).strip()

def read_docx_text(source):
    """
    source: either file path string or uploaded file-like object from Streamlit
    Returns: joined text of paragraphs
    """
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file .docx: {e}")
        return ""
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paragraphs)

# ---------------------------
# CABBANK parser (Kỹ thuật) - robust
# ---------------------------
def parse_cabbank(source):
    """
    Parse cabbank: question lines followed by options a./b./c. or a)/b)/c) etc.
    - Correct answer indicated by '*' immediately before the letter, e.g. '*a.' or '*a)'
    - Options may be on same line or dính liền; we insert newlines before option markers to split them.
    """
    raw = read_docx_text(source)
    if not raw:
        return []

    # Insert newline before any answer marker (if not already start of line).
    # Handles patterns like "*a.", "a.", "a)", "d .", "d )", with optional spaces.
    # Positive lookahead: optional '*', optional spaces, letter A-D, optional spaces, then '.' or ')'
    lookahead = r'(?<!\n)(?=\*?\s*[A-Da-d]\s*(?:\.\s*|\)\s*))'
    text = re.sub(lookahead, '\n', raw, flags=re.I)

    # Split into non-empty trimmed lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    questions = []
    current = {"question": "", "options": [], "answer": ""}

    opt_re = re.compile(r'^\*?\s*([A-Da-d])\s*(?:[.\)])\s*(.*)$', flags=re.S)

    for ln in lines:
        m = opt_re.match(ln)
        if m:
            # This is an option line
            letter = m.group(1).lower()
            body = clean_text(m.group(2))
            opt_text = f"{letter}. {body}" if body else f"{letter}."
            # If body may contain subsequent answer markers (rare), we already inserted newlines above.
            # If this line starts with *, mark as correct
            is_star = ln.lstrip().startswith('*')
            current["options"].append(opt_text)
            if is_star:
                current["answer"] = opt_text
        else:
            # Not an option marker -> a question line (or continuation)
            # If current already has options, that means we've reached the next question
            if current["options"]:
                # finalize previous question if valid
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    # clean entries
                    current["question"] = clean_text(current["question"])
                    current["options"] = [clean_text(o) for o in current["options"]]
                    current["answer"] = clean_text(current["answer"])
                    questions.append(current)
                # start new question
                current = {"question": clean_text(ln), "options": [], "answer": ""}
            else:
                # still collecting question text (concat multi-line question)
                if current["question"]:
                    current["question"] = clean_text(current["question"] + " " + ln)
                else:
                    current["question"] = clean_text(ln)

    # append last
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        current["question"] = clean_text(current["question"])
        current["options"] = [clean_text(o) for o in current["options"]]
        current["answer"] = clean_text(current["answer"])
        questions.append(current)

    return questions

# ---------------------------
# Simple LAWBANK parser (kept compatible)
# ---------------------------
def parse_lawbank(source):
    """
    Parse lawbank: blocks numbered 1., 2., ... with options a., b., c., d. and 'Ref.' possibly present.
    This is more tolerant but focus was on cabbank first.
    """
    raw = read_docx_text(source)
    if not raw:
        return []

    # Split into blocks using numbers as separators (keeps the number at start of block)
    # We'll split on newline followed by digits + dot/), or start of text digits + dot
    # Use finditer for robustness
    # To simplify, use regex to find all matches of pattern: number + '.' then everything until next number or end
    pattern = re.compile(r'(\d+\s*[.)]\s*)(.*?)(?=(?:\n\s*\d+\s*[.)]\s*)|\Z)', flags=re.S)
    matches = pattern.findall(raw)

    questions = []
    opt_re = re.compile(r'^\*?\s*([A-Da-d])\s*(?:[.\)])\s*(.*)$', flags=re.S)

    if not matches:
        # fallback: try more naive splitting by occurrences of digit-dot
        parts = re.split(r'\n\s*\d+\s*[.)]\s*', raw)
        iter_parts = parts[1:] if parts and not parts[0].strip() else parts
    else:
        iter_parts = [m[1].strip() for m in matches]

    for part in iter_parts:
        if not part.strip():
            continue
        # Remove everything after "Ref" to avoid confusion with numbers inside ref
        part_head = re.split(r'\bRef[:.]', part, flags=re.I)[0]
        # Insert newline before option markers
        lookahead = r'(?<!\n)(?=\*?\s*[A-Da-d]\s*(?:\.\s*|\)\s*))'
        part2 = re.sub(lookahead, '\n', part_head, flags=re.I)
        lines = [l.strip() for l in part2.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        q_line = re.sub(r'^\d+\s*[.)]\s*', '', lines[0]).strip()
        qtext = clean_text(q_line)
        opts = []
        correct = ""
        for ln in lines[1:]:
            m = opt_re.match(ln)
            if m:
                letter = m.group(1).lower()
                body = clean_text(m.group(2))
                opt = f"{letter}. {body}"
                opts.append(opt)
                if ln.lstrip().startswith('*'):
                    correct = opt
            else:
                # continuation
                if opts:
                    opts[-1] = clean_text(opts[-1] + " " + ln)
                else:
                    qtext = clean_text(qtext + " " + ln)
        if opts:
            if not correct:
                correct = opts[0]
            questions.append({"question": qtext, "options": opts, "answer": correct})

    return questions

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")
st.title("📚 Ngân hàng câu hỏi — Debug & Quiz")

# Upload is optional (for testing)
uploaded = st.file_uploader("Upload file .docx (nếu muốn test file riêng)", type=["docx"])

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])

# Choose source: uploaded if given else default files
if uploaded is not None:
    source = uploaded
else:
    source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"

# Parse based on bank
if "Kỹ thuật" in bank_choice:
    questions = parse_cabbank(source)
else:
    questions = parse_lawbank(source)

# Debug / preview area
st.markdown("---")
st.header("🔍 Kết quả parsing (preview)")

if not questions:
    st.error("Không đọc được câu hỏi nào. Kiểm tra file hoặc định dạng. Nếu upload file, thử mở file gốc và copy 1–2 câu mẫu vào đây để debug.")
    st.stop()

st.success(f"Đã đọc được {len(questions)} câu hỏi từ nguồn.")

# Show some diagnostics
with st.expander("Xem 10 câu đầu (kiểm tra chi tiết)"):
    for i, q in enumerate(questions[:10], start=1):
        st.markdown(f"**{i}. {q['question']}**")
        for o in q['options']:
            flag = "✅" if o == q['answer'] else ""
            st.write(f"- {o} {flag}")
        st.markdown("---")

# Identify problematic parsed questions
bad = []
for idx, q in enumerate(questions, start=1):
    if not q.get("question") or not q.get("options"):
        bad.append(idx)
    elif len(q.get("options", [])) < 3:
        # maybe a sign of incomplete parsing — still list it
        bad.append(idx)

if bad:
    with st.expander("⚠️ Những câu có thể bị parse không đầy đủ (xem index)"):
        st.write(f"Số lượng khả nghi: {len(bad)}")
        st.write(bad[:200])

st.markdown("---")

# Start quiz only when user clicks
if st.button("🚀 Bắt đầu làm bài với ngân hàng này"):
    TOTAL = len(questions)
    group_size = 10
    num_groups = math.ceil(TOTAL / group_size)
    group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

    # Manage session_state for bank changes
    if "current_bank" not in st.session_state:
        st.session_state.current_bank = bank_choice
    if st.session_state.current_bank != bank_choice:
        # clear old answers
        for k in list(st.session_state.keys()):
            if k.startswith("q_"):
                del st.session_state[k]
        st.session_state.current_bank = bank_choice

    selected_group = st.selectbox("Chọn nhóm câu:", group_labels)
    start = group_labels.index(selected_group) * group_size
    end = min(start + group_size, TOTAL)
    batch = questions[start:end]

    placeholder = "-- Chưa chọn --"
    st.markdown(f"### 🧾 Nhóm {selected_group} (các câu {start+1} → {end})")

    # render questions
    for i, q in enumerate(batch, start=start + 1):
        st.markdown(f"**{i}. {q['question']}**")
        opts_ui = [placeholder] + q["options"]
        # default index 0 (placeholder)
        st.radio("", opts_ui, index=0, key=f"q_{i}")
        st.markdown("")

    if st.button("✅ Nộp bài và kiểm tra"):
        # check unanswered
        unanswered = [i for i in range(start+1, end+1) if st.session_state.get(f"q_{i}") in (None, placeholder)]
        if unanswered:
            st.warning(f"Bạn chưa chọn đáp án cho {len(unanswered)} câu: {', '.join(map(str, unanswered[:30]))}")
        else:
            # grading
            score = 0
            for i, q in enumerate(batch, start=start + 1):
                selected = st.session_state.get(f"q_{i}")
                # compare normalized
                if clean_text(selected) == clean_text(q["answer"]):
                    score += 1
                    st.success(f"{i}. ✅ Đúng — {q['answer']}")
                else:
                    st.error(f"{i}. ❌ Sai — Bạn: {selected} — Đáp án đúng: {q['answer']}")
            st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")

    st.markdown("---")
    st.write("Bạn có thể kéo xuống để làm nhóm khác hoặc nhấn làm lại nhóm hiện tại (xóa lựa chọn) bằng cách refresh trang hoặc thay đổi ngân hàng.")

# End of app
