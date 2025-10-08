import streamlit as st
import re
from docx import Document
import math

# =========================
# Cấu hình giao diện (canh giữa)
# =========================
st.set_page_config(page_title="Ngân hàng câu hỏi luật", page_icon="⚖️", layout="wide")
st.markdown("""
    <style>
    .main { display: flex; justify-content: center; }
    div.block-container { text-align: center; max-width: 900px; padding-top: 1rem; }
    .stRadio > label { font-weight: normal; }
    .stButton>button { width: 60%; margin: 10px auto; display: block; border-radius: 10px; font-size: 18px; padding: 0.6rem 1rem; }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ NGÂN HÀNG CÂU HỎI KIỂM TRA LUẬT (SOP)")

# =========================
# Hàm đọc file .docx (lọc chính xác, bỏ Ref.)
# =========================
def load_questions(docx_path):
    try:
        doc = Document(docx_path)
    except Exception as e:
        st.error(f"❌ Không thể đọc file Word: {e}")
        return [], [], []

    # Lấy paragraphs (loại bỏ dòng rỗng)
    paragraphs = [p.text.rstrip() for p in doc.paragraphs if p.text and p.text.strip()]

    questions = []
    problematic = []  # lưu các đoạn nghi ngờ
    current = {"question": "", "options": [], "answer": None}
    prev_non_option = None

    # Regex linh hoạt cho đáp án:
    # có thể có số thứ tự trước (ví dụ "29. a. ..."), có thể có '*', chữ hoa/thường,
    # nhận các dấu . ) - – :
    opt_re = re.compile(r'^\s*(?:\d+\.\s*)?([\*]?)\s*([a-zA-Z])\s*[\.\)\-–:]\s*(.*)$')

    for idx, line in enumerate(paragraphs):
        # Bỏ hoàn toàn dòng bắt đầu bằng Ref (Ref., Ref:, ref., v.v.)
        if re.match(r'^\s*Ref[:\.]\s*', line, re.IGNORECASE):
            # bỏ qua dòng Ref.
            continue

        # thử detect đáp án
        m = opt_re.match(line)
        if m:
            star = m.group(1) or ""
            letter = m.group(2)
            opt_text = m.group(3).strip()

            # nếu không có đoạn question hiện tại nhưng có prev_non_option -> dùng làm question
            if not current["question"] and prev_non_option:
                current["question"] = prev_non_option
                prev_non_option = None

            # nếu opt_text rỗng thì đánh dấu problematic
            if not opt_text:
                problematic.append((idx, line))
                continue

            current["options"].append(opt_text)
            if star:
                current["answer"] = opt_text

        else:
            # không phải dòng đáp án
            # nếu current đã có options => đây là khả năng bắt đầu câu mới
            if current["options"]:
                # chuẩn hóa: nếu chỉ có 1 option và chưa có answer thì set luôn
                if not current["answer"] and len(current["options"]) == 1:
                    current["answer"] = current["options"][0]

                # loại bỏ số thứ tự đứng đầu câu (nếu có) cho hiển thị gọn
                current["question"] = re.sub(r'^\s*\d+\.\s*', '', current["question"]).strip()

                # nếu hợp lệ thì lưu
                if current["question"] and current["options"]:
                    questions.append(current)
                else:
                    problematic.append(("incomplete", current))

                # bắt đầu câu mới từ dòng hiện tại
                current = {"question": line.strip(), "options": [], "answer": None}
                prev_non_option = line.strip()
            else:
                # chưa có options -> đang nối nội dung câu hỏi
                if current["question"]:
                    current["question"] += " " + line.strip()
                else:
                    current["question"] = line.strip()
                prev_non_option = line.strip()

    # sau vòng lặp: thêm câu cuối nếu hợp lệ
    if current["options"]:
        if not current["answer"] and len(current["options"]) == 1:
            current["answer"] = current["options"][0]
        current["question"] = re.sub(r'^\s*\d+\.\s*', '', current["question"]).strip()
        if current["question"] and current["options"]:
            questions.append(current)
        else:
            problematic.append(("end_incomplete", current))

    # Lọc final: chỉ giữ những câu có ít nhất 1 option
    final_questions = []
    for q in questions:
        # loại bỏ bất kỳ 'Ref.' còn sót trong question (dù đã cố loại)
        q_text = re.sub(r'\bRef[:\.].*$', '', q["question"], flags=re.IGNORECASE).strip()
        q["question"] = q_text
        if q["options"]:
            final_questions.append(q)
        else:
            problematic.append(("no_options", q))

    return final_questions, paragraphs, problematic


# =========================
# Tải dữ liệu
# =========================
questions, paragraphs, problematic = load_questions("bank.docx")
TOTAL = len(questions)

if TOTAL == 0:
    st.error("❌ Không đọc được câu hỏi nào. Kiểm tra lại file bank.docx hoặc gửi mình vài dòng đầu để mình điều chỉnh.")
    st.stop()

st.success(f"📘 Đã tải thành công {TOTAL} câu hỏi (Ref. đã bị loại bỏ).")

# Hiển thị debug (tùy chọn, giúp tìm 2 câu bị lạc)
with st.expander("🔎 Xem thông tin debug (đoạn không được nhận diện)"):
    st.write(f"Tổng paragraphs: {len(paragraphs)}")
    st.write(f"Số câu đọc được: {TOTAL}")
    st.write(f"Số đoạn nghi ngờ (problematic): {len(problematic)} — (nhiều khi là đoạn rỗng hoặc format lạ)")
    if problematic:
        st.markdown("**Một vài đoạn problem (index, nội dung):**")
        for item in problematic[:50]:
            st.write(item)

# =========================
# Chia nhóm 20 câu, giữ thứ tự gốc
# =========================
group_size = 20
num_groups = math.ceil(TOTAL / group_size)
group_labels = [f"Câu {i*group_size+1} - {min((i+1)*group_size, TOTAL)}" for i in range(num_groups)]

# khi đổi group -> reset trạng thái trả lời/nộp
if "last_group" not in st.session_state:
    st.session_state.last_group = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False

selected_group = st.selectbox("📋 Bạn muốn làm nhóm câu nào?", group_labels, index=0)

# Nếu đổi nhóm, clear mọi key q_... và reset submitted
if st.session_state.last_group != selected_group:
    for k in list(st.session_state.keys()):
        if k.startswith("q_"):
            del st.session_state[k]
    st.session_state.submitted = False
    st.session_state.last_group = selected_group

start_idx = group_labels.index(selected_group) * group_size
end_idx = min(start_idx + group_size, TOTAL)
batch = questions[start_idx:end_idx]

# =========================
# Hiển thị 20 câu cùng lúc (với placeholder "(Chưa chọn)")
# =========================
if not st.session_state.submitted:
    st.markdown(f"### 🧩 Nhóm {selected_group}")

    for i, q in enumerate(batch, start=start_idx + 1):
        st.markdown(f"**{i}. {q['question']}**")
        opts = ["(Chưa chọn)"] + q["options"]
        # radio với placeholder
        st.radio("", opts, index=0, key=f"q_{i}")
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("✅ Nộp bài và xem kết quả"):
        st.session_state.submitted = True
        st.rerun()

else:
    # Tính điểm và hiển thị kết quả
    score = 0
    for i, q in enumerate(batch, start=start_idx + 1):
        selected = st.session_state.get(f"q_{i}", "(Chưa chọn)")
        correct = q["answer"]
        if selected == "(Chưa chọn)":
            is_correct = False
        else:
            is_correct = selected == correct
        if is_correct:
            score += 1
            st.success(f"{i}. {q['question']}\n\n✅ Đúng ({correct})")
        else:
            st.error(f"{i}. {q['question']}\n\n❌ Sai. Đáp án đúng: **{correct}**")
        st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader(f"🎯 Kết quả: {score}/{len(batch)} câu đúng")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Làm lại nhóm này"):
            for i in range(start_idx + 1, end_idx + 1):
                key = f"q_{i}"
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.submitted = False
            st.rerun()
    with col2:
        if st.button("➡️ Sang nhóm khác"):
            for i in range(start_idx + 1, end_idx + 1):
                key = f"q_{i}"
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.submitted = False
            st.rerun()
