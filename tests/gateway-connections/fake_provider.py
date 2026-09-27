"""Deterministic OpenAI-compatible provider; never leaves the fixture network."""
import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        payload = {'id': 'chatcmpl-' + uuid.uuid4().hex, 'object': 'chat.completion',
                   'created': 1, 'model': body['model'],
                   'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'OK'},
                                'finish_reason': 'stop'}],
                   'usage': {'prompt_tokens': 3, 'completion_tokens': 1, 'total_tokens': 4}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
