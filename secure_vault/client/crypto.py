import os
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey
)


# ============================================================
# KEY PATHS
# ============================================================

KEYS_DIR = Path("client/keys")
PRIVATE_KEY_FILE = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "public_key.pem"


# ============================================================
# KEY LOADING
# ============================================================

def load_private_key() -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(
        PRIVATE_KEY_FILE.read_bytes(),
        password=None
    )


def load_public_key() -> Ed25519PublicKey:
    return serialization.load_pem_public_key(
        PUBLIC_KEY_FILE.read_bytes()
    )


# ============================================================
# AES-GCM ENCRYPTION
# ============================================================

def encrypt_message(plaintext: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Retorna:
    - ciphertext
    - nonce
    - symmetric key
    """
    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return ciphertext, nonce, key


def decrypt_message(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ============================================================
# HASH + SIGNATURE
# ============================================================

def calculate_hash(data: bytes) -> bytes:
    """
    Hash binario (NO hex string).
    Mejor para firmas y DB.
    """
    return hashlib.sha256(data).digest()


def sign_hash(content_hash: bytes) -> bytes:
    private_key = load_private_key()
    return private_key.sign(content_hash)


def verify_signature(
    content_hash: bytes,
    signature: bytes,
    public_key: Ed25519PublicKey
) -> bool:
    try:
        public_key.verify(signature, content_hash)
        return True
    except Exception:
        return False


# ============================================================
# HIGH-LEVEL OPERATION
# ============================================================

def encrypt_and_sign(plaintext: bytes) -> dict:
    """
    Operación atómica:
    - cifra
    - hashea el ciphertext
    - firma el hash
    """
    ciphertext, nonce, key = encrypt_message(plaintext)

    content_hash = calculate_hash(ciphertext)
    signature = sign_hash(content_hash)

    return {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "key": key,
        "content_hash": content_hash,
        "signature": signature
    }
