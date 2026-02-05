$ErrorActionPreference = "Stop"

function Assert-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command not found: $Name"
    }
}

Assert-Command "docker"
Assert-Command "python"

Write-Host "Starting services..."
docker compose up -d --build | Out-Null

Write-Host "Waiting for database to be ready..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    $status = docker compose exec -T db pg_isready -U vault -d secure_vault 2>$null
    if ($status -match "accepting connections") {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw "Database is not ready"
}

Write-Host "Checking schema state..."
$schemaExists = docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.users') IS NOT NULL;"
$keysExists = docker compose exec -T db psql -U vault -d secure_vault -tAc "SELECT to_regclass('public.user_keys') IS NOT NULL;"

if ($schemaExists -match "t") {
    if ($keysExists -match "t") {
        Write-Host "Schema already exists. Skipping schema apply."
    } else {
        Write-Host "Applying user_keys migration..."
        type "scripts\migrate_user_keys_table.sql" | docker compose exec -T db psql -U vault -d secure_vault | Out-Null
    }
} else {
    Write-Host "Applying schema..."
    type " db\schema.sql" | docker compose exec -T db psql -U vault -d secure_vault | Out-Null
}

Write-Host "Checking tables..."
docker compose exec -T db psql -U vault -d secure_vault -c "\dt"

Write-Host "Backfilling user keys..."
type "scripts\migrate_user_keys.sql" | docker compose exec -T db psql -U vault -d secure_vault | Out-Null

Write-Host "Generating fingerprints..."
$finger1 = @'
import base64, hashlib
print(base64.b64encode(hashlib.sha256(b"pubkey-demo").digest()).decode())
'@ | python -

$finger2 = @'
import base64, hashlib
print(base64.b64encode(hashlib.sha256(b"pubkey-demo2").digest()).decode())
'@ | python -

Write-Host "Creating users via API..."
$user1 = @"
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
payload={"public_key":"pubkey-demo","fingerprint":"$finger1".strip()}
r=requests.post(base+"/users", json=payload, timeout=5)
if r.headers.get("content-type","").startswith("application/json"):
    print(r.json()["user_id"])
else:
    print(r.status_code, r.text, file=sys.stderr)
    sys.exit(1)
"@ | python -

$user2 = @"
import requests, sys
base="http://localhost:8000"
payload={"public_key":"pubkey-demo2","fingerprint":"$finger2".strip()}
r=requests.post(base+"/users", json=payload, timeout=5)
if r.headers.get("content-type","").startswith("application/json"):
    print(r.json()["user_id"])
else:
    print(r.status_code, r.text, file=sys.stderr)
    sys.exit(1)
"@ | python -

Write-Host "Creating conversation and sending message..."
@"
import requests
base="http://localhost:8000"
user1="$user1".strip()
user2="$user2".strip()

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

r = requests.get(base + f"/conversations/{conversation_id}/messages", timeout=5)
print("list messages", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/conversations/{conversation_id}/messages/last-hash", timeout=5)
print("last hash", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

r = requests.get(base + f"/users/{user1}/conversations", timeout=5)
print("list conversations", r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else r.text)

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
"@ | python -

Write-Host "Verification complete."
