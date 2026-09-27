#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
    python_cmd=python3
else
    python_cmd=python
fi
exec "$python_cmd" "$project_dir/scripts/dashboard.py" "${1:-start}"
