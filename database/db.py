import sqlite3
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            remind_at TIMESTAMP NOT NULL,
            sent BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS water_params (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        ph REAL NOT NULL,
        temp REAL NOT NULL,
        ammonia REAL NOT NULL
    )
    """)
    db.commit()

def add_reminder(db, user_id, text, remind_at):
    cur = db.cursor()
    cur.execute(
        "INSERT INTO reminders (user_id, text, remind_at) VALUES (?, ?, ?)",
        (user_id, text, remind_at)
    )
    db.commit()

def fetch_reminders(db, user_id):
    cur = db.cursor()
    cur.execute(
        "SELECT id, text, remind_at, sent FROM reminders WHERE user_id = ?",
        (user_id,)
    )
    return cur.fetchall()

def delete_reminder(db, rid):
    cur = db.cursor()
    cur.execute("DELETE FROM reminders WHERE id = ?", (rid,))
    db.commit()
    return cur.rowcount > 0

def fetch_due_reminders(db, now):
    cur = db.cursor()
    cur.execute(
        "SELECT user_id AS chat_id, text, id FROM reminders"
        " WHERE remind_at <= ? AND sent = 0", (now,)
    )
    rows = cur.fetchall()
    cur.execute(
        "UPDATE reminders SET sent = 1 WHERE remind_at <= ? AND sent = 0", (now,)
    )
    db.commit()
    return [(r["chat_id"], r["text"], r["id"]) for r in rows]