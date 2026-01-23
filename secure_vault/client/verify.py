from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


# ============================================================
# HASH
# ============================================================

def compute_hash(data: bytes) -> bytes:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    return digest.finalize()


# ============================================================
# FIRMA
# ============================================================

def verify_signature(
    public_key_pem: str,
    content_hash: bytes,
    signature: bytes
) -> bool:
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode()
    )

    try:
        public_key.verify(
            signature,
            content_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False


# ============================================================
# VERIFICACIÓN DE MENSAJE
# ============================================================

def verify_message(
    message: dict,
    previous_hash: bytes | None,
    public_key_pem: str
) -> bool:
    """
    message = fila recuperada desde la DB
    """

    # 1. Verificar hash de contenido
    recomputed_hash = compute_hash(message["ciphertext"])

    if recomputed_hash != message["content_hash"]:
        raise ValueError("Content hash mismatch")

    # 2. Verificar encadenamiento
    if message["prev_hash"] != previous_hash:
        raise ValueError("Broken message chain")

    # 3. Verificar firma
    if not verify_signature(
        public_key_pem,
        message["content_hash"],
        message["signature"]
    ):
        raise ValueError("Invalid signature")

    return True


# ============================================================
# VERIFICACIÓN DE CONVERSACIÓN COMPLETA
# ============================================================

def verify_conversation(messages: list, public_key_lookup: dict):
    """
    public_key_lookup = { user_id: public_key_pem }
    """
    prev_hash = None

    for msg in messages:
        pub_key = public_key_lookup[msg["sender_id"]]

        verify_message(msg, prev_hash, pub_key)

        prev_hash = msg["content_hash"]

    print("Conversation integrity verified")
