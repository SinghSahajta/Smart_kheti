import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "/tmp/farm.db" if os.getenv("VERCEL") else "data/farm.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_dir = os.path.dirname(DB_PATH) or "."
    os.makedirs(db_dir, exist_ok=True)

    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            location_name TEXT,
            lat REAL,
            lng REAL,
            crop TEXT,
            sowing_date TEXT,
            has_irrigation INTEGER,
            farm_size_acres REAL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            type TEXT,
            severity TEXT,
            message TEXT,
            stage TEXT,
            timestamp TEXT,
            dismissed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            role TEXT,
            message TEXT,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS health_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            image_path TEXT,
            diagnosis TEXT,
            severity TEXT,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS weather_cache (
            id INTEGER PRIMARY KEY,
            data TEXT,
            cached_at TEXT
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized at", DB_PATH)

if __name__ == "__main__":
    init_db()

