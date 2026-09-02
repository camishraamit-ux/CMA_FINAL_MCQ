import io
import random
import pdfplumber
import pandas as pd
import streamlit as st
import urllib.parse
import plotly.graph_objects as go
from fpdf import FPDF

# ==============================================================================
# 1. STREAMLIT CONFIGURATION & CUSTOM MOBILE STYLING
# ==============================================================================
st.set_page_config(page_title="CMA FINAL MCQ Assessment Portal", layout="centered", page_icon="🎯")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 2rem !important;
        max-width: 720px !important;
    }

    /* ---------- Top Info Bar ---------- */
    .top-info-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        padding: 14px 20px;
        border-radius: 14px;
        margin-bottom: 14px;
        box-shadow: 0px 6px 16px rgba(30, 58, 138, 0.25);
    }
    .subject-badge {
        font-size: 17px;
        font-weight: 800;
        color: #ffffff;
    }
    .candidate-badge {
        font-size: 15px;
        font-weight: 600;
        color: #dbeafe;
    }

    /* ---------- Progress Ring Row ---------- */
    .progress-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 18px;
    }
    .progress-track {
        flex: 1;
        height: 14px;
        background: #e2e8f0;
        border-radius: 999px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        border-radius: 999px;
        transition: width 0.4s ease;
    }
    .progress-count {
        font-size: 16px;
        font-weight: 800;
        color: #1e3a8a;
        white-space: nowrap;
    }

    /* ---------- Question Card ---------- */
    .question-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 28px 24px;
        margin-bottom: 20px;
        border: 2px solid #1e3a8a;
        box-shadow: 0px 8px 20px rgba(30, 58, 138, 0.10);
    }
    .q-label {
        display: inline-block;
        background: #1e3a8a;
        color: #fff;
        font-size: 14px;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 999px;
        margin-bottom: 12px;
    }
    .question-text {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        line-height: 1.45 !important;
    }

    /* ---------- Option Cards (radio reskinned) ---------- */
    div[data-testid="stRadio"] { width: 100% !important; }
    div[data-testid="stRadio"] > div {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 14px !important;
    }
    div[data-testid="stRadio"] label {
        width: 100% !important;
        min-height: 70px !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        padding: 18px 22px !important;
        border-radius: 14px !important;
        background-color: #f8fafc !important;
        border: 2.5px solid #cbd5e1 !important;
        display: flex !important;
        align-items: center !important;
        cursor: pointer !important;
        box-sizing: border-box !important;
        transition: all 0.15s ease-in-out !important;
        box-shadow: 0px 3px 10px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stRadio"] label:hover {
        background-color: #eff6ff !important;
        border-color: #2563eb !important;
        color: #1e3a8a !important;
        transform: translateY(-2px);
        box-shadow: 0px 8px 16px rgba(37, 99, 235, 0.15) !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"],
    div[data-testid="stRadio"] label:has(input:checked) {
        background-color: #dbeafe !important;
        border-color: #1e3a8a !important;
        box-shadow: 0px 6px 14px rgba(30, 58, 138, 0.2) !important;
    }
    div[data-testid="stRadio"] input[type="radio"] {
        transform: scale(2) !important;
        margin-right: 20px !important;
        accent-color: #1e3a8a !important;
    }

    /* ---------- Nav Buttons ---------- */
    div.stButton > button {
        font-size: 22px !important;
        font-weight: 800 !important;
        padding: 18px 22px !important;
        height: 62px !important;
        border-radius: 14px !important;
        box-shadow: 0px 5px 12px rgba(0, 0, 0, 0.12) !important;
        transition: transform 0.1s ease !important;
    }
    div.stButton > button:active { transform: scale(0.97); }

    /* ---------- Review Cards ---------- */
    .review-card {
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        border-left: 8px solid #94a3b8;
        background: #f8fafc;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
    }
    .review-card.correct { border-left-color: #10b981; background: #ecfdf5; }
    .review-card.incorrect { border-left-color: #ef4444; background: #fef2f2; }
    .review-card.unanswered { border-left-color: #f59e0b; background: #fffbeb; }
    .review-q { font-size: 19px; font-weight: 800; color: #0f172a; margin-bottom: 10px; }
    .review-tag {
        display: inline-block;
        font-size: 13px;
        font-weight: 800;
        padding: 3px 10px;
        border-radius: 999px;
        color: #fff;
        margin-bottom: 8px;
    }
    .tag-correct { background: #10b981; }
    .tag-incorrect { background: #ef4444; }
    .tag-unanswered { background: #f59e0b; }
    .review-line { font-size: 16px; color: #334155; margin: 2px 0; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PDF EXTRACTION LOGIC
# ==============================================================================
@st.cache_data
def extract_mcqs_from_pdf(pdf_path):
    questions_dict = {}
    answers_dict = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                for row in table:
                    clean_row = [cell.replace('\n', ' ').strip() if cell else "" for cell in row]

                    if len(clean_row) < 3 or not clean_row[0].isdigit():
                        continue

                    q_num = int(clean_row[0])

                    if len(clean_row) >= 6:
                        questions_dict[q_num] = {
                            "id": q_num,
                            "question": clean_row[1],
                            "options": [clean_row[2], clean_row[3], clean_row[4], clean_row[5]]
                        }
                    elif len(clean_row) == 3:
                        answers_dict[q_num] = clean_row[2]

    mcq_list = []
    for q_num, q_data in questions_dict.items():
        ans_text = answers_dict.get(q_num, "").strip()

        if not ans_text:
            continue

        correct_index = None
        for idx, opt in enumerate(q_data["options"]):
            if opt and (opt.strip().lower() == ans_text.lower() or opt.strip().lower() in ans_text.lower()):
                correct_index = idx
                break

        mcq_list.append({
            "id": q_data["id"],
            "question": q_data["question"],
            "options": q_data["options"],
            "correct_answer_text": ans_text,
            "correct_index": correct_index
        })

    return pd.DataFrame(mcq_list)

# ==============================================================================
# 3. PDF SCORECARD GENERATOR
# ==============================================================================
class ScorecardPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 58, 138)
        self.cell(0, 10, "CMA FINAL MCQ ASSESSMENT REPORT CARD", ln=True, align="C")
        self.ln(2)

def generate_pdf_scorecard(candidate_name, subject_name, score, total_questions, percentage, detailed_report):
    pdf = ScorecardPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(243, 244, 246)
    pdf.set_draw_color(209, 213, 219)

    meta_info = [
        ("Candidate Name:", candidate_name),
        ("Subject:", subject_name),
        ("Final Score:", f"{score} / {total_questions}"),
        ("Percentage:", f"{percentage}%")
    ]

    for label, val in meta_info:
        pdf.cell(45, 7, f"  {label}", border=1, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(135, 7, f"  {val}", border=1, ln=True)
        pdf.set_font("Helvetica", "B", 10)

    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, "Detailed Assessment Breakdown", ln=True)
    pdf.set_draw_color(30, 58, 138)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    for item in detailed_report:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, f"{item['q_num']}. {item['question']}")
        pdf.ln(1)

        pdf.set_font("Helvetica", "", 9)
        if item["status_type"] == "correct":
            pdf.set_text_color(16, 185, 129)
            pdf.cell(0, 5, f"   Marked Answer : {item['user_answer']} (Correct - 1 Mark)", ln=True)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 5, f"   Correct Answer: {item['correct_answer']}", ln=True)
        elif item["status_type"] == "incorrect":
            pdf.set_text_color(239, 68, 68)
            pdf.cell(0, 5, f"   Marked Answer : {item['user_answer']} (Incorrect - 0 Marks)", ln=True)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 5, f"   Correct Answer: {item['correct_answer']}", ln=True)
        else:
            pdf.set_text_color(217, 119, 6)
            pdf.cell(0, 5, f"   Marked Answer : Unanswered (0 Marks)", ln=True)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 5, f"   Correct Answer: {item['correct_answer']}", ln=True)

        pdf.ln(3)

    return bytes(pdf.output())

# ==============================================================================
# 4. APP STATE INITIALIZATION
# ==============================================================================
SUBJECT_FILES = {
    "Corporate and Economic Laws": "13. CORPORATE AND ECONOMIC LAWS.pdf",
    "Strategic Financial Management": "14. STRATEGIC FINANCIAL MANAGEMENT.pdf",
    "Direct Tax Laws and International Taxation": "15. DIRECT TAX LAWS AND INTERNATIONAL TAXATION.pdf",
    "Strategic Cost Management": "16. STRATEGIC COST MANAGEMENT.pdf",
    "Cost and Management Audit": "17. COST AND MANAGEMENT AUDIT.pdf",
    "Corporate Financial Reporting": "18. CORPORATE FINANCIAL REPORTING.pdf",
    "Strategic Performance Management & Business Valuation": "20A. STRATEGIC PERFORMANCE MANAGEMENT & BUSINESS VALUATION.pdf"
}

for key, default in [
    ("test_started", False),
    ("candidate_name", ""),
    ("selected_subject", list(SUBJECT_FILES.keys())[0]),
    ("assessment_df", None),
    ("user_answers", {}),
    ("submitted", False),
    ("current_q_index", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==============================================================================
# 5. REGISTRATION SCREEN
# ==============================================================================
if not st.session_state.test_started:
    st.markdown('<h1 style="color:#1e3a8a; font-size:30px; font-weight:900;">🎯 CMA FINAL MCQ Assessment Portal</h1>', unsafe_allow_html=True)
    st.write("Configure your assessment settings below to get started.")

    with st.form("setup_form"):
        name_input = st.text_input("Enter Your Full Name:", value=st.session_state.candidate_name)
        subject_choice = st.selectbox("Select Subject:", options=list(SUBJECT_FILES.keys()))

        q_count = st.selectbox(
            "Select Number of Questions:",
            options=[10, 20, 25, 30, 50],
            index=2
        )

        start_btn = st.form_submit_button("Start Assessment 🚀", type="primary", use_container_width=True)

        if start_btn:
            if not name_input.strip():
                st.error("Please enter your name to proceed.")
            else:
                st.session_state.candidate_name = name_input.strip()
                st.session_state.selected_subject = subject_choice

                pdf_filename = SUBJECT_FILES[subject_choice]
                try:
                    df_all = extract_mcqs_from_pdf(pdf_filename)
                    total_available = len(df_all)

                    if total_available == 0:
                        st.error("No valid questions with available answers were found in this PDF.")
                    else:
                        num_to_sample = min(q_count, total_available)
                        if num_to_sample < q_count:
                            st.warning(f"Note: Only {total_available} questions available in this subject.")

                        st.session_state.assessment_df = df_all.sample(n=num_to_sample).reset_index(drop=True)
                        st.session_state.user_answers = {}
                        st.session_state.submitted = False
                        st.session_state.current_q_index = 0
                        st.session_state.test_started = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not load '{pdf_filename}'. Ensure file is uploaded. Error: {e}")

# ==============================================================================
# 6. MCQ QUESTION DISPLAY SCREEN
# ==============================================================================
else:
    df_test = st.session_state.assessment_df
    total_q = len(df_test)

    if not st.session_state.submitted:
        curr_idx = st.session_state.current_q_index
        row = df_test.iloc[curr_idx]

        # Top Info Bar
        st.markdown(
            f'''
            <div class="top-info-bar">
                <span class="subject-badge">📚 {st.session_state.selected_subject}</span>
                <span class="candidate-badge">👤 {st.session_state.candidate_name}</span>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # Custom Progress Bar with count
        pct = int(((curr_idx + 1) / total_q) * 100)
        st.markdown(
            f'''
            <div class="progress-wrap">
                <div class="progress-track">
                    <div class="progress-fill" style="width:{pct}%;"></div>
                </div>
                <div class="progress-count">{curr_idx + 1}/{total_q}</div>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # Question Card
        st.markdown(
            f'''
            <div class="question-card">
                <span class="q-label">QUESTION {curr_idx + 1}</span>
                <div class="question-text">{row["question"]}</div>
            </div>
            ''',
            unsafe_allow_html=True
        )

        valid_options = [opt for opt in row["options"] if opt]
        saved_choice = st.session_state.user_answers.get(curr_idx, None)

        choice = st.radio(
            label="Select your answer:",
            options=range(len(valid_options)),
            format_func=lambda x: f"{chr(65 + x)}   {valid_options[x]}",
            key=f"q_radio_{curr_idx}",
            index=saved_choice,
            label_visibility="collapsed",
        )

        if choice is not None:
            st.session_state.user_answers[curr_idx] = choice

        st.write("")

        col_prev, col_next = st.columns([1, 1])
        with col_prev:
            if curr_idx > 0:
                if st.button("⬅️ Previous", use_container_width=True):
                    st.session_state.current_q_index -= 1
                    st.rerun()
            else:
                st.button("⬅️ Previous", disabled=True, use_container_width=True)

        with col_next:
            if curr_idx == total_q - 1:
                if st.button("✅ Submit", type="primary", use_container_width=True):
                    st.session_state.submitted = True
                    st.rerun()
            else:
                if st.button("Next ➡️", type="primary", use_container_width=True):
                    st.session_state.current_q_index += 1
                    st.rerun()

    # ==========================================================================
    # 7. SCORECARD & REVIEW SCREEN
    # ==========================================================================
    else:
        st.markdown(f'<h2 style="color:#1e3a8a; font-weight:900;">CMA Final - {st.session_state.selected_subject}</h2>', unsafe_allow_html=True)
        st.markdown(f"**Candidate Name:** {st.session_state.candidate_name}")
        st.divider()

        score = 0
        total_questions = len(df_test)
        detailed_report = []

        for display_num, row in df_test.iterrows():
            sn = display_num + 1
            user_choice = st.session_state.user_answers.get(display_num)
            correct_idx = row["correct_index"]
            correct_ans_text = row["correct_answer_text"]
            valid_options = [opt for opt in row["options"] if opt]

            is_correct = False
            user_ans_str = ""
            if user_choice is not None:
                selected_opt_text = valid_options[user_choice]
                user_ans_str = f"{chr(65 + user_choice)}. {selected_opt_text}"
                is_correct = (user_choice == correct_idx) or (selected_opt_text.strip().lower() == correct_ans_text.strip().lower())

            status_type = "unanswered"
            if is_correct:
                score += 1
                status_type = "correct"
            elif user_choice is not None:
                status_type = "incorrect"

            detailed_report.append({
                "q_num": f"Q{sn}",
                "question": row["question"],
                "user_answer": user_ans_str,
                "correct_answer": correct_ans_text,
                "status_type": status_type
            })

        percentage = round((score / total_questions) * 100, 2)
        incorrect_count = sum(1 for i in detailed_report if i["status_type"] == "incorrect")
        unanswered_count = sum(1 for i in detailed_report if i["status_type"] == "unanswered")

        st.subheader("📊 Final Assessment Scorecard")
        col1, col2 = st.columns(2)
        col1.metric(label="Total Score", value=f"{score} / {total_questions}")
        col2.metric(label="Percentage", value=f"{percentage}%")

        # Interactive donut chart
        fig = go.Figure(data=[go.Pie(
            labels=["Correct", "Incorrect", "Unanswered"],
            values=[score, incorrect_count, unanswered_count],
            hole=0.6,
            marker=dict(colors=["#10b981", "#ef4444", "#f59e0b"]),
            textinfo="label+value",
            textfont=dict(size=16, color="#ffffff", family="Inter"),
        )])
        fig.update_layout(
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            annotations=[dict(text=f"{percentage}%", x=0.5, y=0.5, font_size=26, font_family="Inter", font_color="#1e3a8a", showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True)
        st.divider()

        st.subheader("📲 Export & Share Results")

        share_text = (
            f"🎓 *CMA FINAL MCQ Assessment Results*\n"
            f"👤 *Candidate:* {st.session_state.candidate_name}\n"
            f"📚 *Subject:* {st.session_state.selected_subject}\n"
            f"🏆 *Score:* {score}/{total_questions} ({percentage}%)\n"
            f"✨ Completed via CMA FINAL MCQ App!"
        )
        whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_text)}"

        st.markdown(
            f'<a href="{whatsapp_url}" target="_blank" style="text-decoration:none;">'
            f'<button style="background-color:#25D366;color:white;border:none;padding:18px 24px;'
            f'border-radius:12px;font-size:22px;font-weight:800;cursor:pointer;width:100%;'
            f'box-shadow:0px 5px 12px rgba(0,0,0,0.12);">'
            f'📲 Share Score on WhatsApp</button></a>',
            unsafe_allow_html=True
        )
        st.write("")

        pdf_data = generate_pdf_scorecard(
            candidate_name=st.session_state.candidate_name,
            subject_name=st.session_state.selected_subject,
            score=score,
            total_questions=total_questions,
            percentage=percentage,
            detailed_report=detailed_report
        )

        st.download_button(
            label="📄 Download Official PDF Scorecard",
            data=pdf_data,
            file_name=f"{st.session_state.candidate_name}_CMA_Scorecard.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        st.divider()
        st.subheader("📝 Question Breakdown & Review")

        tag_map = {
            "correct": ("tag-correct", "✅ CORRECT · 1 MARK"),
            "incorrect": ("tag-incorrect", "❌ INCORRECT · 0 MARKS"),
            "unanswered": ("tag-unanswered", "⚠️ UNANSWERED · 0 MARKS"),
        }

        for item in detailed_report:
            tag_class, tag_label = tag_map[item["status_type"]]
            user_line = item["user_answer"] if item["user_answer"] else "Not attempted"
            st.markdown(
                f'''
                <div class="review-card {item["status_type"]}">
                    <span class="review-tag {tag_class}">{tag_label}</span>
                    <div class="review-q">{item["q_num"]}. {item["question"]}</div>
                    <div class="review-line">🖊️ <b>Your answer:</b> {user_line}</div>
                    <div class="review-line">✔️ <b>Correct answer:</b> {item["correct_answer"]}</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        if st.button("🔄 Take Another Test", use_container_width=True):
            st.session_state.test_started = False
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.session_state.current_q_index = 0
            st.rerun()
