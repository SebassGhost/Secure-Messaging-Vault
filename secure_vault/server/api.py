from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from secure_vault.server import storage

app = FastAPI(title="Secure Messaging Vault")


# ======== MODELOS ========

class MessageIn(BaseModel):
    sender: str
    recipient: str
    content: str


# ======== RUTAS ========

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Secure Vault API running"
    }


@app.post("/messages")
def create_message(data: MessageIn):
    """
    Crear un nuevo mensaje
    """
    return storage.store_message(
        sender=data.sender,
        recipient=data.recipient,
        content=data.content
    )


@app.get("/messages/{message_id}")
def get_message(message_id: str):
    """
    Obtener un mensaje por ID
    """
    message = storage.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@app.get("/messages")
def list_messages(recipient: str | None = None):
    """
    Listar todos los mensajes
    (opcional: filtrar por recipient)
    """
    return storage.list_messages(recipient)


@app.delete("/messages/{message_id}")
def delete_message(message_id: str):
    """
    Eliminar un mensaje
    """
    deleted = storage.delete_message(message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"deleted": True}
