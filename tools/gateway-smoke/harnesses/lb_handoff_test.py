"""Offline LB transport checks. Pass a local nginx >=1.27.3 executable.
Uses only temporary files and loopback mock backends, never the Compose stack.
Docker DNS rotation is not covered: upstream names are replaced with loopback.
"""
import http.client
import http.server
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time


def main():
    nginx = str(Path(sys.argv[1]).resolve())
    root = Path(__file__).resolve().parents[3]
    hits = []
    mode = ['ok']

    class Mock(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            hits.append((dict(self.headers), body))
            assert self.path == '/v1/chat/completions?trace=a%2Fb' or self.path == '/v1/chat/completions', self.path
            self.close_connection = True
            if mode[0] == 'drop':
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if mode[0] == 'sse':
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(b'data: first\n\n')
                self.wfile.flush()
                time.sleep(0.8)
                self.wfile.write(b'data: [DONE]\n\n')
                self.close_connection = True
                return
            status = 503 if mode[0] == '503' else 200 if self.headers.get('Authorization') == 'Bearer mock-only' else 401
            self.send_response(status)
            self.send_header('Content-Length', '2')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(b'{}')

    def backend(port=0):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Mock)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server

    servers = [backend(), backend()]
    ports = [s.server_port for s in servers]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        tls_port = sock.getsockname()[1]

    def request(path='/gateway/v1/chat/completions?trace=a%2Fb', host='apigateway.rangdong.com.vn', auth=True, stream=False, source='127.0.0.1'):
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=25, source_address=(source, 0))
        headers = {'Host': host, 'X-User': 'mock.user', 'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '127.0.0.1', 'Cookie': 'secret=mock', 'X-API-Key': 'mock-secret'}
        if auth:
            headers['Authorization'] = 'Bearer mock-only'
        try:
            started = time.monotonic()
            conn.request('POST' if '/chat/completions' in path else 'GET', path, b'{}', headers)
            response = conn.getresponse()
            if stream:
                assert response.readline() == b'data: first\n'
                assert time.monotonic() - started < 0.6, 'SSE was buffered'
            return response.status, response.read()
        finally:
            conn.close()

    status_process = subprocess.Popen(['node', '-e',
        "const {createMonitor}=require('./tools/gateway-status/server');"
        "const s=createMonitor({timeoutMs:100});"
        "s.prependListener('request',(req)=>{"
        "require('node:assert/strict').deepEqual(Object.keys(req.headers).sort(),['host']);"
        "require('node:assert/strict').equal(req.headers.host,'localhost');});"
        "s.listen(0,'127.0.0.1',()=>console.log(s.address().port));"],
        cwd=root, stdout=subprocess.PIPE, text=True)
    status_port = int(status_process.stdout.readline())
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix='gateway-lb-check-') as temp:
            temp = Path(temp)
            (temp / 'logs').mkdir()
            (temp / 'temp').mkdir()
            config = (root / 'docker/gateway/nginx.conf').read_text(encoding='utf-8').replace('${LLM_GATEWAY_DOMAIN}', 'apigateway.rangdong.com.vn')
            config = config.replace('${LLM_GATEWAY_ADMIN_CIDR}', '127.0.0.1/32')
            # Distinct from the admin CIDR above and from every source IP this harness
            # uses (127.0.0.1, 127.0.0.2), so the spoofed-XFF/admin-ACL check below is
            # unaffected by this second allowlist existing.
            config = config.replace('${LLM_GATEWAY_LAN_CIDR}', '203.0.113.0/24')
            config = config.replace('127.0.0.1:8089', f'127.0.0.1:{status_port}')
            config = config.replace('listen 4000', f'listen 127.0.0.1:{port}')
            # gateway-lb also terminates HTTPS on 4443 (see docker/gateway/tls); nginx
            # refuses to start without a loadable cert, so hand it a throwaway one.
            # This harness never exercises HTTPS itself, only that HTTP still works
            # with the extra listener present.
            subprocess.run(['openssl', 'req', '-x509', '-nodes', '-newkey', 'rsa:2048',
                             '-keyout', str(temp / 'tls.key'), '-out', str(temp / 'tls.crt'),
                             '-days', '1', '-subj', '/CN=apigateway.rangdong.com.vn'],
                            check=True, capture_output=True)
            config = config.replace('/etc/nginx/tls/apigateway.crt', str(temp / 'tls.crt'))
            config = config.replace('/etc/nginx/tls/apigateway.key', str(temp / 'tls.key'))
            config = config.replace('listen 4443 ssl;', f'listen 127.0.0.1:{tls_port} ssl;')
            for i, upstream in enumerate(ports, 1):
                config = config.replace(f'litellm-{i}:4000 resolve', f'127.0.0.1:{upstream}')
            # Shorten passive recovery only; preserve the production retry policy.
            config = config.replace('fail_timeout=30s', 'fail_timeout=1s')
            (temp / 'nginx.conf').write_text('daemon off;\nworker_processes 1;\nevents {}\nhttp {\nserver_names_hash_bucket_size 64;\n' + config + '\n}\n', encoding='utf-8')
            args = [nginx, '-p', temp.as_posix() + '/', '-c', 'nginx.conf']
            subprocess.run(args + ['-t'], check=True)
            process = subprocess.Popen(args)
            deadline = time.monotonic() + 5
            while True:
                try:
                    assert request('/lb-health')[0] == 200
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
            assert request('/edge-health')[1] == b'edge-ok\n'
            for host in ['apigateway.rangdong.com.vn', '192.168.20.111', '127.0.0.1']:
                for path, marker in [('/', b'<!DOCTYPE html>'), ('/app.js', b'use strict'),
                                     ('/style.css', b'{'), ('/api/status', b'checked_at')]:
                    status, data = request(path, host)
                    assert status == 200 and marker.lower() in data.lower(), (host, path, status)
                    assert request(path, host, source='127.0.0.2')[0] == 403, 'spoofed XFF bypassed admin ACL'
            assert request('/v1/chat/completions')[0] == 200
            assert request(host='192.168.20.111')[0] == 200
            for path in ['/gateway', '/gateway/', '/gateway/v1/models', '/gateway/key/generate', '/gateway/v1/chat/completions/extra', '/api/keys', '/app.js/extra', '/status/', '/key/generate', '/v1/models', '/v1/chat/completions/extra', '/health/liveliness']:
                assert request(path)[0] == 404, path
            try:
                request('/lb-health', 'evil.invalid')
                raise AssertionError('unknown Host accepted')
            except (http.client.RemoteDisconnected, ConnectionResetError):
                pass
            assert request()[0] == 200
            headers, body = hits[-1]
            normalized = {k.lower(): v for k, v in headers.items()}
            assert normalized['authorization'] == 'Bearer mock-only'
            assert normalized['x-user'] == 'mock.user'
            assert normalized['x-forwarded-proto'] == 'https'
            assert normalized['host'] == 'apigateway.rangdong.com.vn'
            assert normalized['x-forwarded-for'].startswith('127.0.0.1, ')
            assert normalized['x-request-id'] and body == b'{}'
            assert request(auth=False)[0] == 401
            mode[0] = 'sse'
            assert request(stream=True)[0] == 200
            for fault in ['503', 'drop']:
                mode[0] = fault
                before = len(hits)
                assert request()[0] == (503 if fault == '503' else 502)
                assert len(hits) == before + 1, 'already-sent POST replayed'
            mode[0] = 'ok'
            servers[0].shutdown()
            servers[0].server_close()
            time.sleep(1.1)
            for _ in range(4):
                assert request()[0] == 200, 'pre-send failover failed'
            servers[1].shutdown()
            servers[1].server_close()
            assert request()[0] == 502
            assert request('/lb-health')[0] == 200
            servers = [backend(p) for p in ports]
            time.sleep(1.1)
            assert request()[0] == 200
            subprocess.run(args + ['-s', 'quit'], check=True)
            process.wait(timeout=5)
            process = None
            try:
                request('/lb-health')
                raise AssertionError('LB still listening after quit')
            except OSError:
                pass
            # Native harness owns separate processes; Docker harness tests supervision.
            status_process.terminate()
            status_process.wait(timeout=5)
            print(json.dumps({'result': 'PASS', 'checks': ['domain/IP/routes', 'status assets/API and TCP-peer ACL with spoofed XFF', 'status strips all client headers/body', 'prefix/query/body and legacy API', 'authorization/identity/forwarded headers', 'SSE early delivery', '503 and dropped POST no replay', 'one upstream down pre-send failover', 'all upstreams down with LB liveness', 'recovery', 'LB shutdown (bundle supervision covered by Docker harness)'], 'docker_dns_rotation': 'NOT TESTED'}))
    finally:
        if process is not None:
            # Stop the master and workers, including on failed assertions.
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
            else:
                process.terminate()
            process.wait(timeout=5)
        status_process.terminate()
        status_process.wait(timeout=5)
        status_process.stdout.close()
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
