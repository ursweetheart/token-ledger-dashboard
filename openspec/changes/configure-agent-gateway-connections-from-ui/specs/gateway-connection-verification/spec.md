## ADDED Requirements

### Requirement: Agent integration instructions
The system SHALL produce context-specific endpoint, model alias and credential placeholders, X-User instructions, Docker default plus Gateway network configuration and recreate guidance. Single mode SHALL prescribe svc.<code>; multiple mode SHALL prescribe a stable login assigned by the agent server. The UI MUST distinguish generated instructions from changes actually deployed in the external agent.

#### Scenario: Docker agent template
- **WHEN** an admin selects Docker integration for a single-user agent
- **THEN** instructions include both networks, svc.<code>, configured model alias and a Virtual Key placeholder without revealing any saved key

### Requirement: Deliberate verification request
The system MUST require an explicit test action that discloses possible provider cost, send a bounded request with correlation ID, and provide distinct routing, logging and reporting results. Preview and passive page load MUST NOT send provider requests.

#### Scenario: Open the connection page
- **WHEN** an admin opens the page or previews settings
- **THEN** no billable AI request is sent

#### Scenario: Quota rejects test
- **WHEN** a verification request receives quota error 429
- **THEN** UI reports the quota rejection distinctly and does not claim a successful AI connection or retry automatically

### Requirement: Evidence for verified connection
The system MUST only report verified when a successful correlated request has evidence of the expected agent tag and provider route, Gateway token/cost records, and the matching ledger record assigned to that agent after refresh. Missing evidence MUST result in pending within a configured timeout or inconclusive afterward, not inferred success or invented zero cost.

#### Scenario: Successful answer uses wrong project route
- **WHEN** an answer succeeds but recorded provider route differs from the expected reference
- **THEN** verification fails and shows a routing mismatch without revealing credentials

#### Scenario: Ledger ingestion delayed
- **WHEN** the expected Gateway log exists but the correlated ledger row is absent
- **THEN** reporting remains pending until timeout and becomes inconclusive if evidence is still missing

#### Scenario: Complete evidence
- **WHEN** correlated route, tag, tokens, cost and ledger agent assignment all match
- **THEN** UI reports verified with timestamp and sanitized evidence identifiers

#### Scenario: Log lacks provider evidence
- **WHEN** the installed Gateway does not expose the upstream route reference
- **THEN** route verification is inconclusive even if the AI answer and dashboard usage exist

### Requirement: Test credentials and verification scope
Worker tests MUST use the actual agent Virtual Key supplied for that test through a protected transient channel, not the Gateway master key. The system MUST distinguish Gateway verification from deployed external-agent verification. External-agent verification MUST require a correlated request originating from that deployed agent with expected identity. Correlation mapping to Gateway request_id and ledger call_id MUST be evidenced, not assumed from a custom header.

#### Scenario: Worker test succeeds
- **WHEN** a worker-originated test has complete routing and ledger evidence
- **THEN** Gateway verification is verified and external-agent verification remains awaiting an agent-originated request

#### Scenario: Chat quota message returns 200
- **WHEN** HTTP 200 contains a quota stop message with quota-block/failure evidence
- **THEN** verification reports quota rejection rather than AI success and does not retry automatically

#### Scenario: Test key retention
- **WHEN** a test completes or times out
- **THEN** its supplied Virtual Key is discarded and cannot be retrieved from operation storage or logs
