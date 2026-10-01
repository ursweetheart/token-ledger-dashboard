"""Platform networking and startup credential checks without deployment changes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).resolve().parents[1]/'scripts/dashboard.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_linux_proxy_reaches_host_loopback(self):
        config = launcher.runtime_config(Path('/repo/.local/connections'), False)['services']
        self.assertEqual(config['connection-worker-proxy']['network_mode'], 'host')
        self.assertIn('host.docker.internal:host-gateway', config['api']['extra_hosts'])

    def test_windows_proxy_uses_desktop_bridge(self):
        config = launcher.runtime_config(Path('runtime'), True)['services']
        self.assertNotIn('network_mode', config['connection-worker-proxy'])
        self.assertIn('host.docker.internal:host-gateway', config['connection-worker-proxy']['extra_hosts'])

    def test_unauthorized_listener_is_not_accepted(self):
        error = urllib.error.HTTPError('http://localhost', 401, 'Unauthorized', {}, None)
        with patch.object(launcher.urllib.request, 'urlopen', side_effect=error):
            self.assertFalse(launcher.worker_ready({'CONNECTION_WORKER_KEY':'probe'}))

    def test_authenticated_missing_profile_confirms_worker(self):
        error = urllib.error.HTTPError('http://localhost', 404, 'Missing profile', {}, None)
        with patch.object(launcher.urllib.request, 'urlopen', side_effect=error):
            self.assertTrue(launcher.worker_ready({'CONNECTION_WORKER_KEY':'probe'}))

    def test_start_brings_postgres_up_before_the_worker(self):
        # After a reboot postgres may be stopped; a worker started first fails every cycle.
        steps = []
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state/'worker-env.json').write_text(json.dumps({'CONNECTION_REPO_ROOT': str(launcher.ROOT)}), encoding='utf-8')
            with patch.object(launcher, 'STATE', state), \
                 patch.object(launcher, 'run', side_effect=lambda args, **kw: steps.append(' '.join(map(str, args)))), \
                 patch.object(launcher, 'worker_ready', side_effect=lambda config: steps.append('worker_ready') or True), \
                 patch.object(launcher, 'read_env', return_value={'DASHBOARD_KEY': 'd', 'CONNECTION_ADMIN_KEY': 'a'}), \
                 patch.object(launcher.urllib.request, 'urlopen') as opened:
                opened.return_value.__enter__.return_value.status = 200
                with contextlib.redirect_stdout(io.StringIO()):
                    launcher.start()
        postgres = next(i for i, step in enumerate(steps) if step.endswith('up -d --wait postgres'))
        self.assertLess(postgres, steps.index('worker_ready'))

    def test_worker_command_starts_only_the_worker(self):
        # `worker` must not rebuild or recreate containers, and must not spawn a second worker.
        steps = []
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state/'worker-env.json').write_text(json.dumps({'CONNECTION_REPO_ROOT': str(launcher.ROOT)}), encoding='utf-8')
            with patch.object(launcher, 'STATE', state), \
                 patch.object(launcher, 'run', side_effect=lambda args, **kw: steps.append(' '.join(map(str, args)))), \
                 patch.object(launcher, 'worker_ready', return_value=True), \
                 patch.object(launcher.subprocess, 'Popen') as spawned:
                with contextlib.redirect_stdout(io.StringIO()):
                    launcher.ensure_worker()
        spawned.assert_not_called()
        self.assertEqual(len(steps), 1)
        self.assertTrue(steps[0].endswith('up -d --wait postgres'))


if __name__ == '__main__':
    unittest.main()
