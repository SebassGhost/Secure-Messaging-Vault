import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "secure_vault"),
    "user": os.getenv("DB_USER", "vault_user"),
    "password": os.getenv("DB_PASSWORD", "vault_pass"),
}


# ============================================================
# CONTEXTO DE CONEXIÓN
# ============================================================

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
# USERS
# ============================================================

def create_user(public_key: str, fingerprint: bytes) -> str:
    """
    Registra una identidad criptográfica.
    Retorna user_id.
    """
    query = """
        INSERT INTO users (public_key, fingerprint)
        VALUES (%s, %s)
        RETURNING user_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (public_key, fingerprint))
            return cur.fetchone()[0]


def get_user_by_fingerprint(fingerprint: bytes):
    query = """
        SELECT user_id, public_key
        FROM users
        WHERE fingerprint = %s;
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (fingerprint,))
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
# MESSAGES
# ============================================================

def insert_message(
    conversation_id: str,
    sender_id: str,
    ciphertext: bytes,
    content_hash: bytes,
    signature: bytes,
    prev_hash: bytes | None = None
):
    """
    Inserta un mensaje cifrado (append-only).
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
                ),
            )


def get_messages(conversation_id: str):
    """
    Recupera mensajes de una conversación.
    La verificación criptográfica se hace en el cliente.
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
