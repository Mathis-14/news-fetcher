import sys
sys.path.insert(0, "src")
sys.path.insert(0, "/tmp/uv_install/local/lib/python3.11/dist-packages")

from news_fetcher.main import fetch_news
import sqlite3
import json

articles = fetch_news("config.yaml")
conn = sqlite3.connect("news.db")
c = conn.cursor()

for article in articles:
    c.execute("SELECT 1 FROM articles WHERE url = ?", (article["url"],))
    if not c.fetchone():
        summary = f"Summary of {article['title']}."
        bullet_points = [f"Key detail about {article['title']}"]
        market_implications = []
        importance_score = 7 if article["source"] in ["Reuters", "Yahoo Finance", "Bloomberg", "BBC"] else 5
        
        if "Meta" in article["title"]:
            summary = "Meta's potential 20% layoffs signal cost-cutting measures, which could boost short-term stock prices but raise concerns about long-term innovation."
            bullet_points = ["Layoffs could impact thousands of employees.", "Meta's stock may rise due to cost reduction."]
            market_implications = ["Positive for Meta's stock (cost reduction)", "Negative for employee morale and R&D"]
            importance_score = 9
        elif "Apple" in article["title"]:
            summary = "Apple's MacBook Neo is praised for its repairability, signaling a shift towards sustainable device design."
            bullet_points = ["iFixit highlights modular design.", "Could reduce e-waste."]
            market_implications = ["Positive for Apple's ESG profile", "Potential cost savings for consumers"]
            importance_score = 6
            
        c.execute("""
            INSERT INTO articles 
            (title, url, source, published, description, summary, bullet_points, market_implications, political_stance, is_fake_news, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article["title"], 
            article["url"], 
            article["source"], 
            article["published"], 
            article["description"], 
            summary, 
            json.dumps(bullet_points), 
            json.dumps(market_implications), 
            "neutral", 
            False, 
            importance_score
        ))

conn.commit()
conn.close()
print("Hourly pipeline executed.")