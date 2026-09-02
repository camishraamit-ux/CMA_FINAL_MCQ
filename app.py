import io
import random
import pdfplumber
import pandas as pd
import streamlit as st
import urllib.parse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==============================================================================
# 1. PDF EXTRACTION LOGIC
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
        ans_text = answers_dict.get(q_num, "")
        
        correct_index = None
        for idx, opt in enumerate(q_data["options"]):
            if opt and (opt.strip().lower() == ans_text.strip().lower() or opt.strip().lower() in ans_text.strip().lower()):
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
# 2. PDF REPORT GENERATOR (ReportLab)
# ==============================================================================
def generate_pdf_scorecard(candidate_name, subject_name, score, total_questions, percentage, detailed_report):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    normal_style = styles['Normal']
    bold_style = ParagraphStyle(name='BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

    elements = []

    # Title Banner
    elements.append(Paragraph("CMA FINAL MCQ ASSESSMENT REPORT CARD", title_style))
    elements.append(Spacer(1, 15))

    # Details Table
    meta_data = [
        [Paragraph("Candidate Name:", bold_style), Paragraph(candidate_name, normal_style)],
        [Paragraph("Subject:", bold_style), Paragraph(subject_name, normal_style)],
        [Paragraph("Final Score:", bold_style), Paragraph(f"{score} / {total_questions}", normal_style)],
        [Paragraph("Percentage:", bold_style), Paragraph(f"{percentage}%", normal_style)]
    ]
    t = Table(meta_data, colWidths=[130, 380])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Breakdown Table
    elements.append(Paragraph("<b>Question Performance Breakdown</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    table_data = [["Q.No", "Status"]]
    for item in detailed_report:
        table_data.append([item["q_num"], item["status"]])

    report_table = Table(table_data, colWidths=[80, 430])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(report_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

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

# Session State Initializations
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
                        st.error("No valid questions found in the selected PDF.")
                    else:
                        num_to_sample = min(q_count, total_available)
                        if num_to_sample < q_count:
                            st.warning(f"Note: Only {total_available} questions were available in this subject PDF. All available questions will be loaded.")
                        
                        st.session_state.assessment_df = df_all.sample(n=num_to_sample).reset_index(drop=True)
                        st.session_state.user_answers = {}
                        st.session_state.submitted = False
                        st.session_state.test_started = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not load '{pdf_filename}'. Ensure this file is uploaded to GitHub. Error: {e}")

# ==============================================================================
# 5. ASSESSMENT SCREEN
# ==============================================================================
else:
    st.title(f"CMA Final - {st.session_state.selected_subject}")
    st.markdown(f"**Candidate Name:** {st.session_state.candidate_name}")
    st.divider()

    df_test = st.session_state.assessment_df

    if not st.session_state.submitted:
        with st.form("quiz_form"):
            for display_num, row in df_test.iterrows():
                sn = display_num + 1
                st.markdown(f"### Q{sn}. {row['question']}")
                
                valid_options = [opt for opt in row["options"] if opt]
                
                choice = st.radio(
                    label=f"Select answer for Q{sn}",
                    options=range(len(valid_options)),
                    format_func=lambda x: f"{chr(65+x)}. {valid_options[x]}",
                    key=f"q_{display_num}",
                    index=None
                )
                
                if choice is not None:
                    st.session_state.user_answers[display_num] = choice
                
                st.write("")
            
            submit_assessment = st.form_submit_button("Submit Assessment", type="primary")
            if submit_assessment:
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
            if user_choice is not None:
                selected_opt_text = valid_options[user_choice]
                is_correct = (user_choice == correct_idx) or (selected_opt_text.strip().lower() == correct_ans_text.strip().lower())
            
            if is_correct:
                score += 1
                detailed_report.append({"q_num": f"Q{sn}", "status": "Correct (1 Mark)"})
            elif user_choice is not None:
                detailed_report.append({"q_num": f"Q{sn}", "status": "Incorrect (0 Marks)"})
            else:
                detailed_report.append({"q_num": f"Q{sn}", "status": "Unanswered (0 Marks)"})

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
        
        for display_num, row in df_test.iterrows():
            sn = display_num + 1
            user_choice = st.session_state.user_answers.get(display_num)
            correct_idx = row["correct_index"]
            correct_ans_text = row["correct_answer_text"]
            valid_options = [opt for opt in row["options"] if opt]
            
            st.markdown(f"**Q{sn}: {row['question']}**")
            
            is_correct = False
            if user_choice is not None:
                selected_opt_text = valid_options[user_choice]
                is_correct = (user_choice == correct_idx) or (selected_opt_text.strip().lower() == correct_ans_text.strip().lower())
            
            if is_correct:
                st.success(f"Your answer: {chr(65+user_choice)}. {valid_options[user_choice]} (Correct - 1 Mark)")
            elif user_choice is not None:
                st.error(f"Your answer: {chr(65+user_choice)}. {valid_options[user_choice]} (Incorrect - 0 Marks)")
                st.info(f"Correct Answer: {correct_ans_text}")
            else:
                st.warning(f"Unanswered (0 Marks). Correct Answer: {correct_ans_text}")
            
            st.divider()
            
        if st.button("🔄 Take Another Test"):
            st.session_state.test_started = False
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.rerun()
