from client.crypto import encrypt_and_sign


def main():
    print("[ Secure Messaging Vault – SEND ]\n")

    # Entrada interactiva del usuario
    message = input("Escribe tu mensaje: ").encode()

    # Cifrar y firmar
    payload = encrypt_and_sign(message)

    print("\n[+] Mensaje cifrado y firmado correctamente")
    print("[*] Listo para transporte o almacenamiento seguro")

    #  No imprimir:
    # - key
    # - ciphertext
    # - signature
    # Esto es intencional (Zero Trust)

    return payload


if __name__ == "__main__":
    main()

