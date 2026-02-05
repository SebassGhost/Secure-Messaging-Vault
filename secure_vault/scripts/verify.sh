#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_cmd docker
require_cmd python3

echo "Starting services..."
docker compose up -d --build >/dev/null

echo "Checking schema state..."
schema_exists="$(docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.users') IS NOT NULL;")"
if echo "$schema_exists" | grep -q "t"; then
  echo "Schema already exists. Skipping schema apply."
else
  echo "Applying schema..."
  cat " db/schema.sql" | docker compose exec -T db psql -U vault -d secure_vault >/dev/null
fi

echo "Checking tables..."
docker compose exec -T db psql -U vault -d secure_vault -c "\dt"

echo "Generating fingerprints..."
finger1="$(python3 - << 'PY'
import base64, hashlib
print(base64.b64encode(hashlib.sha256(b"pubkey-demo").digest()).decode())
PY
)"
finger2="$(python3 - << 'PY'
import base64, hashlib
print(base64.b64encode(hashlib.sha256(b"pubkey-demo2").digest()).decode())
PY
)"

echo "Creating users via API..."
user1="$(python3 - << PY
import requests, time, sys
base="http://localhost:8000"

def wait_ready():
    for _ in range(30):
        try:
            r = requests.get(base + "/", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    print("API not ready", file=sys.stderr)
    sys.exit(1)

wait_ready()
payload={"public_key":"pubkey-demo","fingerprint":"${finger1}"}
r=requests.post(base+"/users", json=payload, timeout=5)
if r.headers.get("content-type","").startswith("application/json"):
    print(r.json()["user_id"])
else:
    print(r.status_code, r.text, file=sys.stderr)
    sys.exit(1)
PY
)"
user2="$(python3 - << PY
import requests, sys
base="http://localhost:8000"
payload={"public_key":"pubkey-demo2","fingerprint":"${finger2}"}
r=requests.post(base+"/users", json=payload, timeout=5)
if r.headers.get("content-type","").startswith("application/json"):
    print(r.json()["user_id"])
else:
    print(r.status_code, r.text, file=sys.stderr)
    sys.exit(1)
PY
)"

echo "Creating conversation and sending message..."
python3 - << PY
import requests
base="http://localhost:8000"
user1="${user1}"
user2="${user2}"

r = requests.post(base + "/conversations", timeout=5)
conversation_id = r.json()["conversation_id"]

requests.post(base + f"/conversations/{conversation_id}/participants", json={"user_id": user1}, timeout=5)
requests.post(base + f"/conversations/{conversation_id}/participants", json={"user_id": user2}, timeout=5)

payload = {
    "sender_id": user1,
    "ciphertext": "Y2lwaGVydGV4dC1kZW1v",
    "content_hash": "Y29udGVudC1oYXNoLWRlbW8=",
    "prev_hash": None,
    "signature": "c2lnbmF0dXJlLWRlbW8=",
    "client_timestamp": "2026-02-05T10:00:00Z",
    "key_id": None,
}

r = requests.post(base + f"/conversations/{conversation_id}/messages", json=payload, timeout=5)
print("send message", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/conversations/{conversation_id}/messages", timeout=5)
print("list messages", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/conversations/{conversation_id}/messages/last-hash", timeout=5)
print("last hash", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/users/{user1}/conversations", timeout=5)
print("list conversations", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)
PY

echo "Verification complete."
