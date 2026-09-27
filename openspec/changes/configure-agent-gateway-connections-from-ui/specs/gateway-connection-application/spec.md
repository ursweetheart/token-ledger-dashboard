## ADDED Requirements

### Requirement: Preview and configuration ownership
The system SHALL generate a mutation-free preview of registry, route, secret references, budget and deployment changes. Managed profiles in DB SHALL be desired state; rendered YAML MUST preserve unmanaged entries and global configuration. Apply MUST reject detected external drift rather than overwrite it.

#### Scenario: Preview a draft
- **WHEN** an admin previews a draft
- **THEN** proposed changes and validation errors are returned without file writes, DB mutations, issued keys, container changes or AI calls

#### Scenario: External file changes
- **WHEN** current configuration hashes differ from the preview baseline
- **THEN** apply returns conflict and requires an explicit reconciled preview

### Requirement: Revision locking and idempotency
The system MUST serialize deployment mutations, require an expected revision and idempotency key, and persist operation checkpoints. Repeated requests for the same operation MUST NOT issue duplicate keys or apply additive quota changes twice.

#### Scenario: Concurrent edits
- **WHEN** a second apply uses an outdated revision
- **THEN** it receives 409 and cannot replace the newer revision

#### Scenario: Retry after worker restart
- **WHEN** the worker restarts after a stage succeeded
- **THEN** it reconciles actual stage state and resumes the same operation without duplicating external effects

### Requirement: Explicit tagged routing and secure secret references
The system MUST create explicit agent-owned routes whose tags match issued keys and MUST require tag filtering. Google key plaintext MUST be stored outside source/config artifacts with restricted access. Shared provider keys MUST be identified as sharing upstream project quota. The public API MUST NOT accept shell commands or arbitrary filesystem targets.

#### Scenario: Tag filtering disabled
- **WHEN** candidate configuration lacks enabled tag filtering
- **THEN** validation blocks deployment with an actionable error

#### Scenario: Export configuration
- **WHEN** a route or agent configuration is exported
- **THEN** it contains a secret reference or placeholder and never the provider key plaintext

### Requirement: Deployment consistency and recovery
Apply SHALL use a restricted worker to deploy and check both Gateway instances, register the agent through existing registry transactions and schedule locked refresh. Key issuance/budget setup SHALL be a separate operation after deployment; applied MUST NOT mean access-ready. Success MUST require all deployment stages; partial failure MUST expose the failed stage and recovery result. Failed rollback MUST block subsequent applies until recovery is resolved.

#### Scenario: Second instance fails
- **WHEN** the second instance fails health or revision validation
- **THEN** the operation cannot become applied and attempts to restore the previous configuration on both instances

#### Scenario: Issuance fails after deployment
- **WHEN** key or budget setup fails after deployment and dashboard registration committed
- **THEN** deployment remains separately applied, issuance is failed, any partially created key is revoked and registry/history are preserved without rebuilding the database

#### Scenario: Recovery fails
- **WHEN** restoring a Gateway instance fails
- **THEN** status is recovery-required and new applies are blocked with the unresolved stage visible

### Requirement: Effective secret delivery and registry coordination
The worker MUST render a fixed-service Compose override delivering managed secret variables to both instances, validate referenced variables before startup, preserve legacy required variables and restore secret versions/overrides during rollback. Registry drift detection, apply and YAML export MUST share the existing registry operation lock; DB and file drift MUST both be checked.

#### Scenario: New dedicated provider key
- **WHEN** a profile references a newly stored provider key
- **THEN** both recreated instances receive the required variable and preflight validation passes without logging its value

#### Scenario: CLI changes registered display name
- **WHEN** CLI changes a managed agent name after preview
- **THEN** apply detects DB drift under the registry lock and does not overwrite the change

### Requirement: Issuance response and uncertain outcomes
Key issuance MUST deliver plaintext only through its authenticated live issuance response, not through persistent operation polling. Uncertain issuance outcomes MUST be reconciled by unique operation identity and any unreceived key MUST be revoked before replacement is permitted.

#### Scenario: Crash after key creation
- **WHEN** the worker crashes before delivering an issuance response
- **THEN** recovery locates and revokes the operation's key and does not create another key blindly
