import random
import pdfplumber
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. PDF EXTRACTION LOGIC (Supports multiple subject files)
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
# 2. STREAMLIT CONFIGURATION & SETUP
# ==============================================================================
st.set_page_config(page_title="CMA Final Assessment", layout="centered")

# Map your 8 subject names to their respective PDF filenames
# (Ensure your 8 PDF files are uploaded to your GitHub repository)
SUBJECT_FILES = {
    "Financial Analysis": "Financial_Analysis.pdf",
    "Strategic Financial Management": "Strategic_Financial_Management.pdf",
    "Strategic Cost Management": "Strategic_Cost_Management.pdf",
    "Direct and Indirect Tax Laws": "Direct_and_Indirect_Tax_Laws.pdf",
    "Corporate Laws and Compliance": "Corporate_Laws_and_Compliance.pdf",
    "Business Strategy and Strategic Management": "Business_Strategy.pdf",
    "Corporate Financial Reporting": "Corporate_Financial_Reporting.pdf",
    "Business Valuation and Management": "Business_Valuation.pdf"
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
# 3. REGISTRATION / SETUP SCREEN
# ==============================================================================
if not st.session_state.test_started:
    st.title("🎯 CMA Final Assessment Portal")
    st.write("Please enter your details and choose a subject to begin your 25-question randomized assessment.")
    
    with st.form("setup_form"):
        name_input = st.text_input("Enter Your Full Name:", value=st.session_state.candidate_name)
        subject_choice = st.selectbox("Select Subject:", options=list(SUBJECT_FILES.keys()))
        
        start_btn = st.form_submit_button("Start Assessment", type="primary")
        
        if start_btn:
            if not name_input.strip():
                st.error("Please enter your name to proceed.")
            else:
                st.session_state.candidate_name = name_input.strip()
                st.session_state.selected_subject = subject_choice
                
                # Load PDF and sample 25 questions randomly
                pdf_filename = SUBJECT_FILES[subject_choice]
                try:
                    df_all = extract_mcqs_from_pdf(pdf_filename)
                    if len(df_all) < 25:
                        st.warning(f"Note: This file only contains {len(df_all)} questions. All will be used.")
                        st.session_state.assessment_df = df_all.sample(frac=1).reset_index(drop=True)
                    else:
                        st.session_state.assessment_df = df_all.sample(n=25).reset_index(drop=True)
                    
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.session_state.test_started = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not load '{pdf_filename}'. Make sure the file is uploaded to your repository. Error: {e}")

# ==============================================================================
# 4. ASSESSMENT SCREEN (25 Random Questions, Sn 1 to 25)
# ==============================================================================
else:
    # Dynamic Heading Requirement
    st.title(f"CMA Final - {st.session_state.selected_subject}")
    st.markdown(f"**Candidate Name:** {st.session_state.candidate_name}")
    st.divider()

    df_test = st.session_state.assessment_df

    if not st.session_state.submitted:
        with st.form("quiz_form"):
            for display_num, row in df_test.iterrows():
                sn = display_num + 1  # Serial number from 1 to 25
                st.markdown(f"### Q{sn}. {row['question']}")
                
                valid_options = [opt for opt in row["options"] if opt]
                
                # Render options using radio buttons
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
    # 5. SCORECARD & RESULTS
    # ==========================================================================
    else:
        score = 0
        total_questions = len(df_test)
        
        st.subheader("📊 Assessment Results Summary")
        
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
                score += 1
                st.success(f"Your answer: {chr(65+user_choice)}. {valid_options[user_choice]} (Correct - 1 Mark)")
            elif user_choice is not None:
                st.error(f"Your answer: {chr(65+user_choice)}. {valid_options[user_choice]} (Incorrect - 0 Marks)")
                st.info(f"Correct Answer: {correct_ans_text}")
            else:
                st.warning(f"Unanswered (0 Marks). Correct Answer: {correct_ans_text}")
            
            st.divider()
            
        st.metric(label="Final Score (Marks)", value=f"{score} / {total_questions}")
        
        if st.button("🔄 Take Another Test / Retake"):
            st.session_state.test_started = False
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.rerun()
