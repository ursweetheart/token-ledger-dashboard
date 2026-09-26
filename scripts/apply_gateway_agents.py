"""Validate/apply Gateway-only dashboard registration; never migrate implicitly."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect, gateway_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--config", default="config/gateway-agents.yaml")
    parser.add_argument("--db", default=connect.DEFAULT_DSN)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    rows = gateway_registry.parse_config(Path(args.config).read_text(encoding="utf-8-sig"))
    with gateway_registry.operation_lock(args.db):
        cn, _ = connect.open_db(args.db)
        try:
            if args.dry_run:
                cn.set_session(readonly=True)
            plan = gateway_registry.apply_config(cn, rows, args.dry_run)
            if args.dry_run:
                cn.rollback()
            else:
                cn.commit()
            print(json.dumps({"dry_run": args.dry_run, "agents": plan}, ensure_ascii=True))
        finally:
            cn.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as exc:
        print(f"Registration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
