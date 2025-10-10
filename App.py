import streamlit as st
from docx import Document
import re
import math
import pandas as pd
import base64

# ====================================================
# ⚙️ HÀM CHUNG
# ====================================================
def clean_text(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r'\s+', ' ', s).strip()

def read_docx_paragraphs(source):
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file .docx: {e}")
        return []
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


# ====================================================
# 🧩 PARSER CABBANK (KỸ THUẬT)
# ====================================================
def parse_cabbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []
    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)]\s+')

    for p in paras:
        matches = list(opt_pat.finditer(p))
        if not matches:
            if current["options"]:
                questions.append(current)
                current = {"question": clean_text(p), "options": [], "answer": ""}
            else:
                current["question"] += " " + clean_text(p)
            continue
        pre = p[:matches[0].start()].strip()
        if pre:
            if current["options"]:
                questions.append(current)
                current = {"question": clean_text(pre), "options": [], "answer": ""}
            else:
                current["question"] = clean_text(pre)
        for i, m in enumerate(matches):
            s, e = m.end(), matches[i+1].start() if i+1 < len(matches) else len(p)
            opt = f"{m.group('letter').lower()}. {clean_text(p[s:e])}"
            current["options"].append(opt)
            if m.group("star"):
                current["answer"] = opt
    if current["question"] and current["options"]:
        questions.append(current)
    return questions


# ====================================================
# 🧩 PARSER LAWBANK (LUẬT)
# ====================================================
def parse_lawbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []
    text = "\n".join(paras)
    text = re.sub(r'\bRef[:.].*?(?=(?:\n|$))', '', text, flags=re.I)
    opt_pat = re.compile(r'(?<![A-Za-z0-9/])(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)]\s+')
    blocks = re.split(r'\n(?=\d+\s*[.)])', text)
    questions = []
    for b in blocks:
        b = re.sub(r'^\d+\s*[.)]\s*', '', b.strip())
        matches = list(opt_pat.finditer(b))
        if not matches:
            continue
        q_text = clean_text(b[:matches[0].start()])
        opts, ans = [], ""
        for i, m in enumerate(matches):
            s, e = m.end(), matches[i+1].start() if i+1 < len(matches) else len(b)
            body = re.sub(r'\n+', ' ', clean_text(b[s:e]))
            opt = f"{m.group('letter').lower()}. {body}"
            opts.append(opt)
            if m.group("star"):
                ans = opt
        if q_text and opts:
            if not ans:
                ans = opts[0]
            questions.append({"question": q_text, "options": opts, "answer": ans})
    return questions


# ====================================================
# 🖥️ GIAO DIỆN STREAMLIT
# ====================================================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")

# Nạp ảnh nền
with open("IMG-a6d291ba3c85a15a6dd4201070bb76e5-V.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# CSS phong cách vintage
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
    background: rgba(250,245,235,0.78);  /* tăng độ rõ */
    backdrop-filter: blur(2.5px);
    z-index: 0;
}}

h1 {{
    text-align: center;
    font-family: 'Playfair Display', serif;
    font-size: 2.7em;
    color: #4b3f2f;
    text-shadow: 1px 1px 3px rgba(0,0,0,0.25);
    margin-top: 0.3em;
    position: relative;
    z-index: 1;
}}

label, .stSelectbox label {{
    font-family: 'Crimson Text', serif;
    font-size: 1.3em;
    color: #3b2f23;
}}
div[data-baseweb="select"] {{
    font-size: 1.25em;
}}
.stButton>button {{
    background-color: #bca37f !important;
    color: white;
    border-radius: 10px;
    font-size: 1.1em;
    font-family: 'Crimson Text', serif;
}}
.stButton>button:hover {{
    background-color: #a68963 !important;
    transform: scale(1.03);
}}
.block-container {{
    background: rgba(255,255,250,0.9);
    border: 1px solid #d6c7a1;
    box-shadow: 0 0 15px rgba(90,70,40,0.2);
    border-radius: 15px;
    padding: 2rem;
    position: relative;
    z-index: 1;
}}
</style>
""", unsafe_allow_html=True)


# ====================================================
# 🏷️ TIÊU ĐỀ + CHỌN NGÂN HÀNG
# ====================================================
st.markdown("<h1>📜 Ngân hàng trắc nghiệm</h1>", unsafe_allow_html=True)
bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])
source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"
questions = parse_cabbank(source) if "Kỹ thuật" in bank_choice else parse_lawbank(source)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào.")
    st.stop()


# ====================================================
# 🧭 TAB LÀM BÀI / TRA CỨU
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu toàn bộ câu hỏi"])

with tab1:
    group_size = 10
    total = len(questions)
    groups = [f"Câu {i*group_size+1} - {min((i+1)*group_size, total)}" for i in range(math.ceil(total/group_size))]
    selected = st.selectbox("Chọn nhóm câu:", groups)
    idx = groups.index(selected)
    start, end = idx*group_size, min((idx+1)*group_size, total)
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
                st.error(f"{i}. ❌ {q['question']} — Đáp án đúng: {q['answer']}")
        st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")
        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start+1, end+1):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.submitted = False
            st.rerun()

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
        } for i, q in enumerate(questions)
    ])
    keyword = st.text_input("🔍 Tìm theo từ khóa:").strip().lower()
    if keyword:
        df_show = df[df.apply(lambda x: keyword in " ".join(x.values.astype(str)).lower(), axis=1)]
    else:
        df_show = df
    st.write(f"Hiển thị {len(df_show)}/{len(df)} câu hỏi")
    st.dataframe(df_show, use_container_width=True)
    st.download_button("⬇️ Tải CSV", df_show.to_csv(index=False).encode("utf-8-sig"), "ngan_hang_cau_hoi.csv", "text/csv")
