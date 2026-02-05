import base64
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from server import db

app = FastAPI(title="Secure Messaging Vault")


# ======== MODELOS ========

class ParticipantIn(BaseModel):
    user_id: str


class UserIn(BaseModel):
    public_key: str
    fingerprint: str


class UserKeyIn(BaseModel):
    key_id: str
    public_key: str
    fingerprint: str
    is_primary: Optional[bool] = False


class MessageIn(BaseModel):
    sender_id: str
    ciphertext: str
    content_hash: str
    prev_hash: Optional[str] = None
    signature: str
    client_timestamp: Optional[str] = None
    key_id: Optional[str] = None


# ======== HELPERS ========

def _b64_to_bytes(value: Optional[str]) -> Optional[bytes]:
    if value is None:
        return None
    try:
        return base64.b64decode(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 payload") from exc


def _bytes_to_b64(value: Optional[bytes]) -> Optional[str]:
    if value is None:
        return None
    return base64.b64encode(value).decode()

def _require_uuid(value: str, label: str):
    try:
        uuid.UUID(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {label} UUID") from exc


# ======== RUTAS ========

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Secure Vault API running"
    }


@app.post("/users")
def create_user(data: UserIn):
    fingerprint_bytes = _b64_to_bytes(data.fingerprint)
    user_id = db.create_user(data.public_key, fingerprint_bytes)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create or fetch user")
    return {"user_id": user_id, "key_id": "primary"}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    _require_uuid(user_id, "user_id")
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user["user_id"],
        "public_key": user["public_key"],
        "created_at": user["created_at"],
    }


@app.get("/users/by-fingerprint")
def get_user_by_fingerprint(fingerprint: str = Query(...)):
    user = db.get_user_by_fingerprint(_b64_to_bytes(fingerprint))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user["user_id"],
        "public_key": user["public_key"],
        "created_at": user["created_at"],
    }


@app.post("/users/{user_id}/keys")
def add_user_key(user_id: str, data: UserKeyIn):
    _require_uuid(user_id, "user_id")
    if not data.key_id.strip():
        raise HTTPException(status_code=400, detail="key_id cannot be empty")
    if not db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")

    key_id = db.add_user_key(
        user_id=user_id,
        key_id=data.key_id,
        public_key=data.public_key,
        fingerprint=_b64_to_bytes(data.fingerprint),
        is_primary=bool(data.is_primary),
    )
    if not key_id:
        raise HTTPException(status_code=409, detail="Key already exists")
    return {"key_id": key_id}


@app.get("/users/{user_id}/keys")
def list_user_keys(user_id: str):
    _require_uuid(user_id, "user_id")
    if not db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    keys = db.list_user_keys(user_id)
    return [
        {
            "key_id": k["key_id"],
            "public_key": k["public_key"],
            "fingerprint": _bytes_to_b64(k["fingerprint"]),
            "is_primary": k["is_primary"],
            "created_at": k["created_at"],
            "revoked_at": k["revoked_at"],
        }
        for k in keys
    ]


@app.post("/users/{user_id}/keys/{key_id}/revoke")
def revoke_user_key(user_id: str, key_id: str):
    _require_uuid(user_id, "user_id")
    if not db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    revoked = db.revoke_user_key(user_id, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return {"revoked": True}


@app.post("/users/{user_id}/keys/{key_id}/primary")
def set_primary_key(user_id: str, key_id: str):
    _require_uuid(user_id, "user_id")
    if not db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    updated = db.set_primary_key(user_id, key_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Key not found or revoked")
    return {"primary": True}


@app.post("/conversations")
def create_conversation():
    conversation_id = db.create_conversation()
    return {"conversation_id": conversation_id}


@app.post("/conversations/{conversation_id}/participants")
def add_participant(conversation_id: str, data: ParticipantIn):
    _require_uuid(conversation_id, "conversation_id")
    _require_uuid(data.user_id, "user_id")
    if not db.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not db.get_user_by_id(data.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.add_participant(conversation_id, data.user_id)
    return {"added": True}


@app.get("/users/{user_id}/conversations")
def list_conversations(user_id: str):
    _require_uuid(user_id, "user_id")
    if not db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return db.list_conversations_for_user(user_id)


@app.post("/conversations/{conversation_id}/messages")
def create_message(conversation_id: str, data: MessageIn):
    _require_uuid(conversation_id, "conversation_id")
    _require_uuid(data.sender_id, "sender_id")
    if not db.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not db.is_participant(conversation_id, data.sender_id):
        raise HTTPException(status_code=403, detail="Sender is not a participant")

    key_id = data.key_id or "primary"
    key = db.get_active_key(data.sender_id, key_id)
    if not key:
        raise HTTPException(status_code=400, detail="Invalid or revoked key_id")

    message_id, created_at = db.insert_message(
        conversation_id=conversation_id,
        sender_id=data.sender_id,
        ciphertext=_b64_to_bytes(data.ciphertext),
        content_hash=_b64_to_bytes(data.content_hash),
        prev_hash=_b64_to_bytes(data.prev_hash),
        signature=_b64_to_bytes(data.signature),
        client_timestamp=data.client_timestamp,
        key_id=key_id,
    )

    return {
        "message_id": message_id,
        "created_at": created_at,
    }


@app.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    after: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    _require_uuid(conversation_id, "conversation_id")
    if not db.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    if after:
        _require_uuid(after, "message_id")
        if not db.message_exists(conversation_id, after):
            raise HTTPException(status_code=400, detail="Invalid 'after' message_id")
    rows = db.get_messages(
        conversation_id=conversation_id,
        after_message_id=after,
        limit=limit,
    )
    return [
        {
            "message_id": r["message_id"],
            "sender_id": r["sender_id"],
            "ciphertext": _bytes_to_b64(r["ciphertext"]),
            "content_hash": _bytes_to_b64(r["content_hash"]),
            "prev_hash": _bytes_to_b64(r["prev_hash"]),
            "signature": _bytes_to_b64(r["signature"]),
            "client_timestamp": r["client_timestamp"],
            "key_id": r["key_id"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.get("/conversations/{conversation_id}/messages/last-hash")
def get_last_hash(conversation_id: str):
    _require_uuid(conversation_id, "conversation_id")
    if not db.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    last_hash = db.get_last_message_hash(conversation_id)
    return {"content_hash": _bytes_to_b64(last_hash)}
