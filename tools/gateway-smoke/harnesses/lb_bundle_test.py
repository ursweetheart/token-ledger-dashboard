"""Build and test the combined container on a unique mock-only Docker network.
No Compose lifecycle, provider calls, shared mounts, fixed host ports or volumes.
"""
import http.client
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
MOCK = r"""
const http=require('http'); let hits=0;
http.createServer((req,res)=>{
 if(req.method==='GET') {res.end(req.url==='/hits'?String(hits):JSON.stringify("I'm alive!"));return;}
 hits++; let body='';req.on('data',b=>body+=b);req.on('end',()=>{
 const mode=JSON.parse(body).mode;
 if(mode==='drop'){req.socket.destroy();return;}
 if(mode==='sse'){res.writeHead(200,{'Content-Type':'text/event-stream'});res.write('data: first\n\n');setTimeout(()=>res.end('data: [DONE]\n\n'),800);return;}
 res.statusCode=mode==='503'?503:req.headers.authorization==='Bearer mock-only'?200:401;
 res.end(JSON.stringify({path:req.url,headers:req.headers,body}));
 });
}).listen(4000,'0.0.0.0');
"""


def docker(*args, check=True):
    p = subprocess.run(['docker', *args], capture_output=True, text=True, encoding='utf-8', timeout=180)
    if check and p.returncode:
        raise AssertionError(f'docker {args[0]} failed: {p.stderr}')
    return p.stdout.strip()


def eventually(check, seconds=45):
    end = time.monotonic() + seconds
    while True:
        try:
            result = check()
            if result:
                return result
        except (OSError, AssertionError, ValueError):
            pass
        if time.monotonic() >= end:
            raise AssertionError('condition did not become true')
        time.sleep(.3)


def main():
    tag = 'gateway-bundle-check-' + uuid.uuid4().hex[:10]
    network, image, lb = tag, tag + ':test', tag + '-lb'
    names = []
    checks = []
    docker('build', '-q', '-f', 'docker/gateway/Dockerfile', '-t', image, str(ROOT))
    try:
        docker('network', 'create', network)
        def start_lb():
            docker('run', '-d', '--name', lb, '--network', network,
                   '--network-alias', 'token-ledger-gateway-lb', '-p', '127.0.0.1::4000', image)
            names.append(lb)
            eventually(lambda: json.loads(docker('inspect', lb))[0]['State']['Health']['Status'] == 'healthy')
            return int(json.loads(docker('inspect', lb))[0]['NetworkSettings']['Ports']['4000/tcp'][0]['HostPort'])

        port = start_lb()
        def request(path='/gateway/v1/chat/completions?trace=a%2Fb', mode='ok', auth=True, stream=False):
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
            headers = {'Host':'apigateway.rangdong.com.vn','X-User':'mock.user','X-Forwarded-Proto':'https','X-Forwarded-For':'127.0.0.1'}
            if auth:
                headers['Authorization'] = 'Bearer mock-only'
            try:
                start = time.monotonic()
                conn.request('POST' if 'completions' in path else 'GET', path, json.dumps({'mode': mode}), headers)
                res = conn.getresponse()
                if stream:
                    assert res.readline() == b'data: first\n'
                    assert time.monotonic()-start < .6, 'SSE buffered'
                return res.status, res.read()
            finally:
                conn.close()

        def internal(path):
            return docker('exec', lb, 'wget', '-q', '-O-', 'http://127.0.0.1:4000'+path)

        assert request()[0] == 502
        for route, marker in [('/', '<!DOCTYPE html>'),('/app.js','use strict'),('/style.css','{'),('/api/status','checked_at')]:
            assert marker.lower() in internal(route).lower()
            assert request(route)[0] == 403, 'default peer ACL bypassed'
        assert json.loads(internal('/api/status'))['status'] == 'unavailable'
        docker('exec', lb, 'nginx', '-t')
        rendered = docker('exec', lb, 'nginx', '-T')
        assert '${LLM_GATEWAY_' not in rendered and '$http_authorization' in rendered
        assert 'server litellm-1:4000 resolve' in rendered
        assert 'proxy_pass http://127.0.0.1:8089;' in rendered
        bindings = json.loads(docker('inspect', lb))[0]['NetworkSettings']['Ports']
        assert {key for key, value in bindings.items() if value} == {'4000/tcp'}, bindings
        sockets = docker('exec', lb, 'cat', '/proc/net/tcp')
        assert '00000000:1F99' in sockets
        status_from_watch = docker('run', '--rm', '--network', network,
                                   '--entrypoint', 'wget', image, '-q', '-O-',
                                   '--header', 'Host: localhost',
                                   'http://token-ledger-gateway-lb:8089/api/status')
        assert json.loads(status_from_watch)['status'] == 'unavailable'
        checks.append('image/envsubst/nginx-t; missing both backends healthy; web/assets/status; private-network collector; denied TCP peer/XFF')

        def start_mock(i):
            name = tag + '-mock' + str(i)
            docker('run','-d','--name',name,'--network',network,'--network-alias',f'litellm-{i}',
                   '--network-alias',f'token-ledger-litellm-{i}','--entrypoint','node',image,'-e',MOCK)
            names.append(name)
            return name
        first = start_mock(1)
        eventually(lambda: request()[0] == 200)
        # Recreate LB while proxy2 is absent: startup must not depend on DNS/health.
        docker('stop','-t','30',lb)
        assert json.loads(docker('inspect',lb))[0]['State']['ExitCode'] == 0
        docker('rm',lb); names.remove(lb)
        port = start_lb()
        eventually(lambda: request()[0] == 200)
        second = start_mock(2)
        eventually(lambda: json.loads(internal('/api/status'))['status'] == 'reachable')
        checks.append('missing one backend startup and later DNS discovery; four collector components reachable')
        for path in ['/gateway/v1/chat/completions?trace=a%2Fb','/v1/chat/completions']:
            status, raw = request(path)
            body = json.loads(raw)
            assert status == 200 and body['path'] == path.removeprefix('/gateway')
            h = body['headers']
            assert h['authorization']=='Bearer mock-only' and h['x-user']=='mock.user'
            assert h['host']=='apigateway.rangdong.com.vn' and h['x-forwarded-proto']=='https'
            assert h['x-request-id'] and h['x-forwarded-for'].startswith('127.0.0.1, ')
            assert json.loads(body['body']) == {'mode':'ok'}
        assert request(auth=False)[0] == 401
        for path in ['/gateway/v1/models','/gateway/v1/chat/completions/extra','/key/generate','/health/liveliness']:
            assert request(path)[0] == 404
        assert request(stream=True,mode='sse')[0] == 200
        def hits():
            return sum(int(docker('exec',n,'wget','-q','-O-','http://127.0.0.1:4000/hits')) for n in [first,second])
        for mode, expected in [('503',503),('drop',502)]:
            before = hits()
            assert request(mode=mode)[0] == expected
            assert hits()==before+1, 'POST replayed'
        checks.append('prefix/query/body/legacy/auth/identity/forwarded headers; exact routes; SSE early delivery; no POST replay')
        docker('stop',first)
        eventually(lambda: request()[0] == 200)
        for _ in range(4):
            assert request()[0] == 200
        docker('stop',second)
        assert request()[0] == 502
        assert request('/lb-health')[0] == 200
        assert json.loads(internal('/api/status'))['status'] == 'unavailable'
        docker('start',first,second)
        eventually(lambda: request()[0] == 200)
        checks.append('one proxy down; all down with UI alive; recovery')
        # A stopped Node must make HEALTHCHECK fail even with Nginx alive.
        docker('exec',lb,'pkill','-STOP','node')
        # wget is intentionally bounded by Docker HEALTHCHECK's timeout.
        eventually(lambda: json.loads(docker('inspect',lb))[0]['State']['Health']['Status']=='unhealthy',110)
        docker('exec',lb,'pkill','-CONT','node')
        eventually(lambda: json.loads(docker('inspect',lb))[0]['State']['Health']['Status']=='healthy')
        checks.append('healthcheck detects nonresponding Node independently of backend health')
        for service in ['node','nginx']:
            started = time.monotonic()
            if service=='node':
                docker('exec',lb,'pkill','-KILL','node')
            else:
                docker('exec',lb,'sh','-c','kill -KILL $(cat /var/run/nginx.pid)')
            eventually(lambda: not json.loads(docker('inspect',lb))[0]['State']['Running'])
            state = json.loads(docker('inspect',lb))[0]['State']
            assert state['ExitCode']==1 and state['Pid']==0
            assert time.monotonic()-started < 5, 'idle sibling shutdown was not fail-fast'
            docker('start',lb)
            eventually(lambda: json.loads(docker('inspect',lb))[0]['State']['Health']['Status']=='healthy')
        docker('stop','-t','30',lb)
        state = json.loads(docker('inspect',lb))[0]['State']
        assert state['ExitCode']==0 and state['Pid']==0
        assert not docker('top',lb,check=False)
        checks.append('Node/master SIGKILL fail-fast sibling shutdown; recovery; graceful Docker stop exit0/no container processes')
        print(json.dumps({'result':'PASS','checks':checks,'scope':'isolated Docker/mock only; no paid inference or deployment'}))
    finally:
        for name in reversed(names):
            docker('rm','-f',name,check=False)
        docker('network','rm',network,check=False)
        docker('image','rm',image,check=False)
        assert not docker('ps','-aq','--filter','name='+tag)
        assert not docker('network','ls','-q','--filter','name='+tag)
        print('Verified isolated container/network cleanup: '+tag)


if __name__ == '__main__':
    main()
