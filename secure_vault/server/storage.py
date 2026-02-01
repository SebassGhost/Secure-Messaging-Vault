import os
import uuid
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# ======== CLAVE ========

SECRET_KEY = os.getenv("VAULT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("VAULT_SECRET_KEY not set")

fernet = Fernet(Fernet.generate_key() if SECRET_KEY == "DEV" else Fernet.generate_key())


# ======== STORAGE EN MEMORIA (por ahora) ========

_MESSAGES: dict[str, dict] = {}


# ======== FUNCIONES ========

def _encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()


def _decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()


def store_message(sender: str, recipient: str, content: str) -> dict:
    message_id = str(uuid.uuid4())

    encrypted_content = _encrypt(content)

    _MESSAGES[message_id] = {
        "id": message_id,
        "sender": sender,
        "recipient": recipient,
        "content": encrypted_content
    }

    return {
        "id": message_id,
        "sender": sender,
        "recipient": recipient
    }


def get_message(message_id: str) -> dict | None:
    msg = _MESSAGES.get(message_id)
    if not msg:
        return None

    return {
        "id": msg["id"],
        "sender": msg["sender"],
        "recipient": msg["recipient"],
        "content": _decrypt(msg["content"])
    }


def list_messages(recipient: str | None = None) -> list[dict]:
    results = []

    for msg in _MESSAGES.values():
        if recipient and msg["recipient"] != recipient:
            continue

        results.append({
            "id": msg["id"],
            "sender": msg["sender"],
            "recipient": msg["recipient"],
            "content": _decrypt(msg["content"])
        })

    return results


def delete_message(message_id: str) -> bool:
    return _MESSAGES.pop(message_id, None) is not None
