-- ============================================================
-- Secure Messaging Vault
-- PostgreSQL Schema (Zero Trust / E2EE)
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- EXTENSIONS
-- ------------------------------------------------------------

-- Modern UUID + crypto primitives
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ============================================================
-- USERS
-- Cryptographic identities only (no personal data)
-- ============================================================

CREATE TABLE users (

    user_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- Public key in PEM or Base64
    public_key TEXT NOT NULL,

    -- Fingerprint = SHA-256(public_key)
    fingerprint BYTEA NOT NULL UNIQUE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- USER KEYS
-- Rotatable keys per user (multi-device / key rotation)
-- ============================================================

CREATE TABLE user_keys (

    user_id UUID NOT NULL,

    -- Client-defined key identifier (e.g., "primary", "device-1")
    key_id TEXT NOT NULL,

    -- Public key in PEM or Base64
    public_key TEXT NOT NULL,

    -- Fingerprint = SHA-256(public_key)
    fingerprint BYTEA NOT NULL UNIQUE,

    is_primary BOOLEAN NOT NULL
        DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    revoked_at TIMESTAMP,

    PRIMARY KEY (user_id, key_id),

    CONSTRAINT fk_user_keys_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_user_keys_user
    ON user_keys(user_id);

-- Only one primary key per user
CREATE UNIQUE INDEX ux_user_keys_primary
    ON user_keys(user_id)
    WHERE is_primary;


-- ============================================================
-- CONVERSATIONS
-- Communication channels
-- ============================================================

CREATE TABLE conversations (

    conversation_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- CONVERSATION PARTICIPANTS
-- Membership registry only (no trust logic)
-- ============================================================

CREATE TABLE conversation_participants (

    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL,

    joined_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

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
-- Append-only, immutable, end-to-end encrypted
-- ============================================================

-- NOTE: Backend must validate that sender_id belongs to the conversation
-- (sender_id ∈ conversation_participants for conversation_id).
CREATE TABLE messages (

    message_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    conversation_id UUID NOT NULL,

    sender_id UUID NOT NULL,

    -- Encrypted payload (E2EE)
    ciphertext BYTEA NOT NULL,

    -- Hash calculated client-side over:
    -- ciphertext + sender_id + conversation_id + prev_hash
    content_hash BYTEA NOT NULL,

    -- Hash of previous message in conversation
    -- NULL only for the first message
    prev_hash BYTEA,

    -- Signature of content_hash using sender private key
    signature BYTEA NOT NULL,

    -- Client-side timestamp (non-trusted, UX only)
    client_timestamp TIMESTAMP,

    -- Optional key identifier (for key rotation)
    -- NULL = primary/default key
    key_id TEXT,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

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
-- MESSAGE STATUS (Delivery / Read Receipts)
-- ============================================================

CREATE TABLE message_status (

    message_id UUID NOT NULL,
    user_id UUID NOT NULL,

    delivered_at TIMESTAMP,
    read_at TIMESTAMP,

    PRIMARY KEY (message_id, user_id),

    CONSTRAINT fk_ms_message
        FOREIGN KEY (message_id)
        REFERENCES messages(message_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ms_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_ms_message
    ON message_status(message_id);

CREATE INDEX idx_ms_user
    ON message_status(user_id);


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_messages_conversation
    ON messages(conversation_id);

CREATE INDEX idx_messages_created_at
    ON messages(created_at);

CREATE INDEX idx_messages_conversation_created
    ON messages(conversation_id, created_at);

CREATE INDEX idx_messages_sender
    ON messages(sender_id);

-- Chain integrity / fast verification
CREATE INDEX idx_messages_chain
    ON messages(conversation_id, prev_hash);

-- Fast lookup: conversations by user
CREATE INDEX idx_cp_user
    ON conversation_participants(user_id);


-- ============================================================
-- ACCESS CONTROL
-- ============================================================

-- Messages are INSERT-only
REVOKE UPDATE, DELETE, TRUNCATE ON messages FROM PUBLIC;


-- ============================================================
-- STRONG IMMUTABILITY (Defense in Depth)
-- ============================================================

CREATE OR REPLACE FUNCTION prevent_message_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RAISE EXCEPTION
        'Messages are immutable (append-only log)';
END;
$$;

CREATE TRIGGER no_message_update_or_delete
BEFORE UPDATE OR DELETE OR TRUNCATE
ON messages
FOR EACH STATEMENT
EXECUTE FUNCTION prevent_message_mutation();


COMMIT;
