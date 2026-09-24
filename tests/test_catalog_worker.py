import io
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from scripts import sync_model_catalog as worker


class WorkerTests(unittest.TestCase):
    def test_real_slow_drip_is_cut_off_by_wall_clock_deadline(self):
        import threading
        import time
        import multiprocessing
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        class Drip(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                try:
                    for byte in b'HTTP/1.1 200 OK\r\nContent-Length: 10000\r\n\r\n' + b' '*60:
                        self.connection.sendall(bytes([byte]))
                        time.sleep(.02)
                except OSError: pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Drip)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        before={p.pid for p in multiprocessing.active_children()}
        try:
            with patch.object(worker,'URLS',(f'http://127.0.0.1:{server.server_port}/',)),patch.object(worker,'TOTAL_TIMEOUT',.5,create=True):
                started=time.monotonic()
                try:
                    worker.fetch_catalog()
                except Exception as exc:
                    self.assertIsInstance(exc,TimeoutError)
                else:
                    self.fail('slow-drip transport exceeded its deadline without timeout')
                self.assertLess(time.monotonic()-started,2)
            self.assertEqual({p.pid for p in multiprocessing.active_children()},before)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_cli_dry_run_never_opens_database(self):
        with patch.object(worker,'fetch_catalog',return_value=[{'status':'valid'}]),patch('db.connect.open_db') as db:
            result=worker.main([])
            self.assertTrue(result['dry_run'])
            db.assert_not_called()

    def test_refresh_tick_survives_ingest_timeout(self):
        import subprocess
        from contextlib import nullcontext
        from scripts import refresh_gateway as refresh
        with patch.object(refresh.gateway_registry,'operation_lock',side_effect=lambda dsn: nullcontext()), patch.object(refresh.load_gateway,'main',return_value=0), patch.object(refresh,'pricing_tick') as pricing, patch.object(refresh,'count_gateway_rows',return_value=(0,0,0,0,0)), patch.object(refresh.subprocess,'run',side_effect=subprocess.TimeoutExpired('rollup',1)) as run:
            self.assertEqual(refresh.run_cycle('unused',True,120),1)
            self.assertEqual(refresh.run_cycle('unused',True,120),1)
            self.assertEqual(pricing.call_count,2)
            self.assertGreater(run.call_args.kwargs['timeout'],0)

    def test_deadline_is_checked_after_final_read(self):
        clock=[0]
        class SlowResponse(io.BytesIO):
            def read(self, size):
                clock[0]=31
                return b''
        with patch.object(worker.time,'monotonic',side_effect=lambda:clock[0]):
            with self.assertRaises(TimeoutError):
                worker.fetch_catalog(lambda *a,**k:SlowResponse())

    def test_both_fixed_urls_and_response_limits(self):
        seen=[]
        payloads=[b'{"data":[{"id":"vendor/chat","pricing":{"prompt":"0","completion":"0"}}]}',
                  b'{"data":[{"id":"vendor/embed","pricing":{"prompt":"0","completion":"0"}}]}']
        def fetch(url, timeout):
            seen.append((url,timeout))
            return io.BytesIO(payloads[len(seen)-1])
        rows=worker.fetch_catalog(fetch)
        self.assertEqual(len(rows),2)
        self.assertEqual([r[0] for r in seen], list(worker.URLS))
        self.assertTrue(all(0<r[1]<=10 for r in seen))
        with self.assertRaises(ValueError):
            worker.fetch_catalog(lambda *a,**k:io.BytesIO(b'x'*(worker.MAX_BYTES+1)))
        self.assertRaises(ValueError,worker.NoRedirect().redirect_request,None,None,302,'',{},'http://invalid')

if __name__=='__main__': unittest.main()
