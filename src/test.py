import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("D:/University/4th year/2nd Semester/GP/Datasets/BIRD/train/train_databases/movie_platform/movie_platform.sqlite")

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

cursor.execute("SELECT AVG(T1.rating_score), T2.director_name FROM ratings AS T1 INNER JOIN movies AS T2 ON T1.movie_id = T2.movie_id WHERE T2.movie_title = 'When Will I Be Loved'") 


rows = cursor.fetchall()

for row in rows:
    print(row)
