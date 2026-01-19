import streamlit as st
import time
from chat import (
    get_chat_response,
    generate_greeting_message,
    classify_user_response,
    generate_question_from_chunk,
    generate_question_with_type,
    validate_mcq_answer,
    validate_true_false_answer,
    evaluate_open_answer,
    generate_follow_up_questions,
    generate_assessment_report
)
from db import (
    initialize_db,
    get_books,
    get_book_chunks,
    get_book_content_if_not_chunked,
    create_assessment_session,
    save_question_response,
    update_assessment_session,
    save_performance_analytics,
    get_assessment_history
)

st.set_page_config(page_title="📚 Book Chat Assessment", layout="centered")
initialize_db()

# Session state setup
defaults = {
    "mode": "chat",
    "chat_history": [],
    "chunk_index": 0,
    "username": "Guest",
    "qa_ready": False,
    "prev_rejected_qa": False,
    "chat_turns_after_rejection": 0,
    "selected_book_id": None,
    "debug_mode": False,
    "question_type": "open",
    "current_question_content": None,
    "awaiting_type_selection": False,
    "total_questions": 10,
    "questions_asked": 0,
    "assessment_mode": False,
    "assessment_started": False,
    "assessment_results": [],
    "current_question_type": "open",
    "current_chunk": "",
    "assessment_session_id": None,
    "question_start_time": None
}

for key, val in defaults.items():
    st.session_state.setdefault(key, val)

st.title("📚 Book Chat Assessment System")

# Sidebar: Book Selection + Configuration
books = get_books()
book_titles = [book['title'] for book in books]
selected_title = st.sidebar.selectbox("📖 Select a Book", ["-- Select a Book --"] + book_titles)

st.sidebar.markdown("### Assessment Configuration")
total_questions = st.sidebar.slider(
    "Number of Questions",
    min_value=5,
    max_value=50,
    value=st.session_state.total_questions,
    help="Set the total number of questions for assessment"
)
st.session_state.total_questions = total_questions
#Difficulty Level
difficulty = st.sidebar.radio(
    "Select Question Difficulty",
    ["easy", "intermediate", "hard"],
    index=1,
    help="CBSE LEVEL: Easy (Class 6-8), Intermediate (class 9-10), Hard (Class 11-12)"
)

# Question type selection
question_type = st.sidebar.radio(
    "Select Question Type",
    ["open", "mcq", "true_false", "mixed"],
    format_func=lambda x: {
        "mixed": "Mixed (All Types)", 
        "open": "Open-ended", 
        "mcq": "Multiple Choice", 
        "true_false": "True/False"
    }[x],
    key="question_type"
)

# Assessment Progress
if st.session_state.assessment_started and st.session_state.questions_asked > 0:
    progress = st.session_state.questions_asked / st.session_state.total_questions
    st.sidebar.progress(progress)
    st.sidebar.write(f"Progress: {st.session_state.questions_asked}/{st.session_state.total_questions}")
    if st.session_state.assessment_results:
        current_score = sum(result['score'] for result in st.session_state.assessment_results)
        max_score = len(st.session_state.assessment_results) * 10
        percentage = (current_score / max_score) * 100 if max_score > 0 else 0
        st.sidebar.write(f"Current Score: {current_score}/{max_score} ({percentage:.1f}%)")

st.sidebar.checkbox("🔧 Enable Debug Mode", key="debug_mode")

if selected_title == "-- Select a Book --":
    st.sidebar.info("Please select a book to begin chatting.")
    st.stop()

# Handle Book Change
selected_book = next((b for b in books if b["title"] == selected_title), None)
if st.session_state.selected_book_id != selected_book["id"]:
    st.session_state.selected_book = selected_book
    st.session_state.selected_book_id = selected_book["id"]
    st.session_state.chunk_index = 0
    st.session_state.chat_history = []
    st.session_state.mode = "chat"
    st.session_state.qa_ready = False
    st.session_state.prev_rejected_qa = False
    st.session_state.chat_turns_after_rejection = 0
    st.session_state.questions_asked = 0
    st.session_state.assessment_results = []
    st.session_state.assessment_started = False
    st.session_state.assessment_session_id = None

# Ensure Book is Chunked
get_book_content_if_not_chunked(selected_book)

# Initial Greetings
if not st.session_state.chat_history:
    greeting = generate_greeting_message(st.session_state.username)
    st.session_state.chat_history.extend([
        {"role": "assistant", "content": greeting},
        {"role": "assistant", "content": "Hello! I can generate questions from the book content to test your understanding. Would you like me to start asking you questions based on the book? 📚"}
    ])
#Mixed Question Type(All-type)
def get_next_question_type():
    """Determine next question type based on setting"""
    if st.session_state.question_type != "mixed":
        return st.session_state.question_type
    types = ["open", "mcq", "true_false"]
    return types[st.session_state.questions_asked % len(types)]

def switch_to_qa_mode():
    """Start the assessment"""
    st.session_state.mode = "qa"
    st.session_state.qa_ready = True
    st.session_state.assessment_started = True
    st.session_state.prev_rejected_qa = False
    st.session_state.chat_turns_after_rejection = 0
    
    # Create assessment session in database
    st.session_state.assessment_session_id = create_assessment_session(
        st.session_state.selected_book["id"],
        st.session_state.total_questions,
        difficulty
    )
    
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": f"🎯 Starting your {st.session_state.total_questions}-question assessment! Let's begin."
    })
    
    # Generate first question
    generate_next_question()

def generate_next_question():
    """Generate the next question in the assessment"""
    if st.session_state.questions_asked >= st.session_state.total_questions:
        finish_assessment()
        return 
    
    book_id = st.session_state.selected_book["id"]
    chunks = get_book_chunks(book_id)
    
    if not chunks:
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": "No content available to generate questions."
        })
        return

    # Select chunk (sequential first, then random)
    if st.session_state.chunk_index < len(chunks):
        selected_chunk = chunks[st.session_state.chunk_index]
        st.session_state.chunk_index += 1
    else:
        import random
        selected_chunk = random.choice(chunks)

    # Determine question type
    current_q_type = get_next_question_type()
    
    # Generate question
    question = generate_question_with_type(
        selected_chunk["chunk_text"],
        question_type=current_q_type,
        difficulty=difficulty,
        question_number=st.session_state.questions_asked + 1,
        total_questions=st.session_state.total_questions
    )
    
    st.session_state.current_question_content = question
    st.session_state.current_question_type = current_q_type
    st.session_state.current_chunk = selected_chunk["chunk_text"]
    st.session_state.question_start_time = time.time()
    
    # Display question
    question_header = f"**Question {st.session_state.questions_asked + 1}/{st.session_state.total_questions}** ({current_q_type.upper()} - {difficulty.upper()})\n\n"
    
    if current_q_type in ["mcq", "true_false"]:
        # Remove correct answer from display
        display_question = question
        lines = question.split('\n')
        display_lines = []
        for line in lines:
            if not (line.strip().startswith('Correct Answer:') or line.strip().startswith('Answer:')):
                display_lines.append(line)
        display_question = '\n'.join(display_lines)
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": question_header + display_question
        })
    else:
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": question_header + question
        })

def handle_chat_mode(user_input):
    label, reason = classify_user_response(user_input)

    if label == "yes":
        switch_to_qa_mode()
    elif label == "no":
        if not st.session_state.prev_rejected_qa:
            st.session_state.prev_rejected_qa = True
            st.session_state.chat_turns_after_rejection = 0
            st.session_state.chat_history.append({"role": "assistant", "content": "Sure! We can just chat for now"})
        else:
            st.session_state.chat_turns_after_rejection += 1
            reply = get_chat_response([
                {"role": "system", "content": "You're a supportive assistant. Keep the conversation friendly and casual."},
                {"role": "user", "content": user_input}
            ])
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

            if st.session_state.chat_turns_after_rejection >= 2:
                st.session_state.chat_history.append({"role": "assistant", "content": "Would you like to try a few questions from the book now?"})
                st.session_state.chat_turns_after_rejection = 0
    else:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "I can generate questions from the book to test your understanding. Would you like me to start asking you questions?"
        })
        if st.session_state.debug_mode:
            st.session_state.chat_history.append({"role": "assistant", "content": f"(debug): Label = {label} | Reason = {reason}"})

def handle_qa_mode(user_input):
    """Handle Q&A assessment mode"""
    current_q_type = st.session_state.get('current_question_type', 'open')
    
    # Calculate response time
    response_time = 0
    if st.session_state.question_start_time:
        response_time = int(time.time() - st.session_state.question_start_time)
    
    # Evaluate the answer
    score = 0
    feedback = ""
    
    if current_q_type == "mcq" and st.session_state.current_question_content:
        feedback = validate_mcq_answer(st.session_state.current_question_content, user_input)
        score = 10 if "Correct!" in feedback else 0
        
    elif current_q_type == "true_false" and st.session_state.current_question_content:
        feedback = validate_true_false_answer(st.session_state.current_question_content, user_input)
        score = 10 if "Correct!" in feedback else 0
        
    else:  # Open-ended question
        feedback, score = evaluate_open_answer(
            st.session_state.current_question_content, 
            user_input, 
            st.session_state.get('current_chunk', ''),
            difficulty
        )
    
    # Generate follow-up if needed
    follow_up = ""
    if score < 7 and current_q_type == "open":
        follow_up = generate_follow_up_questions(
            user_input, 
            st.session_state.current_question_content,
            st.session_state.get('current_chunk', '')
        )
    
    # Save to database
    if st.session_state.assessment_session_id:
        save_question_response(
            st.session_state.assessment_session_id,
            st.session_state.questions_asked + 1,
            current_q_type,
            st.session_state.current_question_content,
            user_input,
            score,
            feedback,
            difficulty,
            st.session_state.get('current_chunk', ''),
            follow_up,
            response_time
        )
    
    # Store assessment result
    assessment_result = {
        'question_number': st.session_state.questions_asked + 1,
        'question': st.session_state.current_question_content,
        'user_answer': user_input,
        'score': score,
        'feedback': feedback,
        'question_type': current_q_type,
        'difficulty': difficulty
    }
    st.session_state.assessment_results.append(assessment_result)
    
    # Display feedback
    st.session_state.chat_history.append({"role": "assistant", "content": feedback})
    
    # Show score
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": f"**Score: {score}/10** 📊"
    })
    
    # Show follow-up if exists
    if follow_up:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"💡 **Follow-up:** {follow_up}"
        })
    
    # Move to next question
    st.session_state.questions_asked += 1
    
    if st.session_state.questions_asked < st.session_state.total_questions:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "Let's move to the next question! 📚"
        })
        generate_next_question()
    else:
        finish_assessment()

def finish_assessment():
    """Complete the assessment and generate report"""
    st.session_state.mode = "completed"
    
    # Calculate final statistics
    total_score = sum(result['score'] for result in st.session_state.assessment_results)
    max_possible_score = st.session_state.total_questions * 10
    percentage = (total_score / max_possible_score) * 100
    
    # Calculate CBSE grade
    if percentage >= 91:
        grade, performance = "A1", "Outstanding"
    elif percentage >= 81:
        grade, performance = "A2", "Excellent"
    elif percentage >= 71:
        grade, performance = "B1", "Very Good"
    elif percentage >= 61:
        grade, performance = "B2", "Good"
    elif percentage >= 51:
        grade, performance = "C1", "Fair"
    elif percentage >= 41:
        grade, performance = "C2", "Satisfactory"
    elif percentage >= 33:
        grade, performance = "D", "Needs Improvement"
    else:
        grade, performance = "E", "Requires Attention"
    
    # Update assessment session in database
    if st.session_state.assessment_session_id:
        update_assessment_session(
            st.session_state.assessment_session_id,
            st.session_state.questions_asked,
            total_score,
            percentage,
            grade,
            performance,
            'completed'
        )
        
        # Save performance analytics by question type
        type_performance = {}
        for result in st.session_state.assessment_results:
            q_type = result['question_type']
            if q_type not in type_performance:
                type_performance[q_type] = {'total': 0, 'score': 0, 'count': 0}
            type_performance[q_type]['total'] += 10
            type_performance[q_type]['score'] += result['score']
            type_performance[q_type]['count'] += 1
        
        for q_type, perf in type_performance.items():
            avg_score = perf['score'] / perf['count'] if perf['count'] > 0 else 0
            perf_percentage = (perf['score'] / perf['total']) * 100 if perf['total'] > 0 else 0
            save_performance_analytics(
                st.session_state.assessment_session_id,
                q_type,
                perf['count'],
                perf['score'],
                avg_score,
                perf_percentage
            )
    
    # Generate CBSE report
    report = generate_assessment_report(
        st.session_state.assessment_results,
        percentage,
        difficulty
    )
    
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": f"🎉 **Assessment Complete!**\n\n{report}"
    })
    
    # Offer to restart
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": "Would you like to take another assessment or discuss any topics from the book? 📖"
    })

# Handle User Input
user_input = st.chat_input("Type your message...")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.spinner("Thinking..."):
        if st.session_state.mode == "qa" and st.session_state.qa_ready:
            handle_qa_mode(user_input)
        elif st.session_state.mode == "completed":
            label, _ = classify_user_response(user_input)
            if label == "yes":
                st.session_state.questions_asked = 0
                st.session_state.assessment_results = []
                st.session_state.chunk_index = 0
                st.session_state.assessment_session_id = None
                switch_to_qa_mode()
            else:
                handle_chat_mode(user_input)
        else:
            handle_chat_mode(user_input)

# Display Chat
for msg in st.session_state.chat_history:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"])

# Assessment Report Sidebar
if st.session_state.assessment_results:
    st.sidebar.markdown("### 📊 Assessment Summary")
    total_score = sum(result['score'] for result in st.session_state.assessment_results)
    max_score = len(st.session_state.assessment_results) * 10
    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    
    st.sidebar.metric("Score", f"{total_score}/{max_score}")
    st.sidebar.metric("Percentage", f"{percentage:.1f}%")
    
    # Grade calculation (CBSE style)
    if percentage >= 90:
        grade = "A1"
        color = "🟢"
    elif percentage >= 80:
        grade = "A2"
        color = "🟢"
    elif percentage >= 70:
        grade = "B1"
        color = "🟡"
    elif percentage >= 60:
        grade = "B2"
        color = "🟡"
    elif percentage >= 50:
        grade = "C1"
        color = "🟠"
    elif percentage >= 40:
        grade = "C2"
        color = "🟠"
    else:
        grade = "D"
        color = "🔴"
    
    st.sidebar.markdown(f"**Grade:** {color} {grade}")

# Assessment History Sidebar
if st.session_state.selected_book_id:
    history = get_assessment_history(st.session_state.selected_book_id, limit=5)
    if history:
        st.sidebar.markdown("### 📈 Recent Assessments")
        for session in history:
            st.sidebar.markdown(f"**{session['percentage_score']:.1f}%** ({session['cbse_grade']}) - {session['completed_at'].strftime('%m/%d/%Y')}")

# Download Buttons
if st.session_state.chat_history:
    chat_log = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.chat_history])
    st.download_button("⬇️ Download Chat History", chat_log, file_name="chat_history.txt", mime="text/plain")

# Add assessment results download if assessment is complete
if st.session_state.assessment_results:
    results_text = "ASSESSMENT RESULTS\n" + "="*50 + "\n\n"
    for i, result in enumerate(st.session_state.assessment_results, 1):
        results_text += f"Question {i} ({result['question_type'].upper()}):\n"
        results_text += f"Q: {result['question']}\n"
        results_text += f"A: {result['user_answer']}\n"
        results_text += f"Score: {result['score']}/10\n"
        results_text += f"Feedback: {result['feedback']}\n\n"
    
    total_score = sum(r['score'] for r in st.session_state.assessment_results)
    max_score = len(st.session_state.assessment_results) * 10
    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    
    results_text += f"FINAL RESULTS:\n"
    results_text += f"Total Score: {total_score}/{max_score}\n"
    results_text += f"Percentage: {percentage:.1f}%\n"
    
    st.download_button(
        "📊 Download Assessment Report",
        results_text,
        file_name=f"assessment_report_{selected_title}.txt",
        mime="text/plain"
    )