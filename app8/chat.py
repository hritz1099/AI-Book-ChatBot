import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()
use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"

def get_chat_response(messages, model="llama3.2:latest"):
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        return f"Error:{str(e)}"
    
def test_connection():
    """Test if the connection works"""
    test_messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Say hello"}
    ]
    result = get_chat_response(test_messages)
    print(f"Test result: {result}")
    return result

if __name__ == "__main__":
    print("Testing connection...")
    test_connection()
#Initial Greeting
def generate_greeting_message(username):
    return f"Hey {username}! Ready to test your knowledge with a comprehensive book assessment?"

def generate_question_with_type(chunk_text, question_type="open", difficulty="intermediate", 
                               prev_question=None, prev_answer=None, question_number=1, total_questions=10):
    """Generate different types of questions from book content with question numbering"""
    # Clean the text first
    clean_text = re.sub(r'https?://[^\s]+', '[LINK]', chunk_text)
    clean_text = re.sub(r'["""]', '"', clean_text)
    clean_text = re.sub(r"[''']", "'", clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    difficulty_levels = {
        "easy": "basic comprehension suitable for Class 6-8 students (simple recall of facts, names, dates)",
        "intermediate": "analytical thinking suitable for Class 9-10 students (understanding relationships, causes, effects)", 
        "hard": "critical evaluation suitable for Class 11-12 students (analysis, synthesis, evaluation of concepts)"
    }
    
    question_prompts = {
        "mcq": f"""Generate exactly ONE multiple choice question about {difficulty_levels.get(difficulty)} from this text.

FORMAT REQUIRED:
Question: [Your question here]?
A) [Option A]
B) [Option B] 
C) [Option C]
D) [Option D]
Correct Answer: [A/B/C/D]

REQUIREMENTS:
- Question must be directly answerable from the given content
- All 4 options should be plausible but only ONE clearly correct
- Make it {difficulty} difficulty level for CBSE standards
- Options should be roughly equal length
- Avoid "All of the above" or "None of the above" options""",

        "true_false": f"""Generate exactly ONE true/false statement about {difficulty_levels.get(difficulty)} from this text.

FORMAT REQUIRED:
Statement: [Your clear statement here]
Answer: [True/False]

REQUIREMENTS:
- Statement must be clearly true or false based on the content
- Make it {difficulty} difficulty level for CBSE standards  
- Avoid ambiguous or trick statements
- Base it strictly on the provided text""",

        "open": f"""Generate exactly ONE open-ended question that requires {difficulty_levels.get(difficulty)} from this text.

REQUIREMENTS:
- Generate EXACTLY ONE thoughtful question
- Must be answerable from the given content
- Should allow for 2-3 sentence answers
- Use question words appropriate for {difficulty} level
- Make it suitable for CBSE {difficulty} level assessment
- End with a question mark"""
    }
    
    # Handle mixed type selection
    if question_type == "mixed":
        import random
        question_type = random.choice(["open", "mcq", "true_false"])
    
    prompt = question_prompts.get(question_type, question_prompts["open"])
    prompt += f"\n\nBOOK CONTENT:\n{clean_text}\n\n"
    
    if prev_question and prev_answer:
        prompt += f"PREVIOUS CONTEXT:\nQ: {prev_question}\nA: {prev_answer}\n\nCreate a NEW question that builds upon this context but focuses on different aspects of the content.\n\n"
    
    prompt += f"Generate a {difficulty} level {question_type} question suitable for CBSE assessment standards."
    
    messages = [
        {"role": "system", "content": f"You are an expert CBSE curriculum designer. Create {difficulty} level {question_type} questions that align with CBSE assessment standards. Follow the exact format specified."},
        {"role": "user", "content": prompt}
    ]
    
    response = get_chat_response(messages)
    return response.strip()

def generate_question_from_chunk(chunk_text, prev_question=None, prev_answer=None, difficulty="intermediate"):
    """Legacy function for backward compatibility"""
    return generate_question_with_type(
        chunk_text=chunk_text,
        question_type="open",
        difficulty=difficulty,
        prev_question=prev_question,
        prev_answer=prev_answer
    )

def classify_user_response(user_input):
    """Enhanced classification with fallback logic"""
    user_lower = user_input.lower().strip()
    
    # Check for yes responses
    yes_indicators = ['yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'start', 'begin', 'let\'s go', 'ready']
    if any(indicator in user_lower for indicator in yes_indicators):
        return "yes", "user agreed to assessment"
    
    # Check for no responses
    no_indicators = ['no', 'not now', 'later', 'maybe later', 'nah', 'nope', 'not ready']
    if any(indicator in user_lower for indicator in no_indicators):
        return "no", "user declined assessment"
    
    try:
        system_prompt = (
            "You're a classifier. Given the user message, classify the intent as:\n"
            "- yes: if the user agrees or is ready for assessment/questions\n"
            "- no: if the user says not now, later, or declines\n"
            "- other: if the intent is unclear or unrelated\n"
            "Reply only with the label and a short reason (e.g., yes: sounds excited)"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User said: '{user_input}'"}
        ]
        response = get_chat_response(messages)

        if ":" in response:
            parts = response.strip().split(":", 1)
            label = parts[0].strip().lower()
            reason = parts[1].strip()
            return label, reason
        else:
            return "other", "could not parse classification response"
            
    except Exception as e:
        return "other", f"classification error: {str(e)}"

def validate_mcq_answer(question_content, user_answer):
    """Validate MCQ answer and provide detailed feedback"""
    try:
        # Extract correct answer from the question content
        lines = question_content.split('\n')
        correct_answer = None
        question_text = ""
        options = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Question:'):
                question_text = line.split(':', 1)[1].strip()
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                option_letter = line[0]
                option_text = line[3:].strip()
                options[option_letter] = option_text
            elif line.startswith('Correct Answer:'):
                correct_answer = line.split(':')[1].strip().upper()
                break
        
        if not correct_answer:
            return "Could not find the correct answer in the question format."
        
        user_answer_clean = user_answer.strip().upper()
        
        # Handle different answer formats
        if user_answer_clean in ['A', 'B', 'C', 'D']:
            user_choice = user_answer_clean
        elif len(user_answer_clean) >= 1 and user_answer_clean[0] in ['A', 'B', 'C', 'D']:
            user_choice = user_answer_clean[0]
        else:
            return f"Please answer with A, B, C, or D. The correct answer was **{correct_answer}) {options.get(correct_answer, '')}**"
        
        if user_choice == correct_answer:
            return f"Correct! Well done! You chose {user_choice}) {options.get(user_choice, '')}"
        else:
            return f"Incorrect. You chose {user_choice}) {options.get(user_choice, '')}\n\nCorrect answer: {correct_answer}) {options.get(correct_answer, '')}"
            
    except Exception as e:
        return f"Error validating answer: {str(e)}"
    
def validate_true_false_answer(question_content, user_answer):
    """Validate True/False answer and provide detailed feedback"""
    try:
        # Extract correct answer
        lines = question_content.split('\n')
        correct_answer = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('Answer:'):
                correct_answer = line.split(':')[1].strip().lower()
                break
        
        if not correct_answer:
            return "Could not find the correct answer in the question format."
        
        user_answer_clean = user_answer.strip().lower()
        
        # Handle different formats (true, t, false, f, yes, no)
        if user_answer_clean in ['true', 't', 'yes', '1', 'correct']:
            user_choice = 'true'
        elif user_answer_clean in ['false', 'f', 'no', '0', 'incorrect']:
            user_choice = 'false'  
        else:
            return f"Please answer with True or False. The correct answer was {correct_answer.title()}."
        
        if user_choice == correct_answer:
            return f"Correct! The statement is indeed {correct_answer.title()}."
        else:
            return f"Incorrect. The statement is {correct_answer.title()}, not {user_choice.title()}."
            
    except Exception as e:
        return f"Error validating answer: {str(e)}"
    
def evaluate_open_answer(question, user_answer, context, difficulty):
    """Evaluate open-ended answers with strict accuracy checking"""
    try:
        # Clean inputs
        clean_context = context[:2000] if len(context) > 2000 else context
        
        # CBSE evaluation criteria
        criteria_prompts = {
            "easy": "Basic recall and understanding - checks if student can identify and state facts correctly",
            "intermediate": "Application and analysis - checks if student can explain relationships and apply knowledge",
            "hard": "Evaluation and synthesis - checks if student can critically analyze and form judgments"
        }
        
        evaluation_prompt = f"""You are a STRICT CBSE examiner. Your job is to evaluate if the student's answer is FACTUALLY CORRECT based on the book content.

QUESTION: {question}

STUDENT ANSWER: {user_answer}

BOOK CONTENT (SOURCE OF TRUTH): 
{clean_context}

EVALUATION CRITERIA ({difficulty} level):
{criteria_prompts.get(difficulty, criteria_prompts['intermediate'])}

CRITICAL INSTRUCTIONS:
1. FIRST, verify if the student's answer contains CORRECT INFORMATION from the book content
2. If the answer contains WRONG facts, dates, times, names, or details = MAXIMUM 3/10
3. If the answer is partially correct but incomplete = 4-6/10
4. If the answer is correct but lacks depth = 7-8/10
5. If the answer is accurate, complete, and well-explained = 9-10/10

SCORING RUBRIC (out of 10):
- 9-10: Excellent - FACTUALLY CORRECT, complete, and well-explained
- 7-8: Good - FACTUALLY CORRECT but lacks some depth or examples
- 5-6: Satisfactory - PARTIALLY CORRECT with some accurate information
- 3-4: Needs Improvement - MOSTLY INCORRECT or significant factual errors
- 1-2: Poor - COMPLETELY WRONG information or major misunderstanding
- 0: No attempt or completely irrelevant

IMPORTANT: 
- Compare the student's specific facts (times, dates, names, numbers) with the book content
- If ANY key fact is wrong, the score MUST be low (0-4)
- Do NOT give high scores for incorrect information, even if it's well-written
- Base your evaluation ONLY on the book content provided

Provide your response in this EXACT format:
SCORE: [number]
CORRECT_FACTS: [list key facts that are correct]
WRONG_FACTS: [list key facts that are incorrect]
FEEDBACK: [2-3 sentences explaining the score]
SUGGESTION: [specific suggestion for improvement]
"""
        
        messages = [
            {"role": "system", "content": "You are a STRICT CBSE examiner who verifies factual accuracy. You do NOT give high scores for incorrect information."},
            {"role": "user", "content": evaluation_prompt}
        ]
        
        response = get_chat_response(messages)
        
        # Parse the response with strict validation
        lines = response.split('\n')
        score = 0  # default to 0 if parsing fails
        feedback = "Answer evaluated."
        suggestion = ""
        correct_facts = ""
        wrong_facts = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('SCORE:'):
                try:
                    score_text = line.split(':')[1].strip()
                    # Extract just the number
                    score_match = re.search(r'\d+', score_text)
                    if score_match:
                        score = int(score_match.group())
                        score = max(0, min(10, score))  # Ensure 0-10 range
                except:
                    score = 0
            elif line.startswith('CORRECT_FACTS:'):
                correct_facts = line.split(':', 1)[1].strip()
            elif line.startswith('WRONG_FACTS:'):
                wrong_facts = line.split(':', 1)[1].strip()
            elif line.startswith('FEEDBACK:'):
                feedback = line.split(':', 1)[1].strip()
            elif line.startswith('SUGGESTION:'):
                suggestion = line.split(':', 1)[1].strip()
        
        # Additional validation: if wrong facts are mentioned, force low score
        if wrong_facts and wrong_facts.lower() not in ['none', 'n/a', 'nil', '']:
            if score > 4:
                score = min(score, 4)  # Cap score at 4 if there are wrong facts
        
        # Format final feedback with factual analysis
        score_label = "Excellent" if score >= 8 else "Good" if score >= 6 else "Fair" if score >= 4 else "Needs Work"
        
        final_feedback = f"**Evaluation ({score_label}):**\n{feedback}"
        
        if correct_facts and correct_facts.lower() not in ['none', 'n/a', 'nil', '']:
            final_feedback += f"\n\n**✓ Correct:** {correct_facts}"
        
        if wrong_facts and wrong_facts.lower() not in ['none', 'n/a', 'nil', '']:
            final_feedback += f"\n\n**✗ Incorrect:** {wrong_facts}"
        
        if suggestion:
            final_feedback += f"\n\n**💡 Tip:** {suggestion}"
        
        return final_feedback, score
        
    except Exception as e:
        return f"Error evaluating answer: {str(e)}", 0
    
def generate_follow_up_questions(user_answer, original_question, context):
    """Generate follow-up questions based on user's response to enhance learning"""
    try:
        prompt = f"""
Based on the student's answer, generate ONE insightful follow-up question that will:
1. Help deepen their understanding
2. Address any gaps in their response  
3. Connect to broader themes in the content

ORIGINAL QUESTION: {original_question}
STUDENT ANSWER: {user_answer}
CONTEXT: {context[:800]}...

Generate a thoughtful follow-up question that encourages critical thinking.
Keep it concise and engaging.
"""
        
        messages = [
            {"role": "system", "content": "You are an expert educator creating follow-up questions to enhance student learning."},
            {"role": "user", "content": prompt}
        ]
        
        response = get_chat_response(messages)
        
        # Clean up the response
        follow_up = response.strip()
        if not follow_up.endswith('?'):
            follow_up += '?'
            
        return follow_up
        
    except Exception as e:
        return f"Error generating follow-up: {str(e)}"
    
def generate_assessment_report(assessment_results, overall_percentage, difficulty):
    """Generate comprehensive CBSE-style assessment report"""
    try:
        total_questions = len(assessment_results)
        total_score = sum(result['score'] for result in assessment_results)
        max_score = total_questions * 10
        
        # Calculate performance by question type
        type_performance = {}
        for result in assessment_results:
            q_type = result['question_type']
            if q_type not in type_performance:
                type_performance[q_type] = {'total': 0, 'score': 0}
            type_performance[q_type]['total'] += 10
            type_performance[q_type]['score'] += result['score']
        
        # CBSE Grade calculation
        if overall_percentage >= 91:
            grade, performance = "A1", "Outstanding"
        elif overall_percentage >= 81:
            grade, performance = "A2", "Excellent"
        elif overall_percentage >= 71:
            grade, performance = "B1", "Very Good"
        elif overall_percentage >= 61:
            grade, performance = "B2", "Good"
        elif overall_percentage >= 51:
            grade, performance = "C1", "Fair"
        elif overall_percentage >= 41:
            grade, performance = "C2", "Satisfactory"
        elif overall_percentage >= 33:
            grade, performance = "D", "Needs Improvement"
        else:
            grade, performance = "E", "Requires Attention"
        
        # Generate detailed analysis
        strengths = []
        improvements = []
        
        for q_type, perf in type_performance.items():
            percentage = (perf['score'] / perf['total']) * 100 if perf['total'] > 0 else 0
            if percentage >= 70:
                strengths.append(f"{q_type.replace('_', ' ').title()} questions ({percentage:.0f}%)")
            else:
                improvements.append(f"{q_type.replace('_', ' ').title()} questions ({percentage:.0f}%)")
        
        report = f"""**ASSESSMENT REPORT**
{'='*40}

**Overall Performance**
- **Total Questions:** {total_questions}
- **Score:** {total_score}/{max_score} ({overall_percentage:.1f}%)
- **Grade:** {grade} ({performance})
- **Difficulty Level:** {difficulty.title()}

**Performance Analysis**
"""
        
        for q_type, perf in type_performance.items():
            percentage = (perf['score'] / perf['total']) * 100 if perf['total'] > 0 else 0
            status = "Strong" if percentage >= 70 else "Average" if percentage >= 50 else "Weak"
            report += f"- **{q_type.replace('_', ' ').title()}:** {status} - {perf['score']}/{perf['total']} ({percentage:.0f}%)\n"
        
        if strengths:
            report += f"\n**Strong Areas:**\n"
            for strength in strengths:
                report += f"- {strength}\n"
        
        if improvements:
            report += f"\n**Areas for Improvement:**\n"
            for improvement in improvements:
                report += f"- {improvement}\n"
        
        # Add recommendations based on performance
        if overall_percentage >= 80:
            report += f"\n**Recommendations:**\nExcellent work! Consider exploring advanced topics or helping peers."
        elif overall_percentage >= 60:
            report += f"\n**Recommendations:**\nGood progress! Focus on areas needing improvement through additional practice."
        else:
            report += f"\n**Recommendations:**\nReview the book content thoroughly and practice more questions in weak areas."
        
        return report
        
    except Exception as e:
        return f"Error generating assessment report: {str(e)}"