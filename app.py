import io
import random
import pdfplumber
import pandas as pd
import streamlit as st
import urllib.parse
from fpdf import FPDF

# ==============================================================================
# 1. PDF EXTRACTION LOGIC (FILTER OUT UNANSWERED QUESTIONS)
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
        
        # EXCLUDE: If the source PDF has no answer for this question, skip it
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
# 2. PDF SCORECARD GENERATOR WITH COMPLETE QUESTION & ANSWER DETAILS (FPDF2)
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

    # Candidate Summary Block
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

    # Detailed Review Header
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, "Detailed Assessment Breakdown", ln=True)
    pdf.set_draw_color(30, 58, 138)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # Question Breakdown inside PDF
    for item in detailed_report:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 0, 0)
        
        # Question Statement
        pdf.multi_cell(0, 5, f"{item['q_num']}. {item['question']}")
        pdf.ln(1)
        
        # Marked & Correct Answer Details
        pdf.set_font("Helvetica", "", 9)
        if item["status_type"] == "correct":
            pdf.set_text_color(16, 185, 129)  # Green
            pdf.cell(0, 5, f"   Marked Answer : {item['user_answer']} (Correct - 1 Mark)", ln=True)
            pdf.set_text_color(30, 58, 138)  # Blue
            pdf.cell(0, 5, f"   Correct Answer: {item['correct_answer']}", ln=True)
        elif item["status_type"] == "incorrect":
            pdf.set_text_color(239, 68, 68)   # Red
            pdf.cell(0, 5, f"   Marked Answer : {item['user_answer']} (Incorrect - 0 Marks)", ln=True)
            pdf.set_text_color(30, 58, 138)  # Blue
            pdf.cell(0, 5, f"   Correct Answer: {item['correct_answer']}", ln=True)
        else:
            pdf.set_text_color(217, 119, 6)   # Amber
            pdf.cell(0, 5, f"   Marked Answer : Unanswered (0 Marks)", ln=True)
            pdf.set_text_color(30, 58, 138)  # Blue
            pdf.cell(0, 5, f"   Correct Answer: {item['correct_answer']}", ln=True)
            
        pdf.ln(3)

    return bytes(pdf.output())

# ==============================================================================
# 3. STREAMLIT CONFIGURATION & SETUP
# ==============================================================================
st.set_page_config(page_title="CMA FINAL MCQ Assessment Portal", layout="centered")

SUBJECT_FILES = {
    "Corporate and Economic Laws": "13. CORPORATE AND ECONOMIC LAWS.pdf",
    "Strategic Financial Management": "14. STRATEGIC FINANCIAL MANAGEMENT.pdf",
    "Direct Tax Laws and International Taxation": "15. DIRECT TAX LAWS AND INTERNATIONAL TAXATION.pdf",
    "Strategic Cost Management": "16. STRATEGIC COST MANAGEMENT.pdf",
    "Cost and Management Audit": "17. COST AND MANAGEMENT AUDIT.pdf",
    "Corporate Financial Reporting": "18. CORPORATE FINANCIAL REPORTING.pdf",
    "Strategic Performance Management & Business Valuation": "20A. STRATEGIC PERFORMANCE MANAGEMENT & BUSINESS VALUATION.pdf"
}

if "test_started" not in st.session_state:
    st.session_state.test_started = False
if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = ""
if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = list(SUBJECT_FILES.keys())[0]
if "assessment_df" not in st.session_state:
    st.session_state.assessment_df = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0

# ==============================================================================
# 4. REGISTRATION & CONFIGURATION SCREEN
# ==============================================================================
if not st.session_state.test_started:
    st.title("🎯 CMA FINAL MCQ Assessment Portal")
    st.write("Configure your assessment settings below to get started.")
    
    with st.form("setup_form"):
        name_input = st.text_input("Enter Your Full Name:", value=st.session_state.candidate_name)
        subject_choice = st.selectbox("Select Subject:", options=list(SUBJECT_FILES.keys()))
        
        q_count = st.selectbox(
            "Select Number of Questions:",
            options=[10, 20, 25, 30, 50],
            index=2
        )
        
        start_btn = st.form_submit_button("Start Assessment", type="primary")
        
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
                            st.warning(f"Note: Only {total_available} questions with valid answers were available in this subject. All available questions will be loaded.")
                        
                        st.session_state.assessment_df = df_all.sample(n=num_to_sample).reset_index(drop=True)
                        st.session_state.user_answers = {}
                        st.session_state.submitted = False
                        st.session_state.current_q_index = 0
                        st.session_state.test_started = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not load '{pdf_filename}'. Ensure this file is uploaded to GitHub. Error: {e}")

# ==============================================================================
# 5. ASSESSMENT SCREEN (ONE QUESTION AT A TIME)
# ==============================================================================
else:
    st.title(f"CMA Final - {st.session_state.selected_subject}")
    st.markdown(f"**Candidate Name:** {st.session_state.candidate_name}")
    st.divider()

    df_test = st.session_state.assessment_df
    total_q = len(df_test)

    if not st.session_state.submitted:
        curr_idx = st.session_state.current_q_index
        row = df_test.iloc[curr_idx]
        
        # Progress indicator
        st.progress((curr_idx + 1) / total_q)
        st.caption(f"Question {curr_idx + 1} of {total_q}")
        
        st.markdown(f"### Q{curr_idx + 1}. {row['question']}")
        
        valid_options = [opt for opt in row["options"] if opt]
        
        # Pre-select previously chosen answer if exists
        saved_choice = st.session_state.user_answers.get(curr_idx, None)
        
        choice = st.radio(
            label="Select your answer:",
            options=range(len(valid_options)),
            format_func=lambda x: f"{chr(65+x)}. {valid_options[x]}",
            key=f"q_radio_{curr_idx}",
            index=saved_choice
        )
        
        if choice is not None:
            st.session_state.user_answers[curr_idx] = choice

        st.divider()
        
        # Navigation Buttons
        col_prev, col_next, col_sub = st.columns([1, 1, 1])
        
        with col_prev:
            if curr_idx > 0:
                if st.button("⬅️ Previous"):
                    st.session_state.current_q_index -= 1
                    st.rerun()
                    
        with col_next:
            if curr_idx < total_q - 1:
                if st.button("Next ➡️", type="primary"):
                    st.session_state.current_q_index += 1
                    st.rerun()
                    
        with col_sub:
            if st.button("✅ Submit Assessment", type="primary" if curr_idx == total_q - 1 else "secondary"):
                st.session_state.submitted = True
                st.rerun()

    # ==========================================================================
    # 6. SCORECARD & PDF DOWNLOAD
    # ==========================================================================
    else:
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
                user_ans_str = f"{chr(65+user_choice)}. {selected_opt_text}"
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

        st.subheader("📊 Final Assessment Scorecard")
        col1, col2 = st.columns(2)
        col1.metric(label="Total Score", value=f"{score} / {total_questions}")
        col2.metric(label="Percentage", value=f"{percentage}%")
        st.divider()

        st.subheader("📲 Export & Share Results")
        
        # WhatsApp Share Link
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
            f'<button style="background-color:#25D366;color:white;border:none;padding:10px 20px;'
            f'border-radius:5px;font-size:16px;font-weight:bold;cursor:pointer;">'
            f'📲 Share Score on WhatsApp</button></a>',
            unsafe_allow_html=True
        )
        st.write("")

        # PDF Scorecard Download Button
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
            mime="application/pdf"
        )

        st.divider()
        st.subheader("📝 Question Breakdown & Review")
        
        for item in detailed_report:
            st.markdown(f"**{item['q_num']}: {item['question']}**")
            
            if item["status_type"] == "correct":
                st.success(f"Your Marked Answer: {item['user_answer']} (Correct - 1 Mark)")
                st.info(f"Correct Answer: {item['correct_answer']}")
            elif item["status_type"] == "incorrect":
                st.error(f"Your Marked Answer: {item['user_answer']} (Incorrect - 0 Marks)")
                st.info(f"Correct Answer: {item['correct_answer']}")
            else:
                st.warning(f"Your Marked Answer: Unanswered (0 Marks)")
                st.info(f"Correct Answer: {item['correct_answer']}")
            
            st.divider()
            
        if st.button("🔄 Take Another Test"):
            st.session_state.test_started = False
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.session_state.current_q_index = 0
            st.rerun()
