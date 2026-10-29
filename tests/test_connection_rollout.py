"""Gateway startup may take a minute while Prisma prepares the database."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend.connection_worker import Worker


class RolloutStartupTests(unittest.TestCase):
    def rollout(self, ready_after):
        elapsed = [0]
        started = {}
        deployed = []
        content = b'model_list: []\n'

        def sleep(seconds):
            elapsed[0] += seconds

        def compose(*args):
            if args[0] == 'up':
                service = args[-1]
                started[service] = elapsed[0]
                deployed.append(service)
                return b''
            return content if args[-1] == '/app/config.yaml' else b''

        def call(service, path):
            if path == '/health/liveliness' and elapsed[0] - started[service] < ready_after:
                raise RuntimeError('Gateway unavailable or invalid response')
            return {}, {'data': []}

        with tempfile.TemporaryDirectory() as folder:
            routes = Path(folder) / 'config.yaml'
            routes.write_bytes(content)
            worker = Worker.__new__(Worker)
            worker.paths = {'routes': routes, 'environment': Path(folder) / 'managed.env'}
            worker.gateways = [SimpleNamespace(call=lambda path, service=service: call(service, path))
                               for service in ('litellm-1', 'litellm-2')]
            with patch.object(worker, 'compose', side_effect=compose), \
                    patch('backend.connection_worker.time.sleep', side_effect=sleep):
                worker.rollout()
        return deployed, elapsed[0]

    def test_rollout_waits_for_slow_startup_on_both_instances(self):
        deployed, elapsed = self.rollout(60)
        self.assertEqual(deployed, ['litellm-1', 'litellm-2'])
        self.assertGreaterEqual(elapsed, 120)

    def test_rollout_stops_when_gateway_never_becomes_ready(self):
        with self.assertRaisesRegex(RuntimeError, 'litellm-1 did not become healthy'):
            self.rollout(float('inf'))


if __name__ == '__main__':
    unittest.main()
