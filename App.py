# app.py
import streamlit as st
from docx import Document
import re
import math


# =====================================================
# 🧩 HÀM ĐỌC FILE LAW BANK (đánh số câu hỏi, *a là đúng)
# =====================================================
def parse_lawbank(source):
    try:
        doc = Document(source)
    except Exception as e:
        st.error(f"❌ Lỗi đọc file: {e}")
        return []

    # Lấy toàn bộ dòng text không rỗng
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # Bỏ các dòng "Ref:" hoặc "REF:"
    lines = [l for l in lines if not re.match(r"(?i)^ref[:\.]", l)]

    questions = []
    current_q = None
    current_opts = []

    def save_current():
        """Lưu lại câu hiện tại vào danh sách"""
        nonlocal current_q, current_opts
        if current_q and current_opts:
            correct = ""
            clean_opts = []
            for opt in current_opts:
                m = re.match(r"^\*?([a-dA-D])[\.\)]\s*(.*)", opt)
                if m:
                    text = f"{m.group(1).lower()}. {m.group(2).strip()}"
                    clean_opts.append(text)
                    if opt.strip().startswith("*"):
                        correct = text
            if not correct and clean_opts:
                correct = clean_opts[0]
            questions.append({
                "question": current_q.strip(),
                "options": clean_opts,
                "answer": correct
            })
        current_q = None
        current_opts = []

    for line in lines:
        # Nếu là dòng bắt đầu bằng số thứ tự => câu hỏi mới
        if re.match(r"^\d+\.", line):
            # Lưu câu trước (nếu có)
            save_current()
            # Bắt đầu câu mới
            current_q = re.sub(r"^\d+\.\s*", "", line).strip()
        # Nếu là dòng đáp án (a,b,c,d)
        elif re.match(r"^\*?[a-dA-D][\.\)]", line):
            current_opts.append(line)
        else:
            # Nối vào câu hỏi (phòng trường hợp câu hỏi dài nhiều dòng)
            if current_q:
                current_q += " " + line
            elif current_opts:
                # nếu đang ở trong options mà có dòng tiếp theo không phải a,b,c,d thì nối
                current_opts[-1] += " " + line

    # Lưu câu cuối
    save_current()

    return questions


# =====================================================
# 🧩 HÀM ĐỌC FILE CAB BANK (đã chạy ổn, giữ nguyên)
# =====================================================
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


# =====================================================
# 🧭 GIAO DIỆN STREAMLIT
# =====================================================
st.set_page_config(page_title="Ngân hàng câu hỏi", layout="wide")
st.title("📘 Ngân hàng trắc nghiệm")

bank_choice = st.selectbox("Chọn ngân hàng:", ["Ngân hàng Luật (Lawbank)", "Ngân hàng Kỹ thuật (Cabbank)"])

file_path = "lawbank.docx" if "Luật" in bank_choice else "cabbank.docx"

st.info(f"📂 Đang đọc file: {file_path}")

questions = parse_lawbank(file_path) if "Luật" in bank_choice else parse_cabbank(file_path)

if not questions:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại định dạng file hoặc ví dụ.")
    st.stop()

st.success(f"✅ Đọc được {len(questions)} câu hỏi.")

# Dò câu / Tra cứu
st.markdown("## 🔍 Tra cứu câu hỏi")
search = st.text_input("Nhập từ khóa tìm kiếm (vd: maintenance, VAECO...):").strip().lower()
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
