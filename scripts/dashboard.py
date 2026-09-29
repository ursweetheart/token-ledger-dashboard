"""Cross-platform local setup/start entry point. Secrets stay in .local/connections."""
import argparse
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import quote
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.local' / 'connections'


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)


def python_path():
    return STATE / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def read_env():
    values = {}
    if (ROOT / '.env').exists():
        for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('\"').strip("'")
    return values


def write_env(updates):
    path = ROOT / '.env'
    text = path.read_text(encoding='utf-8-sig') if path.exists() else ''
    for key, value in updates.items():
        pattern = '^' + re.escape(key) + '=.*$'
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, lambda _: key + '=' + value, text, flags=re.M)
        else:
            text = text.rstrip() + '\n' + key + '=' + value + '\n'
    path.write_text(text, encoding='utf-8')
    if os.name != 'nt':
        path.chmod(0o600)


def compose_args():
    args = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'docker-compose.yml')]
    for name in ('runtime.yaml', 'compose.connections.yaml'):
        if (STATE / name).exists():
            args += ['-f', str(STATE / name)]
    return args


def restricted_state():
    STATE.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        script = "$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; icacls $env:DASHBOARD_STATE /inheritance:r /grant:r ('*'+$sid+':(OI)(CI)F') '*S-1-5-18:(OI)(CI)F'"
        run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
            env={**os.environ, 'DASHBOARD_STATE': str(STATE)})
    else:
        STATE.chmod(0o700)


def runtime_config(state, windows):
    def mount(name, target):
        return {'type': 'bind', 'source': str(state / name), 'target': target, 'read_only': True}
    proxy = {'image': 'nginx:1.28-alpine', 'restart': 'unless-stopped',
             'volumes': [mount('proxy.conf', '/etc/nginx/conf.d/default.conf'),
                         mount('worker.crt', '/certs/worker.crt'), mount('worker.key', '/certs/worker.key')]}
    api = {'environment': {'SSL_CERT_FILE': '/connection-ca/worker.crt'},
           'volumes': [mount('worker.crt', '/connection-ca/worker.crt')]}
    if windows:
        proxy['extra_hosts'] = ['host.docker.internal:host-gateway']
    else:
        # Native Linux containers cannot reach a host loopback listener through
        # the bridge gateway. The TLS proxy shares the host network instead.
        proxy['network_mode'] = 'host'
        api['extra_hosts'] = ['host.docker.internal:host-gateway']
    return {'services': {'api': api, 'connection-worker-proxy': proxy,
                        'litellm-1': {'ports': ['127.0.0.1:4401:4000']},
                        'litellm-2': {'ports': ['127.0.0.1:4402:4000']}}}


def certificate(cert_path, key_path, hostname, extra_names=()):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=5))
            .not_valid_after(datetime.now(timezone.utc)+timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(n) for n in (hostname, *extra_names)]), False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), True).sign(key, hashes.SHA256()))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    if os.name != 'nt':
        key_path.chmod(0o600)


def setup():
    if (STATE / 'worker-env.json').exists():
        print('Already configured; credentials retained. Run: python scripts/dashboard.py start')
        return
    import psycopg2
    from psycopg2 import sql
    from alembic import command
    from alembic.config import Config
    import yaml
    restricted_state()
    env = read_env()
    generated = {}
    for name in ('DASHBOARD_KEY', 'LITELLM_MASTER_KEY', 'LITELLM_SALT_KEY', 'REDIS_PASSWORD'):
        if not env.get(name):
            generated[name] = ('sk-' if name == 'LITELLM_MASTER_KEY' else '') + secrets.token_urlsafe(32)
    for name in ('KEY_GOOGLE_AI_STU', 'KEY_CRM_FEEDBACK', 'KEY_RALLI', 'KEY_TLA_HD'):
        if not env.get(name):
            generated[name] = getpass.getpass(name + ' (required by existing Gateway routes): ').strip()
            if not generated[name]:
                raise ValueError('Missing ' + name)
    if env.get('WEB_TLS_PORT', '8443') == env.get('LLM_GATEWAY_TLS_ALT_PORT', '8443'):
        generated['LLM_GATEWAY_TLS_ALT_PORT'] = '9443'
    write_env(generated)
    env.update(generated)
    tls = ROOT / 'docker/gateway/tls'
    tls.mkdir(parents=True, exist_ok=True)
    if not (tls / 'apigateway.crt').exists() or not (tls / 'apigateway.key').exists():
        certificate(tls / 'apigateway.crt', tls / 'apigateway.key', 'localhost', ('apigateway.rangdong.com.vn',))
    run(compose_args() + ['up', '-d', '--wait', 'postgres'])
    run(compose_args() + ['run', '--rm', 'api-db-init'])
    backup = STATE / ('ledger-before-setup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.dump')
    with backup.open('wb') as output:
        run(compose_args() + ['exec', '-T', 'postgres', 'sh', '-c', 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'], stdout=output)
    def dsn(user, password, database, host='127.0.0.1'):
        port = env.get('PGPORT', '5432') if host == '127.0.0.1' else '5432'
        return f'postgresql://{quote(user,safe="")}:{quote(password,safe="")}@{host}:{port}/{database}'
    database = env.get('PGDATABASE', 'token_ledger_v2')
    ledger = dsn(env.get('PGUSER', 'token'), env.get('PGPASSWORD', 'token_local'), database)
    os.environ['TOKEN_LEDGER_DSN'] = ledger
    sys.path.insert(0, str(ROOT))
    cfg = Config(str(ROOT / 'alembic.ini'))
    cfg.attributes['explicit_dsn'] = ledger
    command.upgrade(cfg, 'head')
    with psycopg2.connect(ledger) as cn:
        with cn.cursor() as cur:
            cur.execute('SELECT baseline FROM gateway_connection_deployment')
            if cur.fetchone()[0]:
                raise ValueError('Existing worker baseline without local configuration. Restore worker-env.json from backup; do not regenerate credentials.')
    password = secrets.token_urlsafe(32)
    with psycopg2.connect(ledger) as cn:
        with cn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='connection_api'")
            if not cur.fetchone():
                cur.execute('CREATE ROLE connection_api LOGIN')
            cur.execute(sql.SQL('ALTER ROLE connection_api PASSWORD {}').format(sql.Literal(password)))
            cur.execute('GRANT connection_admin TO connection_api')
            cur.execute('GRANT USAGE ON SCHEMA public TO connection_admin')
            cur.execute('GRANT SELECT ON ref_model_catalog,ref_model_price_version,ref_price_sync_state,gateway_agent_registry,gateway_observed_identity TO api_readonly')
    certificate(STATE / 'worker.crt', STATE / 'worker.key', 'connection-worker-proxy', ('host.docker.internal',))
    admin, rpc = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    (STATE / 'admin-key.txt').write_text(admin, encoding='utf-8')
    windows = os.name == 'nt'
    worker_url = 'https://' + ('connection-worker-proxy' if windows else 'host.docker.internal') + ':8767'
    write_env({'CONNECTIONS_ENABLED': '1', 'CONNECTION_ADMIN_KEY': admin,
               'CONNECTION_ADMIN_DSN': dsn('connection_api', password, database, 'postgres'),
               'CONNECTION_WORKER_URL': worker_url, 'CONNECTION_WORKER_KEY': rpc})
    network = run(compose_args() + ['ps', '-q', 'postgres'], capture_output=True, text=True).stdout.strip()
    inspected = json.loads(run(['docker', 'inspect', network], capture_output=True, text=True).stdout)
    network = next(iter(inspected[0]['NetworkSettings']['Networks']))
    worker = {'CONNECTION_REPO_ROOT': str(ROOT), 'CONNECTION_SECRET_DIR': str(STATE),
              'CONNECTION_WORKER_DSN': ledger,
              'CONNECTION_GATEWAY_DSN': dsn(env.get('GATEWAY_PGUSER','llmproxy'), env.get('GATEWAY_PGPASSWORD','llmproxy_local'), env.get('GATEWAY_PGDATABASE','litellm')),
              'CONNECTION_GATEWAY_ENDPOINTS': 'http://127.0.0.1:4401,http://127.0.0.1:4402',
              'CONNECTION_GATEWAY_MASTER_KEY': env['LITELLM_MASTER_KEY'],
              'CONNECTION_HOST_ENDPOINT': 'http://127.0.0.1:' + env.get('LLM_GATEWAY_EDGE_PORT','8088'),
              'CONNECTION_DOCKER_ENDPOINT': 'http://gateway-lb:4000',
              'CONNECTION_DOCKER_NETWORK': network, 'CONNECTION_WORKER_KEY': rpc}
    upstream = 'host.docker.internal' if windows else '127.0.0.1'
    (STATE / 'proxy.conf').write_text('server { listen 8767 ssl; ssl_certificate /certs/worker.crt; ssl_certificate_key /certs/worker.key; location / { proxy_pass http://' + upstream + ':8766; proxy_read_timeout 40s; } }', encoding='utf-8')
    (STATE / 'runtime.yaml').write_text(yaml.safe_dump(runtime_config(STATE, windows)), encoding='utf-8')
    # Bootstrap before saving the completion marker. Retrying a failed setup
    # must not appear to be a successfully initialized installation.
    os.environ.update(worker)
    from scripts.connection_worker import configured_worker
    instance = configured_worker()
    if not instance.baseline():
        instance.bootstrap()
    (STATE / 'worker-env.json').write_text(json.dumps(worker), encoding='utf-8')
    print('Setup complete. Run: python scripts/dashboard.py start')


def worker_ready(config):
    request = urllib.request.Request('http://127.0.0.1:8766/rpc/template',
        data=b'{"code":"__startup_probe__","context":"host"}',
        headers={'Authorization': 'Bearer ' + config['CONNECTION_WORKER_KEY'], 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(request, timeout=2).close()
        return True
    except urllib.error.HTTPError as exc:
        return exc.code == 404
    except OSError:
        return False


def start():
    path = STATE / 'worker-env.json'
    if not path.exists():
        raise ValueError('Run setup first: python scripts/dashboard.py setup')
    config = json.loads(path.read_text(encoding='utf-8'))
    if Path(config['CONNECTION_REPO_ROOT']).resolve() != ROOT:
        raise ValueError('Project moved; update worker-env.json and runtime.yaml paths before starting')
    # Worker mở ledger ngay khi bật. Sau khi máy khởi động lại, postgres có thể đang tắt: đo 30/09/2026,
    # mọi vòng worker báo OperationalError và lệnh start hết giờ chờ. Cùng lệnh với setup().
    run(compose_args() + ['up', '-d', '--wait', 'postgres'])
    if not worker_ready(config):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',8766)) == 0:
                raise ValueError('Port 8766 belongs to another process or worker credential; inspect it first')
        log = (STATE / 'worker.log').open('ab')
        options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS} if os.name == 'nt' else {'start_new_session': True}
        try:
            process = subprocess.Popen([str(python_path()), str(ROOT/'scripts/connection_worker.py'), 'serve', '--config', str(path)],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options)
        finally:
            log.close()
        for _ in range(30):
            if worker_ready(config):
                break
            if process.poll() is not None:
                raise ValueError('Worker exited; inspect .local/connections/worker.log')
            time.sleep(0.5)
        else:
            raise ValueError('Worker startup timed out; inspect .local/connections/worker.log')
    run(compose_args() + ['--profile','gateway','--profile','refresh','up','-d','--build',
        'api','web','litellm-1','litellm-2','gateway-lb','connection-worker-proxy'])
    run(compose_args() + ['--profile','gateway','run','--rm','gateway-readonly-init'])
    run(compose_args() + ['--profile','gateway','--profile','refresh','up','-d','--build','ledger-refresh'])
    run(compose_args() + ['restart','web'])
    env = read_env()
    base = 'http://127.0.0.1:' + env.get('WEB_PORT','8080')
    for path, credential in [('/api/usage','DASHBOARD_KEY'),('/api/gateway-connections','CONNECTION_ADMIN_KEY')]:
        for attempt in range(30):
            try:
                req = urllib.request.Request(base+path, headers={'Authorization':'Bearer '+env[credential]})
                with urllib.request.urlopen(req,timeout=3) as response:
                    if response.status == 200:
                        break
            except (OSError, KeyError):
                pass
            time.sleep(0.5)
        else:
            raise ValueError('Startup check failed for '+path+'; inspect Docker API logs')
    print('Dashboard: '+base+'\nAdministration key: .local/connections/admin-key.txt')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup','start'])
    parser.add_argument('--in-venv', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(ROOT)
    if not args.in_venv:
        if args.command == 'setup' and (STATE / 'worker-env.json').exists():
            print('Already configured; credentials retained. Run: python scripts/dashboard.py start')
            return
        executable = python_path()
        if not executable.exists():
            if args.command != 'setup':
                raise ValueError('Run setup first: python scripts/dashboard.py setup')
            restricted_state()
            run([sys.executable,'-m','venv',STATE/'venv'])
        if args.command == 'setup':
            run([executable,'-m','pip','install','-r',ROOT/'backend/requirements.txt','cryptography'])
        run([executable,Path(__file__).resolve(),args.command,'--in-venv'])
        return
    if args.command == 'setup':
        setup()
    else:
        start()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print('STOP: '+str(exc), file=sys.stderr)
        sys.exit(1)
