import os
import uuid
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from .database import get_connection, init_db

load_dotenv()
init_db()

SECRET_KEY = os.getenv("VAULT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("VAULT_SECRET_KEY not set")

fernet = Fernet(SECRET_KEY.encode())


# ======== HELPERS ========

def _encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()


def _decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()


# ======== CRUD ========

def store_message(sender: str, recipient: str, content: str) -> dict:
    message_id = str(uuid.uuid4())
    encrypted = _encrypt(content)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?)",
        (message_id, sender, recipient, encrypted)
    )

    conn.commit()
    conn.close()

    return {
        "id": message_id,
        "sender": sender,
        "recipient": recipient
    }


def get_message(message_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "sender": row[1],
        "recipient": row[2],
        "content": _decrypt(row[3])
    }


def list_messages(recipient: str | None = None):
    conn = get_connection()
    cur = conn.cursor()

    if recipient:
        cur.execute("SELECT * FROM messages WHERE recipient = ?", (recipient,))
    else:
        cur.execute("SELECT * FROM messages")

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "sender": r[1],
            "recipient": r[2],
            "content": _decrypt(r[3])
        }
        for r in rows
    ]


def delete_message(message_id: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    deleted = cur.rowcount > 0

    conn.commit()
    conn.close()

    return deleted
