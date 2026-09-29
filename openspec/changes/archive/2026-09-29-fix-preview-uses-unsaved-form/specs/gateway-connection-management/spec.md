## ADDED Requirements

### Requirement: Preview reflects the form on screen
The connection wizard SHALL preview exactly the configuration shown in the form when the admin requests a preview. If the form has unsaved changes or the profile is new, the wizard MUST validate and save the form as a new draft revision before requesting the preview. If the form is unchanged, the wizard MUST NOT save a new revision. Apply MUST stay disabled unless the latest preview was produced from the draft that matches the form.

#### Scenario: Edit without an explicit save
- **WHEN** an admin changes a field of a saved profile and requests a preview without any other action
- **THEN** the draft is saved as a new revision first and the preview shows the changed value

#### Scenario: Unchanged form
- **WHEN** an admin requests a preview for a loaded profile without changing any field
- **THEN** no new revision or audit entry is created and the preview shows the saved draft

#### Scenario: Save rejected
- **WHEN** the form is invalid or the stored revision has changed since the profile was loaded
- **THEN** the error is shown, no preview is requested and Apply stays disabled

#### Scenario: Form changed after preview
- **WHEN** an admin changes any field, adds or removes a model, or imports a provider key after a preview
- **THEN** Apply is disabled until a new preview is produced

### Requirement: Preview summarises changes against the applied profile
Every preview SHALL show, above the full configuration, a summary of the admin-editable fields that differ between the previewed draft and the last applied profile of the same agent, one line per field with the old and new value. The summary MUST state explicitly when nothing differs and when the agent has never been applied, and MUST state that changes made outside the UI are reviewed through reconciliation, not in this summary.

#### Scenario: One field changed
- **WHEN** the applied profile has RPM 15 and the previewed draft has RPM 20
- **THEN** the summary shows a single line for RPM from 15 to 20

#### Scenario: Nothing changed
- **WHEN** the previewed draft equals the applied profile
- **THEN** the summary states that there is no change against the running configuration

#### Scenario: Never applied
- **WHEN** the agent has no applied profile
- **THEN** the summary states that the whole configuration is new

### Requirement: Controls reflect state and report outcomes
Each control in the connection tab SHALL be enabled only when its action can succeed with the current state, and every completed action MUST show an outcome message.

#### Scenario: Drift accepted
- **WHEN** an admin accepts a reviewed baseline
- **THEN** the accept control stays disabled until a new reconciliation review is loaded

#### Scenario: Single key revoked
- **WHEN** an admin revokes one selected key and the revocation succeeds
- **THEN** the tab shows a message naming the revoked key

### Requirement: Credential fields are not autofilled
Password fields in the connection tab (admin credential, provider key, test Virtual Key) SHALL ask the browser not to fill saved values.

#### Scenario: Opening the tab
- **WHEN** the connection tab is opened in a browser that has saved a password for this origin
- **THEN** the admin credential field is empty until the admin types or pastes a value
