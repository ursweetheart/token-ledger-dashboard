"""Offline audit guards; synthetic settings, no dotenv or TCP egress."""
import os
import sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
for key in ('GEMINI_API_KEY_1', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3', 'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'KIMI_API_KEY_1', 'KIMI_API_KEY_2', 'MISTRAL_API_KEY_1', 'MISTRAL_API_KEY_2', 'MISTRAL_API_KEY_3', 'LLAMA_CLOUD_API_KEY_1', 'LLAMA_CLOUD_API_KEY_2'):
    os.environ[key] = ''
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://audit:audit@127.0.0.1:1/audit_never_connect'
os.environ['JWT_SECRET'] = 'synthetic-offline-audit-not-a-real-secret'
os.environ['LLM_MODE'] = 'gateway'
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'

def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0]).replace('\\', '/').lower()
        if path.rsplit('/', 1)[-1] == '.env':
            raise PermissionError('Audit forbids dotenv reads')
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
        caller = sys._getframe(1)
        if (event == 'socket.connect' and caller.f_code.co_name == '_fallback_socketpair'
                and caller.f_code.co_filename.replace('\\', '/').endswith('/socket.py')
                and args[1][0] in ('127.0.0.1', '::1')):
            return  # Windows asyncio internal wakeup socket, never app traffic.
        raise PermissionError('Audit forbids network access')
sys.addaudithook(guard)
import dotenv
import dotenv.main
dotenv.load_dotenv = dotenv.main.load_dotenv = lambda *a, **k: False
dotenv.dotenv_values = dotenv.main.dotenv_values = lambda *a, **k: {}
from pydantic_settings.sources import DotEnvSettingsSource
DotEnvSettingsSource._read_env_files = lambda self: {}
