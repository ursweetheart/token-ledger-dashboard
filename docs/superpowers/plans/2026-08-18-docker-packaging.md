# Token Ledger Docker Packaging Implementation Plan

> **Trạng thái (06/09/2026):** Đã triển khai lên server thật — anh Trần Xuân Tuấn xác
> nhận dashboard đã chạy trên server, không còn ở giai đoạn kế hoạch. Quyết định đóng
> việc này nằm ở `openspec/changes/close-the-known-gateway-loose-ends/tasks.md` mục 3.
> Hai tham chiếu hỏng trong plan (`scripts/copy_to_postgres.py`,
> `var/token_ledger.sqlite` — cả hai đã bị xoá khỏi repo) giữ nguyên không sửa: plan đã
> thực thi xong, không ai còn chạy theo runbook này nữa nên sửa lại không còn giá trị.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible Docker Compose stack with an Nginx gateway, a non-root FastAPI API, and persistent PostgreSQL, first testable on the Windows VM at `http://127.0.0.1:8080` and later deployable at `https://dashboard.rangdong.com.vn:45501`.

**Architecture:** Nginx is the only public-facing service and serves `web/` while proxying `/api/*` to FastAPI. FastAPI connects to PostgreSQL over an internal Compose network; PostgreSQL stores data in a named volume. SQLite import/audit are explicit one-shot tool services, while secrets, database files, and TLS keys stay outside every image.

**Tech Stack:** Docker Desktop with WSL2 Linux containers, Docker Compose v2, Nginx 1.28 Alpine, Python 3.12 slim, FastAPI/Uvicorn, PostgreSQL 17 Alpine, Node.js built-in test runner, PowerShell smoke tests.

**Spec:** `docs/superpowers/specs/2026-08-18-docker-packaging-design.md`

## Global Constraints

- Target host is Windows 10 Pro 22H2 x64 with WSL2, nested virtualization, and SLAT enabled.
- Production URL is `https://dashboard.rangdong.com.vn:45501`; only host TCP port 45501 may be public.
- `gateway`, `api`, and `postgres` are separate long-running services.
- PostgreSQL 17 data lives in named volume `pgdata`; never use `docker compose down -v` in production.
- API and PostgreSQL must not publish host ports; optional pgAdmin may bind only to host loopback under the explicit `tools` profile.
- Database files, raw data, `.env`, certificates, and private keys must never enter an image or Git.
- Production TLS files are mounted read-only at `/etc/nginx/tls/fullchain.pem` and `/etc/nginx/tls/private.key`.
- Until SSO/access gateway exists, production access remains restricted by company network, VPN, or allowlist.
- Keep existing dashboard business logic and offline fallback behavior unchanged.
- Every task must preserve the existing Node test suite.

---

## File Structure

| File | Responsibility |
|---|---|
| `.dockerignore` | Keep secrets, data, archives, caches, and local state out of build contexts. |
| `docker/api.Dockerfile` | Build the non-root FastAPI runtime and one-shot database tool image. |
| `docker/gateway.Dockerfile` | Build immutable static frontend assets on Nginx. |
| `docker/nginx.local.conf` | Serve local HTTP and proxy same-origin `/api/`. |
| `docker/nginx.prod.conf` | Terminate TLS on container port 443 and proxy `/api/`. |
| `docker-compose.yml` | Define services, internal networks, health checks, tool profiles, and named volumes without publishing the gateway. |
| `docker-compose.local.yml` | Bind local gateway only to `127.0.0.1:8080`. |
| `docker-compose.prod.yml` | Bind host `45501` to gateway `443` and mount TLS files read-only. |
| `web/js/api.js` | Select same-origin API behind the gateway while preserving `?api=` override and file-mode fallback. |
| `.env.example` | Document required Compose/PostgreSQL/TLS values without secrets. |
| `tests/docker-packaging.test.js` | Enforce packaging, security, and configuration contracts. |
| `tests/docker-smoke.ps1` | Validate a running local stack and ensure internal ports are not published. |
| `README.md` | Document build, import, local run, production run, backup, restore, and diagnostics. |

---

### Task 1: Make Hosted Frontend Use the Same-Origin API

**Files:**
- Create: `tests/docker-packaging.test.js`
- Modify: `web/js/api.js:14-45`

**Interfaces:**
- Consumes: existing `?api=<base-url>` query override.
- Produces: `TokenLedgerAPI.base(): string`, returning `""` for HTTP/HTTPS hosting and `http://127.0.0.1:8000` for direct `file://` use.

- [ ] **Step 1: Write the failing same-origin tests**

Create `tests/docker-packaging.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

function loadApi(location) {
  const source = read("web/js/api.js");
  const window = {
    location,
    URLSearchParams,
    console: { warn() {} },
  };
  vm.runInNewContext(source, { window, URLSearchParams, fetch: () => {} }, {
    filename: "web/js/api.js",
  });
  return window.TokenLedgerAPI;
}

test("hosted dashboard uses same-origin API paths", () => {
  const api = loadApi({ protocol: "https:", search: "" });
  assert.equal(api.base(), "");
});

test("file-mode dashboard preserves the local backend fallback", () => {
  const api = loadApi({ protocol: "file:", search: "" });
  assert.equal(api.base(), "http://127.0.0.1:8000");
});

test("api query parameter overrides hosted and file defaults", () => {
  const api = loadApi({
    protocol: "https:",
    search: "?api=https%3A%2F%2Fapi.example.test%2F",
  });
  assert.equal(api.base(), "https://api.example.test");
});
```

- [ ] **Step 2: Run the new tests and verify the hosted case fails**

Run:

```powershell
node --test tests\docker-packaging.test.js
```

Expected: FAIL because HTTPS currently resolves to `http://127.0.0.1:8000`.

- [ ] **Step 3: Implement protocol-aware API base selection**

Replace the API address comment in `web/js/api.js` with:

```javascript
   Địa chỉ backend:
   - HTTP/HTTPS: cùng origin; gateway chuyển /api/* tới FastAPI.
   - file://: giữ backend phát triển tại http://127.0.0.1:8000.
   - Mọi chế độ đều có thể ghi đè bằng ?api=https://may-khac.
```

Replace `DEFAULT_BASE` with:

```javascript
  var DEFAULT_BASE = global.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : "";
```

Keep the existing `base()` query override unchanged.

- [ ] **Step 4: Run focused and regression tests**

```powershell
node --test tests\docker-packaging.test.js tests\date-range-filter.test.js
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the frontend contract**

```powershell
git add web/js/api.js tests/docker-packaging.test.js
git commit -m "fix: use same-origin API behind gateway"
```

## Task 2: Build a secret-safe, non-root API image

**Files:**

- Create: `.dockerignore`
- Create: `docker/api.Dockerfile`
- Modify: `tests/docker-packaging.test.js`

- [ ] **Step 1: Add failing image-contract tests**

Append tests that require:

- `.dockerignore` to exclude `.git/`, `.env`, `data/`, `var/`, database files, private keys, certificate bundles, `secrets/`, and backups while retaining `.env.example`.
- `docker/api.Dockerfile` to start from `python:3.12-slim`, expose port `8000`, switch to `USER tokenledger`, copy only required runtime files, and include the import/audit scripts.
- The Dockerfile not to contain `COPY . .` or another whole-repository copy.

Run:

```powershell
node --test tests\docker-packaging.test.js
```

Expected: FAIL because both packaging files are absent.

- [ ] **Step 2: Add the Docker build-context exclusions**

Create `.dockerignore` with this minimum policy:

```dockerignore
.git/
.github/
.agent/
.claude/
.codex/
.env
.env.*
!.env.example
data/
var/
secrets/
backups/
*.sqlite
*.sqlite3
*.db
*.key
*.pem
*.crt
*.cer
*.pfx
*.p12
__pycache__/
*.pyc
*.log
node_modules/
docs/archive/
planning/
openspec/
tools/
```

This prevents the local database, certificates, private keys, secrets, history, and developer-only files from entering either application image.

- [ ] **Step 3: Add the FastAPI image**

Create `docker/api.Dockerfile`:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system tokenledger \
    && useradd --system --gid tokenledger --home-dir /nonexistent \
       --shell /usr/sbin/nologin tokenledger

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --chown=tokenledger:tokenledger backend/ ./backend/
COPY --chown=tokenledger:tokenledger db/ ./db/
COPY --chown=tokenledger:tokenledger scripts/copy_to_postgres.py ./scripts/copy_to_postgres.py
COPY --chown=tokenledger:tokenledger scripts/audit_db.py ./scripts/audit_db.py

USER tokenledger
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Verify the static contract and build the image**

```powershell
node --test tests\docker-packaging.test.js
docker build -f docker/api.Dockerfile -t token-ledger-api:test .
docker run --rm --entrypoint id token-ledger-api:test
docker run --rm --entrypoint sh token-ledger-api:test -c "test ! -e /app/.env && test ! -e /app/data && test ! -e /app/var"
```

Expected: tests PASS, the reported user is `tokenledger`, and forbidden paths are absent.

- [ ] **Step 5: Commit the API image**

```powershell
git add .dockerignore docker/api.Dockerfile tests/docker-packaging.test.js
git commit -m "build: add non-root FastAPI image"
```

## Task 3: Build the Nginx gateway image

**Files:**

- Create: `docker/gateway.Dockerfile`
- Create: `docker/nginx.local.conf`
- Create: `docker/nginx.prod.conf`
- Modify: `tests/docker-packaging.test.js`

- [ ] **Step 1: Add failing gateway-contract tests**

Append tests that require:

- The gateway image to use `nginx:1.28-alpine`, copy `web/`, and expose `80` and `443`.
- Both Nginx configurations to proxy `/api/` to `http://api:8000` without stripping `/api`.
- The local configuration to listen on HTTP port `80`.
- The production configuration to listen on `443 ssl`, use `dashboard.rangdong.com.vn`, and load `/etc/nginx/tls/fullchain.pem` plus `/etc/nginx/tls/private.key`.
- Static files to be served with `try_files`, while API responses use `Cache-Control: no-store`.

Run:

```powershell
node --test tests\docker-packaging.test.js
```

Expected: FAIL because the gateway files do not exist.

- [ ] **Step 2: Add the gateway Dockerfile**

Create `docker/gateway.Dockerfile`:

```dockerfile
FROM nginx:1.28-alpine

COPY docker/nginx.local.conf /etc/nginx/conf.d/default.conf
COPY web/ /usr/share/nginx/html/

EXPOSE 80 443
```

- [ ] **Step 3: Add the local Nginx configuration**

Create `docker/nginx.local.conf` with:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store" always;
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
```

The absence of a URI suffix on `proxy_pass` is intentional: `/api/...` must reach FastAPI unchanged.

- [ ] **Step 4: Add the production TLS configuration**

Create `docker/nginx.prod.conf` with the same static and proxy locations plus:

```nginx
listen 443 ssl;
server_name dashboard.rangdong.com.vn;
ssl_certificate /etc/nginx/tls/fullchain.pem;
ssl_certificate_key /etc/nginx/tls/private.key;
ssl_protocols TLSv1.2 TLSv1.3;
add_header Strict-Transport-Security "max-age=31536000" always;
```

- [ ] **Step 5: Validate both Nginx configurations**

```powershell
node --test tests\docker-packaging.test.js
docker build -f docker/gateway.Dockerfile -t token-ledger-gateway:test .
docker run --rm token-ledger-gateway:test nginx -t
```

Expected: static tests PASS and the local configuration reports valid syntax. Full production `nginx -t` is deferred until real certificates are mounted because Nginx opens certificate files during configuration validation.

- [ ] **Step 6: Commit the gateway image**

```powershell
git add docker/gateway.Dockerfile docker/nginx.local.conf docker/nginx.prod.conf tests/docker-packaging.test.js
git commit -m "build: add Nginx gateway image"
```

## Task 4: Orchestrate the runtime and one-shot database tools

**Files:**

- Modify: `docker-compose.yml`
- Create: `docker-compose.local.yml`
- Create: `docker-compose.prod.yml`
- Modify: `.env.example`
- Modify: `tests/docker-packaging.test.js`

- [ ] **Step 1: Add failing rendered-Compose tests**

Import `node:child_process` in `tests/docker-packaging.test.js` and add a helper that renders an override as JSON:

```javascript
function composeConfig(override) {
  return JSON.parse(childProcess.execFileSync(
    "docker",
    ["compose", "-f", "docker-compose.yml", "-f", override,
      "config", "--format", "json"],
    {
      cwd: ROOT,
      encoding: "utf8",
      env: {
        ...process.env,
        PGPASSWORD: "0123456789abcdef0123456789abcdef",
        PGADMIN_PASSWORD: "0123456789abcdef0123456789abcdef",
        TLS_CERT_FILE: "C:/certs/fullchain.pem",
        TLS_KEY_FILE: "C:/certs/private.key",
      },
    },
  ));
}
```

Add tests that assert:

- `api` and `postgres` publish no host ports.
- The `data` network has `internal: true` and Postgres mounts named volume `pgdata` at `/var/lib/postgresql/data`.
- The local override publishes only gateway `127.0.0.1:8080 -> 80`.
- The production override publishes only gateway `0.0.0.0:45501 -> 443` and mounts both TLS files read-only.
- `db-import`, `db-audit`, and `pgadmin` are in the explicit `tools` profile.
- Both rendered configurations contain health checks for `postgres`, `api`, and `gateway`.

Run:

```powershell
node --test tests\docker-packaging.test.js
```

Expected: FAIL against the existing database-only Compose file.

- [ ] **Step 2: Replace the base Compose model**

Replace `docker-compose.yml` with:

```yaml
name: token-ledger

x-api-image: &api-image
  image: token-ledger-api:${APP_TAG:-local}
  build:
    context: .
    dockerfile: docker/api.Dockerfile

x-dsn: &dsn postgresql://${PGUSER:-token}:${PGPASSWORD:?Set PGPASSWORD in .env}@postgres:5432/${PGDATABASE:-token_ledger}

services:
  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${PGDATABASE:-token_ledger}
      POSTGRES_USER: ${PGUSER:-token}
      POSTGRES_PASSWORD: ${PGPASSWORD:?Set PGPASSWORD in .env}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PGUSER:-token} -d ${PGDATABASE:-token_ledger}"]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 10s

  api:
    <<: *api-image
    restart: unless-stopped
    environment:
      TOKEN_LEDGER_DSN: *dsn
    networks:
      - edge
      - data
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 10s
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true

  gateway:
    image: token-ledger-gateway:${APP_TAG:-local}
    build:
      context: .
      dockerfile: docker/gateway.Dockerfile
    restart: unless-stopped
    networks:
      - edge
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://127.0.0.1/"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 5s
    security_opt:
      - no-new-privileges:true

  db-import:
    <<: *api-image
    profiles: ["tools"]
    restart: "no"
    environment:
      PGHOST: postgres
      PGPORT: 5432
      PGDATABASE: ${PGDATABASE:-token_ledger}
      PGUSER: ${PGUSER:-token}
      PGPASSWORD: ${PGPASSWORD:?Set PGPASSWORD in .env}
    command: ["python", "scripts/copy_to_postgres.py", "--nguon", "/import/token_ledger.sqlite"]
    volumes:
      - type: bind
        source: ${SQLITE_SOURCE:-./var/token_ledger.sqlite}
        target: /import/token_ledger.sqlite
        read_only: true
    networks:
      - data
    depends_on:
      postgres:
        condition: service_healthy
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true

  db-audit:
    <<: *api-image
    profiles: ["tools"]
    restart: "no"
    environment:
      TOKEN_LEDGER_DSN: *dsn
    command:
      - python
      - scripts/audit_db.py
      - --db
      - *dsn
    networks:
      - data
    depends_on:
      postgres:
        condition: service_healthy
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true

  pgadmin:
    image: dpage/pgadmin4:8
    profiles: ["tools"]
    restart: unless-stopped
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL:-admin@example.com}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:?Set PGADMIN_PASSWORD in .env}
      PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: "False"
      PGADMIN_CONFIG_SERVER_MODE: "False"
    ports:
      - "127.0.0.1:${PGADMIN_PORT:-5050}:80"
    volumes:
      - pgadmin:/var/lib/pgadmin
      - ./docker/pgadmin-servers.json:/pgadmin4/servers.json:ro
    networks:
      - data
    depends_on:
      postgres:
        condition: service_healthy

networks:
  edge:
  data:
    internal: true

volumes:
  pgdata:
  pgadmin:
```

Use `PGHOST=postgres` for the importer because that script builds its default destination DSN from the standard PostgreSQL environment variables. The audit command receives the same anchored DSN as the API.

- [ ] **Step 3: Add the local-only port override**

Create `docker-compose.local.yml`:

```yaml
services:
  gateway:
    ports:
      - target: 80
        published: "${LOCAL_PORT:-8080}"
        host_ip: 127.0.0.1
        protocol: tcp
```

- [ ] **Step 4: Add the production TLS/port override**

Create `docker-compose.prod.yml`:

```yaml
services:
  gateway:
    ports:
      - target: 443
        published: "${PUBLIC_PORT:-45501}"
        host_ip: 0.0.0.0
        protocol: tcp
    volumes:
      - type: bind
        source: ${TLS_CERT_FILE:?Set TLS_CERT_FILE in .env}
        target: /etc/nginx/tls/fullchain.pem
        read_only: true
      - type: bind
        source: ${TLS_KEY_FILE:?Set TLS_KEY_FILE in .env}
        target: /etc/nginx/tls/private.key
        read_only: true
      - type: bind
        source: ./docker/nginx.prod.conf
        target: /etc/nginx/conf.d/default.conf
        read_only: true
    healthcheck:
      test: ["CMD", "wget", "--no-check-certificate", "-q", "--spider", "https://127.0.0.1/"]
```

- [ ] **Step 5: Extend the environment template without real secrets**

Keep the existing upstream application settings in `.env.example`, then replace its database section with documented empty/placeholder deployment settings:

```dotenv
PGDATABASE=token_ledger
PGUSER=token
PGPASSWORD=
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=
PGADMIN_PORT=5050
LOCAL_PORT=8080
PUBLIC_PORT=45501
TLS_CERT_FILE=C:/certs/dashboard/fullchain.pem
TLS_KEY_FILE=C:/certs/dashboard/private.key
SQLITE_SOURCE=./var/token_ledger.sqlite
APP_TAG=local
```

Document this PowerShell secret generator immediately above the password fields:

```powershell
-join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
```

The hexadecimal output avoids URI-reserved characters in the PostgreSQL DSN.

- [ ] **Step 6: Render and validate both Compose variants**

```powershell
$env:PGPASSWORD = '0123456789abcdef0123456789abcdef'
$env:PGADMIN_PASSWORD = '0123456789abcdef0123456789abcdef'
$env:TLS_CERT_FILE = 'C:/certs/dashboard/fullchain.pem'
$env:TLS_KEY_FILE = 'C:/certs/dashboard/private.key'
docker compose -f docker-compose.yml -f docker-compose.local.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
node --test tests\docker-packaging.test.js
```

Expected: both Compose variants parse, required variables resolve, and all contract tests PASS.

- [ ] **Step 7: Commit the orchestration layer**

```powershell
git add docker-compose.yml docker-compose.local.yml docker-compose.prod.yml .env.example tests/docker-packaging.test.js
git commit -m "build: compose gateway API and persistent database"
```

## Task 5: Add an operator smoke test and deployment runbook

**Files:**

- Create: `tests/docker-smoke.ps1`
- Modify: `tests/docker-packaging.test.js`
- Modify: `README.md`

- [ ] **Step 1: Add failing documentation-contract tests**

Append static tests requiring the README to document:

- Windows/WSL2/Docker prerequisites and Linux-container verification.
- Local startup and `http://127.0.0.1:8080`.
- Explicit one-shot import and audit commands.
- Backup and restore commands.
- Production startup and `https://dashboard.rangdong.com.vn:45501`.
- The warning that `docker compose down -v` deletes database volumes.
- The warning that `db-import` rebuilds the target schema and must run only during a maintenance window after a backup.

Also require `tests/docker-smoke.ps1` to request `/` and `/api/health`, validate `ranges` and `warnings`, inspect container health, and ensure neither API nor Postgres publishes a host port.

Run:

```powershell
node --test tests\docker-packaging.test.js
```

Expected: FAIL because the smoke test and runbook are incomplete.

- [ ] **Step 2: Create the PowerShell smoke test**

Create `tests/docker-smoke.ps1` with a `-BaseUrl` parameter defaulting to `http://127.0.0.1:8080`. It must:

1. Fail on any PowerShell error.
2. Request the frontend root and require HTTP 200.
3. Request `$BaseUrl/api/health`, requiring the JSON object to contain `ranges` and `warnings`.
4. Use `docker compose -f docker-compose.yml -f docker-compose.local.yml ps --format json` to require running/healthy `gateway`, `api`, and `postgres` containers.
5. Call `docker compose ... port api 8000` and `docker compose ... port postgres 5432`; treat any non-empty output as a failure even if Docker returns a non-zero status for an unpublished port.
6. Print a compact success summary containing the URL and service names.

Do not require pgAdmin: it is an optional `tools` profile and, when enabled, is intentionally published only on loopback.

- [ ] **Step 3: Document prerequisites and local packaging**

Add a `Docker deployment` section to `README.md` with exact PowerShell commands:

```powershell
wsl --update
docker version
docker info --format 'Server={{.ServerVersion}}; OS={{.OSType}}; Arch={{.Architecture}}'
Copy-Item .env.example .env
notepad .env
docker compose -f docker-compose.yml -f docker-compose.local.yml config
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
powershell -ExecutionPolicy Bypass -File tests/docker-smoke.ps1
```

The expected Docker server result is `OS=linux`. State that the Docker Desktop setting `Use the WSL 2 based engine` must be enabled and Windows Containers must not be selected.

- [ ] **Step 4: Document first import and auditing**

Document the maintenance sequence:

```powershell
docker compose up -d postgres
docker compose --profile tools run --rm db-import
docker compose --profile tools run --rm db-audit
```

Explain that `db-import` reads the SQLite bind mount read-only but drops and recreates the PostgreSQL `public` schema. It must not be used as a routine application startup command.

- [ ] **Step 5: Document backup and restore**

Use a timestamped custom-format dump inside the Postgres container, then copy it to the host:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/token-ledger.dump'
New-Item -ItemType Directory -Force backups | Out-Null
docker compose cp postgres:/tmp/token-ledger.dump "backups/token-ledger-$stamp.dump"
docker compose exec -T postgres rm -f /tmp/token-ledger.dump
```

Document restore as an explicit maintenance operation:

```powershell
docker compose stop gateway api
docker compose cp .\backups\token-ledger-YYYYMMDD-HHMMSS.dump postgres:/tmp/restore.dump
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/restore.dump'
docker compose exec -T postgres rm -f /tmp/restore.dump
docker compose --profile tools run --rm db-audit
docker compose start api gateway
```

- [ ] **Step 6: Document production configuration and verification**

Document that the administrator must provide certificate and key files matching `dashboard.rangdong.com.vn`, map internal DNS to `192.168.20.111`, and allow TCP `45501` only from the intended company network/VPN. The application has no login layer, so it must not be exposed directly to the public Internet.

State that Nginx expects a PEM certificate chain and an unencrypted PEM private key at the paths configured by `TLS_CERT_FILE` and `TLS_KEY_FILE`. If the company supplies `.pfx`/`.p12`, coordinate its conversion outside the repository, protect the export password, and never commit either the bundle or extracted key.

Use:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl.exe -k https://dashboard.rangdong.com.vn:45501/api/health
```

Explain that `-k` is only a connectivity check before the corporate trust chain is installed. Normal browser and API use must validate the certificate without bypassing TLS.

- [ ] **Step 7: Add safety and troubleshooting notes**

Include:

- `docker compose down` stops/removes containers but retains `pgdata`.
- Never run `docker compose down -v` unless permanent database deletion is intentional and a restore has been tested.
- `docker compose logs --tail 200 gateway api postgres` for diagnosis.
- Certificate filenames and paths belong in `.env`; certificate/private-key bytes never belong in Git or either image.
- Database password changes do not alter an already-initialized Postgres volume; follow a deliberate password-rotation procedure instead of deleting the volume.

- [ ] **Step 8: Run documentation and regression tests**

```powershell
node --test tests\docker-packaging.test.js
node --test
```

Expected: all static packaging tests and existing frontend tests PASS.

- [ ] **Step 9: Commit the runbook and smoke test**

```powershell
git add README.md tests/docker-smoke.ps1 tests/docker-packaging.test.js
git commit -m "docs: add Docker operations and smoke checks"
```

## Task 6: Prove the package end to end

**Files:**

- Modify only if verification exposes a defect in files from Tasks 1-5.

- [ ] **Step 1: Verify the Docker runtime target**

```powershell
docker version
docker info --format 'Server={{.ServerVersion}}; OS={{.OSType}}; Arch={{.Architecture}}'
```

Expected: the Docker server is reachable and reports `OS=linux`, normally `Arch=x86_64` on this VM.

- [ ] **Step 2: Validate and build both deployment variants**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.local.yml build --pull
```

Expected: both models render and both application images build successfully. Production containers are not started until real certificate files exist at the configured paths.

- [ ] **Step 3: Start Postgres and perform the controlled initial import**

Confirm `SQLITE_SOURCE` points to the approved source database, then run:

```powershell
docker compose up -d postgres
docker compose ps
docker compose --profile tools run --rm db-import
docker compose --profile tools run --rm db-audit
```

Expected: Postgres becomes healthy, import completes, and audit reports no `HONG` failures. Stop if the approved SQLite source is unavailable; do not manufacture or substitute production data.

- [ ] **Step 4: Start and smoke-test the local stack**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
powershell -ExecutionPolicy Bypass -File tests/docker-smoke.ps1
docker compose -f docker-compose.yml -f docker-compose.local.yml logs --tail 100 gateway api postgres
```

Expected: all three runtime services are healthy, root HTML loads, `/api/health` returns data metadata, and logs contain no startup error.

- [ ] **Step 5: Prove named-volume persistence**

Record the database row count, recreate the containers without `-v`, then compare:

```powershell
$before = docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM fact_usage_daily;"'
docker compose -f docker-compose.yml -f docker-compose.local.yml down
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
$after = docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM fact_usage_daily;"'
if ($before.Trim() -ne $after.Trim()) { throw "pgdata did not persist" }
```

Expected: the before/after counts are identical and the stack returns healthy.

- [ ] **Step 6: Verify isolation and image contents**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml port api 8000
docker compose -f docker-compose.yml -f docker-compose.local.yml port postgres 5432
docker run --rm --entrypoint sh token-ledger-api:local -c "test ! -e /app/.env && test ! -e /app/data && test ! -e /app/var"
docker image inspect token-ledger-api:local token-ledger-gateway:local
```

Expected: API/Postgres port queries return no published address, secret/data paths are absent, and image metadata targets Linux images.

- [ ] **Step 7: Run the final verification suite**

```powershell
node --test
powershell -ExecutionPolicy Bypass -File tests/docker-smoke.ps1
git diff --check
git status --short
```

Expected: all tests PASS, smoke checks PASS, no whitespace errors are reported, and only intentional changes remain.

- [ ] **Step 8: Commit only verification-driven corrections**

If any defect was found, fix it with the smallest targeted change, rerun the failing command plus the final suite, and commit:

```powershell
git add --patch
git commit -m "fix: correct Docker deployment verification"
```

Do not create an empty verification commit when no correction was necessary.
