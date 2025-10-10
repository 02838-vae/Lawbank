import streamlit as st
from docx import Document
import re
import math

# ==========================
# 🧩 ĐỌC FILE LAW BANK
# ==========================
def parse_lawbank(source):
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return []

    # Lấy toàn bộ text (ghép các đoạn lại)
    full_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    # Bỏ dòng Ref
    full_text = re.sub(r"(?i)Ref[:].*?(?=\n\d+\.|$)", "", full_text)

    # Gom các đáp án a,b,c,d nếu dính liền nhau (a....b....c....)
    full_text = re.sub(r'(?<!\n)(?=[*]?[a-dA-D][\.\)])', '\n', full_text)

    # Cắt thành từng câu hỏi: bắt đầu bằng số thứ tự 1., 2., 3., ...
    blocks = re.split(r'\n(?=\d+\.)', full_text)
    questions = []

    for block in blocks:
        block = block.strip()
        if not block or not re.match(r"^\d+\.", block):
            continue

        # Tách phần số thứ tự ra
        q_text = re.sub(r"^\d+\.\s*", "", block)

        # Tách câu hỏi và phần đáp án (a,b,c,d)
        parts = re.split(r'\n(?=[*]?[a-dA-D][\.\)])', q_text)
        if len(parts) == 1:
            continue
        question = parts[0].strip()
        options_raw = parts[1:]

        options = []
        correct = ""
        for opt in options_raw:
            opt = opt.strip()
            m = re.match(r"^\*?([a-dA-D])[\.\)]\s*(.*)", opt)
            if not m:
                continue
            letter = m.group(1).lower()
            text = m.group(2).strip()
            opt_text = f"{letter}. {text}"
            options.append(opt_text)
            if opt.startswith("*"):
                correct = opt_text

        if not options:
            continue
        if not correct:
            correct = options[0]

        questions.append({
            "question": question,
            "options": options,
            "answer": correct
        })

    return questions


# ==========================
# 🧩 ĐỌC FILE CAB BANK (OK)
# ==========================
def parse_cabbank(source):
    doc = Document(source)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    questions = []
    current = {"question": "", "options": [], "answer": ""}
    opt_pat = re.compile(r'(?<!\S)(?P<star>\*)?(?P<letter>[A-Da-d])\s*(?:[.)])')

    for p in paras:
        text = p
        if re.match(r"(?i)^ref[:\.]", text):
            continue
        matches = list(opt_pat.finditer(text))
        if not matches:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": text, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + text).strip() if current["question"] else text
            continue
        pre = text[:matches[0].start()].strip()
        if pre:
            if current["options"]:
                if current["question"] and current["options"]:
                    if not current["answer"]:
                        current["answer"] = current["options"][0]
                    questions.append(current)
                current = {"question": pre, "options": [], "answer": ""}
            else:
                current["question"] = (current["question"] + " " + pre).strip() if current["question"] else pre
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(text)
            opt_body = text[start:end].strip()
            letter = m.group("letter").lower()
            opt_text = f"{letter}. {opt_body}"
            current["options"].append(opt_text)
            if m.group("star"):
                current["answer"] = opt_text
    if current["question"] and current["options"]:
        if not current["answer"]:
            current["answer"] = current["options"][0]
        questions.append(current)
    return questions


# ==========================
# 🧭 GIAO DIỆN STREAMLIT
# ==========================
st.set_page_config(page_title="Ngân hàng câu hỏi", layout="wide")
st.title("📘 Ngân hàng trắc nghiệm")

bank_choice = st.selectbox(
    "Chọn ngân hàng:",
    ["Ngân hàng Luật (Lawbank)", "Ngân hàng Kỹ thuật (Cabbank)"]
)

file_path = "lawbank.docx" if "Luật" in bank_choice else "cabbank.docx"
st.info(f"📂 Đang đọc file: {file_path}")

questions = parse_lawbank(file_path) if "Luật" in bank_choice else parse_cabbank(file_path)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại file Word và định dạng.")
    st.stop()

st.success(f"✅ Đọc được {len(questions)} câu hỏi từ {file_path}.")

# ==========================
# 🔍 TRA CỨU CÂU HỎI
# ==========================
st.markdown("## 🔍 Tra cứu câu hỏi")
search = st.text_input("Nhập từ khóa (vd: maintenance, VAECO...):").strip().lower()
limit = st.number_input("Giới hạn số câu hiển thị (0 = tất cả):", min_value=0, value=0)

count = 0
for idx, q in enumerate(questions, start=1):
    if search and search not in q["question"].lower() and not any(search in o.lower() for o in q["options"]):
        continue
    if limit and count >= limit:
        break
    st.markdown(f"### {idx}. {q['question']}")
    for o in q["options"]:
        mark = "✅" if o == q["answer"] else ""
        st.write(f"- {o} {mark}")
    st.markdown("---")
    count += 1

st.success(f"Hiển thị {count}/{len(questions)} câu hỏi.")
