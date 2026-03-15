#!/usr/bin/env python3

import sqlite3
import json
from datetime import datetime

def list_unreviewed_articles():
    """List all unreviewed articles from the database."""
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    
    # Create 'reviewed' column if it doesn't exist
    c.execute("""
        ALTER TABLE articles 
        ADD COLUMN reviewed BOOLEAN DEFAULT FALSE
    """,)
    conn.commit()
    
    # Fetch unreviewed articles
    c.execute("""
        SELECT id, title, source, importance_score, summary, bullet_points, market_implications, url
        FROM articles
        WHERE reviewed = FALSE
        ORDER BY published DESC
    """
    )
    articles = c.fetchall()
    
    if not articles:
        print("No unreviewed articles.")
        return []
    
    print("\n--- Unreviewed Articles ---\n")
    for idx, article in enumerate(articles, 1):
        id_, title, source, importance, summary, bullet_points, market_implications, url = article
        bullet_points = json.loads(bullet_points) if bullet_points else []
        market_implications = json.loads(market_implications) if market_implications else []
        
        print(f"{idx}. **{title}** ({source}, Importance: {importance})")
        print(f"   - *Summary*: {summary}")
        if bullet_points:
            print(f"   - *Key Points*: {', '.join(bullet_points)}")
        if market_implications:
            print(f"   - *Market Impact*: {', '.join(market_implications)}")
        print(f"   - [Read more]({url})")
        print(f"   - ID: {id_}\n")
    
    conn.close()
    return articles

def mark_as_reviewed(article_id, is_relevant=True):
    """Mark an article as reviewed and optionally delete if irrelevant."""
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    
    if not is_relevant:
        # Backup the article before deletion
        c.execute("""
            INSERT INTO articles_deleted (
                title, url, source, published, description, 
                summary, bullet_points, market_implications, 
                political_stance, is_fake_news, importance_score, 
                reviewed, deleted_at
            )
            SELECT 
                title, url, source, published, description, 
                summary, bullet_points, market_implications, 
                political_stance, is_fake_news, importance_score, 
                TRUE, datetime('now')
            FROM articles
            WHERE id = ?
        """, (article_id,))
        
        # Delete the article
        c.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        print(f"Article {article_id} marked as irrelevant and deleted.")
    else:
        # Mark as reviewed
        c.execute("UPDATE articles SET reviewed = TRUE WHERE id = ?", (article_id,))
        print(f"Article {article_id} marked as reviewed.")
    
    conn.commit()
    conn.close()

def create_deleted_table():
    """Create a table to store deleted articles for safeguard."""
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles_deleted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            source TEXT,
            published TEXT,
            description TEXT,
            summary TEXT,
            bullet_points TEXT,
            market_implications TEXT,
            political_stance TEXT,
            is_fake_news BOOLEAN,
            importance_score INTEGER,
            reviewed BOOLEAN,
            deleted_at TEXT
        )
    """
    )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_deleted_table()
    articles = list_unreviewed_articles()
    
    if articles:
        print("Enter the ID of the article to review (or 'q' to quit):")
        while True:
            choice = input("> ").strip()
            if choice.lower() == 'q':
                break
            try:
                article_id = int(choice)
                relevance = input("Is this article relevant? (y/n): ").strip().lower()
                if relevance == 'y':
                    mark_as_reviewed(article_id, is_relevant=True)
                elif relevance == 'n':
                    mark_as_reviewed(article_id, is_relevant=False)
                else:
                    print("Invalid input. Use 'y' or 'n'.")
            except ValueError:
                print("Invalid ID. Enter a number or 'q' to quit.")