import base64

from client.crypto import (
    decrypt_message,
    verify_signature,
    load_public_key,
    calculate_hash
)


def receive(payload: dict):
    print("\n[📥] Mensaje recibido")

    # =========================
    # Zero Trust: validación estricta
    # =========================
    required_fields = {
        "ciphertext",
        "nonce",
        "key",
        "content_hash",
        "signature",
    }

    if not isinstance(payload, dict):
        raise Exception("Payload inválido: no es un diccionario")

    if not required_fields.issubset(payload.keys()):
        raise Exception("Payload incompleto o malformado")

    ciphertext = payload["ciphertext"]
    nonce = payload["nonce"]
    encoded_key = payload["key"]
    received_hash = payload["content_hash"]
    signature = payload["signature"]

    # =========================
    # 1. Verificar integridad
    # =========================
    calculated_hash = calculate_hash(ciphertext)

    if calculated_hash != received_hash:
        raise Exception("Hash inválido: el mensaje fue alterado")

    print("[✓] Integridad verificada")

    # =========================
    # 2. Verificar firma
    # =========================
    public_key = load_public_key()

    if not verify_signature(received_hash, signature, public_key):
        raise Exception("Firma inválida: autor no confiable")

    print("[✓] Firma verificada")

    # =========================
    # 3. Decodificar la key
    # =========================
    try:
        key = base64.b64decode(encoded_key)
    except Exception:
        raise Exception("Key inválida: error al decodificar")

    if len(key) not in (16, 24, 32):
        raise Exception(
            f"Key inválida para AES-GCM ({len(key)*8} bits)"
        )

    # =========================
    # 4. Descifrar mensaje
    # =========================
    plaintext = decrypt_message(key, nonce, ciphertext)

    print("\n Mensaje en claro:")
    print(plaintext.decode())

    return plaintext


def main():
    print(
        "[!] Este módulo no se ejecuta solo.\n"
        "Debe recibir un payload desde transporte seguro."
    )


if __name__ == "__main__":
    main()
