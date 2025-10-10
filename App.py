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
# 🧩 PARSER NGÂN HÀNG KỸ THUẬT (CABBANK)
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

        pre_text = p[:matches[0].start()].strip()
        if pre_text:
            if current["options"]:
                questions.append(current)
                current = {"question": clean_text(pre_text), "options": [], "answer": ""}
            else:
                current["question"] = clean_text(pre_text)

        for i, m in enumerate(matches):
            s, e = m.end(), matches[i + 1].start() if i + 1 < len(matches) else len(p)
            opt_body = clean_text(p[s:e])
            opt = f"{m.group('letter').lower()}. {opt_body}"
            current["options"].append(opt)
            if m.group("star"):
                current["answer"] = opt

    if current["question"] and current["options"]:
        questions.append(current)

    return questions


# ====================================================
# 🧩 PARSER NGÂN HÀNG LUẬT (LAWBANK)
# ====================================================
def parse_lawbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?<![A-Za-z0-9/])(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)]\s+')

    for p in paras:
        if re.match(r'^\s*Ref', p, re.I):
            continue

        matches = list(opt_pat.finditer(p))
        if not matches:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": clean_text(p), "options": [], "answer": ""}
            else:
                current["question"] += " " + clean_text(p)
            continue

        first_match = matches[0]
        pre_text = p[:first_match.start()].strip()
        if pre_text:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": clean_text(pre_text), "options": [], "answer": ""}
            else:
                current["question"] += " " + clean_text(pre_text)

        for i, m in enumerate(matches):
            s = m.end()
            e = matches[i+1].start() if i+1 < len(matches) else len(p)
            opt_body = clean_text(p[s:e])
            letter = m.group("letter").lower()
            option = f"{letter}. {opt_body}"
            current["options"].append(option)
            if m.group("star"):
                current["answer"] = option

    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)

    return questions


# ====================================================
# 🖥️ GIAO DIỆN STREAMLIT
# ====================================================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")

# === ẢNH NỀN ===
with open("IMG-a6d291ba3c85a15a6dd4201070bb76e5-V.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# === CSS: rõ nét, dễ nhìn trên mobile ===
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Crimson+Text&display=swap');

[data-testid="stAppViewContainer"] {{
    background-image: url("data:image/jpeg;base64,{img_base64}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; inset: 0;
    background: rgba(255,248,235,0.85);
    backdrop-filter: blur(3px);
    z-index: 0;
}}
h1 {{
    text-align: center;
    font-family: 'Playfair Display', serif;
    font-size: 2.5em;
    color: #2a1f0f;
    margin-top: 0.2em;
    z-index: 1;
}}
/* Tăng độ tương phản câu hỏi và đáp án */
.stRadio label {{
    color: #1a1a1a !important;
    font-size: 1.1em !important;
    font-weight: 500;
}}
div[data-testid="stMarkdownContainer"] p {{
    color: #1a1a1a !important;
}}
.stSelectbox label {{
    font-size: 1.2em;
    color: #2a1f0f;
}}
.stButton>button {{
    background-color: #b0854c !important;
    color: white !important;
    border-radius: 10px;
    font-size: 1.05em;
    font-family: 'Crimson Text', serif;
}}
.stButton>button:hover {{
    background-color: #8a693c !important;
    transform: scale(1.03);
}}
</style>
""", unsafe_allow_html=True)


# ====================================================
# 🏷️ GIAO DIỆN CHÍNH
# ====================================================
st.markdown("<h1>📜 Ngân hàng trắc nghiệm</h1>", unsafe_allow_html=True)

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])
source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"

questions = parse_cabbank(source) if "Kỹ thuật" in bank_choice else parse_lawbank(source)
if not questions:
    st.error("❌ Không đọc được câu hỏi nào.")
    st.stop()


# ====================================================
# 🧭 TAB: LÀM BÀI / TRA CỨU
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu toàn bộ câu hỏi"])

# ========== TAB 1 ==========
with tab1:
    group_size = 10
    total = len(questions)
    groups = [f"Câu {i*group_size+1}-{min((i+1)*group_size, total)}" for i in range(math.ceil(total/group_size))]
    selected = st.selectbox("Chọn nhóm câu:", groups)
    idx = groups.index(selected)
    start, end = idx * group_size, min((idx+1) * group_size, total)
    batch = questions[start:end]

    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if not st.session_state.submitted:
        for i, q in enumerate(batch, start=start+1):
            st.markdown(f"<p style='color:#1a1a1a; font-size:1.15em; font-weight:600;'>{i}. {q['question']}</p>", unsafe_allow_html=True)
            st.radio("", q["options"], key=f"q_{i}")
            st.markdown("---")
        if st.button("✅ Nộp bài"):
            st.session_state.submitted = True
            st.rerun()
    else:
        score = 0
        for i, q in enumerate(batch, start=start+1):
            selected = st.session_state.get(f"q_{i}")
            correct = clean_text(q["answer"])
            is_correct = clean_text(selected) == correct

            st.markdown(f"<p style='color:#1a1a1a; font-size:1.15em; font-weight:600;'>{i}. {q['question']}</p>", unsafe_allow_html=True)

            for opt in q["options"]:
                opt_clean = clean_text(opt)
                if opt_clean == correct:
                    style = "color:#006400; font-weight:700;"
                elif opt_clean == clean_text(selected):
                    style = "color:#cc0000; font-weight:700; text-decoration: underline;"
                else:
                    style = "color:#1a1a1a;"
                st.markdown(f"<div style='{style}'>{opt}</div>", unsafe_allow_html=True)

            if is_correct:
                st.success(f"✅ Đúng — {q['answer']}")
                score += 1
            else:
                st.error(f"❌ Sai — Đáp án đúng: {q['answer']}")
            st.markdown("---")

        st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")

        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start+1, end+1):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.submitted = False
            st.rerun()


# ========== TAB 2 ==========
with tab2:
    st.markdown("### 🔎 Tra cứu toàn bộ câu hỏi trong ngân hàng")
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
    df_filtered = df[df.apply(lambda r: keyword in " ".join(r.values.astype(str)).lower(), axis=1)] if keyword else df

    st.write(f"Hiển thị {len(df_filtered)}/{len(df)} câu hỏi")
    st.dataframe(df_filtered, use_container_width=True)

    csv = df_filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải danh sách (CSV)", csv, "ngan_hang_cau_hoi.csv", "text/csv")
