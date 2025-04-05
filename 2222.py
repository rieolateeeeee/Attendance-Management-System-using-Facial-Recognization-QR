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
    name = pyip.inputStr(prompt="Enter student's name: ")
    email = pyip.inputEmail(prompt="Enter student's email: ")
    branch = pyip.inputStr(prompt="Enter student's branch: ")
    year = pyip.inputInt(prompt="Enter student's year: ", min=1, max=5)

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO student_details (StudentID, Name, Email, Branch, Year)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (student_id, name, email, branch, year))
        conn.commit()
        print("Student added successfully.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()

def student_exists(student_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = "SELECT StudentID FROM student_details WHERE StudentID = %s"
        cursor.execute(query, (student_id,))
        result = cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return False
    finally:
        cursor.close()
        conn.close()
    return result is not None

def handle_attendance_with_both(student_id):
    # Check if student exists in the database by barcode scan
    if not student_exists(student_id):
        print(f"Student ID {student_id} not found.")
        if pyip.inputYesNo("Do you want to add this student? (yes/no): ") == 'yes':
            add_student(student_id)
        else:
            return

    # Move to face recognition to confirm the student's identity
    recognized_student_id = recognize_face()

    if recognized_student_id is None:
        print("No face recognized. Attendance cannot be marked.")
        return
    elif recognized_student_id != student_id:
        print(f"Face recognition mismatch! Barcode scanned for {student_id}, but face recognized as {recognized_student_id}.")
        return
    else:
        # Mark attendance
        try:
            conn = mysql.connector.connect(**db_config)
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
                    print(f"Checked out: {student_id}")
                else:
                    insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
                    cursor.execute(insert_query, (student_id, datetime.now()))
                    print(f"Checked in: {student_id}")
            else:
                insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
                cursor.execute(insert_query, (student_id, datetime.now()))
                print(f"Checked in: {student_id}")

            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()

# --- Face Enrollment Database (JSON-based) Utility Functions ---
def load_face_db(db_file="face_db.json"):
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            data = json.load(f)
            for student_id, encodings in data.items():
                data[student_id] = [np.array(encoding) for encoding in encodings]
            return data
    return {}

def save_face_db(db, db_file="face_db.json"):
    for student_id, encodings in db.items():
        db[student_id] = [encoding.tolist() for encoding in encodings]
    with open(db_file, "w") as f:
        json.dump(db, f)

# --- Face Enrollment Function ---
def enroll_face(student_id, db_file="face_db.json"):
    db = load_face_db(db_file)
    print(f"Starting face enrollment for student: {student_id}")

    video_capture = cv2.VideoCapture(0)
    face_encoding = None

    while True:
        ret, frame = video_capture.read()
        if not ret:
            continue

        # Ensure the frame is in 8-bit and has 3 channels (RGB)
        if frame is None or frame.dtype != np.uint8 or frame.shape[2] != 3:
            print("Invalid frame format. Skipping frame.")
            continue

        # Convert BGR (OpenCV default) to RGB for face_recognition library
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        cv2.imshow("Face Enrollment - Press 's' to capture", frame)

        if cv2.waitKey(1) & 0xFF == ord('s'):
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
        if student_id not in db:
            db[student_id] = []
        db[student_id].append(np.array(face_encoding))  # Store numpy array
        save_face_db(db, db_file)
        print("Face enrollment successful!")
    else:
        print("Face enrollment failed.")

# --- Face Deletion Function ---
def delete_face(student_id, db_file="face_db.json"):
    db = load_face_db(db_file)
    if student_id in db:
        del db[student_id]
        save_face_db(db, db_file)
        print(f"Face data for student {student_id} has been deleted.")
    else:
        print(f"No face data found for student {student_id}.")

# --- Face Recognition Function ---
def recognize_face(db_file="face_db.json", tolerance=0.5):
    db = load_face_db(db_file)
    if not db:
        print("No enrolled faces found. Please enroll a face first.")
        return None

    known_ids = list(db.keys())
    known_encodings = [enc for student_id in known_ids for enc in db[student_id]]

    video_capture = cv2.VideoCapture(0)
    recognized_student_id = None
    print("Starting face recognition. Press 'q' to quit.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            continue

        # Ensure the frame is in 8-bit and has 3 channels (RGB)
        if frame is None or frame.dtype != np.uint8 or frame.shape[2] != 3:
            print("Invalid frame format. Skipping frame.")
            continue

        # Convert BGR (OpenCV default) to RGB for face_recognition library
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
            if True in matches:
                match_index = matches.index(True)
                recognized_student_id = known_ids[match_index // len(db[known_ids[match_index]])]
                cv2.putText(frame, f"ID: {recognized_student_id}", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                print(f"Recognized student: {recognized_student_id}")
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
        print("3. Barcode attendance with face recognition")
        print("4. Delete face data")
        print("5. Quit")
        choice = pyip.inputStr(prompt="Enter your choice (1/2/3/4/5): ").strip()

        if choice == "1":
            student_id = pyip.inputStr(prompt="Enter the Student ID to enroll: ")
            enroll_face(student_id)
        elif choice == "2":
            recognized_id = recognize_face()
            if recognized_id:
                handle_attendance_with_both(recognized_id)
        elif choice == "3":
            student_id = pyip.inputStr(prompt="Enter Student ID (from barcode): ")
            handle_attendance_with_both(student_id)
        elif choice == "4":
            student_id = pyip.inputStr(prompt="Enter the Student ID to delete: ")
            delete_face(student_id)
        elif choice == "5":
            break
        else:
            print("Invalid option, please try again.")

if __name__ == "__main__":
    main_menu()