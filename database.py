# database.py — SQLite data layer (section 6.1 entities, section 6.2 relationships)
# Uses only the Python standard library sqlite3 — no external dependencies.

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grades.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows accessible by column name
    conn.execute("PRAGMA foreign_keys = ON") # enforce FK constraints
    return conn


def init_db():
    """Create all tables if they do not exist yet."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS student (
                student_id    TEXT PRIMARY KEY,
                full_name     TEXT NOT NULL,
                class_section TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assessment (
                assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT NOT NULL,
                subject       TEXT NOT NULL,
                maximum_mark  REAL NOT NULL,
                weight        REAL NOT NULL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS student_mark (
                mark_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
                assessment_id INTEGER NOT NULL REFERENCES assessment(assessment_id) ON DELETE CASCADE,
                score         REAL,
                updated_at    TEXT DEFAULT (datetime('now')),
                UNIQUE (student_id, assessment_id)
            );
        """)


# ---------------------------------------------------------------------------
# Student CRUD
# ---------------------------------------------------------------------------

def add_student(student_id, full_name, class_section):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO student (student_id, full_name, class_section) VALUES (?, ?, ?)",
            (student_id, full_name, class_section),
        )


def student_exists(student_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM student WHERE student_id = ?", (student_id,)
        ).fetchone()
        return row is not None


def get_student(student_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM student WHERE student_id = ?", (student_id,)
        ).fetchone()


def search_students(query=""):
    with get_connection() as conn:
        if query:
            like = f"%{query}%"
            return conn.execute(
                "SELECT * FROM student WHERE student_id LIKE ? OR full_name LIKE ? ORDER BY full_name",
                (like, like),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM student ORDER BY full_name"
        ).fetchall()


def update_student(student_id, full_name, class_section):
    with get_connection() as conn:
        conn.execute(
            "UPDATE student SET full_name = ?, class_section = ? WHERE student_id = ?",
            (full_name, class_section, student_id),
        )


def delete_student(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM student WHERE student_id = ?", (student_id,))


# ---------------------------------------------------------------------------
# Assessment CRUD
# ---------------------------------------------------------------------------

def add_assessment(title, subject, maximum_mark, weight=1.0):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO assessment (title, subject, maximum_mark, weight) VALUES (?, ?, ?, ?)",
            (title, subject, maximum_mark, weight),
        )
        return cur.lastrowid


def get_all_assessments():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM assessment ORDER BY subject, title"
        ).fetchall()


def get_assessment(assessment_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM assessment WHERE assessment_id = ?", (assessment_id,)
        ).fetchone()


def update_assessment(assessment_id, title, subject, maximum_mark, weight):
    with get_connection() as conn:
        conn.execute(
            "UPDATE assessment SET title=?, subject=?, maximum_mark=?, weight=? WHERE assessment_id=?",
            (title, subject, maximum_mark, weight, assessment_id),
        )


def delete_assessment(assessment_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM assessment WHERE assessment_id = ?", (assessment_id,))


# ---------------------------------------------------------------------------
# Mark CRUD
# ---------------------------------------------------------------------------

def upsert_mark(student_id, assessment_id, score):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO student_mark (student_id, assessment_id, score, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(student_id, assessment_id)
            DO UPDATE SET score = excluded.score, updated_at = excluded.updated_at
        """, (student_id, assessment_id, score))


def get_marks_for_student(student_id):
    """Return all marks joined with assessment details for a given student."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT a.assessment_id, a.title, a.subject, a.maximum_mark, a.weight,
                   sm.score, sm.updated_at
            FROM assessment a
            LEFT JOIN student_mark sm
                   ON a.assessment_id = sm.assessment_id AND sm.student_id = ?
            ORDER BY a.subject, a.title
        """, (student_id,)).fetchall()
