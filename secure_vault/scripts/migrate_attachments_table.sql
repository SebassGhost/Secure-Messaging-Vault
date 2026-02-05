-- Create attachments table for E2EE attachments if missing

CREATE TABLE IF NOT EXISTS attachments (
    attachment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,
    uploader_id UUID NOT NULL,
    ciphertext BYTEA NOT NULL,
    content_hash BYTEA NOT NULL,
    signature BYTEA NOT NULL,
    meta_ciphertext BYTEA,
    meta_hash BYTEA,
    meta_signature BYTEA,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_attachment_message
        FOREIGN KEY (message_id)
        REFERENCES messages(message_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_attachment_uploader
        FOREIGN KEY (uploader_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_attachments_message
    ON attachments(message_id);

CREATE INDEX IF NOT EXISTS idx_attachments_uploader
    ON attachments(uploader_id);
