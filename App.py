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
            # <-- FIX: so s, e with matches length, not len(p)
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
        # Bỏ dòng Ref hoặc các dòng tham chiếu
        if re.match(r'^\s*Ref', p, re.I):
            continue

        matches = list(opt_pat.finditer(p))
        if not matches:
            # Không có đáp án trong dòng => phần của câu hỏi
            if current["options"]:
                # Dòng mới => câu hỏi mới
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    current = {k: clean_text(v) if isinstance(v, str) else [clean_text(x) for x in v]
                               for k, v in current.items()}
                    questions.append(current)
                current = {"question": clean_text(p), "options": [], "answer": ""}
            else:
                current["question"] += " " + clean_text(p)
            continue

        # Dòng có đáp án
        first_match = matches[0]
        pre_text = p[:first_match.start()].strip()
        if pre_text:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    current = {k: clean_text(v) if isinstance(v, str) else [clean_text(x) for x in v]
                               for k, v in current.items()}
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

    # Đóng câu cuối
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        current = {k: clean_text(v) if isinstance(v, str) else [clean_text(x) for x in v]
                   for k, v in current.items()}
        questions.append(current)

    return questions


# ====================================================
# 🖥️ GIAO DIỆN STREAMLIT
# ====================================================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")

# === ĐỌC ẢNH NỀN ===
with open("IMG-a6d291ba3c85a15a6dd4201070bb76e5-V.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# === CSS NỀN VINTAGE + CĂN GIỮA TIÊU ĐỀ & ẨN PHẦN TRẮNG ===
# === CSS NỀN VINTAGE + CĂN GIỮA TIÊU ĐỀ & TỐI ƯU CHO MOBILE ===
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Crimson+Text&display=swap');

/* Ẩn phần trắng đầu trang và padding mặc định */
.block-container {{
    padding-top: 0rem !important;
    padding-bottom: 1rem !important;
}}

[data-testid="stHeader"], header {{
    display: none;
}}

[data-testid="stAppViewContainer"] {{
    background-image: url("data:image/jpeg;base64,{img_base64}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; inset: 0;
    background: rgba(250,245,235,0.83);
    backdrop-filter: blur(3px);
    z-index: 0;
}}

h1 {{
    text-align: center;
    font-family: 'Playfair Display', serif;
    font-size: 2.4em;
    color: #3d2d1b;
    text-shadow: 1px 1px 3px rgba(255,255,255,0.3);
    margin-top: 0.3em;
    position: relative;
    z-index: 1;
}}

label, .stSelectbox label, .stTextInput label {{
    font-family: 'Crimson Text', serif;
    font-size: 1.25em;
    color: #3b2f23;
}}

div[data-baseweb="select"], .stTextInput input {{
    font-size: 1.15em;
    color: #2e241a !important;
}}

.stMarkdown, .stRadio, .stDataFrame, .stText, .stTextInput, .stSelectbox {{
    color: #2e241a !important;
    font-family: 'Crimson Text', serif;
    font-size: 1.1em;
}}

.stRadio label p {{
    color: #2e241a !important;
}}

.stButton>button {{
    background-color: #bca37f !important;
    color: white !important;
    border-radius: 10px;
    font-size: 1.05em;
    font-family: 'Crimson Text', serif;
}}
.stButton>button:hover {{
    background-color: #a68963 !important;
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

if "Kỹ thuật" in bank_choice:
    questions = parse_cabbank(source)
else:
    questions = parse_lawbank(source)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào.")
    st.stop()


# ====================================================
# 🧭 TAB: LÀM BÀI / TRA CỨU
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu toàn bộ câu hỏi"])

with tab1:
    group_size = 10
    total = len(questions)
    groups = [f"Câu {i*group_size+1} - {min((i+1)*group_size, total)}" for i in range(math.ceil(total / group_size))]
    selected = st.selectbox("Chọn nhóm câu:", groups)
    idx = groups.index(selected)
    start, end = idx * group_size, min((idx + 1) * group_size, total)
    batch = questions[start:end]

    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if not st.session_state.submitted:
        for i, q in enumerate(batch, start=start + 1):
            st.markdown(f"**{i}. {q['question']}**")
            st.radio("", q["options"], key=f"q_{i}")
            st.markdown("---")
        if st.button("✅ Nộp bài"):
            st.session_state.submitted = True
            st.rerun()
    else:
        score = 0
        for i, q in enumerate(batch, start=start + 1):
            chosen = st.session_state.get(f"q_{i}")
            if clean_text(chosen) == clean_text(q["answer"]):
                st.success(f"{i}. ✅ {q['question']} — {q['answer']}")
                score += 1
            else:
                st.error(f"{i}. ❌ {q['question']} — Đáp án đúng: {q['answer']}")
        st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")

        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start + 1, end + 1):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.submitted = False
            st.rerun()

with tab2:
    st.markdown("### 🔎 Tra cứu toàn bộ câu hỏi trong ngân hàng")
    df = pd.DataFrame([
        {
            "STT": i + 1,
            "Câu hỏi": q["question"],
            "Đáp án A": q["options"][0] if len(q["options"]) > 0 else "",
            "Đáp án B": q["options"][1] if len(q["options"]) > 1 else "",
            "Đáp án C": q["options"][2] if len(q["options"]) > 2 else "",
            "Đáp án D": q["options"][3] if len(q["options"]) > 3 else "",
            "Đáp án đúng": q["answer"],
        } for i, q in enumerate(questions)
    ])

    keyword = st.text_input("🔍 Tìm theo từ khóa:").strip().lower()
    if keyword:
        df_filtered = df[df.apply(lambda r: keyword in " ".join(r.values.astype(str)).lower(), axis=1)]
    else:
        df_filtered = df

    st.write(f"Hiển thị {len(df_filtered)}/{len(df)} câu hỏi")
    st.dataframe(df_filtered, use_container_width=True)

    csv = df_filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải xuống danh sách (CSV)", csv, "ngan_hang_cau_hoi.csv", "text/csv")
