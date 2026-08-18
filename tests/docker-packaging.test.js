const test = require("node:test");
const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const API_PATH = path.join(ROOT, "web", "js", "api.js");
const SMOKE_PUBLISHER_TEST_PATH = path.join(
  ROOT,
  "tests",
  "docker-smoke-publishers.test.ps1",
);
const powershellExecutable = ["powershell.exe", "pwsh"].find((candidate) => {
  try {
    childProcess.execFileSync(candidate, ["-NoProfile", "-Command", "exit 0"], {
      stdio: "ignore",
    });
    return true;
  } catch {
    return false;
  }
});
const composeAvailable = (() => {
  try {
    childProcess.execFileSync("docker", ["compose", "version"], {
      stdio: "ignore",
    });
    return true;
  } catch {
    return false;
  }
})();

function composeConfig(override) {
  return JSON.parse(childProcess.execFileSync(
    "docker",
    [
      "compose",
      "-f",
      "docker-compose.yml",
      "-f",
      override,
      "config",
      "--format",
      "json",
    ],
    {
      cwd: ROOT,
      encoding: "utf8",
      env: {
        ...process.env,
        PGDATABASE: "token_ledger_test",
        PGUSER: "token_admin_test",
        PGPASSWORD: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        API_PGUSER: "token_reader_test",
        API_PGPASSWORD: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        PGADMIN_PASSWORD: "cccccccccccccccccccccccccccccccc",
        LOCAL_PORT: "8080",
        PUBLIC_PORT: "45501",
        TLS_CERT_FILE: "C:/controlled-certs/fullchain.pem",
        TLS_KEY_FILE: "C:/controlled-certs/private.key",
      },
    },
  ));
}

function publishedPorts(service) {
  return (service.ports ?? []).map(({ target, published, host_ip, protocol }) => ({
    target,
    published,
    host_ip,
    protocol,
  }));
}

function networkNames(service) {
  return Array.isArray(service.networks)
    ? service.networks
    : Object.keys(service.networks ?? {});
}

function normalizedMountSource(source) {
  return path.normalize(path.resolve(ROOT, source));
}

function readOnlyBindMounts(service) {
  return (service.volumes ?? [])
    .filter(({ type }) => type === "bind")
    .map(({ source, target, read_only }) => ({
      source: normalizedMountSource(source),
      target,
      read_only,
    }));
}

function loadApi(protocol, search) {
  const window = {
    location: { protocol, search },
    URLSearchParams,
    console: { warn() {} },
  };
  const source = fs.readFileSync(API_PATH, "utf8");
  vm.runInNewContext(source, { window, URLSearchParams }, { filename: API_PATH });
  return window.TokenLedgerAPI;
}

test("hosted HTTP and HTTPS use the same-origin API", () => {
  for (const protocol of ["http:", "https:"]) {
    assert.equal(loadApi(protocol, "").base(), "");
  }
});

test("file mode preserves the local API fallback", () => {
  assert.equal(loadApi("file:", "").base(), "http://127.0.0.1:8000");
});

test("api query parameter overrides hosted and file defaults", () => {
  const search = "?api=https%3A%2F%2Fapi.example.test%2F";
  assert.equal(loadApi("https:", search).base(), "https://api.example.test");
  assert.equal(loadApi("file:", search).base(), "https://api.example.test");
});

test("smoke publisher classification distinguishes exposure from host bindings", {
  skip: !powershellExecutable,
}, () => {
  childProcess.execFileSync(
    powershellExecutable,
    [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      SMOKE_PUBLISHER_TEST_PATH,
    ],
    {
      cwd: ROOT,
      encoding: "utf8",
      stdio: "pipe",
    },
  );
});

test("local Compose keeps API and Postgres private and exposes only the local gateway", { skip: !composeAvailable }, () => {
  const config = composeConfig("docker-compose.local.yml");
  const { services } = config;

  assert.deepEqual(services.api.ports ?? [], []);
  assert.deepEqual(services.postgres.ports ?? [], []);
  assert.deepEqual(networkNames(services.gateway), ["edge"]);
  assert.equal(config.networks.data.internal, true);
  assert.ok(services.postgres.volumes.some((volume) =>
    volume.type === "volume"
    && volume.source === "pgdata"
    && volume.target === "/var/lib/postgresql/data"));
  assert.deepEqual(publishedPorts(services.gateway), [{
    target: 80,
    published: "8080",
    host_ip: "127.0.0.1",
    protocol: "tcp",
  }]);
  assert.deepEqual(
    publishedPorts(services.pgadmin).map(({ target, host_ip, protocol }) => ({
      target,
      host_ip,
      protocol,
    })),
    [{ target: 80, host_ip: "127.0.0.1", protocol: "tcp" }],
  );
});

test("production Compose exposes TLS gateway only with exact read-only mounts", { skip: !composeAvailable }, () => {
  const { services } = composeConfig("docker-compose.prod.yml");

  assert.deepEqual(services.api.ports ?? [], []);
  assert.deepEqual(services.postgres.ports ?? [], []);
  assert.deepEqual(networkNames(services.gateway), ["edge"]);
  assert.deepEqual(publishedPorts(services.gateway), [{
    target: 443,
    published: "45501",
    host_ip: "0.0.0.0",
    protocol: "tcp",
  }]);
  assert.deepEqual(readOnlyBindMounts(services.gateway), [
    {
      source: normalizedMountSource("C:/controlled-certs/fullchain.pem"),
      target: "/etc/nginx/tls/fullchain.pem",
      read_only: true,
    },
    {
      source: normalizedMountSource("C:/controlled-certs/private.key"),
      target: "/etc/nginx/tls/private.key",
      read_only: true,
    },
    {
      source: normalizedMountSource(path.join(ROOT, "docker", "nginx.prod.conf")),
      target: "/etc/nginx/conf.d/default.conf",
      read_only: true,
    },
  ]);
});

test("rendered Compose services place database tools in the tools profile and healthcheck the runtime", { skip: !composeAvailable }, () => {
  for (const override of ["docker-compose.local.yml", "docker-compose.prod.yml"]) {
    const config = composeConfig(override);
    const { services } = config;
    const readerDsn = "postgresql://token_reader_test:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@postgres:5432/token_ledger_test";

    for (const service of ["db-import", "db-grant", "db-audit", "pgadmin"]) {
      assert.deepEqual(services[service].profiles, ["tools"]);
    }
    for (const service of ["postgres", "api", "gateway"]) {
      assert.ok(services[service].healthcheck);
    }

    assert.equal(services.api.environment.TOKEN_LEDGER_DSN, readerDsn);
    assert.equal(services["db-audit"].environment.TOKEN_LEDGER_DSN, readerDsn);
    assert.equal(services["db-audit"].command.at(-1), readerDsn);
    assert.ok(!JSON.stringify(services.api).includes("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));
    assert.ok(!JSON.stringify(services["db-audit"]).includes("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"));
    assert.equal(services.postgres.environment.POSTGRES_USER, "token_admin_test");
    assert.equal(
      services.postgres.environment.POSTGRES_PASSWORD,
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    );
    assert.equal(services["db-import"].environment.PGUSER, "token_admin_test");
    assert.equal(
      services["db-import"].environment.PGPASSWORD,
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    );

    const grantService = services["db-grant"];
    assert.deepEqual(networkNames(grantService), ["data"]);
    assert.deepEqual(grantService.ports ?? [], []);
    assert.equal(grantService.depends_on.postgres.condition, "service_healthy");
    assert.equal(grantService.read_only, true);
    assert.deepEqual(readOnlyBindMounts(grantService), [{
      source: normalizedMountSource(path.join(ROOT, "docker", "read-only-api.sql")),
      target: "/grants/read-only-api.sql",
      read_only: true,
    }]);
    const grantCommand = grantService.command.join("\n");
    for (const variable of [
      "PGUSER",
      "PGPASSWORD",
      "PGDATABASE",
      "API_PGUSER",
      "API_PGPASSWORD",
    ]) {
      assert.ok(grantCommand.includes(`$${variable}`));
    }
    assert.equal(config.networks.data.internal, true);
  }
});
