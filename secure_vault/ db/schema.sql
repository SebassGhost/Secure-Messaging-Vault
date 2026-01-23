-- ============================================================
-- Secure Messaging Vault
-- Database Schema (PostgreSQL)
--
-- Filosofía:
-- - Zero Trust: la base de datos NO es confiable
-- - Append-only: los mensajes no se modifican ni se eliminan
-- - End-to-end encryption: la DB nunca ve texto plano
-- - Integridad verificable desde el cliente
-- ============================================================


-- ------------------------------------------------------------
-- Extensiones necesarias
-- ------------------------------------------------------------

-- UUIDs no predecibles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Utilidades criptográficas (hashing binario, etc.)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ============================================================
-- USERS
-- Identidades criptográficas (NO personales)
-- ============================================================
CREATE TABLE users (

    -- Identificador lógico del usuario
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Clave pública del usuario (PEM / Base64)
    public_key TEXT NOT NULL,

    -- Fingerprint de la clave pública
    -- hash(public_key) generado en el cliente
    fingerprint BYTEA NOT NULL UNIQUE,

    -- Momento de creación de la identidad
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- CONVERSATIONS
-- Canales de comunicación
-- No contienen metadata sensible
-- ============================================================
CREATE TABLE conversations (

    -- Identificador del canal
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Fecha de creación del canal
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- CONVERSATION PARTICIPANTS
-- Quién pertenece a cada conversación
-- La DB NO decide confianza, solo registra
-- ============================================================
CREATE TABLE conversation_participants (

    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL,

    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (conversation_id, user_id),

    CONSTRAINT fk_cp_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_cp_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);


-- ============================================================
-- MESSAGES
-- Núcleo del sistema
-- Cada fila es INMUTABLE (append-only)
-- ============================================================
CREATE TABLE messages (

    -- Identificador único del mensaje
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Conversación a la que pertenece
    conversation_id UUID NOT NULL,

    -- Usuario emisor (identidad criptográfica)
    sender_id UUID NOT NULL,

    -- Mensaje cifrado (E2EE)
    ciphertext BYTEA NOT NULL,

    -- Hash criptográfico del mensaje
    -- Calculado en el cliente sobre:
    -- ciphertext + metadata relevante
    content_hash BYTEA NOT NULL,

    -- Hash del mensaje anterior en la conversación
    -- Permite detectar:
    -- - eliminación
    -- - reordenamiento
    -- - manipulación
    prev_hash BYTEA,

    -- Firma digital del content_hash
    -- Garantiza:
    -- - autoría
    -- - integridad
    -- - no repudio
    signature BYTEA NOT NULL,

    -- Fecha de inserción (solo referencia temporal)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_message_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_message_sender
        FOREIGN KEY (sender_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);


-- ============================================================
-- ÍNDICES
-- Performance sin comprometer seguridad
-- ============================================================

-- Mensajes por conversación
CREATE INDEX idx_messages_conversation
    ON messages(conversation_id);

-- Mensajes ordenados cronológicamente
CREATE INDEX idx_messages_created_at
    ON messages(created_at);

-- Conversación + tiempo (lectura eficiente)
CREATE INDEX idx_messages_conversation_created
    ON messages(conversation_id, created_at);

-- Auditoría local por emisor
CREATE INDEX idx_messages_sender
    ON messages(sender_id);


-- ============================================================
-- PROTECCIÓN LÓGICA
-- Defensa en profundidad
-- ============================================================

-- Nadie puede UPDATE o DELETE mensajes
REVOKE UPDATE, DELETE ON messages FROM PUBLIC;


-- ============================================================
-- PROTECCIÓN EXTRA (INMUTABILIDAD FUERTE)
-- Incluso para roles privilegiados
-- ============================================================

CREATE OR REPLACE FUNCTION prevent_message_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Messages are immutable (append-only log)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_message_update_or_delete
BEFORE UPDATE OR DELETE ON messages
FOR EACH ROW
EXECUTE FUNCTION prevent_message_mutation();
