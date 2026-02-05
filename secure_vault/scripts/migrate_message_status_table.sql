-- Create message_status table for delivery/read receipts if missing

CREATE TABLE IF NOT EXISTS message_status (
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

CREATE INDEX IF NOT EXISTS idx_ms_message
    ON message_status(message_id);

CREATE INDEX IF NOT EXISTS idx_ms_user
    ON message_status(user_id);
