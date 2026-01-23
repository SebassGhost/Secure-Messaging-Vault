import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey
)
from pathlib import Path


KEYS_DIR = Path("client/keys")
PRIVATE_KEY_FILE = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "public_key.pem"


# =========================
# Key loading
# =========================
def load_private_key() -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(
        PRIVATE_KEY_FILE.read_bytes(),
        password=None
    )


def load_public_key() -> Ed25519PublicKey:
    return serialization.load_pem_public_key(
        PUBLIC_KEY_FILE.read_bytes()
    )


# =========================
# AES-GCM encryption
# =========================
def encrypt_message(plaintext: bytes) -> dict:
    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return {
        "key": key,
        "nonce": nonce,
        "ciphertext": ciphertext
    }


def decrypt_message(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# =========================
# Hash + signature
# =========================
def calculate_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_hash(hash_hex: str) -> bytes:
    private_key = load_private_key()
    return private_key.sign(hash_hex.encode())


def verify_signature(
    hash_hex: str,
    signature: bytes,
    public_key: Ed25519PublicKey
) -> bool:
    try:
        public_key.verify(signature, hash_hex.encode())
        return True
    except Exception:
        return False


# =========================
# High-level operation
# =========================
def encrypt_and_sign(plaintext: bytes) -> dict:
    encrypted = encrypt_message(plaintext)

    content_hash = calculate_hash(encrypted["ciphertext"])
    signature = sign_hash(content_hash)

    return {
        "ciphertext": encrypted["ciphertext"],
        "nonce": encrypted["nonce"],
        "key": encrypted["key"],
        "content_hash": content_hash,
        "signature": signature
    }
