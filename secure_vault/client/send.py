from client.crypto import encrypt_and_sign
from client.identity import load_identity
from server.db import (
    create_user,
    create_conversation,
    add_participant,
    insert_message,
    get_messages,
)

MESSAGE = b"Hola desde Secure Messaging Vault"


def main():
    # 1. Cargar identidad
    identity = load_identity()
    public_key = identity["public_key"]
    private_key = identity["private_key"]
    fingerprint = identity["fingerprint"]

    # 2. Registrar usuario (si no existe)
    user_id = create_user(public_key, fingerprint)

    # 3. Crear conversación
    conversation_id = create_conversation()
    add_participant(conversation_id, user_id)

    # 4. Obtener último hash (encadenamiento)
    previous_messages = get_messages(conversation_id)
    prev_hash = (
        previous_messages[-1]["content_hash"]
        if previous_messages else None
    )

    # 5. Cifrar y firmar
    ciphertext, content_hash, signature = encrypt_and_sign(
        MESSAGE,
        private_key
    )

    # 6. Insertar mensaje
    insert_message(
        conversation_id=conversation_id,
        sender_id=user_id,
        ciphertext=ciphertext,
        content_hash=content_hash,
        signature=signature,
        prev_hash=prev_hash
    )

    print(" Mensaje enviado correctamente")


if __name__ == "__main__":
    main()

