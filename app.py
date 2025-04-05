import csv
import io
import os
from flask import Flask, Response, render_template, request, redirect, send_file, send_from_directory, url_for, session,flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = '_bams@#$_'  # Needed for session management

# Update these credentials to your MySQL database cre0000000000005372
# dentials
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7875328118@Dj',
    'database': 'barcode_attendance_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

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

@app.route('/student_details')
def view_student_details():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Assuming you're filtering based on some criteria
    branch = request.args.get('branch', '')
    year = request.args.get('year', '')
    print("Query Year - %s\r\nQuery Branch - %s",year,branch)
    cursor.execute('SELECT DISTINCT Year FROM student_details ORDER BY Year')
    years = [row['Year'] for row in cursor.fetchall()]
    cursor.execute('SELECT DISTINCT Branch FROM student_details ORDER BY Branch')
    branches = [row['Branch'] for row in cursor.fetchall()]
    
    query = 'SELECT * FROM student_details WHERE 1=1'
    query_params = []
    
    if branch:
        query += ' AND Branch = %s'
        query_params.append(branch)
    
    if year:
        query += ' AND Year = %s'
        query_params.append(year)
        
    cursor.execute(query, query_params)
    students = cursor.fetchall()

    conn.close()
    return render_template('student_details.html', students=students, years=years, branches=branches, selected_year=year, selected_branch=branch)



@app.route('/edit_student/<student_id>')
def edit_student(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM student_details WHERE StudentID = %s', (student_id,))
    student = cursor.fetchone()
    conn.close()
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('view_student_details'))
    return render_template('edit_student.html', student=student)

@app.route('/update_student/<student_id>', methods=['POST'])
def update_student(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    name = request.form['name']
    email = request.form['email']
    branch = request.form['branch']
    year = request.form['year']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE student_details SET Name = %s, Email = %s, Branch = %s, Year = %s WHERE StudentID = %s',
        (name, email, branch, year, student_id)
    )
    conn.commit()
    conn.close()
    flash('Student details updated successfully.', 'success')
    return redirect(url_for('view_student_details'))

@app.route('/add_student', methods=['POST'])
def add_student():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    student_id = "\""+request.form['studentId'] +"\""
    name = request.form['name']
    email = request.form['email']
    branch = request.form['branch']
    year = request.form['year']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check for existing student ID or email
    cursor.execute("SELECT * FROM student_details WHERE StudentID = %s OR Email = %s", (student_id, email))
    existing_student = cursor.fetchone()
    if existing_student:
        # Handle the case where the student ID or email already exists
        flash('Student ID or Email already exists.', 'error')
        return redirect(url_for('show_add_student_form'))

    # Insert new student record
    cursor.execute(
        "INSERT INTO student_details (StudentID, Name, Email, Branch, Year) VALUES (%s, %s, %s, %s, %s)",
        (student_id, name, email, branch, year)
    )
    conn.commit()
    conn.close()

    flash('New student added successfully.', 'success')
    return redirect(url_for('view_student_details'))

@app.route('/add_student', methods=['GET'])
def show_add_student_form():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('add_student.html')

@app.route('/upload_students', methods=['POST'])
def upload_students():
    if not request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)
    if file and file.filename.endswith('.csv'):
        conn = get_db_connection()
        cursor = conn.cursor()
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input, None)  # Skip the header row
        for row in csv_input:
            cursor.execute(
                'INSERT INTO student_details (StudentID,Name, Email, Branch, Year) VALUES (%s,%s, %s, %s, %s)',
                row
            )
        conn.commit()
        conn.close()
        flash('Students uploaded successfully.', 'success')
        return redirect(url_for('view_student_details'))
    else:
        flash('Invalid file format', 'error')
        return redirect(request.url)

@app.route('/download_sample_csv')
def download_sample_csv():
    directory = os.getcwd()  # Or specify the directory where you placed the sample CSV
    print(directory)
    directory += "\\Barcode_Attendance_Admin\\"
    print(directory)
    return send_from_directory(directory, 'sample_students.csv', as_attachment=True)

@app.route('/upload_page')
def upload_page():
    return render_template('upload_page.html')

@app.route('/export_records')
def export_records():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    records = get_all_records()

    # Use BytesIO for binary mode
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV header and rows
    writer.writerow(['Record ID', 'Student ID', 'In Time', 'Out Time'])
    for record in records:
        writer.writerow([record['RecordID'], "\""+str(record['StudentID'])+"\"", record['InTime'], record['OutTime']])

    # Seek to start
    output.seek(0)

    # Send the binary stream as a file
    return Response( output.getvalue(),mimetype='text/csv',headers={'Content-Disposition': 'attachment; filename=records.csv'})
def get_all_records():
    if not session.get('logged_in'):
        # This returns an empty list if not logged in, but you might handle this differently.
        # For CSV export, you may want to ensure this check is handled in the route itself.
        return []

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM attendance_records')
    records = cursor.fetchall()
    conn.close()
    return records

def get_filtered_students(year, branch):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base query
    query = "SELECT * FROM student_details WHERE 1=1"
    params = []
    
    # Add year filter to the query if specified
    if year:
        query += " AND Year = %s"
        params.append(year)
    
    # Add branch filter to the query if specified
    if branch:
        query += " AND Branch = %s"
        params.append(branch)
    
    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()
    return students


@app.route('/export_students')
def export_students():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Retrieve filter parameters from the query string
    year = request.args.get('year', '')
    branch = request.args.get('branch', '')
    print("Query Year - %s\r\nQuery Branch - %s",year,branch)
    students = get_filtered_students(year, branch)


    # Use StringIO for text mode, adjust to BytesIO if needed based on your environment
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV header
    writer.writerow(['Student ID', 'Name', 'Email', 'Branch', 'Year'])  # Adjust headers as per your students table

    # Write student rows
    for student in students:
        writer.writerow(["\""+str(student['StudentID'])+"\"", student['Name'], student['Email'], student['Branch'], student['Year']])

    # Seek to start
    output.seek(0)

    # Send the text stream as a file
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=students.csv'})

def get_all_students():
    if not session.get('logged_in'):
        # This returns an empty list if not logged in, but you might handle this differently.
        # For CSV export, you may want to ensure this check is handled in the route itself.
        return []

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM student_details')
    records = cursor.fetchall()     

    conn.close()
    return records

if __name__ == '__main__':
    app.run(debug=True)
