import json
import sqlite3
import datetime
from database.db import get_db


def migrate_faq_json_to_sqlite(json_path):
    db = get_db()
    with open(json_path, "r", encoding="utf-8") as f:
        faq_data = json.load(f)

    now = datetime.datetime.now().isoformat()
    for item in faq_data:
        db.execute(
            "INSERT INTO faq (category, question, answer, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (item["category"], item["question"], item["answer"], now, now)
        )
    db.commit()
    print("Міграція завершена.")


if __name__ == "__main__":
    migrate_faq_json_to_sqlite("data/faq.json")