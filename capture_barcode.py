
import mysql.connector
from datetime import datetime
import pyinputplus as pyip

# Database connection parameters
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7875328118@Dj',
    'database': 'barcode_attendance_db'
}

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
            # If OutTime is also recorded, insert a new InTime for a new cycle
            insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
            cursor.execute(insert_query, (student_id, datetime.now()))
            print(f"Checked in: {student_id}")
    else:
        # If no record found, insert a new record with InTime
        insert_query = "INSERT INTO attendance_records (StudentID, InTime) VALUES (%s, %s)"
        cursor.execute(insert_query, (student_id, datetime.now()))
        print(f"Checked in: {student_id}")

    # Commit changes to the database and close connection
    conn.commit()
    cursor.close()
    conn.close()

# Main loop to accept barcode scans
try:
    while True:
        # Simulate barcode scan with text input
        user_id = pyip.inputStr(prompt="Scan Barcode: ")
        
        # Handle the logic for checking in or out
        handle_attendance(user_id)

except KeyboardInterrupt:
    print("Program Closed by user.")
