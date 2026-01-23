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
-- Extensión para generación de UUIDs
-- Se usan UUIDs para evitar IDs predecibles
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
-- USERS
-- Identidades criptográficas (NO personales)
-- ============================================================
CREATE TABLE users (

    -- Identificador lógico del usuario
    -- No representa identidad real, solo una entidad criptográfica
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Clave pública del usuario (PEM/Base64)
    -- Usada por otros clientes para verificar firmas
    public_key TEXT NOT NULL,

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
-- MESSAGES
-- Núcleo del sistema
-- Cada fila es INMUTABLE (append-only)
-- ============================================================
CREATE TABLE messages (

    -- Identificador único del mensaje
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Canal al que pertenece el mensaje
    conversation_id UUID NOT NULL,

    -- Usuario emisor (identidad criptográfica)
    sender_id UUID NOT NULL,

    -- Mensaje cifrado (E2EE)
    -- La base de datos NO puede interpretarlo
    ciphertext BYTEA NOT NULL,

    -- Hash criptográfico del contenido del mensaje
    -- Calculado en el cliente
    -- Incluye: ciphertext + metadatos relevantes
    content_hash TEXT NOT NULL,

    -- Hash del mensaje anterior en la conversación
    -- Permite:
    -- - detección de eliminación
    -- - detección de reordenamiento
    -- - integridad temporal
    prev_hash TEXT,

    -- Firma digital del content_hash
    -- Prueba:
    -- - autoría
    -- - integridad
    -- - no repudio
    signature TEXT NOT NULL,

    -- Fecha de inserción del mensaje
    -- Usada solo como referencia temporal
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Relación con la conversación
    CONSTRAINT fk_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE RESTRICT,

    -- Relación con el usuario emisor
    CONSTRAINT fk_sender
        FOREIGN KEY (sender_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);


-- ============================================================
-- ÍNDICES
-- Optimizan consultas sin comprometer seguridad
-- ============================================================

-- Búsqueda rápida de mensajes por conversación
CREATE INDEX idx_messages_conversation
    ON messages(conversation_id);

-- Orden cronológico eficiente
CREATE INDEX idx_messages_created_at
    ON messages(created_at);


-- ============================================================
-- PROTECCIÓN LÓGICA
-- Defensa en profundidad
-- ============================================================

-- Evita modificaciones o eliminaciones accidentales
-- Incluso si alguien obtiene acceso a la DB
REVOKE UPDATE, DELETE ON messages FROM PUBLIC;


-- ============================================================
-- PROTECCIÓN EXTRA (OPCIONAL PERO RECOMENDADA)
-- Bloquea UPDATE y DELETE incluso para roles privilegiados
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
