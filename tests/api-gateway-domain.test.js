const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const configPath = path.join(ROOT, "docker", "gateway", "edge.conf.template");
const composePath = path.join(ROOT, "docker-compose.yml");
const envExamplePath = path.join(ROOT, ".env.example");

function read(file) {
  return fs.readFileSync(file, "utf8");
}

test("edge Nginx uses the configured domain and proxies only inference to gateway-lb", () => {
  const nginx = read(configPath);

  assert.match(nginx, /server_name\s+\$\{LLM_GATEWAY_DOMAIN\};/);
  assert.match(nginx, /listen\s+8080;/);
  assert.match(nginx, /location\s+=\s+\/v1\/chat\/completions\s*\{/);
  assert.match(nginx, /resolver\s+127\.0\.0\.11/);
  assert.match(nginx, /server\s+gateway-lb:4000\s+resolve;/);
  assert.match(nginx, /proxy_pass\s+http:\/\/gateway_pool;/);
  assert.match(nginx, /proxy_set_header\s+Authorization\s+\$http_authorization;/);
  assert.match(nginx, /proxy_set_header\s+X-User\s+\$http_x_user;/);
  assert.match(nginx, /proxy_buffering\s+off;/);
  assert.match(nginx, /proxy_next_upstream\s+off;/);
  assert.match(nginx, /location\s+\/\s*\{\s*return\s+404;/s);
  assert.doesNotMatch(nginx, /non_idempotent/);
  assert.doesNotMatch(nginx, /ssl_certificate|listen\s+443/);
});

test("Compose publishes only the edge port on loopback and keeps gateway-lb private", () => {
  const compose = read(composePath);
  const example = read(envExamplePath);

  assert.match(compose, /gateway-edge:/);
  assert.match(compose, /\$\{LLM_GATEWAY_EDGE_BIND:-127\.0\.0\.1\}:\$\{LLM_GATEWAY_EDGE_PORT:-8088\}:8080/);
  assert.match(compose, /LLM_GATEWAY_DOMAIN:\s+\$\{LLM_GATEWAY_DOMAIN:-apigateway\.rangdong\.com\.vn\}/);
  assert.doesNotMatch(compose, /\$\{GATEWAY_PORT:-4000\}:4000/);
  assert.doesNotMatch(compose, /\$\{LITELLM_[12]_PORT:-400[12]\}:4000/);
  assert.match(example, /LLM_GATEWAY_DOMAIN=apigateway\.rangdong\.com\.vn/);
  assert.match(example, /LLM_GATEWAY_EDGE_BIND=127\.0\.0\.1/);
  assert.match(example, /LLM_GATEWAY_EDGE_PORT=8088/);
});
