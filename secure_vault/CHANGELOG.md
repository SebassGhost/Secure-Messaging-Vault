# Changelog

## [Unreleased]

### Added
- User key rotation with `user_keys` table and related API endpoints.
- Message status receipts (delivered/read) with `message_status` table and endpoints.
- E2EE attachments with encrypted payload and optional encrypted metadata.
- Verification scripts expanded to cover key rotation, message status, and attachments.
- Basic API test suite with pytest.

### Changed
- API now validates `key_id` on message send and defaults to `primary`.
- Base64 decoding is now strict (invalid input returns 400).
- README expanded with advanced API docs and client integration guide.

### Fixed
- Verification scripts made idempotent and resilient to DB readiness.
