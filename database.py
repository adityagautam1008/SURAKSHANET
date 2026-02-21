import sqlite3

conn = sqlite3.connect("suraksha.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS missing_persons(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
age TEXT,
gender TEXT,
last_seen TEXT,
description TEXT,
photo TEXT,
reporter TEXT,
phone TEXT
)
""")

conn.commit()