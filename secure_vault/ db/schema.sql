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

    -- Fingerprint = hash(public_key)
    fingerprint BYTEA NOT NULL UNIQUE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


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
