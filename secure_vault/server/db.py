import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional


# ============================================================
# DATABASE CONFIG
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),   # 👈 int, no str
    "dbname": os.getenv("DB_NAME", "secure_vault"),
    "user": os.getenv("DB_USER", "vault"),
    "password": os.getenv("DB_PASSWORD", "vaultpass"),
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
# USERS (Cryptographic identities only)
# ============================================================

def create_user(public_key: str, fingerprint: bytes) -> Optional[str]:
    """
    fingerprint = hash(public_key) generado en el cliente
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (public_key, fingerprint)
                VALUES (%s, %s)
                ON CONFLICT (fingerprint) DO NOTHING
                RETURNING user_id;
                """,
                (
                    public_key,
                    psycopg2.Binary(fingerprint),
                )
            )
            row = cur.fetchone()
            if row:
                return row[0]

            cur.execute(
                """
                SELECT user_id
                FROM users
                WHERE fingerprint = %s;
                """,
                (psycopg2.Binary(fingerprint),)
            )
            existing = cur.fetchone()
            return existing[0] if existing else None


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


def get_user_by_id(user_id: str):
    query = """
        SELECT user_id, public_key, created_at
        FROM users
        WHERE user_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            return cur.fetchone()


# ============================================================
# CONVERSATIONS
# ============================================================

def create_conversation() -> str:
    """
    UUID generado EXCLUSIVAMENTE por PostgreSQL
    """

    query = """
        INSERT INTO conversations
        DEFAULT VALUES
        RETURNING conversation_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]


def conversation_exists(conversation_id: str) -> bool:
    query = """
        SELECT 1
        FROM conversations
        WHERE conversation_id = %s
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (conversation_id,))
            return cur.fetchone() is not None


def add_participant(conversation_id: str, user_id: str):
    query = """
        INSERT INTO conversation_participants (conversation_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (conversation_id, user_id))


def list_conversations_for_user(user_id: str):
    query = """
        SELECT c.conversation_id, c.created_at
        FROM conversations c
        INNER JOIN conversation_participants cp
            ON cp.conversation_id = c.conversation_id
        WHERE cp.user_id = %s
        ORDER BY c.created_at DESC;
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            return cur.fetchall()


def is_participant(conversation_id: str, user_id: str) -> bool:
    query = """
        SELECT 1
        FROM conversation_participants
        WHERE conversation_id = %s AND user_id = %s
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (conversation_id, user_id))
            return cur.fetchone() is not None


# ============================================================
# MESSAGES (Append-only / E2EE)
# ============================================================

def insert_message(
    conversation_id: str,
    sender_id: str,
    ciphertext: bytes,
    content_hash: bytes,
    signature: bytes,
    prev_hash: Optional[bytes] = None,
    client_timestamp: Optional[str] = None,
    key_id: Optional[str] = None,
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
            signature,
            client_timestamp,
            key_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING message_id, created_at;
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
                    client_timestamp,
                    key_id,
                )
            )
            return cur.fetchone()


def get_messages(
    conversation_id: str,
    after_message_id: Optional[str] = None,
    limit: int = 50,
):
    """
    Devuelve mensajes en orden cronológico
    (la verificación criptográfica se hace en el cliente)
    """

    if after_message_id:
        query = """
            SELECT
                message_id,
                sender_id,
                ciphertext,
                content_hash,
                prev_hash,
                signature,
                client_timestamp,
                key_id,
                created_at
            FROM messages
            WHERE conversation_id = %s
              AND created_at > (
                  SELECT created_at
                  FROM messages
                  WHERE message_id = %s
              )
            ORDER BY created_at ASC
            LIMIT %s;
        """
        params = (conversation_id, after_message_id, limit)
    else:
        query = """
            SELECT
                message_id,
                sender_id,
                ciphertext,
                content_hash,
                prev_hash,
                signature,
                client_timestamp,
                key_id,
                created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            LIMIT %s;
        """
        params = (conversation_id, limit)

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def message_exists(conversation_id: str, message_id: str) -> bool:
    query = """
        SELECT 1
        FROM messages
        WHERE conversation_id = %s AND message_id = %s
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (conversation_id, message_id))
            return cur.fetchone() is not None


def get_last_message_hash(conversation_id: str) -> Optional[bytes]:
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
