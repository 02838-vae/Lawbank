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

def read_docx_paragraphs(source):
    """Return list of non-empty paragraph texts. source may be filepath or uploaded file-like"""
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file .docx: {e}")
        return []
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return paras

# ---------------------------
# Robust parser for CABBANK (Kỹ thuật)
# ---------------------------
def parse_cabbank(source):
    """
    Parse cabbank with robust paragraph-based logic:
    - Find option markers within each paragraph using finditer (handles *a., a., a), d . etc.)
    - If paragraph has no option markers:
        - if current question has no options -> append to question text
        - if current question has options -> finalize current and start a new question with this paragraph
    - If paragraph has option markers:
        - text before first marker is appended to current.question (or used to start question)
        - each (marker, text_until_next_marker) becomes one option
    """
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

    questions = []
    current = {"question": "", "options": [], "answer": ""}

    # Pattern: optional '*', optional spaces, letter A-D, optional spaces, then '.' or ')', allow spaces between letter and punctuation
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])\s*(?:\.\s*|\)\s*)')

    for p in paras:
        matches = list(opt_pat.finditer(p))
        if not matches:
            # no option markers in this paragraph
            if current["options"]:
                # this paragraph looks like the next question header -> finalize previous question
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    # normalize
                    current["question"] = clean_text(current["question"])
                    current["options"] = [clean_text(o) for o in current["options"]]
                    current["answer"] = clean_text(current["answer"])
                    questions.append(current)
                # start new question with this paragraph text
                current = {"question": clean_text(p), "options": [], "answer": ""}
            else:
                # still collecting question (paragraph continuation)
                current["question"] = (current["question"] + " " + p).strip() if current["question"] else clean_text(p)
            continue

        # Paragraph has one or more option markers
        # Text before first match (if any) belongs to question (or may indicate new question)
        first_match = matches[0]
        pre_text = p[:first_match.start()].strip()
        if pre_text:
            if current["options"]:
                # ambiguous: we've already collected options for current, but now there's pre_text before new options:
                # treat pre_text as start of next question — finalize current and start new one
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    current["question"] = clean_text(current["question"])
                    current["options"] = [clean_text(o) for o in current["options"]]
                    current["answer"] = clean_text(current["answer"])
                    questions.append(current)
                current = {"question": clean_text(pre_text), "options": [], "answer": ""}
            else:
                # no options yet -> pre_text is part (or all) of question
                current["question"] = (current["question"] + " " + pre_text).strip() if current["question"] else clean_text(pre_text)

        # Extract each option by slicing from match.end() to next match.start() (or end)
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(p)
            opt_body = p[start:end].strip()
            opt_body = clean_text(opt_body)
            letter = m.group("letter").lower()
            option_text = f"{letter}. {opt_body}" if opt_body else f"{letter}."
            current["options"].append(option_text)
            if m.group("star"):
                current["answer"] = option_text

        # do NOT finalize here; maybe next paragraph contains continuation or next question

    # After loop, finalize last current if valid
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        current["question"] = clean_text(current["question"])
        current["options"] = [clean_text(o) for o in current["options"]]
        current["answer"] = clean_text(current["answer"])
        questions.append(current)

    return questions

# ---------------------------
# Tolerant parser for LAWBANK (kept robust)
# ---------------------------
def parse_lawbank(source):
    """
    Parse lawbank blocks numbered 1., 2., ... Accept 'Ref.' and options a./b./c./d.
    Uses a similar paragraph-aware approach to avoid cutting questions.
    """
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

    # Join paras with newline to find numbered blocks (number may be at line start)
    text = "\n".join(paras)
    # Find blocks by numeric headings (keep everything after the numeric marker)
    blocks = re.finditer(r'(?:(?:^)|\n)\s*(\d+)\s*[.)]\s*(.*?)(?=(?:\n\s*\d+\s*[.)]\s*)|\Z)', text, flags=re.S)
    questions = []
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])\s*(?:\.\s*|\)\s*)')

    for b in blocks:
        body = b.group(2).strip()
        # remove Ref: part to avoid numbers inside Ref confusing parsing
        body_head = re.split(r'\bRef[:.]', body, flags=re.I)[0].strip()
        # find matches for options within this block
        matches = list(opt_pat.finditer(body_head))
        if not matches:
            continue
        # text before first match is question text
        first = matches[0]
        q_text = body_head[:first.start()].strip()
        q_text = clean_text(q_text)
        opts = []
        answer = ""
        for idx, m in enumerate(matches):
            s = m.end()
            e = matches[idx+1].start() if idx+1 < len(matches) else len(body_head)
            opt_body = body_head[s:e].strip()
            opt_body = clean_text(opt_body)
            letter = m.group("letter").lower()
            option_text = f"{letter}. {opt_body}" if opt_body else f"{letter}."
            opts.append(option_text)
            if m.group("star"):
                answer = option_text
        if opts:
            if not answer:
                answer = opts[0]
            questions.append({"question": q_text, "options": opts, "answer": answer})
    return questions

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")
st.title("📚 Ngân hàng câu hỏi — (fix parser CABBANK)")

uploaded = st.file_uploader("Upload file .docx (tùy chọn, ưu tiên test file riêng)", type=["docx"])

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])

source = uploaded if uploaded is not None else ("cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx")

if "Kỹ thuật" in bank_choice:
    questions = parse_cabbank(source)
else:
    questions = parse_lawbank(source)

if not questions:
    st.error("Không đọc được câu hỏi nào. Kiểm tra file hoặc upload file mẫu để debug.")
    st.stop()

st.success(f"Đã đọc được {len(questions)} câu hỏi từ nguồn.")

with st.expander("🔍 Xem 10 câu đầu (kiểm tra parsing)"):
    for i, q in enumerate(questions[:10], start=1):
        st.markdown(f"**{i}. {q['question']}**")
        for o in q['options']:
            mark = "✅" if o == q['answer'] else ""
            st.write(f"- {o} {mark}")
        st.markdown("---")

# Show indices that may be suspicious (few options or missing)
suspicious = []
for idx, q in enumerate(questions, start=1):
    if not q.get("question") or not q.get("options") or len(q.get("options", [])) < 3:
        suspicious.append(idx)
if suspicious:
    with st.expander("⚠️ Những câu có thể parse chưa đầy đủ (index)"):
        st.write(f"Số lượng khả nghi: {len(suspicious)}")
        st.write(suspicious[:200])

# Quiz flow
if st.button("🚀 Bắt đầu làm bài với ngân hàng này"):
    TOTAL = len(questions)
    group_size = 10
    num_groups = math.ceil(TOTAL / group_size)
    group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

    # session reset when changing bank/upload
    if "current_bank" not in st.session_state:
        st.session_state.current_bank = bank_choice
    if st.session_state.current_bank != bank_choice:
        for k in list(st.session_state.keys()):
            if k.startswith("q_"):
                del st.session_state[k]
        st.session_state.current_bank = bank_choice

    selected_group = st.selectbox("Chọn nhóm:", group_labels)
    start = group_labels.index(selected_group) * group_size
    end = min(start + group_size, TOTAL)
    batch = questions[start:end]

    placeholder = "-- Chưa chọn --"
    st.markdown(f"### 🧾 Nhóm {selected_group} (các câu {start+1} → {end})")

    for i, q in enumerate(batch, start=start + 1):
        st.markdown(f"**{i}. {q['question']}**")
        opts_ui = [placeholder] + q["options"]
        st.radio("", opts_ui, index=0, key=f"q_{i}")
        st.markdown("")

    if st.button("✅ Nộp bài và kiểm tra"):
        unanswered = [i for i in range(start+1, end+1) if st.session_state.get(f"q_{i}") in (None, placeholder)]
        if unanswered:
            st.warning(f"Bạn chưa chọn đáp án cho {len(unanswered)} câu: {', '.join(map(str, unanswered[:30]))}")
        else:
            score = 0
            for i, q in enumerate(batch, start=start + 1):
                selected = st.session_state.get(f"q_{i}")
                if clean_text(selected) == clean_text(q["answer"]):
                    score += 1
                    st.success(f"{i}. ✅ Đúng — {q['answer']}")
                else:
                    st.error(f"{i}. ❌ Sai — Bạn: {selected} — Đúng: {q['answer']}")
            st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")
