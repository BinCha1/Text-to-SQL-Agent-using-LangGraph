import sqlite3

# Connect to SQLite DB (or create it)
conn = sqlite3.connect("university.db")
cursor = conn.cursor()

# Drop tables if already exist (for clean re-run)
tables = [
    "Enrollments", "Course_Assignments", "Exams", "Results", "Payments",
    "Library_Records", "Student_Clubs", "Club_Members", "Attendance",
    "Teachers", "Students", "Courses", "Departments", "Admins", "Classrooms"
]
for table in tables:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")

# Create all tables
cursor.executescript("""

CREATE TABLE Departments (
    dept_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    building TEXT,
    head TEXT
);

CREATE TABLE Admins (
    admin_id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    dept_id INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
);

CREATE TABLE Teachers (
    teacher_id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    dept_id INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
);

CREATE TABLE Courses (
    course_id INTEGER PRIMARY KEY,
    title TEXT,
    credit_hours INTEGER,
    dept_id INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
);

CREATE TABLE Students (
    student_id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    dept_id INTEGER,
    enrollment_year INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
);

CREATE TABLE Enrollments (
    enroll_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    course_id INTEGER,
    semester TEXT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

CREATE TABLE Classrooms (
    room_id INTEGER PRIMARY KEY,
    building TEXT,
    room_number TEXT,
    capacity INTEGER,
    dept_id INTEGER,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
);

CREATE TABLE Course_Assignments (
    assign_id INTEGER PRIMARY KEY,
    teacher_id INTEGER,
    course_id INTEGER,
    semester TEXT,
    FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id),
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

CREATE TABLE Exams (
    exam_id INTEGER PRIMARY KEY,
    course_id INTEGER,
    date TEXT,
    location TEXT,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

CREATE TABLE Results (
    result_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    exam_id INTEGER,
    grade TEXT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (exam_id) REFERENCES Exams(exam_id)
);

CREATE TABLE Payments (
    payment_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    amount REAL,
    payment_date TEXT,
    method TEXT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
);

CREATE TABLE Library_Records (
    record_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    book_title TEXT,
    issue_date TEXT,
    return_date TEXT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
);

CREATE TABLE Student_Clubs (
    club_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    advisor TEXT
);

CREATE TABLE Club_Members (
    member_id INTEGER PRIMARY KEY,
    club_id INTEGER,
    student_id INTEGER,
    role TEXT,
    FOREIGN KEY (club_id) REFERENCES Student_Clubs(club_id),
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
);

CREATE TABLE Attendance (
    attendance_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    course_id INTEGER,
    date TEXT,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);
""")

# Insert data using Nepali names (in English script)
cursor.executescript("""

INSERT INTO Departments VALUES
(1, 'Computer Science', 'A Block', 'Dr. Ram Prasad'),
(2, 'Electronics', 'B Block', 'Dr. Shanti Devi'),
(3, 'Business', 'C Block', 'Dr. Gopal Gautam'),
(4, 'Mathematics', 'D Block', 'Dr. Rupa Koirala'),
(5, 'Arts', 'E Block', 'Dr. Laxmi Sharma');

INSERT INTO Admins VALUES
(1, 'Ramesh Karki', 'ramesh@uni.edu', '9800000001', 1),
(2, 'Sunita Thapa', 'sunita@uni.edu', '9800000002', 2),
(3, 'Binod Poudel', 'binod@uni.edu', '9800000003', 3),
(4, 'Rekha Joshi', 'rekha@uni.edu', '9800000004', 4),
(5, 'Kishor Lama', 'kishor@uni.edu', '9800000005', 5);

INSERT INTO Teachers VALUES
(1, 'Suman Adhikari', 'suman@uni.edu', '9811111111', 1),
(2, 'Bina Shrestha', 'bina@uni.edu', '9822222222', 2),
(3, 'Gyanendra Bista', 'gyanendra@uni.edu', '9833333333', 3),
(4, 'Dipendra KC', 'dipendra@uni.edu', '9844444444', 1),
(5, 'Manju Bhattarai', 'manju@uni.edu', '9855555555', 4);

INSERT INTO Courses VALUES
(1, 'Data Structures', 3, 1),
(2, 'Microprocessors', 4, 2),
(3, 'Marketing 101', 2, 3),
(4, 'Linear Algebra', 3, 4),
(5, 'Art History', 2, 5);

INSERT INTO Students VALUES
(1, 'Aayush Shrestha', 'aayush@stu.uni.edu', 1, 2022),
(2, 'Sita Bhandari', 'sita@stu.uni.edu', 2, 2021),
(3, 'Raju Neupane', 'raju@stu.uni.edu', 3, 2022),
(4, 'Pooja Dahal', 'pooja@stu.uni.edu', 4, 2023),
(5, 'Nabin Gurung', 'nabin@stu.uni.edu', 1, 2021);

INSERT INTO Enrollments VALUES
(1, 1, 1, 'Spring'),
(2, 2, 2, 'Fall'),
(3, 3, 3, 'Spring'),
(4, 4, 4, 'Fall'),
(5, 5, 1, 'Spring');

INSERT INTO Classrooms VALUES
(1, 'A Block', 'A101', 40, 1),
(2, 'B Block', 'B202', 30, 2),
(3, 'C Block', 'C303', 25, 3),
(4, 'D Block', 'D404', 20, 4),
(5, 'E Block', 'E505', 15, 5);

INSERT INTO Course_Assignments VALUES
(1, 1, 1, 'Spring'),
(2, 2, 2, 'Fall'),
(3, 3, 3, 'Spring'),
(4, 4, 1, 'Fall'),
(5, 5, 4, 'Spring');

INSERT INTO Exams VALUES
(1, 1, '2025-01-20', 'A101'),
(2, 2, '2025-01-25', 'B202'),
(3, 3, '2025-01-28', 'C303'),
(4, 4, '2025-02-02', 'D404'),
(5, 1, '2025-01-22', 'A101');

INSERT INTO Results VALUES
(1, 1, 1, 'A'),
(2, 2, 2, 'B'),
(3, 3, 3, 'A'),
(4, 4, 4, 'C'),
(5, 5, 5, 'A');

INSERT INTO Payments VALUES
(1, 1, 500.0, '2025-01-10', 'Cash'),
(2, 2, 700.0, '2025-01-15', 'Card'),
(3, 3, 600.0, '2025-01-18', 'Online'),
(4, 4, 550.0, '2025-01-20', 'UPI'),
(5, 5, 500.0, '2025-01-22', 'Card');

INSERT INTO Library_Records VALUES
(1, 1, 'Operating Systems', '2025-01-01', '2025-01-15'),
(2, 2, 'Embedded C', '2025-01-02', '2025-01-18'),
(3, 3, 'Business Ethics', '2025-01-03', '2025-01-16'),
(4, 4, 'Algebra Basics', '2025-01-05', '2025-01-20'),
(5, 5, 'Computer Networks', '2025-01-06', '2025-01-22');

INSERT INTO Student_Clubs VALUES
(1, 'Robotics Club', 'Building Bots and AI', 'Suman Adhikari'),
(2, 'Drama Club', 'Acting and Theatre', 'Bina Shrestha'),
(3, 'Business Club', 'Entrepreneurship', 'Gyanendra Bista'),
(4, 'Math Club', 'Solving Math Problems', 'Dipendra KC'),
(5, 'Art Society', 'Art and Painting', 'Manju Bhattarai');

INSERT INTO Club_Members VALUES
(1, 1, 1, 'President'),
(2, 2, 2, 'Member'),
(3, 3, 3, 'Treasurer'),
(4, 4, 4, 'Vice President'),
(5, 5, 5, 'Member');

INSERT INTO Attendance VALUES
(1, 1, 1, '2025-01-10', 'Present'),
(2, 2, 2, '2025-01-11', 'Absent'),
(3, 3, 3, '2025-01-12', 'Present'),
(4, 4, 4, '2025-01-13', 'Present'),
(5, 5, 1, '2025-01-14', 'Absent');

""")

conn.commit()
conn.close()
print("Database created ")
