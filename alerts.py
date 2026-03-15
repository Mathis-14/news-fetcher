#!/usr/bin/env python3

import sqlite3
from datetime import datetime

# Connect to SQLite database
conn = sqlite3.connect('news.db')
c = conn.cursor()

# Get today's date in YYYY-MM-DD format
today = datetime.now().strftime('%Y-%m-%d')

# Query for today's high-importance articles (score >= 8)
c.execute('''
    SELECT title, url, source, importance_score
    FROM articles
    WHERE date(published) = date('now')
    AND importance_score >= 8
    ORDER BY importance_score DESC
''')

articles = c.fetchall()

# Print alerts
if articles:
    for title, url, source, score in articles:
        print(f"🚨 ALERT: {title} (Score: {score}) - {url}")
else:
    print("No high-importance alerts today.")

conn.close()