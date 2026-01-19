import pymysql
from pymysql.cursors import DictCursor
import os
from dotenv import load_dotenv
from file_handler import read_file_from_path
from chunker import chunk_text

load_dotenv()

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        cursorclass=DictCursor
    )

def initialize_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Create books table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255),
        author VARCHAR(255),
        genre VARCHAR(100),
        file_path TEXT
    )
    """)

    # Create book_chunks table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS book_chunks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        book_id INT,
        chunk_index INT,
        chunk_text TEXT
    )
    """)

    # Create user_answers table (legacy - for backward compatibility)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_answers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        book_id INT,
        chunk_index INT,
        question TEXT,
        answer TEXT,
        review TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # NEW: Create assessment_sessions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        book_id INT,
        total_questions INT,
        questions_completed INT,
        total_score INT,
        max_possible_score INT,
        percentage_score DECIMAL(5,2),
        difficulty_level VARCHAR(20),
        cbse_grade VARCHAR(5),
        performance_level VARCHAR(50),
        session_status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP NULL
    )
    """)

    # NEW: Create detailed question_responses table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS question_responses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        assessment_session_id INT,
        question_number INT,
        question_type VARCHAR(20),
        question_text TEXT,
        user_answer TEXT,
        score INT,
        max_score INT DEFAULT 10,
        feedback TEXT,
        difficulty_level VARCHAR(20),
        chunk_content TEXT,
        follow_up_question TEXT,
        response_time_seconds INT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assessment_session_id) REFERENCES assessment_sessions(id) ON DELETE CASCADE
    )
    """)

    # NEW: Create performance_analytics table for detailed tracking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS performance_analytics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        assessment_session_id INT,
        question_type VARCHAR(20),
        questions_count INT,
        total_score INT,
        average_score DECIMAL(4,2),
        performance_percentage DECIMAL(5,2),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assessment_session_id) REFERENCES assessment_sessions(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

def get_books():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    cur.close()
    conn.close()
    return books

def get_book_chunks(book_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM book_chunks WHERE book_id = %s ORDER BY chunk_index", (book_id,))
    chunks = cur.fetchall()
    cur.close()
    conn.close()
    return chunks

def get_book_content_if_not_chunked(book):
    book_id = book["id"]
    if get_book_chunks(book_id):
        return  # Already chunked

    file_path = book["file_path"]
    text = read_file_from_path(file_path)
    chunks = chunk_text(text)

    conn = get_db_connection()
    cur = conn.cursor()
    for i, chunk in enumerate(chunks):
        cur.execute(
            "INSERT INTO book_chunks (book_id, chunk_index, chunk_text) VALUES (%s, %s, %s)",
            (book_id, i, chunk)
        )
    conn.commit()
    cur.close()
    conn.close()

# NEW ASSESSMENT FUNCTIONS

def create_assessment_session(book_id, total_questions, difficulty_level):
    """Create a new assessment session and return the session ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO assessment_sessions 
        (book_id, total_questions, questions_completed, total_score, max_possible_score, 
         difficulty_level, session_status) 
        VALUES (%s, %s, 0, 0, %s, %s, 'active')
    """, (book_id, total_questions, total_questions * 10, difficulty_level))
    
    session_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return session_id

def save_question_response(session_id, question_number, question_type, question_text, 
                          user_answer, score, feedback, difficulty_level, 
                          chunk_content="", follow_up_question="", response_time=0):
    """Save individual question response"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO question_responses 
        (assessment_session_id, question_number, question_type, question_text, user_answer, 
         score, feedback, difficulty_level, chunk_content, follow_up_question, response_time_seconds)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (session_id, question_number, question_type, question_text, user_answer, 
          score, feedback, difficulty_level, chunk_content, follow_up_question, response_time))
    
    conn.commit()
    cur.close()
    conn.close()

def update_assessment_session(session_id, questions_completed, total_score, percentage_score, 
                            cbse_grade, performance_level, session_status='active'):
    """Update assessment session progress"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if session_status == 'completed':
        cur.execute("""
            UPDATE assessment_sessions 
            SET questions_completed = %s, total_score = %s, percentage_score = %s, 
                cbse_grade = %s, performance_level = %s, session_status = %s,
                completed_at = NOW()
            WHERE id = %s
        """, (questions_completed, total_score, percentage_score, cbse_grade, 
              performance_level, session_status, session_id))
    else:
        cur.execute("""
            UPDATE assessment_sessions 
            SET questions_completed = %s, total_score = %s, percentage_score = %s, 
                cbse_grade = %s, performance_level = %s, session_status = %s
            WHERE id = %s
        """, (questions_completed, total_score, percentage_score, cbse_grade, 
              performance_level, session_status, session_id))
    
    conn.commit()
    cur.close()
    conn.close()

def save_performance_analytics(session_id, question_type, questions_count, 
                             total_score, average_score, performance_percentage):
    """Save performance analytics by question type"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if analytics for this session and question type already exist
    cur.execute("""
        SELECT id FROM performance_analytics 
        WHERE assessment_session_id = %s AND question_type = %s
    """, (session_id, question_type))
    
    existing = cur.fetchone()
    
    if existing:
        # Update existing record
        cur.execute("""
            UPDATE performance_analytics 
            SET questions_count = %s, total_score = %s, average_score = %s, 
                performance_percentage = %s, timestamp = NOW()
            WHERE id = %s
        """, (questions_count, total_score, average_score, performance_percentage, existing['id']))
    else:
        # Insert new record
        cur.execute("""
            INSERT INTO performance_analytics 
            (assessment_session_id, question_type, questions_count, total_score, 
             average_score, performance_percentage)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session_id, question_type, questions_count, total_score, 
              average_score, performance_percentage))
    
    conn.commit()
    cur.close()
    conn.close()

def get_assessment_history(book_id=None, limit=10):
    """Get assessment history for a book or all books"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if book_id:
        cur.execute("""
            SELECT a.*, b.title as book_title 
            FROM assessment_sessions a 
            JOIN books b ON a.book_id = b.id 
            WHERE a.book_id = %s AND a.session_status = 'completed'
            ORDER BY a.completed_at DESC 
            LIMIT %s
        """, (book_id, limit))
    else:
        cur.execute("""
            SELECT a.*, b.title as book_title 
            FROM assessment_sessions a 
            JOIN books b ON a.book_id = b.id 
            WHERE a.session_status = 'completed'
            ORDER BY a.completed_at DESC 
            LIMIT %s
        """, (limit,))
    
    history = cur.fetchall()
    cur.close()
    conn.close()
    return history

def get_detailed_assessment_report(session_id):
    """Get detailed assessment report for a specific session"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get session info
    cur.execute("""
        SELECT a.*, b.title as book_title, b.author 
        FROM assessment_sessions a 
        JOIN books b ON a.book_id = b.id 
        WHERE a.id = %s
    """, (session_id,))
    session_info = cur.fetchone()
    
    if not session_info:
        cur.close()
        conn.close()
        return None
    
    # Get all question responses for this session
    cur.execute("""
        SELECT * FROM question_responses 
        WHERE assessment_session_id = %s 
        ORDER BY question_number
    """, (session_id,))
    questions = cur.fetchall()
    
    # Get performance analytics
    cur.execute("""
        SELECT * FROM performance_analytics 
        WHERE assessment_session_id = %s
    """, (session_id,))
    analytics = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        'session': session_info,
        'questions': questions,
        'analytics': analytics
    }

def get_user_progress_stats(book_id=None):
    """Get comprehensive user progress statistics"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    base_query = """
        SELECT 
            COUNT(*) as total_sessions,
            AVG(percentage_score) as avg_score,
            MAX(percentage_score) as best_score,
            MIN(percentage_score) as lowest_score,
            COUNT(CASE WHEN percentage_score >= 80 THEN 1 END) as excellent_count,
            COUNT(CASE WHEN percentage_score >= 60 AND percentage_score < 80 THEN 1 END) as good_count,
            COUNT(CASE WHEN percentage_score < 60 THEN 1 END) as needs_improvement_count
        FROM assessment_sessions 
        WHERE session_status = 'completed'
    """
    
    if book_id:
        cur.execute(base_query + " AND book_id = %s", (book_id,))
    else:
        cur.execute(base_query)
    
    stats = cur.fetchone()
    cur.close()
    conn.close()
    return stats

def get_question_type_performance(session_id=None, book_id=None):
    """Get performance breakdown by question type"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if session_id:
        cur.execute("""
            SELECT 
                question_type,
                COUNT(*) as total_questions,
                AVG(score) as avg_score,
                SUM(score) as total_score,
                (AVG(score) / 10.0) * 100 as percentage
            FROM question_responses 
            WHERE assessment_session_id = %s
            GROUP BY question_type
        """, (session_id,))
    elif book_id:
        cur.execute("""
            SELECT 
                qr.question_type,
                COUNT(*) as total_questions,
                AVG(qr.score) as avg_score,
                SUM(qr.score) as total_score,
                (AVG(qr.score) / 10.0) * 100 as percentage
            FROM question_responses qr
            JOIN assessment_sessions a ON qr.assessment_session_id = a.id
            WHERE a.book_id = %s AND a.session_status = 'completed'
            GROUP BY qr.question_type
        """, (book_id,))
    else:
        cur.execute("""
            SELECT 
                qr.question_type,
                COUNT(*) as total_questions,
                AVG(qr.score) as avg_score,
                SUM(qr.score) as total_score,
                (AVG(qr.score) / 10.0) * 100 as percentage
            FROM question_responses qr
            JOIN assessment_sessions a ON qr.assessment_session_id = a.id
            WHERE a.session_status = 'completed'
            GROUP BY qr.question_type
        """)
    
    performance = cur.fetchall()
    cur.close()
    conn.close()
    return performance

def get_learning_insights(book_id=None, limit=5):
    """Get learning insights and recommendations"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get recent weak areas (low scoring question types)
    if book_id:
        cur.execute("""
            SELECT 
                qr.question_type,
                AVG(qr.score) as avg_score,
                COUNT(*) as question_count
            FROM question_responses qr
            JOIN assessment_sessions a ON qr.assessment_session_id = a.id
            WHERE a.book_id = %s AND a.session_status = 'completed'
            GROUP BY qr.question_type
            HAVING AVG(qr.score) < 6
            ORDER BY avg_score ASC
            LIMIT %s
        """, (book_id, limit))
    else:
        cur.execute("""
            SELECT 
                qr.question_type,
                AVG(qr.score) as avg_score,
                COUNT(*) as question_count
            FROM question_responses qr
            JOIN assessment_sessions a ON qr.assessment_session_id = a.id
            WHERE a.session_status = 'completed'
            GROUP BY qr.question_type
            HAVING AVG(qr.score) < 6
            ORDER BY avg_score ASC
            LIMIT %s
        """, (limit,))
    
    weak_areas = cur.fetchall()
    
    # Get improvement trends (comparing recent vs older sessions)
    if book_id:
        cur.execute("""
            SELECT 
                AVG(CASE WHEN a.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) 
                    THEN a.percentage_score END) as recent_avg,
                AVG(CASE WHEN a.created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) 
                    THEN a.percentage_score END) as older_avg
            FROM assessment_sessions a
            WHERE a.book_id = %s AND a.session_status = 'completed'
        """, (book_id,))
    else:
        cur.execute("""
            SELECT 
                AVG(CASE WHEN a.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) 
                    THEN a.percentage_score END) as recent_avg,
                AVG(CASE WHEN a.created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) 
                    THEN a.percentage_score END) as older_avg
            FROM assessment_sessions a
            WHERE a.session_status = 'completed'
        """)
    
    trends = cur.fetchone()
    cur.close()
    conn.close()
    
    return {
        'weak_areas': weak_areas,
        'trends': trends
    }

def add_book(title, author, genre, file_path):
    """Add a new book to the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO books (title, author, genre, file_path) 
        VALUES (%s, %s, %s, %s)
    """, (title, author, genre, file_path))
    
    book_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return book_id

def delete_book(book_id):
    """Delete a book and all associated data"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Delete in order due to foreign key constraints
        cur.execute("DELETE FROM question_responses WHERE assessment_session_id IN (SELECT id FROM assessment_sessions WHERE book_id = %s)", (book_id,))
        cur.execute("DELETE FROM performance_analytics WHERE assessment_session_id IN (SELECT id FROM assessment_sessions WHERE book_id = %s)", (book_id,))
        cur.execute("DELETE FROM assessment_sessions WHERE book_id = %s", (book_id,))
        cur.execute("DELETE FROM book_chunks WHERE book_id = %s", (book_id,))
        cur.execute("DELETE FROM user_answers WHERE book_id = %s", (book_id,))
        cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def get_active_session(book_id):
    """Get active assessment session for a book"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM assessment_sessions 
        WHERE book_id = %s AND session_status = 'active'
        ORDER BY created_at DESC 
        LIMIT 1
    """, (book_id,))
    
    session = cur.fetchone()
    cur.close()
    conn.close()
    return session

def cleanup_incomplete_sessions():
    """Clean up sessions that have been inactive for more than 24 hours"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE assessment_sessions 
        SET session_status = 'abandoned'
        WHERE session_status = 'active' 
        AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """)
    
    rows_affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return rows_affected

# Legacy functions for backward compatibility
def save_user_answer(book_id, chunk_index, question, answer, review):
    """Legacy function - saves to old user_answers table"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_answers (book_id, chunk_index, question, answer, review) VALUES (%s, %s, %s, %s, %s)",
        (book_id, chunk_index, question, answer, review)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_user_answers(book_id):
    """Legacy function - gets answers from old user_answers table"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_answers WHERE book_id = %s", (book_id,))
    answers = cur.fetchall()
    cur.close()
    conn.close()
    return answers