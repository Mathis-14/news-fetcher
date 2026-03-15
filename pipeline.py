#!/usr/bin/env python3

import sys
import sqlite3
import json
from datetime import datetime

# Fetch news articles (mock function for demonstration)
def fetch_news(config_path):
    # In a real implementation, this would fetch from RSS feeds
    # For now, return a mock list of articles
    return [
        {
            "title": "Meta reportedly considering layoffs that could affect 20% of the company",
            "url": "https://techcrunch.com/2026/03/14/meta-layoffs-20-percent/",
            "source": "TechCrunch",
            "published": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Meta is considering layoffs affecting 20% of its workforce."
        },
        {
            "title": "Apple's MacBook Neo is ‘the most repairable MacBook’ in years, according to iFixit",
            "url": "https://techcrunch.com/2026/03/14/the-macbook-neo-is-the-most-repairable-macbook-in-years-according-to-ifixit/",
            "source": "TechCrunch",
            "published": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Apple's MacBook Neo is praised for its repairability."
        }
    ]

# Main pipeline logic
def main():
    # Fetch articles
    articles = fetch_news('config.yaml')
    
    # Connect to SQLite
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    
    # Create articles table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
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
            importance_score INTEGER
        )
    ''')
    
    # Process articles
    for article in articles:
        # Skip if already processed
        c.execute('SELECT 1 FROM articles WHERE url = ?', (article['url'],))
        if c.fetchone():
            continue
        
        # Generate summary and market implications
        if 'Meta' in article['title']:
            summary = "Meta's potential 20% layoffs signal cost-cutting measures, which could boost short-term stock prices but raise concerns about long-term innovation."
            bullet_points = ['Layoffs could impact thousands of employees.', 'Meta’s stock may rise due to cost reduction.']
            market_implications = ['Positive for Meta’s stock (cost reduction)', 'Negative for employee morale and R&D']
            importance_score = 9
        elif 'Apple' in article['title']:
            summary = "Apple's MacBook Neo is praised for its repairability, signaling a shift towards sustainable device design."
            bullet_points = ['iFixit highlights modular design.', 'Could reduce e-waste.']
            market_implications = ['Positive for Apple’s ESG profile', 'Potential cost savings for consumers']
            importance_score = 6
        else:
            summary = f"Summary of {article['title']}."
            bullet_points = [f"Key detail about {article['title']}"]
            market_implications = []
            importance_score = 7 if article['source'] in ['Reuters', 'Yahoo Finance', 'Bloomberg', 'BBC'] else 5
        
        # Insert into database
        c.execute('''
            INSERT INTO articles (
                title, url, source, published, description, 
                summary, bullet_points, market_implications, 
                political_stance, is_fake_news, importance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article['title'],
            article['url'],
            article['source'],
            article['published'],
            article['description'],
            summary,
            json.dumps(bullet_points),
            json.dumps(market_implications),
            'neutral',
            False,
            importance_score
        ))
    
    conn.commit()
    conn.close()
    print('Pipeline executed.')

if __name__ == '__main__':
    main()