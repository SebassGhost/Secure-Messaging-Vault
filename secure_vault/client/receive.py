from client.crypto import (
    decrypt_message,
    verify_signature,
    load_public_key,
    calculate_hash
)


def receive(payload: dict):
    print("\n[📥] Mensaje recibido")

    ciphertext = payload["ciphertext"]
    nonce = payload["nonce"]
    key = payload["key"]
    received_hash = payload["content_hash"]
    signature = payload["signature"]

    # =========================
    # 1. Verificar integridad
    # =========================
    calculated_hash = calculate_hash(ciphertext)
    if calculated_hash != received_hash:
        raise Exception("Hash inválido: el mensaje fue alterado")

    # =========================
    # 2. Verificar firma
    # =========================
    public_key = load_public_key()
    if not verify_signature(received_hash, signature, public_key):
        raise Exception("Firma inválida: autor no confiable")

    print("[✓] Firma e integridad verificadas")

    # =========================
    # 3. Descifrar mensaje
    # =========================
    plaintext = decrypt_message(key, nonce, ciphertext)

    print("\n Mensaje en claro:")
    print(plaintext.decode())


def main():
    print(
        "[!] Este módulo no se ejecuta solo.\n"
        "Úsalo desde client.interactive o desde el transporte (DB/red)."
    )


if __name__ == "__main__":
    main()
