# Secure Messaging Vault

## Descripción

Secure Messaging Vault es un backend de mensajería con enfoque Zero‑Trust y E2EE.
El servidor **no descifra** mensajes: solo almacena `ciphertext`, hashes y firmas.

## Estado actual (lo que ya funciona)

- Esquema PostgreSQL con:
  - usuarios criptográficos
  - conversaciones y participantes
  - mensajes append‑only con hash encadenado
- API con endpoints para:
  - crear usuarios
  - crear conversaciones
  - agregar participantes
  - enviar mensajes E2EE (base64)
  - listar mensajes y obtener el último hash
- Scripts de verificación en Windows y Linux/macOS

## Flujo completo de uso (actual)

### 1) Levantar servicios

```bash
docker compose up -d --build
```

### 2) Aplicar el esquema SQL

El archivo del esquema vive en la carpeta ` db` (nota: tiene un espacio al inicio).

**Windows (PowerShell):**
```powershell
type " db\schema.sql" | docker compose exec -T db psql -U vault -d secure_vault
```

**Linux/macOS:**
```bash
cat " db/schema.sql" | docker compose exec -T db psql -U vault -d secure_vault
```

### 3) Crear usuarios (claves públicas)

El cliente genera su `public_key` y el `fingerprint = SHA‑256(public_key)` en base64.

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"public_key":"pubkey-demo","fingerprint":"Y29udGVudC1oYXNoLWRlbW8="}'
```

### 4) Crear conversación

```bash
curl -X POST http://localhost:8000/conversations
```

### 5) Agregar participantes

```bash
curl -X POST http://localhost:8000/conversations/{conversation_id}/participants \
  -H "Content-Type: application/json" \
  -d '{"user_id":"{user_id}"}'
```

### 6) Enviar mensaje E2EE

El cliente envía `ciphertext`, `content_hash`, `signature` en base64.
El servidor no descifra ni valida criptografía (solo almacena).

```bash
curl -X POST http://localhost:8000/conversations/{conversation_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id":"{user_id}",
    "ciphertext":"Y2lwaGVydGV4dC1kZW1v",
    "content_hash":"Y29udGVudC1oYXNoLWRlbW8=",
    "prev_hash":null,
    "signature":"c2lnbmF0dXJlLWRlbW8=",
    "client_timestamp":"2026-02-05T10:00:00Z",
    "key_id":null
  }'
```

### 7) Listar mensajes

```bash
curl "http://localhost:8000/conversations/{conversation_id}/messages?limit=50"
```

### 8) Obtener último hash (encadenamiento)

```bash
curl "http://localhost:8000/conversations/{conversation_id}/messages/last-hash"
```

### 9) Listar conversaciones de un usuario

```bash
curl "http://localhost:8000/users/{user_id}/conversations"
```

## Contrato de datos E2EE (actual)

Esta sección describe el **formato mínimo** esperado por el backend. No define
el algoritmo criptográfico del cliente, solo el **contrato de intercambio**.

### Campos E2EE en mensajes

- `ciphertext` (base64): contenido cifrado por el cliente.
- `content_hash` (base64): hash calculado por el cliente sobre:
  - `ciphertext + sender_id + conversation_id + prev_hash`
- `signature` (base64): firma del `content_hash` con la clave privada del emisor.
- `prev_hash` (base64 | null): hash del mensaje anterior (null si es el primero).
- `client_timestamp` (string ISO 8601 | null): solo UX, **no confiable**.
- `key_id` (string | null): identificador de clave (rotación futura).

### Reglas básicas

1. El cliente **siempre** cifra y firma antes de enviar.
2. El servidor **nunca** descifra, solo almacena y devuelve lo recibido.
3. El cliente valida firmas y cadena de hashes antes de mostrar mensajes.
4. Si `key_id` no se envía, el servidor asume `"primary"`.

## Documentación avanzada de la API

**Base URL:** `http://localhost:8000`  
**Formato:** JSON  
**Codificación binaria:** todos los campos binarios van en **base64**  

### Convenciones generales

- `user_id`, `conversation_id`, `message_id` son UUID.
- El servidor **no descifra** ni verifica criptografía.
- Un emisor debe pertenecer a la conversación para enviar (`sender_id ∈ conversation_participants`).
- `client_timestamp` es solo para UX, no es confiable.

### Errores comunes

- `400 Bad Request`: payload inválido (base64 mal formado, campos faltantes).
- `403 Forbidden`: el `sender_id` no pertenece a la conversación.
- `404 Not Found`: recurso no encontrado.
- `500 Internal Server Error`: error no controlado o conflicto de datos.

## Variables de entorno

Estas son las variables necesarias para el backend actual:

```
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

Nota: `VAULT_SECRET_KEY` ya no es necesaria porque el cifrado es 100% cliente.

### 1) Healthcheck

**GET /**  
Respuesta:
```json
{
  "status": "ok",
  "message": "Secure Vault API running"
}
```

### 2) Crear usuario

**POST /users**  
Body:
```json
{
  "public_key": "string",
  "fingerprint": "base64"
}
```
Respuesta:
```json
{
  "user_id": "uuid",
  "key_id": "primary"
}
```

Notas:
- `fingerprint` = SHA‑256(`public_key`) en base64.
- Si el fingerprint ya existe, devuelve el `user_id` existente.

### 3) Obtener usuario por ID

**GET /users/{user_id}**  
Respuesta:
```json
{
  "user_id": "uuid",
  "public_key": "string",
  "created_at": "2026-02-05T00:50:01.186203"
}
```

### 4) Obtener usuario por fingerprint

**GET /users/by-fingerprint?fingerprint={base64}**  
Respuesta:
```json
{
  "user_id": "uuid",
  "public_key": "string",
  "created_at": "2026-02-05T00:50:01.186203"
}
```

### 4.1) Agregar nueva clave (rotación)

**POST /users/{user_id}/keys**  
Body:
```json
{
  "key_id": "device-1",
  "public_key": "string",
  "fingerprint": "base64",
  "is_primary": false
}
```
Respuesta:
```json
{
  "key_id": "device-1"
}
```

Notas:
- `key_id` lo define el cliente (por ejemplo: `primary`, `device-1`).
- `fingerprint` = SHA‑256(`public_key`) en base64.

### 4.2) Listar claves de un usuario

**GET /users/{user_id}/keys**  
Respuesta:
```json
[
  {
    "key_id": "primary",
    "public_key": "string",
    "fingerprint": "base64",
    "is_primary": true,
    "created_at": "2026-02-05T00:50:01.186203",
    "revoked_at": null
  }
]
```

### 4.3) Revocar clave

**POST /users/{user_id}/keys/{key_id}/revoke**  
Respuesta:
```json
{
  "revoked": true
}
```

### 4.4) Marcar clave como primaria

**POST /users/{user_id}/keys/{key_id}/primary**  
Respuesta:
```json
{
  "primary": true
}
```

### 5) Crear conversación

**POST /conversations**  
Respuesta:
```json
{
  "conversation_id": "uuid"
}
```

### 6) Agregar participante

**POST /conversations/{conversation_id}/participants**  
Body:
```json
{
  "user_id": "uuid"
}
```
Respuesta:
```json
{
  "added": true
}
```

### 7) Listar conversaciones de un usuario

**GET /users/{user_id}/conversations**  
Respuesta:
```json
[
  {
    "conversation_id": "uuid",
    "created_at": "2026-02-05T00:50:01.139330"
  }
]
```

### 8) Enviar mensaje E2EE

**POST /conversations/{conversation_id}/messages**  
Body:
```json
{
  "sender_id": "uuid",
  "ciphertext": "base64",
  "content_hash": "base64",
  "prev_hash": "base64|null",
  "signature": "base64",
  "client_timestamp": "ISO-8601|null",
  "key_id": "string|null"
}
```
Respuesta:
```json
{
  "message_id": "uuid",
  "created_at": "2026-02-05T00:50:01.186203"
}
```

### 9) Listar mensajes (paginado)

**GET /conversations/{conversation_id}/messages?after={message_id}&limit=50**  
Parámetros:
- `after` (opcional): `message_id` a partir del cual se listan los siguientes.
- `limit` (opcional): 1 a 200 (default 50).

Respuesta:
```json
[
  {
    "message_id": "uuid",
    "sender_id": "uuid",
    "ciphertext": "base64",
    "content_hash": "base64",
    "prev_hash": "base64|null",
    "signature": "base64",
    "client_timestamp": "ISO-8601|null",
    "key_id": "string|null",
    "created_at": "2026-02-05T00:50:01.186203"
  }
]
```

### 10) Obtener último hash

**GET /conversations/{conversation_id}/messages/last-hash**  
Respuesta:
```json
{
  "content_hash": "base64|null"
}
```

### 11) Marcar mensaje como entregado

**POST /messages/{message_id}/delivered**  
Body:
```json
{
  "user_id": "uuid"
}
```
Respuesta:
```json
{
  "delivered": true
}
```

### 12) Marcar mensaje como leído

**POST /messages/{message_id}/read**  
Body:
```json
{
  "user_id": "uuid"
}
```
Respuesta:
```json
{
  "read": true
}
```

### 13) Obtener estado de un mensaje

**GET /messages/{message_id}/status**  
Respuesta:
```json
[
  {
    "user_id": "uuid",
    "delivered_at": "2026-02-05T01:32:52.225837",
    "read_at": "2026-02-05T01:33:10.100000"
  }
]
```

**Ejemplo rápido (PowerShell):**
```powershell
curl -X POST http://localhost:8000/messages/{message_id}/delivered `
  -H "Content-Type: application/json" `
  -d "{\"user_id\":\"{user_id}\"}"

curl -X POST http://localhost:8000/messages/{message_id}/read `
  -H "Content-Type: application/json" `
  -d "{\"user_id\":\"{user_id}\"}"

curl "http://localhost:8000/messages/{message_id}/status"
```

### 14) Subir adjunto cifrado

**POST /messages/{message_id}/attachments**  
Body:
```json
{
  "uploader_id": "uuid",
  "ciphertext": "base64",
  "content_hash": "base64",
  "signature": "base64",
  "meta_ciphertext": "base64|null",
  "meta_hash": "base64|null",
  "meta_signature": "base64|null"
}
```
Respuesta:
```json
{
  "attachment_id": "uuid",
  "created_at": "2026-02-05T16:46:17.211498"
}
```

### 15) Listar adjuntos de un mensaje

**GET /messages/{message_id}/attachments?user_id={user_id}**  
Respuesta:
```json
[
  {
    "attachment_id": "uuid",
    "uploader_id": "uuid",
    "meta_ciphertext": "base64|null",
    "meta_hash": "base64|null",
    "meta_signature": "base64|null",
    "created_at": "2026-02-05T16:46:17.211498"
  }
]
```

### 16) Obtener adjunto

**GET /attachments/{attachment_id}?user_id={user_id}**  
Respuesta:
```json
{
  "attachment_id": "uuid",
  "message_id": "uuid",
  "uploader_id": "uuid",
  "ciphertext": "base64",
  "content_hash": "base64",
  "signature": "base64",
  "meta_ciphertext": "base64|null",
  "meta_hash": "base64|null",
  "meta_signature": "base64|null",
  "created_at": "2026-02-05T16:46:17.211498"
}
```

**Ejemplo rápido (PowerShell):**
```powershell
curl -X POST http://localhost:8000/messages/{message_id}/attachments `
  -H "Content-Type: application/json" `
  -d '{
    "uploader_id":"{user_id}",
    "ciphertext":"YXR0YWNobWVudC1iaW5hcnk=",
    "content_hash":"YXR0YWNobWVudC1oYXNo",
    "signature":"YXR0YWNobWVudC1zaWc=",
    "meta_ciphertext":"bWV0YS1lbmM=",
    "meta_hash":"bWV0YS1oYXNo",
    "meta_signature":"bWV0YS1zaWc="
  }'

curl "http://localhost:8000/messages/{message_id}/attachments?user_id={user_id}"

curl "http://localhost:8000/attachments/{attachment_id}?user_id={user_id}"
```

## Guía de integración del cliente (E2EE)

Esta guía describe **qué debe hacer el cliente** antes de enviar un mensaje.
No impone un algoritmo específico, solo el flujo compatible con el backend.

### 1) Generar identidad criptográfica

1. Generar par de claves (pública/privada) en el cliente.
2. Calcular `fingerprint = SHA‑256(public_key)` en bytes.
3. Enviar `public_key` y `fingerprint` en base64 a `POST /users`.

### 1.1) Rotar claves

Cuando se genera una nueva clave:
1. Enviar a `POST /users/{user_id}/keys` con `key_id` único.
2. Si será la clave principal, llamar a `POST /users/{user_id}/keys/{key_id}/primary`.
3. Para desactivar una clave vieja, usar `POST /users/{user_id}/keys/{key_id}/revoke`.

### 2) Preparar el mensaje

1. Serializar el contenido real del mensaje en bytes.
2. Cifrar con la clave del destinatario o una clave de sesión E2EE.
3. Codificar `ciphertext` en base64.

### 3) Encadenar integridad

1. Obtener `prev_hash` con `GET /conversations/{id}/messages/last-hash`.
2. Construir el hash del mensaje:

```
content_hash = SHA-256(
  ciphertext + sender_id + conversation_id + prev_hash
)
```

3. Firmar `content_hash` con la **clave privada** del emisor.
4. Codificar `content_hash` y `signature` en base64.

### 4) Enviar mensaje

Enviar a `POST /conversations/{conversation_id}/messages`:
- `sender_id`
- `ciphertext` (base64)
- `content_hash` (base64)
- `prev_hash` (base64|null)
- `signature` (base64)
- `client_timestamp` (opcional)
- `key_id` (opcional)

### 5) Validar al recibir

Cuando el cliente recibe mensajes:
1. Verificar la firma con la **clave pública** del emisor.
2. Recalcular `content_hash` y comparar.
3. Validar la cadena de hashes (`prev_hash`) para detectar huecos.
4. Solo después descifrar y mostrar al usuario.

## Verificación automática (recomendada)

Esta guía valida que el esquema PostgreSQL, los endpoints del API y el flujo básico E2EE funcionan de punta a punta.

### Requisitos
- Docker Desktop en ejecución
- Python 3 instalado
- Acceso a `docker compose`

### 1) Verificar tablas creadas

```bash
docker compose exec -T db psql -U vault -d secure_vault -c "\dt"
```

Debes ver:
- `users`
- `conversations`
- `conversation_participants`
- `messages`

### 2) Ejecutar scripts de verificación

Se incluyen dos scripts que hacen una prueba completa:
- crean usuarios vía API
- crean conversación
- agregan participantes
- envían mensaje E2EE dummy (base64)
- listan mensajes y last-hash

**Windows (PowerShell):**
```powershell
.\scripts\verify.ps1
```

**Linux/macOS:**
```bash
chmod +x scripts/verify.sh
./scripts/verify.sh
```

### 5) ¿Qué valida exactamente?

1. Postgres está arriba y el esquema aplica sin errores.  
2. El API responde en `http://localhost:8000`.  
3. Se pueden crear usuarios y conversaciones por API.  
4. El envío de mensajes almacena `ciphertext`, `hash` y `signature` (sin descifrar en servidor).  
5. Listado de mensajes y last-hash funcionan correctamente.  

### 6) Problemas comunes

- **Timeout en `docker compose up`:** reintenta; a veces el primer build tarda más.
- **`Did not find any relations`:** el esquema no se aplicó; repite el paso 2.
- **Errores 403 al enviar mensaje:** el `sender_id` no es participante de la conversación.

## Pruebas (pytest)

Pruebas unitarias básicas del API con `TestClient`:

```bash
pytest -q
```

## Cliente CLI (Python)

Cliente mínimo para probar el API desde terminal.

### Comandos principales

```bash
# Crear identidad local (si no existe) y registrar usuario
python -m client.cli register

# Crear conversación
python -m client.cli create-conversation

# Agregar participante
python -m client.cli add-participant <conversation_id> <user_id>

# Enviar mensaje demo
python -m client.cli send <conversation_id> "hola mundo"

# Listar mensajes
python -m client.cli list-messages <conversation_id>

# Marcar entregado / leído
python -m client.cli delivered <message_id> <user_id>
python -m client.cli read <message_id> <user_id>

# Ver estado
python -m client.cli status <message_id>
```

Variables útiles:
- `--api` para cambiar la URL (default `http://localhost:8000`)
- `--user-id` para enviar como un usuario específico

## Cliente Web (React/Vite)

Cliente básico para probar el flujo E2EE sin tooling extra en backend.

```bash
cd web
npm install
npm run dev
```

Opcional:
```
VITE_API_URL=http://localhost:8000
```

## Funciones futuras (roadmap)

Estas son mejoras planeadas y coherentes con el diseño E2EE:

1. **Rotación de claves y multi‑dispositivo**
   - `key_id` para versionar claves por dispositivo.
   - Revocación de dispositivos comprometidos.
2. **Estados de mensajes**
   - `delivered_at` y `read_at` por usuario.
3. **Adjuntos cifrados**
   - Tabla `attachments` con metadata cifrada.
4. **Borrado lógico / expiración**
   - Tombstones o TTL sin romper el append‑only.
5. **Validación criptográfica en cliente**
   - Verificación de firma y cadena de hashes antes de mostrar mensajes.
