import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Optional

import httpx

from client import crypto, identity


STATE_FILE = Path("client/state.json")


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode()


def b64d(text: str) -> bytes:
    return base64.b64decode(text)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def api_client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=10)


def ensure_keys() -> None:
    if not crypto.PRIVATE_KEY_FILE.exists() or not crypto.PUBLIC_KEY_FILE.exists():
        identity.main()


def cmd_register(args: argparse.Namespace) -> None:
    ensure_keys()
    public_key = crypto.PUBLIC_KEY_FILE.read_text(encoding="utf-8")
    fingerprint = hashlib.sha256(public_key.encode()).digest()

    payload = {
        "public_key": public_key,
        "fingerprint": b64e(fingerprint),
    }

    with api_client(args.api) as client:
        resp = client.post("/users", json=payload)
        resp.raise_for_status()
        data = resp.json()

    state = load_state()
    state["user_id"] = data["user_id"]
    save_state(state)
    print(f"[+] Registrado: user_id={data['user_id']} key_id={data.get('key_id')}")


def cmd_create_conversation(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.post("/conversations")
        resp.raise_for_status()
        data = resp.json()
    print(f"[+] conversation_id={data['conversation_id']}")


def cmd_add_participant(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.post(
            f"/conversations/{args.conversation_id}/participants",
            json={"user_id": args.user_id},
        )
        resp.raise_for_status()
    print("[+] participante agregado")


def cmd_last_hash(args: argparse.Namespace) -> Optional[bytes]:
    with api_client(args.api) as client:
        resp = client.get(f"/conversations/{args.conversation_id}/messages/last-hash")
        resp.raise_for_status()
        data = resp.json()
    if not data.get("content_hash"):
        return None
    return b64d(data["content_hash"])


def cmd_send_message(args: argparse.Namespace) -> None:
    ensure_keys()
    state = load_state()
    user_id = args.user_id or state.get("user_id")
    if not user_id:
        raise SystemExit("Falta user_id. Usa --user-id o ejecuta register.")

    prev_hash = cmd_last_hash(args)
    encrypted = crypto.encrypt_message(args.message.encode())
    ciphertext = encrypted["ciphertext"]

    content_hash = hashlib.sha256(
        ciphertext
        + user_id.encode()
        + args.conversation_id.encode()
        + (prev_hash or b"")
    ).digest()
    signature = crypto.sign_hash(content_hash)

    payload = {
        "sender_id": user_id,
        "ciphertext": b64e(ciphertext),
        "content_hash": b64e(content_hash),
        "prev_hash": b64e(prev_hash) if prev_hash else None,
        "signature": b64e(signature),
        "client_timestamp": args.client_timestamp,
        "key_id": args.key_id or "primary",
    }

    with api_client(args.api) as client:
        resp = client.post(
            f"/conversations/{args.conversation_id}/messages",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    # Store local key/nonce for demo decryption (same device)
    state.setdefault("message_keys", {})
    state["message_keys"][data["message_id"]] = {
        "key": b64e(encrypted["key"]),
        "nonce": b64e(encrypted["nonce"]),
    }
    save_state(state)
    print(f"[+] mensaje enviado: {data['message_id']}")


def cmd_list_messages(args: argparse.Namespace) -> None:
    params = {}
    if args.after:
        params["after"] = args.after
    if args.limit:
        params["limit"] = args.limit

    with api_client(args.api) as client:
        resp = client.get(
            f"/conversations/{args.conversation_id}/messages",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    print(json.dumps(data, indent=2))


def cmd_mark_delivered(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.post(
            f"/messages/{args.message_id}/delivered",
            json={"user_id": args.user_id},
        )
        resp.raise_for_status()
    print("[+] delivered")


def cmd_mark_read(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.post(
            f"/messages/{args.message_id}/read",
            json={"user_id": args.user_id},
        )
        resp.raise_for_status()
    print("[+] read")


def cmd_message_status(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.get(f"/messages/{args.message_id}/status")
        resp.raise_for_status()
        data = resp.json()
    print(json.dumps(data, indent=2))


def cmd_add_attachment(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.post(
            f"/messages/{args.message_id}/attachments",
            json={
                "uploader_id": args.user_id,
                "ciphertext": args.ciphertext,
                "content_hash": args.content_hash,
                "signature": args.signature,
                "meta_ciphertext": args.meta_ciphertext,
                "meta_hash": args.meta_hash,
                "meta_signature": args.meta_signature,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    print(json.dumps(data, indent=2))


def cmd_list_attachments(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.get(
            f"/messages/{args.message_id}/attachments",
            params={"user_id": args.user_id},
        )
        resp.raise_for_status()
        data = resp.json()
    print(json.dumps(data, indent=2))


def cmd_get_attachment(args: argparse.Namespace) -> None:
    with api_client(args.api) as client:
        resp = client.get(
            f"/attachments/{args.attachment_id}",
            params={"user_id": args.user_id},
        )
        resp.raise_for_status()
        data = resp.json()
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Secure Vault CLI")
    parser.add_argument("--api", default="http://localhost:8000")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("register")

    c1 = sub.add_parser("create-conversation")

    c2 = sub.add_parser("add-participant")
    c2.add_argument("conversation_id")
    c2.add_argument("user_id")

    c3 = sub.add_parser("send")
    c3.add_argument("conversation_id")
    c3.add_argument("message")
    c3.add_argument("--user-id")
    c3.add_argument("--key-id")
    c3.add_argument("--client-timestamp", default=None)

    c4 = sub.add_parser("list-messages")
    c4.add_argument("conversation_id")
    c4.add_argument("--after")
    c4.add_argument("--limit", type=int, default=50)

    c5 = sub.add_parser("delivered")
    c5.add_argument("message_id")
    c5.add_argument("user_id")

    c6 = sub.add_parser("read")
    c6.add_argument("message_id")
    c6.add_argument("user_id")

    c7 = sub.add_parser("status")
    c7.add_argument("message_id")

    c8 = sub.add_parser("add-attachment")
    c8.add_argument("message_id")
    c8.add_argument("user_id")
    c8.add_argument("ciphertext")
    c8.add_argument("content_hash")
    c8.add_argument("signature")
    c8.add_argument("--meta-ciphertext")
    c8.add_argument("--meta-hash")
    c8.add_argument("--meta-signature")

    c9 = sub.add_parser("list-attachments")
    c9.add_argument("message_id")
    c9.add_argument("user_id")

    c10 = sub.add_parser("get-attachment")
    c10.add_argument("attachment_id")
    c10.add_argument("user_id")

    args = parser.parse_args()

    if args.cmd == "register":
        cmd_register(args)
    elif args.cmd == "create-conversation":
        cmd_create_conversation(args)
    elif args.cmd == "add-participant":
        cmd_add_participant(args)
    elif args.cmd == "send":
        cmd_send_message(args)
    elif args.cmd == "list-messages":
        cmd_list_messages(args)
    elif args.cmd == "delivered":
        cmd_mark_delivered(args)
    elif args.cmd == "read":
        cmd_mark_read(args)
    elif args.cmd == "status":
        cmd_message_status(args)
    elif args.cmd == "add-attachment":
        cmd_add_attachment(args)
    elif args.cmd == "list-attachments":
        cmd_list_attachments(args)
    elif args.cmd == "get-attachment":
        cmd_get_attachment(args)


if __name__ == "__main__":
    main()
