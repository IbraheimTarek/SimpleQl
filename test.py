import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("datasets/train/train_databases/movie_platform/movie_platform.sqlite")

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

cursor.execute("SELECT AVG(movie_popularity) FROM movies WHERE director_name = 'Stanley Kubrick'") 

rows = cursor.fetchall()

for row in rows:
    print(row)
