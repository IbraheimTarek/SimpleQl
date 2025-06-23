import sqlite3
from Params import DB_PATH
# Connect to the SQLite database
conn = sqlite3.connect(DB_PATH)

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

cursor.execute("""SELECT T1.case_number, T1.location, T1.subject_statuses FROM incidents AS T1 INNER JOIN subjects AS T2 ON T1.case_number = T2.case_number WHERE T2.gender = 'M'
""") 



rows = cursor.fetchall()

for row in rows:
    print(row)
