from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from pathlib import Path


KEYS_DIR = Path("client/keys")
PRIVATE_KEY_FILE = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "public_key.pem"


def generate_keys():
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    if PRIVATE_KEY_FILE.exists():
        print("[!] Las claves ya existen.")
        return

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    PRIVATE_KEY_FILE.write_bytes(private_bytes)
    PUBLIC_KEY_FILE.write_bytes(public_bytes)

    print("[+] Claves generadas correctamente.")


def load_private_key():
    return serialization.load_pem_private_key(
        PRIVATE_KEY_FILE.read_bytes(),
        password=None
    )


def load_public_key():
    return serialization.load_pem_public_key(
        PUBLIC_KEY_FILE.read_bytes()
    )


if __name__ == "__main__":
    generate_keys()

