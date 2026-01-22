-- ============================================
-- Secure Messaging Vault
-- Database Schema (PostgreSQL)
-- ============================================

-- Extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS
-- Identidades lógicas (no personales)
-- ============================================
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    public_key TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- CONVERSATIONS
-- Canales de comunicación
-- ============================================
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- MESSAGES
-- Núcleo del sistema (append-only)
-- ============================================
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    conversation_id UUID NOT NULL,
    sender_id UUID NOT NULL,

    -- Mensaje cifrado (la DB no puede leerlo)
    ciphertext BYTEA NOT NULL,

    -- Hash del mensaje + metadatos
    content_hash TEXT NOT NULL,

    -- Hash del mensaje anterior (integridad temporal)
    prev_hash TEXT,

    -- Firma digital del hash
    signature TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id),

    CONSTRAINT fk_sender
        FOREIGN KEY (sender_id)
        REFERENCES users(user_id)
);

-- ============================================
-- ÍNDICES (performance y orden)
-- ============================================
CREATE INDEX idx_messages_conversation
    ON messages(conversation_id);

CREATE INDEX idx_messages_created_at
    ON messages(created_at);

-- ============================================
-- PROTECCIÓN LÓGICA
-- ============================================

-- Evitar modificaciones accidentales
REVOKE UPDATE, DELETE ON messages FROM PUBLIC;

