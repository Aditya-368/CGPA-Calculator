import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This makes rows behave like dictionaries
    return conn

def init_db():
    db = get_db()
    cursor = db.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    ''')

    # Create Grading Systems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grading_systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            grade_letter TEXT NOT NULL,
            grade_point REAL NOT NULL,
            UNIQUE(user_id, grade_letter),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    # Create Courses table
    # We add a 'calculation_method' to indicate if it's based on components or final grade.
    # 'final_grade_letter' and 'final_grade_point' will store the resulting grade.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            credits REAL NOT NULL,
            calculation_method TEXT DEFAULT 'final_grade', -- 'final_grade' or 'components'
            final_grade_letter TEXT, -- Stored if method is 'final_grade' or calculated from components
            final_grade_point REAL,  -- Stored if method is 'final_grade' or calculated from components
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    # Create Course Components table
    # This table stores the individual marks for each course.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            weight REAL NOT NULL, -- e.g., 0.20 for 20%
            score REAL,           -- User's score (e.g., 85 for 85%)
            max_score REAL DEFAULT 100.0, -- Max possible score for the component
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
    ''')

    db.commit()
    db.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized.")