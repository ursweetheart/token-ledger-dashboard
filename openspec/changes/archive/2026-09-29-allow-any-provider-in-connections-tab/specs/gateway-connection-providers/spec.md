## ADDED Requirements

### Requirement: Provider and model catalog from the pinned Gateway
The worker SHALL build the provider/model catalog from `GET /public/litellm_model_cost_map` and `GET /public/providers` of a configured Gateway instance, keeping only entries whose `mode` is `chat`. A provider is valid only when it is the routing prefix of at least one routable chat name (see catalog name normalization) and appears in `/public/providers`; the `litellm_provider` field alone MUST NOT define a provider, because it contains non-routable values such as `vertex_ai-language-models`. The catalog MUST NOT be read from the OpenRouter catalog (`ref_model_catalog`) and MUST NOT fall back to accepting any name when the Gateway catalog is unavailable. A concrete upstream already present in the deployed route configuration MUST remain valid even if it is absent from the catalog, so a catalog refresh cannot invalidate an applied profile.

#### Scenario: Catalog unavailable during preview
- **WHEN** the Gateway catalog request fails or returns a non-object body
- **THEN** preview fails with an actionable error, no configuration is written and no model is treated as valid

#### Scenario: Non-chat model requested
- **WHEN** a profile names a model whose catalog entry has a mode other than `chat`
- **THEN** preview rejects that model entry

#### Scenario: Deployed model missing from a newer catalog
- **WHEN** an applied profile uses `gemini/gemini-3.5-flash-lite`, which is in the deployed route configuration, and the current catalog no longer lists it
- **THEN** preview still accepts that entry

### Requirement: Provider-scoped model entries
Each model entry SHALL have an upstream of either `<provider>/*` or `<provider>/<model>`. Saving a draft MUST reject a bare `*`, an asterisk anywhere other than the whole segment after the first `/`, and characters outside the existing allowed set. For a wildcard upstream the alias MUST equal the upstream. Preview MUST reject a provider absent from the catalog and a concrete model absent from that provider's catalog entries. Routes produced from wildcard entries MUST carry exactly the agent's tag, like concrete routes.

#### Scenario: Provider wildcard accepted
- **WHEN** an admin saves and previews an entry with alias `anthropic/*` and upstream `anthropic/*`, and `anthropic` has chat models in the catalog
- **THEN** preview proposes a route `model_name: anthropic/*`, `model: anthropic/*` tagged with the agent code

#### Scenario: Bare or misplaced wildcard
- **WHEN** an admin saves an upstream `*`, `gemini/*-flash` or an alias `foo/*` for upstream `anthropic/*`
- **THEN** the draft is rejected with a field-specific error and the applied configuration is unchanged

#### Scenario: Misspelled provider
- **WHEN** an admin previews an entry with upstream `antropic/*`
- **THEN** preview rejects it because `antropic` is not a catalog provider

### Requirement: Catalog name normalization
When a chat catalog key contains `/`, its routable name SHALL be the key unchanged and its provider the text before the first `/`. When the key has no `/`, its routable name SHALL be `<litellm_provider>/<key>`. In both cases the entry MUST be excluded when the resulting provider is not listed by `/public/providers`. Model suggestions shown to the admin MUST use the routable name.

#### Scenario: Anthropic model without prefix
- **WHEN** the catalog has key `claude-haiku-4-5` with `litellm_provider: anthropic`
- **THEN** the admin sees and may save `anthropic/claude-haiku-4-5`, and preview accepts it

#### Scenario: Non-routable provider label
- **WHEN** the catalog has key `gemini-2.5-flash` with `litellm_provider: vertex_ai-language-models`, which `/public/providers` does not list
- **THEN** no routable name is produced from that entry and `vertex_ai-language-models` is not offered as a provider

### Requirement: Unrestricted-model Virtual Keys with tag isolation
Virtual Keys issued from the connections tab SHALL carry `models: ["*"]` and `metadata.tags` equal to exactly the agent code. Preview MUST list every deployed route without an identity tag, because such routes are reachable by any `*` key.

#### Scenario: Issue a key
- **WHEN** an admin issues a key for an applied profile
- **THEN** the Gateway key has models `["*"]` and tags `[<agent code>]`, and the plaintext is returned only in the issuance response

#### Scenario: Untagged legacy route exists
- **WHEN** preview runs while the deployed configuration contains a route without tags
- **THEN** preview lists that route name as reachable by the agent's key

### Requirement: Concrete model for verification and agent template
Gateway verification and the agent configuration template SHALL use a concrete model name. When the profile has a concrete entry, the alias of the first concrete entry MUST be used and verification MUST expect that entry's route. When every entry is a wildcard, verification MUST require the admin to supply a concrete catalog model under one of the profile's wildcard providers and MUST expect the route of that provider's wildcard entry, and the template MUST show a placeholder instead of a wildcard.

#### Scenario: Wildcard-only profile verification
- **WHEN** an admin starts verification for a profile whose only entry is `anthropic/*` without choosing a test model
- **THEN** verification is rejected before any provider request is sent

#### Scenario: Test model outside the wildcard provider
- **WHEN** the admin chooses test model `openai/gpt-5-mini` for a profile whose only entry is `anthropic/*`
- **THEN** verification is rejected before any provider request is sent

### Requirement: Provider-neutral connection form
The connection form SHALL label the provider secret and model fields without naming Google, SHALL offer the catalog providers for selection and SHALL describe a shared secret reference as sharing the upstream provider account quota rather than a Google project.

#### Scenario: Admin opens a new profile
- **WHEN** the admin opens the connections tab with a reachable Gateway catalog
- **THEN** the provider list contains the catalog providers and no field label is specific to Google
