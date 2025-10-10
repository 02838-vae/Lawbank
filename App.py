import streamlit as st
from docx import Document
import re
import math
import pandas as pd

# ====================================================
# ⚙️ HÀM CHUNG
# ====================================================
def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()

def read_docx_paragraphs(source):
    """Đọc file Word và trả về danh sách đoạn text không rỗng."""
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file .docx: {e}")
        return []
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


# ====================================================
# 🧩 PARSER NGÂN HÀNG KỸ THUẬT (CABBANK) – giữ nguyên
# ====================================================
def parse_cabbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])\s*(?:\.|\))\s*')

    for p in paras:
        matches = list(opt_pat.finditer(p))
        if not matches:
            if current["options"]:
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
            start = m.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(p)
            opt = clean_text(p[start:end])
            letter = m.group("letter").lower()
            text = f"{letter}. {opt}"
            current["options"].append(text)
            if m.group("star"):
                current["answer"] = text

    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        current = {k: clean_text(v) if isinstance(v, str) else [clean_text(x) for x in v]
                   for k, v in current.items()}
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
    opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])[\.\)]\s*')

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
st.title("📚 Ngân hàng trắc nghiệm")

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])
source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"

# Đọc dữ liệu
questions = parse_cabbank(source) if "Kỹ thuật" in bank_choice else parse_lawbank(source)
if not questions:
    st.error("Không đọc được câu hỏi nào. Kiểm tra file .docx hoặc đường dẫn.")
    st.stop()

st.success(f"✅ Đã đọc được {len(questions)} câu hỏi từ {bank_choice}.")

# ====================================================
# 🧭 TAB CHỨC NĂNG
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu toàn bộ câu hỏi"])

# TAB 1: Làm bài
with tab1:
    group_size = 10
    TOTAL = len(questions)
    num_groups = math.ceil(TOTAL / group_size)
    group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

    selected_group = st.selectbox("Chọn nhóm câu:", group_labels)
    start = group_labels.index(selected_group) * group_size
    end = min(start + group_size, TOTAL)
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
            selected = st.session_state.get(f"q_{i}")
            if clean_text(selected) == clean_text(q["answer"]):
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

# TAB 2: Tra cứu
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
        }
        for i, q in enumerate(questions)
    ])

    keyword = st.text_input("🔍 Tìm theo từ khóa (câu hỏi hoặc đáp án):").strip().lower()
    df_filtered = df[df.apply(lambda r: keyword in " ".join(r.values.astype(str)).lower(), axis=1)] if keyword else df

    st.write(f"Hiển thị {len(df_filtered)}/{len(df)} câu hỏi")
    st.dataframe(df_filtered, use_container_width=True)

    csv = df_filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải danh sách (CSV)", csv, "ngan_hang_cau_hoi.csv", "text/csv")
