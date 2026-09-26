# Connecting an Agent to the Gateway — Simple English Guide

This guide explains [noi-agent-vao-gateway-hai-phia.md](docs/reference/noi-agent-vao-gateway-hai-phia.md) in simple English.

The original document is dated September 23, 2026. Its notes about the current setup describe that snapshot. This guide explains the document; it does not report a new check of the running system.

The main idea is to connect an AI app (an **agent**) to the Gateway and show its usage on the dashboard.

Think of the Gateway as a shared front desk. Your app sends an AI request to it. The Gateway checks access, chooses the right Google model, and records usage and cost.

## 1. What “two directions” means

There are two separate flows:

```text
Getting an answer:
Agent → Gateway → Google AI
Agent ← Gateway ← AI answer

Showing usage:
Gateway logs → ledger-refresh → Dashboard
```

The Gateway does not start a new call back to the agent. It returns the answer to the agent’s original request.

The agent can work even if dashboard setup is missing. Usage stays in the Gateway logs and can be loaded later.

## 2. What you need before starting

Prepare five things:

- An agent code, such as `dms-feedback`.
- A display name that people can read.
- A Google Cloud project.
- Whether the app serves one shared identity or many named users.
- A shared Google API key or a separate key for this project.

The agent code connects records across the system, so choose it early and use it consistently.

## 3. What changes inside the agent

The agent must send its AI requests through the Gateway. Each request includes:

| Value | Simple meaning |
|---|---|
| Virtual Key | The agent’s access key for the Gateway |
| Model alias | A short model name that the Gateway knows |
| `X-User` | Who is using the agent |

The Virtual Key is different from the Google API key. The agent uses the Virtual Key; the Gateway holds the Google key.

For a shared service, `X-User` looks like `svc.dms-feedback`. For an app with many users, it contains the current user’s login name.

The document also says to:

- Keep the old connection option so you can switch back.
- Avoid automatic retries at both layers, because they can multiply requests.
- Connect the agent to the Gateway’s Docker network while keeping its own network.
- Recreate the container after changing environment settings.
- Check whether an answer was cut short before trying to read it as complete output.

## 4. What changes inside the Gateway

The Gateway needs a **route**: a rule saying which model and Google key to use.

A **tag** is the agent’s identifying label. The route and Virtual Key must carry the correct tag, and tag filtering must be enabled. Otherwise, a request may succeed while using the wrong project’s key.

When adding a separate Google key, several files must be updated so the containers receive it and check that it exists. The test setup also needs a matching dummy value.

Then recreate both Gateway instances and issue a Virtual Key. Save that key safely when it is created.

## 5. How spending limits work

Set the agent’s spending limit in the dashboard’s Settings tab. According to the document, an agent without a configured limit will not be stopped by this quota system.

When the limit is reached:

- A chat app can receive a readable message explaining that it has reached its limit.
- An automated app receives error `429`, so its code can handle the stop.

This distinction matters: an automated app expecting JSON may fail if it receives a normal sentence instead.

## 6. What changes inside the dashboard

For a new Gateway-only agent, edit `config/gateway-agents.yaml`: code, name,
single/multiple user mode, start date and active state. No Google project or
downloaded billing, monitoring or user-directory files are required.

If that match is missing, the dashboard loader skips the record.

After the one-time schema upgrade, run `scripts/apply_gateway_agents.py --dry-run`,
then the same command without `--dry-run`, then `scripts/refresh_gateway.py`.
Saving YAML alone does not update the database. **Do not rebuild the database.**

The `ledger-refresh` service loads new usage. For multiple users, it discovers
agent-scoped IDs from Gateway logs; these are observed IDs, not a staff directory.
New models can be registered automatically. See the complete commands and
safety rules in [the registration runbook](docs/reference/gateway-agent-registration.md).

## 7. How to check that everything works

The document asks for four checks:

1. Send ten real requests and confirm they succeed.
2. Find ten matching Gateway log records with token and cost values.
3. Use a temporary wrong-tag route to check that requests never reach it. Remove that test route afterward and recreate the Gateway instances.
4. Run the dashboard loader and confirm no records are skipped and usage appears. Stop the automatic refresh service first so the two runs do not overlap.

Its central warning is that **a successful AI answer does not prove the whole setup is correct**. Requests can succeed while costs go to the wrong project or usage is missing from the dashboard.

## 8. How to disconnect later

Switch the agent’s backend setting and recreate its container, or revoke its Virtual Key through the Gateway API.

Keep its historical dashboard records and mark the agent inactive.
