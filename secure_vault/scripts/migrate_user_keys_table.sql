-- Create user_keys table for key rotation if missing

CREATE TABLE IF NOT EXISTS user_keys (
    user_id UUID NOT NULL,
    key_id TEXT NOT NULL,
    public_key TEXT NOT NULL,
    fingerprint BYTEA NOT NULL UNIQUE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    PRIMARY KEY (user_id, key_id),
    CONSTRAINT fk_user_keys_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_keys_user
    ON user_keys(user_id);

-- Only one primary key per user
CREATE UNIQUE INDEX IF NOT EXISTS ux_user_keys_primary
    ON user_keys(user_id)
    WHERE is_primary;
