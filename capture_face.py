import mysql.connector
from datetime import datetime
import pyinputplus as pyip
import cv2
import face_recognition
import numpy as np
import json
import os

# --- MySQL Database Connection Parameters ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7875328118@Dj',
    'database': 'barcode_attendance_db'
}

# --- Database Functions for Student and Attendance ---

def add_student(student_id):
    print("Adding a new student.")
    # Prompt for student details with validation
    name = pyip.inputStr(prompt="Enter student's name: ")
    email = pyip.inputEmail(prompt="Enter student's email: ")
    branch = pyip.inputStr(prompt="Enter student's branch: ")
    year = pyip.inputInt(prompt="Enter student's year: ", min=1, max=5)  # Assuming 1-5 are valid years

    # Insert new student into the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO student_details (StudentID, Name, Email, Branch, Year)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(insert_query, (student_id, name, email, branch, year))
    conn.commit()
    print("Student added successfully.")
    cursor.close()
    conn.close()

def student_exists(student_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = "SELECT StudentID FROM student_details WHERE StudentID = %s"
    cursor.execute(query, (student_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def handle_attendance(student_id):
    if not student_exists(student_id):
        print(f"Student ID {student_id} not found in student details.")
        if pyip.inputYesNo("Do you want to add this student? (yes/no): ") == 'yes':
            add_student(student_id)
        else:
            return

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Check the latest attendance record for today
    check_query = """
    SELECT RecordID, InTime, OutTime FROM attendance_records
    WHERE StudentID=%s AND DATE(InTime)=CURDATE()
    ORDER BY RecordID DESC LIMIT 1
    """
    cursor.execute(check_query, (student_id,))
    record = cursor.fetchone()

    if record:
        # If latest InTime is recorded and OutTime is not, update OutTime
        if record[1] and not record[2]:
            update_query = "UPDATE attendance_records SET OutTime=%s WHERE RecordID=%s"
            cursor.execute(update_query, (datetime.now(), record[0]))
            print(f"Checked out: {student_id}")
        else:
            # If OutTime is recorded, insert a new InTime for a new cycle
            insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
            cursor.execute(insert_query, (student_id, datetime.now()))
            print(f"Checked in: {student_id}")
    else:
        # If no record found, insert a new record with InTime
        insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
        cursor.execute(insert_query, (student_id, datetime.now()))
        print(f"Checked in: {student_id}")

    conn.commit()
    cursor.close()
    conn.close()

# --- Face Enrollment Database (JSON-based) Utility Functions ---

def load_face_db(db_file="face_db.json"):
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            return json.load(f)
    return {}

def save_face_db(db, db_file="face_db.json"):
    with open(db_file, "w") as f:
        json.dump(db, f)

# --- Face Enrollment Function ---

def enroll_face(student_id, db_file="face_db.json"):
    """
    Enroll a new face with the given student ID.
    Uses the webcam to capture an image, computes its face encoding,
    and stores it in a JSON file.
    """
    db = load_face_db(db_file)
    print(f"Starting face enrollment for student: {student_id}")

    # Adjust the camera index if necessary (here using index 0)
    video_capture = cv2.VideoCapture(0)
    face_encoding = None

    while True:
        ret, frame = video_capture.read()
        if not ret:
            continue

        # Ensure frame has three channels
        if frame.ndim != 3 or frame.shape[2] != 3:
            print("Captured frame does not have 3 channels. Skipping.")
            continue

        cv2.imshow("Face Enrollment - Press 's' to capture", frame)

        # Press 's' to capture the face
        if cv2.waitKey(1) & 0xFF == ord('s'):
            # Convert frame from BGR to RGB and ensure contiguous array
            rgb_frame = np.ascontiguousarray(frame[:, :, ::-1], dtype=np.uint8)
            face_locations = face_recognition.face_locations(rgb_frame)
            if face_locations:
                encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                face_encoding = encodings[0]
                print(f"Face captured for student {student_id}")
                break
            else:
                print("No face detected, please try again.")

    video_capture.release()
    cv2.destroyAllWindows()

    if face_encoding is not None:
        db[student_id] = face_encoding.tolist()
        save_face_db(db, db_file)
        print("Face enrollment successful!")
    else:
        print("Face enrollment failed.")

# --- Face Recognition Function ---

def recognize_face(db_file="face_db.json", tolerance=0.6):
    """
    Recognize a face from the webcam feed.
    Loads enrolled face encodings from the JSON file.
    If a face is recognized, it calls handle_attendance (which checks and updates the MySQL DB).
    """
    db = load_face_db(db_file)
    if not db:
        print("No enrolled faces found. Please enroll a face first.")
        return None

    known_ids = list(db.keys())
    known_encodings = [np.array(db[sid]) for sid in known_ids]

    video_capture = cv2.VideoCapture(0)
    recognized_student_id = None
    print("Starting face recognition. Press 'q' to quit.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            continue

        # Ensure frame is in expected format
        if frame.ndim != 3 or frame.shape[2] != 3:
            continue

        rgb_frame = np.ascontiguousarray(frame[:, :, ::-1], dtype=np.uint8)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
            if True in matches:
                match_index = matches.index(True)
                recognized_student_id = known_ids[match_index]
                cv2.putText(frame, f"ID: {recognized_student_id}", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                print(f"Recognized student: {recognized_student_id}")
                # Use the same logic as barcode scanning to update attendance
                handle_attendance(recognized_student_id)
                video_capture.release()
                cv2.destroyAllWindows()
                return recognized_student_id

        cv2.imshow("Face Recognition - Press 'q' to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    return None

# --- Interactive Menu ---

def main_menu():
    while True:
        print("\nSelect an option:")
        print("1. Enroll a new face")
        print("2. Recognize face and mark attendance")
        print("3. Quit")
        choice = pyip.inputStr(prompt="Enter your choice (1/2/3): ").strip()

        if choice == "1":
            student_id = pyip.inputStr(prompt="Enter the Student ID for enrollment: ").strip()
            if student_id:
                enroll_face(student_id)
            else:
                print("Invalid Student ID. Please try again.")
        elif choice == "2":
            recognized_id = recognize_face()
            if recognized_id:
                print(f"Attendance marked for student {recognized_id}.")
            else:
                print("No face recognized.")
        elif choice == "3":
            print("Exiting the system.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
