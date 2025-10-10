# app.py — bản fix đầy đủ cho cả LAWBank và CABBANK
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

def read_docx_paragraphs(source):
    """Đọc file Word và trả về danh sách đoạn text không rỗng."""
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Không thể đọc file .docx: {e}")
        return []
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return paras

# ====================================================
# 🧩 PARSER CABBANK (KỸ THUẬT)
# ====================================================
def parse_cabbank(source):
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

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
                    current["question"] = clean_text(current["question"])
                    current["options"] = [clean_text(o) for o in current["options"]]
                    current["answer"] = clean_text(current["answer"])
                    questions.append(current)
                current = {"question": clean_text(p), "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + p).strip() if current["question"] else clean_text(p)
            continue

        first_match = matches[0]
        pre_text = p[:first_match.start()].strip()
        if pre_text:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    current["question"] = clean_text(current["question"])
                    current["options"] = [clean_text(o) for o in current["options"]]
                    current["answer"] = clean_text(current["answer"])
                    questions.append(current)
                current = {"question": clean_text(pre_text), "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre_text).strip() if current["question"] else clean_text(pre_text)

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

    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        current["question"] = clean_text(current["question"])
        current["options"] = [clean_text(o) for o in current["options"]]
        current["answer"] = clean_text(current["answer"])
        questions.append(current)

    return questions

# ====================================================
# 🧩 PARSER LAWBANK (LUẬT)
# ====================================================
def parse_lawbank(source):
    """Đọc ngân hàng câu hỏi dạng đánh số 1., 2., 3... có dòng REF, xóa REF và xác định đáp án *a/*b/..."""
    paras = read_docx_paragraphs(source)
    if not paras:
        return []

    # Gộp các đoạn lại, thêm xuống dòng giữa các đoạn
    text = "\n".join(paras)

    # Chuẩn hóa: nếu thiếu xuống dòng giữa các câu hỏi (ví dụ "1.Who..." dính vào "2.What...")
    text = re.sub(r'(?<=\d)\.(?=\S)', '. ', text)

    # Tách thành từng block câu hỏi theo số thứ tự
    blocks = re.split(r'\n(?=\d+\.)', text)
    questions = []

    for block in blocks:
        block = block.strip()
        if not block or not re.match(r'^\d+\.', block):
            continue

        # Xoá dòng Ref... nếu có
        block = re.sub(r'(?i)Ref.*', '', block)

        # Tách dòng đầu làm câu hỏi
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        # Ghép các dòng lại nếu Word ngắt giữa câu hỏi / đáp án
        joined = " ".join(lines)
        # Tìm các đáp án a,b,c,d trong chuỗi
        opt_pat = re.compile(r'(?P<star>\*)?\s*(?P<letter>[A-Da-d])\s*(?:\.|\))\s*')
        matches = list(opt_pat.finditer(joined))
        if not matches:
            continue

        # Câu hỏi là phần trước đáp án đầu tiên
        q_text = clean_text(joined[:matches[0].start()])

        opts, answer = [], ""
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(joined)
            opt_body = clean_text(joined[start:end])
            letter = m.group("letter").lower()
            option_text = f"{letter}. {opt_body}"
            opts.append(option_text)
            if m.group("star"):
                answer = option_text

        if opts:
            if not answer:
                answer = opts[0]
            questions.append({"question": q_text, "options": opts, "answer": answer})

    return questions

# ====================================================
# 🖥️ GIAO DIỆN STREAMLIT
# ====================================================
st.set_page_config(page_title="Ngân hàng trắc nghiệm", layout="wide")
st.title("📚 Ngân hàng trắc nghiệm")

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Kỹ thuật", "Ngân hàng Luật"])
source = "cabbank.docx" if "Kỹ thuật" in bank_choice else "lawbank.docx"

# Đọc dữ liệu
if "Kỹ thuật" in bank_choice:
    questions = parse_cabbank(source)
else:
    questions = parse_lawbank(source)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra file .docx hoặc định dạng.")
    st.stop()

st.success(f"✅ Đã đọc được {len(questions)} câu hỏi từ {bank_choice}.")

# ====================================================
# 🧭 TAB CHỨC NĂNG
# ====================================================
tab1, tab2 = st.tabs(["🧠 Làm bài", "🔍 Tra cứu toàn bộ câu hỏi"])

# ====================================================
# TAB 1: LÀM BÀI
# ====================================================
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

# ====================================================
# TAB 2: TRA CỨU CÂU HỎI
# ====================================================
with tab2:
    st.markdown("### 🔎 Tra cứu toàn bộ câu hỏi")

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
    if keyword:
        df_filtered = df[df.apply(lambda row: keyword in " ".join(row.values.astype(str)).lower(), axis=1)]
    else:
        df_filtered = df

    st.write(f"Hiển thị {len(df_filtered)}/{len(df)} câu hỏi")
    st.dataframe(df_filtered, use_container_width=True)

    csv = df_filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải xuống danh sách (CSV)", csv, "ngan_hang_cau_hoi.csv", "text/csv")
