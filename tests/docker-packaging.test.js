const test = require("node:test");
const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const API_PATH = path.join(ROOT, "web", "js", "api.js");
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
        PGPASSWORD: "0123456789abcdef0123456789abcdef",
        PGADMIN_PASSWORD: "0123456789abcdef0123456789abcdef",
        TLS_CERT_FILE: "C:/certs/fullchain.pem",
        TLS_KEY_FILE: "C:/certs/private.key",
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

test("local Compose keeps API and Postgres private and exposes only the local gateway", { skip: !composeAvailable }, () => {
  const config = composeConfig("docker-compose.local.yml");
  const { services } = config;

  assert.deepEqual(services.api.ports ?? [], []);
  assert.deepEqual(services.postgres.ports ?? [], []);
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
});

test("production Compose exposes TLS gateway only with read-only certificate mounts", { skip: !composeAvailable }, () => {
  const { services } = composeConfig("docker-compose.prod.yml");

  assert.deepEqual(publishedPorts(services.gateway), [{
    target: 443,
    published: "45501",
    host_ip: "0.0.0.0",
    protocol: "tcp",
  }]);
  for (const target of [
    "/etc/nginx/tls/fullchain.pem",
    "/etc/nginx/tls/private.key",
  ]) {
    assert.ok(services.gateway.volumes.some((volume) =>
      volume.type === "bind"
      && volume.target === target
      && volume.read_only === true));
  }
});

test("rendered Compose services place database tools in the tools profile and healthcheck the runtime", { skip: !composeAvailable }, () => {
  for (const override of ["docker-compose.local.yml", "docker-compose.prod.yml"]) {
    const { services } = composeConfig(override);
    for (const service of ["db-import", "db-audit", "pgadmin"]) {
      assert.deepEqual(services[service].profiles, ["tools"]);
    }
    for (const service of ["postgres", "api", "gateway"]) {
      assert.ok(services[service].healthcheck);
    }
  }
});
