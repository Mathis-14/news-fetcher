#!/usr/bin/env python3

import sqlite3
from datetime import datetime

# Connect to SQLite database
conn = sqlite3.connect('news.db')
c = conn.cursor()

# Get today's date in YYYY-MM-DD format
today = datetime.now().strftime('%Y-%m-%d')

# Query for today's high-importance articles (score >= 7)
c.execute('''
    SELECT title, url, source, importance_score, summary, bullet_points, market_implications
    FROM articles
    WHERE date(published) = date('now')
    AND importance_score >= 7
    ORDER BY importance_score DESC
    LIMIT 5
''')

articles = c.fetchall()

# Generate markdown report
markdown_report = f"### Today's Top News ({today})\n\n"

if articles:
    markdown_report += "#### High Importance (Score ≥ 7)\n"
    for idx, article in enumerate(articles, 1):
        title, url, source, score, summary, bullet_points, market_implications = article
        bullet_points = eval(bullet_points)  # Convert JSON string to list
        market_implications = eval(market_implications) if market_implications else []
        
        markdown_report += f"{idx}. **{title}** ({source}, Score: {score})\n"
        markdown_report += f"   - *Summary*: {summary}\n"
        if market_implications:
            markdown_report += f"   - *Market Impact*: {', '.join(market_implications)}\n"
        markdown_report += f"   - [Read more]({url})\n\n"
else:
    markdown_report += "No high-importance news today.\n"

# Query for other notable news (score 5-6)
c.execute('''
    SELECT title, url, source, importance_score
    FROM articles
    WHERE date(published) = date('now')
    AND importance_score BETWEEN 5 AND 6
    ORDER BY importance_score DESC
    LIMIT 5
''')

notable_articles = c.fetchall()

if notable_articles:
    markdown_report += "\n#### Other Notable News\n"
    for title, url, source, score in notable_articles:
        markdown_report += f"- **{title}** ({source}, Score: {score}): [Read more]({url})\n"

conn.close()

# Print the report
print(markdown_report)