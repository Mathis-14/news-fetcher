import sqlite3

conn = sqlite3.connect("news.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM articles;")
count = c.fetchone()[0]
print(f"Number of articles in the database: {count}")

# Fetch and print the first few articles for verification
c.execute("SELECT title, source FROM articles LIMIT 5;")
articles = c.fetchall()
print("\nFirst few articles:")
for article in articles:
    print(f"- {article[0]} (Source: {article[1]})")

conn.close()