#!/bin/bash
set -e
# Run the stock template hooks and validate before starting either service.
/docker-entrypoint.sh nginx -t
# Job control gives each service its own process group, including Nginx workers.
set -m
su-exec nginx node /app/server.js &
node_pid=$!
nginx -g 'daemon off; worker_shutdown_timeout 20s;' &
nginx_pid=$!
shutdown() {
    trap '' TERM INT
    kill -QUIT -- -"$nginx_pid" 2>/dev/null || true
    # Bound shutdown below Compose's 30s grace period, even after master failure.
    ( sleep 25; kill -KILL -- -"$nginx_pid" -"$node_pid" 2>/dev/null || true ) &
    watchdog=$!
    wait "$nginx_pid" 2>/dev/null || true
    kill -TERM -- -"$node_pid" 2>/dev/null || true
    wait "$node_pid" 2>/dev/null || true
    kill -KILL -- -"$watchdog" 2>/dev/null || true
    wait "$watchdog" 2>/dev/null || true
}
trap 'shutdown; exit 0' TERM INT
# Any service exit, even status 0, is unexpected: stop its sibling and fail fast.
wait -n "$node_pid" "$nginx_pid" || true
shutdown
exit 1
