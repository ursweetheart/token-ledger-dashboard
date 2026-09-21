const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const configPath = path.join(ROOT, "docker", "gateway", "nginx.conf");
const composePath = path.join(ROOT, "docker-compose.yml");
const envExamplePath = path.join(ROOT, ".env.example");

function read(file) {
  return fs.readFileSync(file, "utf8");
}

test("LB enforces the domain inference allowlist and retains dynamic upstream failover", () => {
  const nginx = read(configPath);

  assert.match(nginx, /server_name\s+\$\{LLM_GATEWAY_DOMAIN\} gateway-lb token-ledger-gateway-lb localhost 127\.0\.0\.1 192\.168\.20\.111;/);
  assert.match(nginx, /listen\s+4000;/);
  assert.match(nginx, /location\s+=\s+\/v1\/chat\/completions\s*\{/);
  assert.match(nginx, /resolver\s+127\.0\.0\.11/);
  assert.match(nginx, /server\s+litellm-[12]:4000\s+resolve/);
  assert.match(nginx, /proxy_pass\s+http:\/\/litellm_pool;/);
  assert.match(nginx, /proxy_set_header\s+Authorization\s+\$http_authorization;/);
  assert.match(nginx, /proxy_set_header\s+X-User\s+\$http_x_user;/);
  assert.match(nginx, /proxy_buffering\s+off;/);
  assert.match(nginx, /client_max_body_size\s+25m;/);
  assert.match(nginx, /proxy_(send|read)_timeout\s+600s;/);
  assert.match(nginx, /proxy_next_upstream_tries\s+2;/);
  assert.match(nginx, /proxy_set_header\s+X-Forwarded-Proto\s+\$gateway_forwarded_proto;/);
  assert.match(nginx, /if \(\$host = \$\{LLM_GATEWAY_DOMAIN\}\) \{ return 404; \}/);
  assert.match(nginx, /proxy_next_upstream\s+error timeout http_502 http_503 http_504;/);
  assert.match(nginx, /location\s+\/\s*\{\s*return\s+404;/s);
  assert.doesNotMatch(nginx.replace(/#.*$/gm, ""), /non_idempotent/);
  assert.match(nginx, /zone\s+litellm_pool\s+64k;/);
  assert.match(nginx, /listen\s+4000\s+default_server;/);
  assert.match(nginx, /return 444;/);
});

test("gateway-lb also terminates HTTPS on 4443, alongside plain HTTP on 4000", () => {
  const nginx = read(configPath);
  const compose = read(composePath);

  assert.match(nginx, /listen 4000;\s*\n\s*listen 4443 ssl;/);
  assert.match(nginx, /ssl_certificate\s+\/etc\/nginx\/tls\/apigateway\.crt;/);
  assert.match(nginx, /ssl_certificate_key\s+\/etc\/nginx\/tls\/apigateway\.key;/);
  assert.match(nginx, /ssl_protocols\s+TLSv1\.2 TLSv1\.3;/);
  // Plain HTTP stays -- HTTPS is additive, not a replacement.
  assert.match(nginx, /listen\s+4000;/);

  assert.match(compose, /\.\/docker\/gateway\/tls:\/etc\/nginx\/tls:ro/);
  assert.match(compose, /\$\{LLM_GATEWAY_TLS_BIND:-127\.0\.0\.1\}:\$\{LLM_GATEWAY_TLS_PORT:-443\}:4443/);
});

test("Compose publishes the compatible loopback handoff on LB only", () => {
  const compose = read(composePath);
  const example = read(envExamplePath);

  assert.doesNotMatch(compose, /gateway-edge:/);
  assert.ok(!fs.existsSync(path.join(ROOT, "docker/gateway/edge.conf.template")));
  assert.match(compose, /nginx\.conf:\/etc\/nginx\/templates\/default\.conf\.template:ro/);
  assert.match(compose, /\$\{LLM_GATEWAY_EDGE_BIND:-127\.0\.0\.1\}:\$\{LLM_GATEWAY_EDGE_PORT:-8088\}:4000/);
  assert.match(compose, /LLM_GATEWAY_DOMAIN:\s+\$\{LLM_GATEWAY_DOMAIN:-apigateway\.rangdong\.com\.vn\}/);
  assert.doesNotMatch(compose, /\$\{GATEWAY_PORT:-4000\}:4000/);
  assert.doesNotMatch(compose, /"127\.0\.0\.1:8089:8089"/);
  assert.doesNotMatch(compose, /\$\{LITELLM_[12]_PORT:-400[12]\}:4000/);
  assert.match(example, /LLM_GATEWAY_DOMAIN=apigateway\.rangdong\.com\.vn/);
  assert.match(example, /LLM_GATEWAY_EDGE_BIND=127\.0\.0\.1/);
  assert.match(example, /LLM_GATEWAY_EDGE_PORT=8088/);
});


test("Same-port status is private and inference prefix is exact", () => {
  const nginx = read(configPath);
  const compose = read(composePath);
  assert.match(nginx, /location = \/gateway\/v1\/chat\/completions\s*\{\s*proxy_pass http:\/\/litellm_pool\/v1\/chat\/completions;/);
  assert.match(nginx, /proxy_pass http:\/\/127\.0\.0\.1:8089;/);
  assert.doesNotMatch(nginx, /gateway-status:8089/);
  assert.match(nginx, /allow \$\{LLM_GATEWAY_ADMIN_CIDR\};\s*allow \$\{LLM_GATEWAY_LAN_CIDR\};\s*deny all;/);
  assert.match(nginx, /proxy_pass_request_headers off;/);
  assert.match(nginx, /proxy_pass_request_body off;/);
  assert.match(nginx, /proxy_set_header Host localhost;/);
  assert.doesNotMatch(nginx, /real_ip_header|set_real_ip_from/);
  assert.match(compose, /LLM_GATEWAY_ADMIN_CIDR: \$\{LLM_GATEWAY_ADMIN_CIDR:-127\.0\.0\.1\/32\}/);
  assert.match(compose, /LLM_GATEWAY_LAN_CIDR: \$\{LLM_GATEWAY_LAN_CIDR:-127\.0\.0\.1\/32\}/);
  assert.match(compose, /NGINX_ENVSUBST_FILTER: \^LLM_GATEWAY_\(DOMAIN\|ADMIN_CIDR\|LAN_CIDR\)\$/);
  assert.doesNotMatch(compose, /^  gateway-status:|8089:8089/m);
  const lb = compose.split('  gateway-lb:')[1].split('\n# Khai ro')[0];
  assert.match(lb, /dockerfile: docker\/gateway\/Dockerfile/);
  assert.doesNotMatch(lb, /depends_on:/);
  assert.match(lb, /STATUS_BIND: "127\.0\.0\.1"/);
});
