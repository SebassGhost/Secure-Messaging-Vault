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

echo "Waiting for database to be ready..."
ready=0
for i in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U vault -d secure_vault >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "Database is not ready" >&2
  exit 1
fi

echo "Checking schema state..."
schema_exists="$(docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.users') IS NOT NULL;")"
keys_exists="$(docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.user_keys') IS NOT NULL;")"
status_exists="$(docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.message_status') IS NOT NULL;")"
attachments_exists="$(docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.attachments') IS NOT NULL;")"
if echo "$schema_exists" | grep -q "t"; then
  if echo "$keys_exists" | grep -q "t"; then
    if echo "$status_exists" | grep -q "t"; then
      if echo "$attachments_exists" | grep -q "t"; then
        echo "Schema already exists. Skipping schema apply."
      else
        echo "Applying attachments migration..."
        cat "scripts/migrate_attachments_table.sql" | docker compose exec -T db psql -U vault -d secure_vault >/dev/null
      fi
    else
      echo "Applying message_status migration..."
      cat "scripts/migrate_message_status_table.sql" | docker compose exec -T db psql -U vault -d secure_vault >/dev/null
    fi
  else
    echo "Applying user_keys migration..."
    cat "scripts/migrate_user_keys_table.sql" | docker compose exec -T db psql -U vault -d secure_vault >/dev/null
  fi
else
  echo "Applying schema..."
  cat " db/schema.sql" | docker compose exec -T db psql -U vault -d secure_vault >/dev/null
fi

echo "Checking tables..."
docker compose exec -T db psql -U vault -d secure_vault -c "\dt"

echo "Backfilling user keys..."
cat "scripts/migrate_user_keys.sql" | docker compose exec -T db psql -U vault -d secure_vault >/dev/null

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
    "key_id": "primary",
}

r = requests.post(base + f"/conversations/{conversation_id}/messages", json=payload, timeout=5)
print("send message", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)
message_id = r.json().get("message_id")

r = requests.get(base + f"/conversations/{conversation_id}/messages", timeout=5)
print("list messages", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/conversations/{conversation_id}/messages/last-hash", timeout=5)
print("last hash", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/users/{user1}/conversations", timeout=5)
print("list conversations", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

# mark delivered/read for user2
if message_id:
    r = requests.post(base + f"/messages/{message_id}/delivered", json={"user_id": user2}, timeout=5)
    print("delivered", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)
    r = requests.post(base + f"/messages/{message_id}/read", json={"user_id": user2}, timeout=5)
    print("read", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)
    r = requests.get(base + f"/messages/{message_id}/status", timeout=5)
    print("status", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

    # add attachment
    payload = {
        "uploader_id": user1,
        "ciphertext": "YXR0YWNobWVudC1iaW5hcnk=",
        "content_hash": "YXR0YWNobWVudC1oYXNo",
        "signature": "YXR0YWNobWVudC1zaWc=",
        "meta_ciphertext": "bWV0YS1lbmM=",
        "meta_hash": "bWV0YS1oYXNo",
        "meta_signature": "bWV0YS1zaWc=",
    }
    r = requests.post(base + f"/messages/{message_id}/attachments", json=payload, timeout=5)
    print("add attachment", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)
    attachment_id = r.json().get("attachment_id") if r.headers.get("content-type","").startswith("application/json") else None

    r = requests.get(base + f"/messages/{message_id}/attachments", params={"user_id": user2}, timeout=5)
    print("list attachments", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

    if attachment_id:
        r = requests.get(base + f"/attachments/{attachment_id}", params={"user_id": user2}, timeout=5)
        print("get attachment", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

# rotate key for user1
payload = {
    "key_id": "device-1",
    "public_key": "pubkey-demo-device-1",
    "fingerprint": "Y2lwaGVydGV4dC1kZW1v",
    "is_primary": False,
}
r = requests.post(base + f"/users/{user1}/keys", json=payload, timeout=5)
if r.status_code == 409:
    print("add key", r.status_code, "already exists (ok)")
else:
    print("add key", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.post(base + f"/users/{user1}/keys/device-1/primary", timeout=5)
print("set primary", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/users/{user1}/keys", timeout=5)
print("list keys", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)
PY

echo "Verification complete."
