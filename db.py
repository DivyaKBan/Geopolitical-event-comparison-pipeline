import sqlite3
from config import DB_PATH

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            url TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            snippet TEXT,
            published TEXT,
            fetched_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            event_key TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT, finished_at TEXT,
            feeds_ok INTEGER, feeds_failed INTEGER,
            new_articles INTEGER, clusters INTEGER,
            analyzed INTEGER, cached INTEGER, failed INTEGER
        );
        """)