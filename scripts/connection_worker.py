"""Host worker CLI. Explicit configuration, never loads repo .env automatically."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.connection_worker import Worker, build_app


def configured_worker():
    names = ['CONNECTION_REPO_ROOT','CONNECTION_SECRET_DIR','CONNECTION_WORKER_DSN',
             'CONNECTION_GATEWAY_DSN','CONNECTION_GATEWAY_ENDPOINTS','CONNECTION_GATEWAY_MASTER_KEY',
             'CONNECTION_HOST_ENDPOINT','CONNECTION_DOCKER_ENDPOINT','CONNECTION_DOCKER_NETWORK']
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise SystemExit('Missing worker configuration: ' + ', '.join(missing))
    return Worker(*(os.environ[name] for name in names[:4]),
                  os.environ[names[4]].split(','), *(os.environ[name] for name in names[5:]))


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('command',choices=['bootstrap','serve','once'])
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--config',type=Path,help='Explicit local JSON environment configuration')
    args = parser.parse_args()
    if args.config:
        os.environ.update(json.loads(args.config.read_text(encoding='utf-8')))
    worker = configured_worker()
    if args.command == 'bootstrap':
        print(worker.bootstrap())
    elif args.command == 'once':
        worker.drain()
    else:
        import uvicorn
        credential = os.environ.get('CONNECTION_WORKER_KEY','')
        app = build_app(worker,credential)
        def consume():
            while True:
                try:
                    worker.drain()
                except Exception as exc:
                    # Names only; no DSNs, subprocess output or upstream secret responses.
                    print('Worker cycle: ' + type(exc).__name__,file=sys.stderr)
                time.sleep(2)
        threading.Thread(target=consume,daemon=True).start()
        uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)


if __name__ == '__main__':
    main()
