import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("datasets/train/train_databases/movie_platform/movie_platform.sqlite")

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

cursor.execute("SELECT CAST(SUM(CASE WHEN T2.rating_score = 5 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM movies AS T1 INNER JOIN ratings AS T2 ON T1.movie_id = T2.movie_id WHERE T1.movie_title = 'Welcome to the Dollhouse'") 



rows = cursor.fetchall()

for row in rows:
    print(row)
