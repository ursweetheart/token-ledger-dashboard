"""Platform networking and startup credential checks without deployment changes."""
import importlib.util
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
