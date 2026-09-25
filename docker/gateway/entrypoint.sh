#!/bin/sh
# Chan truoc khi LiteLLM khoi dong.
#
# Ly do ton tai file nay: LITELLM_MASTER_KEY rong KHONG lam LiteLLM dung lai --
# no khoi dong voi "khong co master key", tuc mo cong 4000 cho bat ky ai goi
# duoc. Che do hong phai la "khong chay", tuyet doi khong phai "chay mo"
# (cung ky luat da ap cho DASHBOARD_KEY o backend/main.py).
#
# Khong dat duoc bang `${VAR:?}` trong compose: compose noi bien cho CA file
# truoc khi loc profile, nen `:?` se lam `docker compose up -d` cua dashboard
# gay theo du nguoi dung khong he dinh bat Gateway.
set -eu

fail() { echo "STOP: $1" >&2; exit 1; }

for v in LITELLM_MASTER_KEY LITELLM_SALT_KEY KEY_GOOGLE_AI_STU KEY_CRM_FEEDBACK KEY_RALLI DATABASE_URL REDIS_PASSWORD; do
  eval "val=\${$v:-}"
  [ -n "$val" ] || fail "$v is missing. Fill it in .env and run again. See .env.example."
done

case "$LITELLM_MASTER_KEY" in
  sk-*) ;;
  *) fail "LITELLM_MASTER_KEY must start with 'sk-' (LiteLLM requires that prefix)." ;;
esac

# Khoa mac dinh cua ban vi du khong duoc phep di ra ngoai may cua nguoi viet no.
case "$LITELLM_MASTER_KEY" in
  sk-doi-khoa-nay|sk-1234|sk-test|sk-local) fail "LITELLM_MASTER_KEY is still the example key. Generate a real one: python -c \"import secrets; print('sk-' + secrets.token_urlsafe(32))\"" ;;
esac

exec /app/docker/prod_entrypoint.sh "$@"
