import csv
import io
import os
from flask import Flask, Response, render_template, request, redirect, send_file, send_from_directory, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import cv2
import face_recognition
import numpy as np
from datetime import datetime
import pyinputplus as pyip

app = Flask(__name__)
app.secret_key = '_bams@#$_'  # Needed for session management

# Update these credentials to your MySQL database credentials
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7875328118@Dj',
    'database': 'barcode_attendance_db'
}

# --- MySQL Database Connection ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

# --- Flask Routes ---
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('view_attendance_records'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Add your logic to verify username and password, e.g., against a database
        if username != 'admin' or password != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            session['logged_in'] = True
            return redirect(url_for('view_attendance_records'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/attendance_records')
def view_attendance_records():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM attendance_records')
    records = cursor.fetchall()
    conn.close()
    return render_template('attendance_records.html', records=records)

# --- Barcode Attendance ---
@app.route('/barcode_attendance', methods=['POST'])
def barcode_attendance():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    student_id = request.form['student_id']
    if student_exists(student_id):
        handle_attendance(student_id)
        flash(f'Attendance marked for Student ID {student_id}.', 'success')
    else:
        flash('Student not found. Please try again.', 'error')
    
    return redirect(url_for('view_attendance_records'))

@app.route('/barcode', methods=['GET', 'POST'])
def barcode_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        return barcode_attendance()
    return render_template('barcode.html')

# --- Face Recognition Attendance ---
@app.route('/recognize_face_attendance', methods=['POST'])
def recognize_face_attendance():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    recognized_id = recognize_face()
    if recognized_id:
        flash(f'Attendance marked for Student ID {recognized_id}.', 'success')
    else:
        flash('No face recognized.', 'error')
    
    return redirect(url_for('view_attendance_records'))

@app.route('/face_recognition', methods=['GET', 'POST'])
def face_recognition_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        return recognize_face_attendance()
    return render_template('face_recognition.html')

# --- Helper Functions (from Attendance System) ---
def student_exists(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT StudentID FROM student_details WHERE StudentID = %s", (student_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def handle_attendance(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    check_query = """
    SELECT RecordID, InTime, OutTime FROM attendance_records
    WHERE StudentID=%s AND DATE(InTime)=CURDATE()
    ORDER BY RecordID DESC LIMIT 1
    """
    cursor.execute(check_query, (student_id,))
    record = cursor.fetchone()

    if record:
        if record[1] and not record[2]:
            update_query = "UPDATE attendance_records SET OutTime=%s WHERE RecordID=%s"
            cursor.execute(update_query, (datetime.now(), record[0]))
        else:
            insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
            cursor.execute(insert_query, (student_id, datetime.now()))
    else:
        insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
        cursor.execute(insert_query, (student_id, datetime.now()))

    conn.commit()
    cursor.close()
    conn.close()

def recognize_face(db_file="face_db.json", tolerance=0.6):
    known_ids = []
    known_encodings = []

    # Load the face database (JSON)
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            db = json.load(f)
            known_ids = list(db.keys())
            known_encodings = [np.array(db[sid]) for sid in known_ids]
    
    if not known_encodings:
        return None

    video_capture = cv2.VideoCapture(0)
    recognized_student_id = None

    while True:
        ret, frame = video_capture.read()
        if not ret:
            continue

        rgb_frame = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
            if True in matches:
                match_index = matches.index(True)
                recognized_student_id = known_ids[match_index]
                handle_attendance(recognized_student_id)
                video_capture.release()
                cv2.destroyAllWindows()
                return recognized_student_id

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    return None

# --- Start the Flask App ---
if __name__ == '__main__':
    app.run(debug=True)
