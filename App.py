import streamlit as st
from docx import Document
import re
import pandas as pd

# ====================================================
# ⚙️ HÀM CHUNG
# ====================================================
def clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def read_docx_paragraphs_with_numbering(source):
    """Đọc file .docx và thêm số nếu có numbering."""
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file {source}: {e}")
        return []
    paras = []
    counter = 1
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        if p.style.name.startswith("List") or p._element.xpath(".//w:numPr"):
            if not re.match(r"^\d+\.", text):
                text = f"{counter}. {text}"
                counter += 1
        paras.append(text)
    return paras

# ====================================================
# 🧩 PARSER CABBANK (chuẩn, đã ổn định)
# ====================================================
def parse_cabbank(source):
    doc = Document(source)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    questions = []
    current = {"question": "", "options": [], "answer": ""}

    opt_pat = re.compile(r'(?<![A-Za-z0-9/])(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)]\s+')

    for p in paras:
        matches = list(opt_pat.finditer(p))
        if not matches:
            if current["options"]:
                if current["question"]:
                    if not current["answer"] and current["options"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": p, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + p).strip() if current["question"] else p
            continue

        pre = p[:matches[0].start()].strip()
        if pre:
            if current["options"]:
                if not current["answer"] and current["options"]:
                    current["answer"] = current["options"][0]
                questions.append(current)
                current = {"question": pre, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre).strip() if current["question"] else pre

        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(p)
            opt_body = clean_text(p[start:end])
            opt_text = f"{m.group('letter').lower()}. {opt_body}"
            current["options"].append(opt_text)
            if m.group("star"):
                current["answer"] = opt_text

    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)
    return questions

# ====================================================
# 🧩 PARSER LAWBANK (đã sửa lỗi cắt sai “Form 6020”)
# ====================================================
def parse_lawbank(source):
    paras = read_docx_paragraphs_with_numbering(source)
    if not paras:
        return []

    text = "\n".join(paras)

    # Xóa Ref: (dù liền câu hay xuống dòng)
    text = re.sub(r'(?i)Ref[:.].*?(?=\n\d+\.|\Z)', '', text, flags=re.S)

    # Chia block theo số thứ tự
    blocks = re.split(r'(?=\n?\d+\.)', text)
    questions = []

    # Regex cực kỳ chặt chẽ:
    # - Không bắt trong A/C, C/S
    # - Cho phép * trước ký tự
    # - Không nuốt ký tự số ngay sau chấm
    opt_pat = re.compile(
        r'(?<![A-Za-z0-9/])(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)](?=\s)',
        flags=re.I
    )

    for block in blocks:
        block = clean_text(block)
        if not block or not re.match(r'^\d+\.', block):
            continue

        joined = " ".join(block.splitlines())
        matches = list(opt_pat.finditer(joined))
        if not matches:
            continue

        q_text = clean_text(joined[:matches[0].start()])
        opts, ans = [], ""

        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(joined)
            opt_body = clean_text(joined[start:end])
            opt_text = f"{m.group('letter').lower()}. {opt_body}"
            opts.append(opt_text)
            if m.group("star"):
                ans = opt_text
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

if "Kỹ thuật" in bank_choice:
    questions = parse_cabbank(source)
else:
    questions = parse_lawbank(source)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào, kiểm tra lại file .docx")
    st.stop()

st.success(f"✅ Đã đọc {len(questions)} câu hỏi từ {bank_choice}")

# ====================================================
# TAB
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu"])

with tab1:
    group_size = 10
    total = len(questions)
    groups = [f"Câu {i*group_size+1}-{min((i+1)*group_size, total)}" for i in range(math.ceil(total/group_size))]
    grp = st.selectbox("Chọn nhóm câu:", groups)
    idx = groups.index(grp)
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
            sel = st.session_state.get(f"q_{i}")
            if clean_text(sel) == clean_text(q["answer"]):
                st.success(f"{i}. ✅ {q['question']} — {q['answer']}")
                score += 1
            else:
                st.error(f"{i}. ❌ {q['question']} — Đúng: {q['answer']}")
        st.subheader(f"🎯 Kết quả: {score}/{len(batch)}")
        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start + 1, end + 1):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.submitted = False
            st.rerun()

with tab2:
    df = pd.DataFrame([
        {
            "STT": i + 1,
            "Câu hỏi": q["question"],
            **{f"Đáp án {chr(65+j)}": q["options"][j] if len(q["options"]) > j else "" for j in range(4)},
            "Đáp án đúng": q["answer"],
        }
        for i, q in enumerate(questions)
    ])
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải CSV", csv, "ngan_hang.csv", "text/csv")
