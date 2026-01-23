from client.crypto import encrypt_and_sign


def main():
    # Entrada interactiva del usuario
    message = input("Escribe tu mensaje: ").encode()

    # Cifrar y firmar
    payload = encrypt_and_sign(message)

    print("\n[+] Mensaje cifrado y firmado correctamente")

    # No imprimimos secretos aquí 
    # Se devuelve el payload para transporte / recepción
    return payload


if __name__ == "__main__":
    main()
