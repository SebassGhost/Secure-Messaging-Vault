-- Backfill user_keys from users table
-- Creates a primary key entry per existing user

INSERT INTO user_keys (user_id, key_id, public_key, fingerprint, is_primary)
SELECT
    u.user_id,
    'primary' AS key_id,
    u.public_key,
    u.fingerprint,
    TRUE AS is_primary
FROM users u
WHERE NOT EXISTS (
    SELECT 1
    FROM user_keys k
    WHERE k.user_id = u.user_id
      AND k.key_id = 'primary'
);
