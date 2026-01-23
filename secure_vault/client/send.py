from client.crypto import encrypt_and_sign


def main():
    print("[ Secure Messaging Vault – SEND ]\n")

    message = input("Escribe tu mensaje: ").encode()

    payload = encrypt_and_sign(message)

    print("\n[+] Mensaje cifrado y firmado correctamente")
    print("[*] Listo para transporte o almacenamiento seguro")

    return payload


if __name__ == "__main__":
    main()

