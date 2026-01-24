from client.crypto import (
    decrypt_message,
    verify_signature,
    load_public_key,
    calculate_hash
)


def receive(payload: dict):
    print("\n[📥] Mensaje recibido")

    # =========================
    # Validación mínima (Zero Trust)
    # =========================
    required_fields = {
        "ciphertext",
        "nonce",
        "key",
        "content_hash",
        "signature",
    }

    if not required_fields.issubset(payload):
        raise Exception("Payload incompleto o malformado")

    ciphertext = payload["ciphertext"]
    nonce = payload["nonce"]
    key = payload["key"]              # bytes DIRECTOS
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
    # 3. Descifrar mensaje
    # =========================
    plaintext = decrypt_message(ciphertext, nonce, key)

    print("\n Mensaje en claro:")
    print(plaintext.decode())

    return plaintext


def main():
    print(
        "[!] Este módulo no se ejecuta solo.\n"
        "Debe recibir un payload desde transporte seguro (DB/red)."
    )


if __name__ == "__main__":
    main()
