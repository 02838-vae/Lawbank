# app.py — phiên bản đã fix đọc numbering tự động trong LAWBank
import streamlit as st
from docx import Document
import re
import math
import pandas as pd

# ====================================================
# ⚙️ HÀM CHUNG
# ====================================================
def clean_text(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r'\s+', ' ', s).strip()

def read_docx_paragraphs_with_numbering(source):
    """Đọc tất cả đoạn văn trong .docx, nếu bị numbering tự động thì thêm số thủ công."""
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file .docx: {e}")
        return []

    paragraphs = []
    counter = 1
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        # Nếu paragraph thuộc list numbering, thêm số vào đầu
        if p.style.name.startswith("List") or p._element.xpath(".//w:numPr"):
            # Kiểm tra xem có sẵn số chưa
            if not re.match(r"^\d+\.", text):
                text = f"{counter}. {text}"
                counter += 1
        paragraphs.append(text)
    return paragraphs

# ====================================================
# 🧩 PARSER CABBANK (KỸ THUẬT)
# ====================================================
def parse_cabbank(source):
    from docx import Document
    paras = [p.text.strip() for p in Document(source).paragraphs if p.text.strip()]
    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])\s*(?:\.\s*|\)\s*)')

    for p in paras:
        matches = list(opt_pat.finditer(p))
        if not matches:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": p, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + p).strip() if current["question"] else p
            continue

        pre_text = p[:matches[0].start()].strip()
        if pre_text:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": pre_text, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre_text).strip() if current["question"] else pre_text

        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(p)
            opt_body = clean_text(p[start:end])
            letter = m.group("letter").lower()
            option_text = f"{letter}. {opt_body}"
            current["options"].append(option_text)
            if m.group("star"):
                current["answer"] = option_text

    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    return questions

# ====================================================
# 🧩 PARSER LAWBANK (LUẬT)
# ====================================================
def parse_lawbank(source):
    paras = read_docx_paragraphs_with_numbering(source)
    if not paras:
        return []

    # Gộp text lại
    text = "\n".join(paras)

    # Xóa dòng Ref...
    text = re.sub(r'(?i)Ref.*', '', text)

    # Thêm xuống dòng trước các số mới
    text = re.sub(r'(?<=\d)\.(?=\s*[A-Z])', '. ', text)
    text = re.sub(r'\n(?=\d+\.)', '\n', text)

    # Chia block theo số thứ tự
    blocks = re.split(r'(?=\n?\d+\.)', text)
    questions = []

    for block in blocks:
        block = block.strip()
        if not block or not re.match(r'^\d+\.', block):
            continue

        joined = " ".join(block.splitlines())
        opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)]\s*')
        matches = list(opt_pat.finditer(joined))
        if not matches:
            continue

        q_text = clean_text(joined[:matches[0].start()])
        opts, ans = [], ""
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(joined)
            opt_text = clean_text(joined[start:end])
            option = f"{m.group('letter').lower()}. {opt_text}"
            opts.append(option)
            if m.group("star"):
                ans = option
        if not ans and opts:
            ans = opts[0]

        questions.append({"question": q_text, "options": opts, "answer": ans})

    return questions

# ====================================================
# 🖥️ GIAO DIỆN STREAMLIT
# ====================================================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")
st.title("📚 Ngân hàng trắc nghiệm")

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])
source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"

# Đọc dữ liệu
questions = parse_cabbank(source) if "Kỹ thuật" in bank_choice else parse_lawbank(source)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra file .docx hoặc định dạng.")
    st.stop()

st.success(f"✅ Đã đọc được {len(questions)} câu hỏi từ {bank_choice}.")

# ====================================================
# TAB CHỨC NĂNG
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu"])

# TAB 1
with tab1:
    group_size = 10
    TOTAL = len(questions)
    groups = [f"Câu {i*group_size+1}-{min((i+1)*group_size,TOTAL)}" for i in range((TOTAL+group_size-1)//group_size)]
    grp = st.selectbox("Chọn nhóm:", groups)
    start = groups.index(grp) * group_size
    end = min(start+group_size, TOTAL)
    batch = questions[start:end]

    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if not st.session_state.submitted:
        for i, q in enumerate(batch, start=start+1):
            st.markdown(f"**{i}. {q['question']}**")
            st.radio("", q["options"], key=f"q_{i}")
            st.markdown("---")
        if st.button("✅ Nộp bài"):
            st.session_state.submitted = True
            st.rerun()
    else:
        score = 0
        for i, q in enumerate(batch, start=start+1):
            sel = st.session_state.get(f"q_{i}")
            if clean_text(sel) == clean_text(q["answer"]):
                st.success(f"{i}. ✅ {q['question']} — {q['answer']}")
                score += 1
            else:
                st.error(f"{i}. ❌ {q['question']} — Đúng: {q['answer']}")
        st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")
        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start+1,end+1):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.submitted = False
            st.rerun()

# TAB 2
with tab2:
    df = pd.DataFrame([
        {"STT": i+1,
         "Câu hỏi": q["question"],
         "Đáp án A": q["options"][0] if len(q["options"])>0 else "",
         "Đáp án B": q["options"][1] if len(q["options"])>1 else "",
         "Đáp án C": q["options"][2] if len(q["options"])>2 else "",
         "Đáp án D": q["options"][3] if len(q["options"])>3 else "",
         "Đáp án đúng": q["answer"]}
        for i,q in enumerate(questions)
    ])
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải CSV", csv, "ngan_hang.csv", "text/csv")
