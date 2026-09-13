const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

test("runtime database default is token_ledger_v2 everywhere", () => {
  assert.equal(1, 2, "CO Y LAM HONG de kiem CI co do khong -- se hoan tac ngay");
  const connect = read("db/connect.py");
  const compose = read("docker-compose.yml");
  const example = read(".env.example");
  const pgadmin = JSON.parse(read("docker/pgadmin-servers.json"));

  assert.match(
    connect,
    /PG_DATABASE = os\.environ\.get\("PGDATABASE", "token_ledger_v2"\)/,
  );
  assert.match(compose, /POSTGRES_DB: \$\{PGDATABASE:-token_ledger_v2\}/);
  assert.match(
    compose,
    /pg_isready -U \$\{PGUSER:-token\} -d \$\{PGDATABASE:-token_ledger_v2\}/,
  );
  assert.match(example, /^# PGDATABASE=token_ledger_v2$/m);
  assert.equal(pgadmin.Servers["1"].MaintenanceDB, "token_ledger_v2");
});

test("LiteLLM keeps its operational database separate from both ledgers", () => {
  const compose = read("docker-compose.yml");

  assert.match(
    compose,
    /DATABASE_URL: "postgresql:\/\/\$\{GATEWAY_PGUSER:-llmproxy\}:[^\n]+\/\$\{GATEWAY_PGDATABASE:-litellm\}"/,
  );
  assert.match(compose, /GW_DB: \$\{GATEWAY_PGDATABASE:-litellm\}/);
});