## ADDED Requirements

### Requirement: Connection profile and wizard
The system SHALL provide an admin connection wizard with agent code, name, user mode, reporting start date, provider secret reference, model aliases (concrete or provider wildcard, as defined by `gateway-connection-providers`), positive RPM/TPM, quota response mode (chat/batch), and finite per-key budget or explicit unlimited choice. Registered immutable fields MUST follow registry v1. Legacy agents outside the registry MUST remain read-only.

#### Scenario: Create a Gateway-only profile
- **WHEN** an admin submits a valid new profile
- **THEN** a draft revision is saved without deploying routes, issuing keys or sending AI requests

#### Scenario: Invalid or immutable input
- **WHEN** input has a duplicate code, a bare or misplaced wildcard alias, invalid rate or changed registered user mode
- **THEN** validation rejects the request with field-specific errors and preserves applied configuration

### Requirement: Separate administration authority
The system MUST require a dedicated server-validated admin credential for connection APIs and MUST NOT grant mutation access through the existing dashboard key or development open mode. Admin credentials MUST NOT be persisted in browser localStorage. Audit MUST identify the credential actor without claiming individual user identity.

#### Scenario: Dashboard reader attempts apply
- **WHEN** a caller supplies only a valid dashboard reading credential
- **THEN** apply is denied with 403 and no operation is executed

#### Scenario: Missing authentication
- **WHEN** an unauthenticated caller accesses a connection API
- **THEN** the API returns 401 and exposes no profile or secret

### Requirement: Independent progress and operation audit
The system SHALL display draft/applied revisions, deployment stage, key status and verification/reporting status separately. Every mutation MUST record actor, time, operation ID, sanitized changes and outcome without plaintext credentials.

#### Scenario: Gateway deployed but no agent traffic
- **WHEN** deployment succeeds and no matching agent request has been observed
- **THEN** UI shows deployment applied and verification awaiting evidence rather than connected

### Requirement: Virtual key lifecycle and quota
The system SHALL issue agent-tagged Virtual Keys whose model access follows `gateway-connection-providers`, set budgets through existing quota semantics, and support explicit rotation/revocation. Plaintext Virtual Keys MUST only be returned in their issuance response and MUST NOT appear in list, audit or config templates. Unlimited quota MUST require explicit selection.

#### Scenario: Lost issuance response
- **WHEN** an issued key response was lost
- **THEN** the UI offers revocation and replacement and does not retrieve the old plaintext key

#### Scenario: Deactivate versus disconnect
- **WHEN** an admin marks an agent inactive
- **THEN** history is preserved and UI states that access remains until an explicit key revocation succeeds

#### Scenario: Rotate a key
- **WHEN** an admin creates a replacement and later explicitly revokes the previous key
- **THEN** each key state is shown independently and the previous key is reported revoked only after Gateway confirmation

### Requirement: Per-key quota semantics and metadata preservation
The UI MUST label quota as a ceiling on each key's cumulative spend, not an aggregate agent budget. Rotation MUST require an explicit new-key budget and disclose independent budgets during overlap. Zero MUST be accepted as a blocking budget. Unlimited transitions MUST remove only quota_usd while preserving tags and other metadata and recording audit. Chat/batch quota response mode MUST be independent of single/multiple identity mode.

#### Scenario: Rotation of a partly spent key
- **WHEN** a key with quota 50 and spend 40 is replaced
- **THEN** the UI requires an explicit replacement budget, warns that the new key has its own spend and does not silently copy quota 50

#### Scenario: Change finite budget to unlimited
- **WHEN** an admin selects unlimited for an existing key
- **THEN** quota_usd is removed, routing tags and unrelated metadata remain and the transition is audited

### Requirement: Bound administration credentials
Admin credentials MUST use Authorization Bearer and constant-time byte comparison, remain bound to the confirmed backend origin, and never appear in URLs or logs. Enabling the feature with missing required administration configuration MUST fail closed.

#### Scenario: Backend origin changes
- **WHEN** an api URL override points to a different backend
- **THEN** the existing admin credential is not sent and the UI requires authentication for that backend
