from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'students.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'student-management-system-secret-key')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be a valid integer')


def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll INTEGER NOT NULL,
            marks INTEGER NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def create_users_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def create_attendance_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(student_id, date),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()


create_table()
create_users_table()
create_attendance_table()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/add_student', methods=['POST'])
def add_student():
    name = (request.form.get('student_name') or '').strip()
    roll_value = request.form.get('roll')
    marks_value = request.form.get('marks')

    if not name:
        return 'Student name is required', 400

    try:
        roll = parse_int(roll_value, 'Roll number')
        marks = parse_int(marks_value, 'Marks')
    except ValueError as exc:
        return str(exc), 400

    if marks < 0 or marks > 100:
        return 'Marks must be between 0 and 100', 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO students (name, roll, marks) VALUES (?, ?, ?)',
        (name, roll, marks)
    )

    conn.commit()
    conn.close()

    return f'Student {name} saved successfully!'


@app.route('/students')
def view_students():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM students ORDER BY id')
    students = [tuple(row) for row in cursor.fetchall()]

    conn.close()

    return render_template('students.html', students=students)


@app.route('/delete/<int:id>', methods=['POST'])
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM students WHERE id = ?', (id,))

    conn.commit()
    conn.close()

    return redirect('/students')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = (request.form.get('student_name') or '').strip()
        roll_value = request.form.get('roll')
        marks_value = request.form.get('marks')

        if not name:
            return 'Student name is required', 400

        try:
            roll = parse_int(roll_value, 'Roll number')
            marks = parse_int(marks_value, 'Marks')
        except ValueError as exc:
            return str(exc), 400

        if marks < 0 or marks > 100:
            return 'Marks must be between 0 and 100', 400

        cursor.execute(
            'UPDATE students SET name=?, roll=?, marks=? WHERE id=?',
            (name, roll, marks, id)
        )

        conn.commit()
        conn.close()
        return redirect('/students')

    cursor.execute('SELECT * FROM students WHERE id=?', (id,))
    student = cursor.fetchone()
    conn.close()

    if student is None:
        return 'Student not found', 404

    return render_template('edit.html', student=student)


@app.route('/search', methods=['GET'])
def search_student():
    roll = request.args.get('roll', '').strip()
    students = []

    if roll:
        try:
            roll_number = parse_int(roll, 'Roll number')
        except ValueError:
            return render_template('search.html', students=[], roll=roll, calculate_grade=calculate_grade)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM students WHERE roll = ?', (roll_number,))
        students = [tuple(row) for row in cursor.fetchall()]
        conn.close()

    return render_template(
        'search.html',
        students=students,
        roll=roll,
        calculate_grade=calculate_grade
    )


@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM students')
    total_students = cursor.fetchone()[0]

    cursor.execute('SELECT AVG(marks) FROM students')
    average_marks = cursor.fetchone()[0] or 0

    cursor.execute('SELECT MAX(marks) FROM students')
    highest_marks = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        'dashboard.html',
        total=total_students,
        average=round(average_marks, 2),
        highest=highest_marks
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password')

        if not username or len(password or '') < 8:
            return 'Username required and password must be at least 8 characters', 400

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return 'Username already exists!'
        finally:
            conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT id, password FROM users WHERE username = ?',
            (username,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password or ''):
            session['user_id'] = user['id']
            session['username'] = username
            return redirect('/dashboard')

        return 'Invalid Username or Password', 401

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


def calculate_grade(marks):
    if marks >= 90:
        return 'A+'
    elif marks >= 80:
        return 'A'
    elif marks >= 70:
        return 'B'
    elif marks >= 60:
        return 'C'
    elif marks >= 40:
        return 'D'
    else:
        return 'F'


@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*), AVG(marks), MAX(marks)
        FROM students
    ''')

    total, average, highest = cursor.fetchone()
    conn.close()

    return render_template(
        'admin.html',
        total_students=total,
        average_marks=round(average or 0, 2),
        highest_marks=highest or 0
    )


@app.route('/report/<int:id>')
def report(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
    student = cursor.fetchone()
    conn.close()

    if student is None:
        return 'Student not found', 404

    return render_template(
        'report.html',
        student=student,
        calculate_grade=calculate_grade
    )


@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            student_id = parse_int(request.form.get('student_id'), 'Student ID')
            status = (request.form.get('status') or '').strip()
            date_value = (request.form.get('date') or '').strip()
        except ValueError as exc:
            conn.close()
            return str(exc), 400

        if not date_value or status not in {'Present', 'Absent'}:
            conn.close()
            return 'Attendance date and status are required', 400

        cursor.execute(
            '''
            INSERT INTO attendance (student_id, date, status)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, date)
            DO UPDATE SET status = excluded.status
            ''',
            (student_id, date_value, status)
        )
        conn.commit()
        print('Attendance saved successfully!')

    cursor.execute('SELECT id, name, roll FROM students ORDER BY id')
    students = [tuple(row) for row in cursor.fetchall()]
    conn.close()

    return render_template(
        'attendance.html',
        students=students,
        saved=request.method == 'POST'
    )


@app.route('/attendance_history')
def attendance_history():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT students.name, students.roll,
               attendance.date, attendance.status
        FROM attendance
        JOIN students ON attendance.student_id = students.id
        ORDER BY attendance.date DESC
    ''')

    records = [tuple(row) for row in cursor.fetchall()]
    conn.close()

    return render_template('attendance_history.html', records=records)


@app.route('/attendance_percentage')
def attendance_percentage():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            students.name,
            students.roll,
            COUNT(attendance.id),
            SUM(CASE WHEN attendance.status = 'Present'
                THEN 1 ELSE 0 END),
            SUM(CASE WHEN attendance.status = 'Absent'
                THEN 1 ELSE 0 END)
        FROM students
        LEFT JOIN attendance
        ON students.id = attendance.student_id
        GROUP BY students.id
    ''')

    records = [tuple(row) for row in cursor.fetchall()]
    conn.close()

    return render_template('attendance_percentage.html', records=records)


@app.route('/get_student_attendance/<roll>')
def get_student_attendance(roll):
    if 'user_id' not in session:
        return {'error': 'Please login'}, 401

    try:
        roll_number = parse_int(roll, 'Roll number')
    except ValueError:
        return {'error': 'Invalid roll number'}, 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT students.name,
               COUNT(attendance.id),
               COALESCE(SUM(CASE WHEN attendance.status = 'Present'
                            THEN 1 ELSE 0 END), 0)
        FROM students
        LEFT JOIN attendance
        ON students.id = attendance.student_id
        WHERE students.roll = ?
        GROUP BY students.id
    ''', (roll_number,))

    student = cursor.fetchone()
    conn.close()

    if student is None:
        return {'error': 'Student not found'}, 404

    return {
        'name': student[0],
        'total': student[1],
        'present': student[2]
    }


@app.route('/attendance_simulator', methods=['GET', 'POST'])
def attendance_simulator():
    result = None
    prediction = None
    total = None
    present = None
    future = None

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        try:
            total = parse_int(request.form.get('total'), 'Total classes')
            present = parse_int(request.form.get('present'), 'Present classes')
            future = parse_int(request.form.get('future'), 'Future classes')
        except ValueError as exc:
            return str(exc), 400

        if total < 0 or present < 0 or future < 0 or present > total:
            result = 'Please enter valid attendance numbers.'
        elif total + future == 0:
            result = 'No classes available to calculate.'
        else:
            percentage = ((present + future) / (total + future)) * 100
            result = round(percentage, 2)
            if (present + future) * 4 >= (total + future) * 3:
                prediction = 'You will reach 75% attendance!'
            else:
                needed = 3 * (total + future) - 4 * (present + future)
                prediction = f'Attend {needed} more classes after the planned future classes to reach 75%.'

    return render_template(
        'attendance_simulator.html',
        result=result,
        prediction=prediction,
        total=total,
        present=present,
        future=future
    )


if __name__ == '__main__':
    app.run(debug=True)
