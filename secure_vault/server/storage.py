from typing import Dict, List
from datetime import datetime
import uuid

# Almacenamiento en memoria (temporal)
_messages: Dict[str, dict] = {}


def store_message(sender: str, recipient: str, content: str) -> dict:
    """
    Guarda un mensaje y devuelve el objeto completo
    """
    message_id = str(uuid.uuid4())

    message = {
        "id": message_id,
        "sender": sender,
        "recipient": recipient,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    }

    _messages[message_id] = message
    return message


def get_message(message_id: str) -> dict | None:
    """
    Obtiene un mensaje por ID
    """
    return _messages.get(message_id)


def list_messages(recipient: str | None = None) -> List[dict]:
    """
    Lista mensajes (opcionalmente filtrados por destinatario)
    """
    if recipient:
        return [m for m in _messages.values() if m["recipient"] == recipient]
    return list(_messages.values())


def delete_message(message_id: str) -> bool:
    """
    Elimina un mensaje
    """
    return _messages.pop(message_id, None) is not None

