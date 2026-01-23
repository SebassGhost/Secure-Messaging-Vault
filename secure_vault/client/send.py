from client.crypto import encrypt_and_sign


def main():
    message = b"Hola desde Secure Messaging Vault"

    payload = encrypt_and_sign(message)

    print("[+] Mensaje preparado para envío\n")

    print("Ciphertext:", payload["ciphertext"].hex())
    print("Nonce:", payload["nonce"].hex())
    print("AES Key:", payload["key"].hex())
    print("Hash:", payload["content_hash"])
    print("Signature:", payload["signature"].hex())


if __name__ == "__main__":
    main()

