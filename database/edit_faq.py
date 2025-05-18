import sqlite3
import datetime
from database.db import get_db


def add_faq(category, question, answer):
    db = get_db()
    now = datetime.datetime.now().isoformat()
    db.execute(
        "INSERT INTO faq (category, question, answer, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (category, question, answer, now, now)
    )
    db.commit()
    print(f"Додано FAQ: {question}")


def update_faq(faq_id, category, question, answer):
    db = get_db()
    now = datetime.datetime.now().isoformat()
    db.execute(
        "UPDATE faq SET category = ?, question = ?, answer = ?, updated_at = ? WHERE id = ?",
        (category, question, answer, now, faq_id)
    )
    db.commit()
    print(f"Оновлено FAQ: {question}")


def delete_faq(faq_id):
    db = get_db()
    db.execute("DELETE FROM faq WHERE id = ?", (faq_id,))
    db.commit()
    print(f"Видалено FAQ з ID: {faq_id}")


def list_faqs():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, category, question, answer FROM faq")
    faqs = cur.fetchall()
    for faq in faqs:
        print(f"ID: {faq['id']}, Категорія: {faq['category']}, Питання: {faq['question']}, Відповідь: {faq['answer']}")


if __name__ == "__main__":
    # Приклади використання
    list_faqs()  # Показати всі FAQ

    # Додати нове FAQ
    add_faq("Вода", "як очистити воду", "Використовуйте фільтр і кондиціонер для води.")

    # Оновити FAQ (замініть ID на потрібний)
    update_faq(1, "Вода", "як часто міняти воду", "Міняйте 20-30% води щотижня.")

    # Видалити FAQ (замініть ID на потрібний)
    delete_faq(2)

    list_faqs()  # Показати оновлений список