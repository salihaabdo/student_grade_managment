# main.py — CLI entry point for the Student Grade Management System
# No external dependencies — standard library only.
# Run with:  python main.py

import sys
from database import (
    init_db,
    add_student, student_exists, get_student, search_students,
    update_student, delete_student,
    add_assessment, get_all_assessments, get_assessment,
    update_assessment, delete_assessment,
    upsert_mark, get_marks_for_student,
)
from grades import compute_student_result, GRADE_SCALE

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

SEP  = "=" * 60
SEP2 = "-" * 60


def clear_screen():
    # Simple separator instead of os.system("cls") for portability
    print("\n" + SEP)


def header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def pause():
    input("\nPress Enter to continue...")


def confirm(prompt="Are you sure? (y/n): "):
    return input(prompt).strip().lower() == "y"


# ---------------------------------------------------------------------------
# Input helpers with validation
# ---------------------------------------------------------------------------

def prompt_text(label, max_len=None, allow_blank=False):
    while True:
        val = input(f"  {label}: ").strip()
        if not val and not allow_blank:
            print(f"  ! {label} is required.")
            continue
        if max_len and len(val) > max_len:
            print(f"  ! Maximum {max_len} characters.")
            continue
        return val


def prompt_float(label, min_val=None, max_val=None, allow_blank=False):
    while True:
        raw = input(f"  {label}: ").strip()
        if raw == "" and allow_blank:
            return None
        if raw == "" and not allow_blank:
            print(f"  ! {label} is required.")
            continue
        try:
            val = float(raw)
        except ValueError:
            print("  ! Must be a number.")
            continue
        if min_val is not None and val < min_val:
            print(f"  ! Must be >= {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"  ! Must be <= {max_val}.")
            continue
        return val


def validate_score(raw, maximum):
    """Return (score, error). Pure validation, no I/O (FR-04)."""
    if raw.strip() == "":
        return None, "Score is required."
    try:
        score = float(raw)
    except ValueError:
        return None, "Score must be a number."
    if score < 0:
        return None, "Score cannot be negative."
    if score > maximum:
        return None, f"Score cannot exceed the maximum of {maximum}."
    return score, None


# ---------------------------------------------------------------------------
# Table printer
# ---------------------------------------------------------------------------

def print_table(headers, rows, col_widths=None):
    if not rows:
        print("  (no records)")
        return
    if col_widths is None:
        col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows))
                      for i, h in enumerate(headers)]
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("  " + "  ".join("-" * w for w in col_widths))
    for row in rows:
        print(fmt.format(*[str(c) if c is not None else "—" for c in row]))


# ---------------------------------------------------------------------------
# Student menu
# ---------------------------------------------------------------------------

def menu_students():
    while True:
        header("STUDENT MANAGEMENT")
        print("  1. List / search students")
        print("  2. Add student")
        print("  3. Edit student")
        print("  4. Delete student")
        print("  0. Back to main menu")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            list_students()
        elif choice == "2":
            add_student_ui()
        elif choice == "3":
            edit_student_ui()
        elif choice == "4":
            delete_student_ui()
        elif choice == "0":
            break
        else:
            print("  ! Invalid option.")


def list_students():
    header("STUDENT LIST")
    query = input("  Search (ID or name, blank = show all): ").strip()
    students = search_students(query)
    if not students:
        if query:
            print(f"\n  No students found matching '{query}'.")  # TC-10
        else:
            print("\n  No students registered yet.")
    else:
        rows = [(s["student_id"], s["full_name"], s["class_section"]) for s in students]
        print_table(["Student ID", "Full Name", "Class/Section"], rows,
                    col_widths=[12, 30, 16])
        print(f"\n  {len(rows)} record(s) found.")
    pause()


def add_student_ui():
    header("ADD STUDENT")
    student_id = prompt_text("Student ID (unique)", max_len=20)

    # FR-10 / TC-02: prevent duplicate IDs
    if student_exists(student_id):
        print(f"\n  ! Student ID '{student_id}' already exists.")
        pause()
        return

    full_name     = prompt_text("Full name", max_len=120)
    class_section = prompt_text("Class/section", max_len=40)

    add_student(student_id, full_name, class_section)
    print(f"\n  Student '{full_name}' registered successfully.")  # FR-09
    pause()


def edit_student_ui():
    header("EDIT STUDENT")
    student_id = prompt_text("Enter Student ID to edit")
    student = get_student(student_id)
    if not student:
        print(f"\n  ! Student '{student_id}' not found.")
        pause()
        return

    print(f"\n  Current: {student['full_name']} | {student['class_section']}")
    print("  (Press Enter to keep current value)\n")

    full_name = input(f"  Full name [{student['full_name']}]: ").strip()
    if not full_name:
        full_name = student["full_name"]

    class_section = input(f"  Class/section [{student['class_section']}]: ").strip()
    if not class_section:
        class_section = student["class_section"]

    update_student(student_id, full_name, class_section)
    print("\n  Student record updated.")
    pause()


def delete_student_ui():
    header("DELETE STUDENT")
    student_id = prompt_text("Enter Student ID to delete")
    student = get_student(student_id)
    if not student:
        print(f"\n  ! Student '{student_id}' not found.")
        pause()
        return

    print(f"\n  About to delete: {student['full_name']} ({student_id})")
    print("  This will also remove all their marks.")
    if confirm("  Confirm delete? (y/n): "):
        delete_student(student_id)
        print("  Student deleted.")
    else:
        print("  Cancelled.")
    pause()


# ---------------------------------------------------------------------------
# Assessment menu
# ---------------------------------------------------------------------------

def menu_assessments():
    while True:
        header("ASSESSMENT MANAGEMENT")
        print("  1. List assessments")
        print("  2. Add assessment")
        print("  3. Edit assessment")
        print("  4. Delete assessment")
        print("  0. Back to main menu")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            list_assessments()
        elif choice == "2":
            add_assessment_ui()
        elif choice == "3":
            edit_assessment_ui()
        elif choice == "4":
            delete_assessment_ui()
        elif choice == "0":
            break
        else:
            print("  ! Invalid option.")


def list_assessments():
    header("ASSESSMENTS")
    assessments = get_all_assessments()
    rows = [(a["assessment_id"], a["title"], a["subject"],
             a["maximum_mark"], a["weight"]) for a in assessments]
    print_table(["ID", "Title", "Subject", "Max Mark", "Weight"], rows,
                col_widths=[4, 24, 20, 10, 8])
    pause()


def add_assessment_ui():
    header("ADD ASSESSMENT")
    title        = prompt_text("Title", max_len=100)
    subject      = prompt_text("Subject", max_len=80)
    maximum_mark = prompt_float("Maximum mark", min_val=1)
    weight       = prompt_float("Weight (default 1)", min_val=0.1, allow_blank=True)
    if weight is None:
        weight = 1.0

    add_assessment(title, subject, maximum_mark, weight)
    print(f"\n  Assessment '{title}' created.")
    pause()


def edit_assessment_ui():
    header("EDIT ASSESSMENT")
    list_assessments_inline()
    try:
        aid = int(input("  Enter Assessment ID to edit: ").strip())
    except ValueError:
        print("  ! Invalid ID.")
        pause()
        return

    a = get_assessment(aid)
    if not a:
        print(f"\n  ! Assessment {aid} not found.")
        pause()
        return

    print(f"\n  Current: [{a['title']}] {a['subject']} max={a['maximum_mark']} w={a['weight']}")
    print("  (Press Enter to keep current value)\n")

    title = input(f"  Title [{a['title']}]: ").strip() or a["title"]
    subject = input(f"  Subject [{a['subject']}]: ").strip() or a["subject"]

    raw_max = input(f"  Maximum mark [{a['maximum_mark']}]: ").strip()
    maximum_mark = float(raw_max) if raw_max else a["maximum_mark"]

    raw_w = input(f"  Weight [{a['weight']}]: ").strip()
    weight = float(raw_w) if raw_w else a["weight"]

    update_assessment(aid, title, subject, maximum_mark, weight)
    print("\n  Assessment updated.")
    pause()


def delete_assessment_ui():
    header("DELETE ASSESSMENT")
    list_assessments_inline()
    try:
        aid = int(input("  Enter Assessment ID to delete: ").strip())
    except ValueError:
        print("  ! Invalid ID.")
        pause()
        return

    a = get_assessment(aid)
    if not a:
        print(f"\n  ! Assessment {aid} not found.")
        pause()
        return

    print(f"\n  About to delete: {a['title']} ({a['subject']})")
    print("  All student marks for this assessment will be removed.")
    if confirm("  Confirm delete? (y/n): "):
        delete_assessment(aid)
        print("  Assessment deleted.")
    else:
        print("  Cancelled.")
    pause()


def list_assessments_inline():
    assessments = get_all_assessments()
    if assessments:
        rows = [(a["assessment_id"], a["title"], a["subject"], a["maximum_mark"])
                for a in assessments]
        print_table(["ID", "Title", "Subject", "Max"], rows, col_widths=[4, 24, 20, 8])
        print()


# ---------------------------------------------------------------------------
# Marks menu
# ---------------------------------------------------------------------------

def menu_marks():
    while True:
        header("MARK ENTRY")
        print("  1. Enter / update marks for a student")
        print("  0. Back to main menu")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            enter_marks_ui()
        elif choice == "0":
            break
        else:
            print("  ! Invalid option.")


def enter_marks_ui():
    header("ENTER MARKS")
    student_id = prompt_text("Student ID")
    student = get_student(student_id)
    if not student:
        print(f"\n  ! Student '{student_id}' not found.")
        pause()
        return

    assessments = get_all_assessments()
    if not assessments:
        print("\n  ! No assessments exist. Add an assessment first.")
        pause()
        return

    print(f"\n  Student: {student['full_name']} ({student_id}) | {student['class_section']}")
    print("  Enter each score. Press Enter to skip (keeps existing value).\n")

    # Load existing marks
    existing = {
        row["assessment_id"]: row["score"]
        for row in get_marks_for_student(student_id)
        if row["score"] is not None
    }

    saved = 0
    for a in assessments:
        current = existing.get(a["assessment_id"])
        label = (
            f"  {a['title']} ({a['subject']}, max {a['maximum_mark']})"
            + (f" [current: {current}]" if current is not None else "")
        )
        raw = input(label + ": ").strip()
        if raw == "":
            continue

        score, err = validate_score(raw, a["maximum_mark"])
        if err:
            print(f"    ! {err} — skipped.")
            continue

        upsert_mark(student_id, a["assessment_id"], score)
        saved += 1

    if saved:
        print(f"\n  {saved} mark(s) saved.")
    else:
        print("\n  No marks were changed.")
    pause()


# ---------------------------------------------------------------------------
# Results menu
# ---------------------------------------------------------------------------

def menu_results():
    while True:
        header("RESULTS")
        print("  1. View result for a student")
        print("  2. View results for all students")
        print("  0. Back to main menu")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            view_result_ui()
        elif choice == "2":
            view_all_results()
        elif choice == "0":
            break
        else:
            print("  ! Invalid option.")


def view_result_ui():
    header("STUDENT RESULT")
    student_id = prompt_text("Student ID")
    student = get_student(student_id)
    if not student:
        print(f"\n  ! Student '{student_id}' not found.")
        pause()
        return

    _print_result(student)
    pause()


def _print_result(student):
    sid = student["student_id"]
    marks_rows = get_marks_for_student(sid)

    print(f"\n  Student  : {student['full_name']}")
    print(f"  ID       : {sid}")
    print(f"  Class    : {student['class_section']}")
    print(f"\n  {SEP2}")
    print(f"  {'Assessment':<24} {'Subject':<18} {'Score':>6} {'Max':>6} {'Weight':>7}")
    print(f"  {'-'*24} {'-'*18} {'-'*6} {'-'*6} {'-'*7}")

    marks_data = []
    for row in marks_rows:
        score_str = f"{row['score']}" if row["score"] is not None else "—"
        print(f"  {row['title']:<24} {row['subject']:<18} {score_str:>6} {row['maximum_mark']:>6} {row['weight']:>7}")
        marks_data.append({
            "score":        row["score"],
            "maximum_mark": row["maximum_mark"],
            "weight":       row["weight"],
        })

    result = compute_student_result(marks_data)

    print(f"\n  {SEP2}")
    if result["complete"]:
        print(f"  Total     : {result['total_earned']} / {result['total_possible']}")
        print(f"  Percentage: {result['percentage']}%")
        print(f"  Grade     : {result['grade']}")
        status = "PASS" if result["percentage"] >= 60 else "FAIL"
        print(f"  Status    : {status}")
    elif result["grade"] == "Incomplete":
        print("  Status    : INCOMPLETE — one or more scores are missing.")  # TC-13
    else:
        print("  Status    : No assessments available.")
    print(f"  {SEP2}")


def view_all_results():
    header("ALL STUDENT RESULTS")
    students = search_students()
    if not students:
        print("  No students registered.")
        pause()
        return

    rows = []
    for s in students:
        marks_rows = get_marks_for_student(s["student_id"])
        marks_data = [
            {"score": r["score"], "maximum_mark": r["maximum_mark"], "weight": r["weight"]}
            for r in marks_rows
        ]
        result = compute_student_result(marks_data)
        pct   = f"{result['percentage']}%" if result["complete"] else "—"
        grade = result["grade"]
        rows.append((s["student_id"], s["full_name"], s["class_section"], pct, grade))

    print_table(
        ["Student ID", "Full Name", "Class", "Percentage", "Grade"],
        rows,
        col_widths=[12, 28, 14, 12, 8],
    )
    pause()


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu():
    while True:
        header("STUDENT GRADE MANAGEMENT SYSTEM")
        print("  1. Students")
        print("  2. Assessments")
        print("  3. Enter Marks")
        print("  4. View Results")
        print("  0. Exit")
        choice = input("\n  Choice: ").strip()

        if choice == "1":
            menu_students()
        elif choice == "2":
            menu_assessments()
        elif choice == "3":
            menu_marks()
        elif choice == "4":
            menu_results()
        elif choice == "0":
            print("\n  Goodbye.\n")
            sys.exit(0)
        else:
            print("  ! Invalid option.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    main_menu()
