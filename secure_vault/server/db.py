import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "secure_vault"),
    "user": os.getenv("DB_USER", "vault_user"),
    "password": os.getenv("DB_PASSWORD", "vault_pass"),
}


@contextmanager
def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================
# USERS
# =========================

def create_user(public_key: str) -> str:
    query = """
        INSERT INTO users (public_key)
        VALUES (%s)
        RETURNING user_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (public_key,))
            return cur.fetchone()[0]


# =========================
# CONVERSATIONS
# =========================

def create_conversation() -> str:
    query = """
        INSERT INTO conversations DEFAULT VALUES
        RETURNING conversation_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]


# =========================
# MESSAGES
# =========================

def insert_message(
    conversation_id: str,
    sender_id: str,
    ciphertext: bytes,
    content_hash: str,
    signature: str,
    prev_hash: str | None = None
):
    query = """
        INSERT INTO messages (
            conversation_id,
            sender_id,
            ciphertext,
            content_hash,
            prev_hash,
            signature
        )
        VALUES (%s, %s, %s, %s, %s, %s);
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    conversation_id,
                    sender_id,
                    psycopg2.Binary(ciphertext),
                    content_hash,
                    prev_hash,
                    signature,
                )
            )


def get_messages(conversation_id: str):
    query = """
        SELECT
            message_id,
            sender_id,
            ciphertext,
            content_hash,
            prev_hash,
            signature,
            created_at
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC;
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (conversation_id,))
            return cur.fetchall()
