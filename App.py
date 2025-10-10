import streamlit as st
from docx import Document
import re
import math
import pandas as pd
import base64

# =======================
# HÀM TIỆN ÍCH
# =======================
def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip()) if s else ""

def read_docx_paragraphs(source):
    try:
        doc = Document(source)
        return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return []

# =======================
# PARSER CABBANK (GIỮ NGUYÊN)
# =======================
def parse_cabbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\s.)]+')

    for p in paras:
        matches = list(opt_pat.finditer(p))
        if not matches:
            if current["options"]:
                questions.append(current)
                current = {"question": p, "options": [], "answer": ""}
            else:
                current["question"] += " " + p
            continue

        qtext = p[:matches[0].start()].strip()
        if qtext:
            current["question"] = qtext

        for idx, m in enumerate(matches):
            s = m.end()
            e = matches[idx + 1].start() if idx + 1 < len(matches) else len(p)
            body = p[s:e].strip()
            letter = m.group("letter").lower()
            opt = f"{letter}. {body}"
            current["options"].append(opt)
            if m.group("star"):
                current["answer"] = opt

        if current["question"] and current["options"]:
            questions.append(current)
            current = {"question": "", "options": [], "answer": ""}

    return questions


# =======================
# PARSER LAWBANK (SỬA CHUẨN)
# =======================
def parse_lawbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []
    text = "\n".join(paras)
    text = re.sub(r'\bRef[:.].*?(?=(?:\n|$))', '', text, flags=re.I)

    blocks = re.split(r'\n(?=\d+\s*[.)])', text)
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\s.)]+')
    questions = []

    for b in blocks:
        b = b.strip()
        if not b:
            continue
        b = re.sub(r'^\d+\s*[.)]\s*', '', b)
        matches = list(opt_pat.finditer(b))
        if not matches:
            continue
        qtext = clean_text(b[:matches[0].start()])
        opts, ans = [], ""
        for i, m in enumerate(matches):
            s = m.end()
            e = matches[i + 1].start() if i + 1 < len(matches) else len(b)
            body = clean_text(b[s:e])
            letter = m.group("letter").lower()
            opt = f"{letter}. {body}"
            opts.append(opt)
            if m.group("star"):
                ans = opt
        if not ans and opts:
            ans = opts[0]
        if qtext and opts:
            questions.append({"question": qtext, "options": opts, "answer": ans})
    return questions


# =======================
# GIAO DIỆN
# =======================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")

# === Nạp ảnh nền dạng base64 ===
def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img_base64 = get_base64_image("IMG-a6d291ba3c85a15a6dd4201070bb76e5-V.jpg")

# === CSS ===
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Crimson+Text&display=swap');

[data-testid="stAppViewContainer"] {{
    background-image: url("data:image/jpeg;base64,{img_base64}");
    background-size: cover;
    background-attachment: fixed;
    background-position: center;
}}
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(250,245,235,0.85);
    backdrop-filter: blur(6px);
    z-index: 0;
}}
h1 {{
    text-align: center;
    font-family: 'Playfair Display', serif;
    font-size: 2.6em;
    color: #4b3f2f;
    text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
    margin-top: 0.5em;
    position: relative;
    z-index: 1;
}}
label, .stSelectbox label {{
    font-family: 'Crimson Text', serif;
    font-size: 1.3em;
    color: #3b2f23;
}}
div[data-baseweb="select"] {{
    font-size: 1.2em;
}}
.stButton>button {{
    background-color: #bca37f !important;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1.1em;
    font-family: 'Crimson Text', serif;
    transition: 0.2s ease-in-out;
}}
.stButton>button:hover {{
    background-color: #a68963 !important;
    transform: scale(1.03);
}}
</style>
""", unsafe_allow_html=True)

# === Tiêu đề ===
st.markdown("<h1>📜 Ngân hàng trắc nghiệm</h1>", unsafe_allow_html=True)

# === Chọn ngân hàng ===
bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])
source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"
questions = parse_cabbank(source) if "Kỹ thuật" in bank_choice else parse_lawbank(source)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra file .docx hoặc đường dẫn.")
    st.stop()

tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu toàn bộ câu hỏi"])

# === Tab 1 ===
with tab1:
    group_size = 10
    TOTAL = len(questions)
    num_groups = math.ceil(TOTAL / group_size)
    labels = [f"Câu {i*group_size+1}-{min((i+1)*group_size,TOTAL)}" for i in range(num_groups)]
    selected = st.selectbox("Chọn nhóm câu:", labels)
    start = labels.index(selected) * group_size
    end = min(start + group_size, TOTAL)
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
            selected = st.session_state.get(f"q_{i}")
            if clean_text(selected) == clean_text(q["answer"]):
                st.success(f"{i}. ✅ {q['question']} — {q['answer']}")
                score += 1
            else:
                st.error(f"{i}. ❌ {q['question']} — Đáp án đúng: {q['answer']}")
        st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")

        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start+1, end+1):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.submitted = False
            st.rerun()

# === Tab 2 ===
with tab2:
    st.markdown("### 🔎 Tra cứu toàn bộ câu hỏi")
    df = pd.DataFrame([
        {
            "STT": i+1,
            "Câu hỏi": q["question"],
            "Đáp án A": q["options"][0] if len(q["options"])>0 else "",
            "Đáp án B": q["options"][1] if len(q["options"])>1 else "",
            "Đáp án C": q["options"][2] if len(q["options"])>2 else "",
            "Đáp án D": q["options"][3] if len(q["options"])>3 else "",
            "Đáp án đúng": q["answer"]
        } for i,q in enumerate(questions)
    ])
    kw = st.text_input("Tìm theo từ khóa:").lower().strip()
    df2 = df[df.apply(lambda r: kw in " ".join(r.values.astype(str)).lower(), axis=1)] if kw else df
    st.write(f"Hiển thị {len(df2)}/{len(df)} câu hỏi")
    st.dataframe(df2, use_container_width=True)
    st.download_button("⬇️ Tải CSV", df2.to_csv(index=False).encode("utf-8-sig"), "ngan_hang.csv", "text/csv")
