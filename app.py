import random
import pdfplumber
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. PDF EXTRACTION LOGIC
# ==============================================================================
@st.cache_data
def extract_mcqs_from_pdf(pdf_path):
    """
    Extracts questions, multiple-choice options, and correct answers from tables inside the PDF.
    """
    questions_dict = {}
    answers_dict = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                
                for row in table:
                    # Clean up inner line breaks and whitespace in table cells
                    clean_row = [cell.replace('\n', ' ').strip() if cell else "" for cell in row]
                    
                    if len(clean_row) < 3 or not clean_row[0].isdigit():
                        continue
                        
                    q_num = int(clean_row[0])
                    
                    # Structure 1: Question Bank Table [SL NO, QUESTION, OPTION 1, OPTION 2, OPTION 3, OPTION 4]
                    if len(clean_row) >= 6:
                        questions_dict[q_num] = {
                            "id": q_num,
                            "question": clean_row[1],
                            "options": [clean_row[2], clean_row[3], clean_row[4], clean_row[5]]
                        }
                    # Structure 2: Answer Key Table [SL NO, QUESTION, CORRECT ANSWER]
                    elif len(clean_row) == 3:
                        answers_dict[q_num] = clean_row[2]

    # Combine extracted questions with their matching answers
    mcq_list = []
    for q_num, q_data in questions_dict.items():
        ans_text = answers_dict.get(q_num, "")
        
        # Match answer text against options to find correct option index (0-3)
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
# 2. STREAMLIT INTERACTIVE DASHBOARD
# ==============================================================================
st.set_page_config(page_title="Interactive MCQ Quiz", layout="centered")

st.title("📚 Interactive MCQ Question Bank")

# Sidebar Setup
st.sidebar.header("Configuration")
uploaded_file = st.sidebar.file_uploader("Upload MCQ PDF", type=["pdf"])

pdf_source = uploaded_file if uploaded_file else "MCQ_Bank_Paper_20A.pdf"

try:
    df_questions = extract_mcqs_from_pdf(pdf_source)
    st.sidebar.success(f"Successfully loaded {len(df_questions)} questions!")
except Exception as e:
    st.error(f"Error reading PDF file: {e}")
    st.stop()

# Initialize Quiz Session States
if "current_idx" not in st.session_state:
    st.session_state.current_idx = random.randint(0, len(df_questions) - 1)
if "selected_option" not in st.session_state:
    st.session_state.selected_option = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "total_answered" not in st.session_state:
    st.session_state.total_answered = 0

# Interactive Scoreboard
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Score", value=f"{st.session_state.score} / {st.session_state.total_answered}")
with col2:
    if st.button("🔄 Reset Quiz"):
        st.session_state.score = 0
        st.session_state.total_answered = 0
        st.session_state.selected_option = None
        st.rerun()

st.divider()

# Load Current Question Information
q_data = df_questions.iloc[st.session_state.current_idx]
options = q_data["options"]
correct_ans_text = q_data["correct_answer_text"]
correct_idx = q_data["correct_index"]

st.subheader(f"Question {q_data['id']}")
st.write(f"**{q_data['question']}**")

# Handle Click Events
def handle_option_click(opt_index):
    if st.session_state.selected_option is None:
        st.session_state.selected_option = opt_index
        st.session_state.total_answered += 1
        
        is_correct = (opt_index == correct_idx) or (options[opt_index].strip().lower() == correct_ans_text.strip().lower())
        if is_correct:
            st.session_state.score += 1

# Render Clickable Option Buttons with Custom Visual Feedback
for idx, opt in enumerate(options):
    if not opt:
        continue
        
    btn_label = f"{chr(65+idx)}. {opt}"
    
    if st.session_state.selected_option is not None:
        is_this_correct = (idx == correct_idx) or (opt.strip().lower() == correct_ans_text.strip().lower())
        
        if is_this_correct:
            # Display correct answer in Green box
            st.markdown(
                f'<div style="background-color: #d4edda; color: #155724; padding: 12px; border-radius: 5px; margin-bottom: 8px; border: 1px solid #c3e6cb;"><b>✓ {btn_label}</b></div>', 
                unsafe_allow_html=True
            )
        elif st.session_state.selected_option == idx:
            # Display wrong answer in Red box
            st.markdown(
                f'<div style="background-color: #f8d7da; color: #721c24; padding: 12px; border-radius: 5px; margin-bottom: 8px; border: 1px solid #f5c6cb;"><b>✗ {btn_label}</b></div>', 
                unsafe_allow_html=True
            )
        else:
            st.button(btn_label, key=f"opt_{idx}", disabled=True)
    else:
        st.button(btn_label, key=f"opt_{idx}", on_click=handle_option_click, args=(idx,), use_container_width=True)

# Post-Selection Feedback Messages
if st.session_state.selected_option is not None:
    selected_idx = st.session_state.selected_option
    is_correct = (selected_idx == correct_idx) or (options[selected_idx].strip().lower() == correct_ans_text.strip().lower())
    
    if is_correct:
        st.success("Correct Answer! 🎉")
    else:
        st.error(f"Incorrect. The correct answer is: **{correct_ans_text}**")

# Next Question Navigation
st.divider()
def next_question():
    st.session_state.selected_option = None
    st.session_state.current_idx = random.randint(0, len(df_questions) - 1)

st.button("➡️ Next Question", on_click=next_question, type="primary")