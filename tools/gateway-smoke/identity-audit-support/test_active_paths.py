"""In-memory probes of real helpers and AST-extracted background functions.
Not authenticated HTTP-router tests; no FastAPI replacement or application startup.
"""
import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.services.token_logger import get_usage_context, token_usage_context
from app.services import parser

ROOT = Path('C:/law_insight/backend/app')

class StopProbe(BaseException):
    pass

def extracted(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), fn], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(ROOT / path), 'exec'), namespace)
    return namespace[name]

@pytest.mark.asyncio
async def test_gateway_pdf_still_selects_direct_ocr_if_key_present(monkeypatch):
    from app.services import gemini_ocr
    seen = []
    async def fake(*args):
        seen.append(get_usage_context())
        return 'synthetic document ' * 10, 1
    monkeypatch.setenv('GEMINI_API_KEY_1', 'synthetic-not-a-provider-key')
    monkeypatch.setattr(gemini_ocr, 'ocr_pdf_with_gemini', fake)
    assert parser.settings.llm_mode == 'gateway'
    assert await parser.parse_pdf(b'synthetic', 'synthetic.pdf')
    assert seen == [None]

@pytest.mark.asyncio
async def test_gateway_pdf_still_selects_cloud_parser_without_identity(monkeypatch):
    seen = []
    async def fake(*args):
        seen.append(get_usage_context())
        return 'synthetic cloud document ' * 10
    monkeypatch.setenv('GEMINI_API_KEY_1', '')
    monkeypatch.setattr(parser.settings, 'llama_cloud_api_key_1', 'synthetic-only')
    monkeypatch.setattr(parser, '_llamaparse', fake)
    assert parser.settings.llm_mode == 'gateway'
    assert await parser.parse_pdf(b'synthetic', 'synthetic.pdf')
    assert seen == [None]

@pytest.mark.asyncio
async def test_knowledge_background_enters_parser_without_usage_context(monkeypatch):
    seen = []
    async def fake(*args):
        seen.append(get_usage_context())
        raise StopProbe()
    monkeypatch.setattr(parser, 'parse_pdf', fake)
    fn = extracted('routers/knowledge.py', '_process_knowledge_background', {'logger': logging.getLogger('audit')})
    with pytest.raises(StopProbe):
        await fn('synthetic-id', b'synthetic', 'synthetic.pdf', 'synthetic', 'LUAT', None)
    assert seen == [None]

@pytest.mark.asyncio
async def test_analyze_background_restores_user_snapshot_and_parallel_tasks(monkeypatch):
    import sys
    # DTO-only stand-in: qdrant_client is absent; not RAG integration evidence.
    monkeypatch.setitem(sys.modules, 'app.services.rag_access', SimpleNamespace(RagAccessContext=SimpleNamespace))
    seen = []
    async def pipeline(*args, **kwargs):
        await asyncio.sleep(0)
        c = get_usage_context()
        seen.append((c.user_id, c.username, c.function_name))
        raise StopProbe()
    fn = extracted('routers/analyze.py', '_run_pipeline_background_impl', {
        'logger': logging.getLogger('audit'), '_cache_get': lambda sid: None,
        'token_usage_context': token_usage_context, 'run_pipeline': pipeline,
    })
    async def one(name):
        with pytest.raises(StopProbe):
            await fn('synthetic-session-' + name, 'synthetic', 'id-' + name, 'user', None, None, name, [], '')
    await asyncio.gather(*(one(name) for name in ['alice', 'bob', 'carol']))
    assert sorted(seen) == [('id-' + n, n, 'analyze') for n in ['alice', 'bob', 'carol']]
    assert get_usage_context() is None

@pytest.mark.asyncio
async def test_marker_llm_executor_does_not_copy_usage_context(monkeypatch):
    from app.services import marker_converter
    seen = []
    monkeypatch.setattr(marker_converter, '_get_llm_converter', lambda: object())
    def convert(*args):
        seen.append(get_usage_context())
        return 'synthetic', 1
    monkeypatch.setattr(marker_converter, '_run_converter', convert)
    with token_usage_context(user_id='id-alice', username='alice', company_id=None, unit_id=None, session_id=None, function_name='ocr'):
        assert await marker_converter.convert_pdf_with_llm(b'synthetic', 'synthetic.pdf') == ('synthetic', 1)
        assert get_usage_context().username == 'alice'
    assert seen == [None]
