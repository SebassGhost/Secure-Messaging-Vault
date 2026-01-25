import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


# ============================================================
# DATABASE CONFIG
# ============================================================

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


# ============================================================
# USERS (Cryptographic identities)
# ============================================================

def create_user(public_key: str, fingerprint: bytes) -> str:
    """
    fingerprint = hash(public_key) generado en el cliente
    """

    query = """
        INSERT INTO users (public_key, fingerprint)
        VALUES (%s, %s)
        RETURNING user_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    public_key,
                    psycopg2.Binary(fingerprint),
                )
            )
            return cur.fetchone()[0]


def get_user_by_fingerprint(fingerprint: bytes):
    query = """
        SELECT user_id, public_key, created_at
        FROM users
        WHERE fingerprint = %s;
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (psycopg2.Binary(fingerprint),))
            return cur.fetchone()


# ============================================================
# CONVERSATIONS
# ============================================================

def create_conversation() -> str:
    query = """
        INSERT INTO conversations DEFAULT VALUES
        RETURNING conversation_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]


def add_participant(conversation_id: str, user_id: str):
    query = """
        INSERT INTO conversation_participants (conversation_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (conversation_id, user_id))


# ============================================================
# MESSAGES (Append-only / E2EE)
# ============================================================

def insert_message(
    conversation_id: str,
    sender_id: str,
    ciphertext: bytes,
    content_hash: bytes,
    signature: bytes,
    prev_hash: bytes | None = None,
):
    """
    content_hash = hash(ciphertext + sender_id + conversation_id + prev_hash)
    signature    = firma(content_hash)
    """

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
                    psycopg2.Binary(content_hash),
                    psycopg2.Binary(prev_hash) if prev_hash else None,
                    psycopg2.Binary(signature),
                )
            )


def get_messages(conversation_id: str):
    """
    Devuelve mensajes en orden cronológico
    (la verificación criptográfica se hace en el cliente)
    """

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


def get_last_message_hash(conversation_id: str) -> bytes | None:
    """
    Útil para encadenar prev_hash
    """

    query = """
        SELECT content_hash
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (conversation_id,))
            row = cur.fetchone()
            return row[0] if row else None
