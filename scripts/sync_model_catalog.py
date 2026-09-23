"""Public catalog only; default CLI dry-run does not open any database."""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.model_pricing import parse_catalogs

URLS = ('https://openrouter.ai/api/v1/models',
        'https://openrouter.ai/api/v1/embeddings/models')
MAX_BYTES = 16 * 1024 * 1024
TOTAL_TIMEOUT = 30


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('catalog redirects forbidden')


def fetch_catalog(transport=None):
    fetch = transport or urllib.request.build_opener(NoRedirect()).open
    timeout_cap = getattr(sys.modules[__name__], 'TOTAL_TIMEOUT', TOTAL_TIMEOUT)
    deadline, payloads, size = time.monotonic() + timeout_cap, [], 0
    for url in URLS:
        remaining = deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError('catalog deadline')
        with fetch(url,timeout=min(10,remaining)) as response:
            chunks=[]
            while True:
                if time.monotonic() >= deadline: raise TimeoutError('catalog deadline')
                chunk=response.read(65536)
                if time.monotonic() >= deadline: raise TimeoutError('catalog deadline')
                if not chunk: break
                size += len(chunk)
                if size>MAX_BYTES: raise ValueError('catalog response exceeds 16 MiB')
                chunks.append(chunk)
            payloads.append(json.loads(b''.join(chunks)))
    return parse_catalogs(*payloads)


def run_if_due(cn, now, fetch=fetch_catalog):
    import uuid
    from db.model_pricing import sync_catalog
    token=str(uuid.uuid4())
    with cn:
        with cn.cursor() as cur:
            cur.execute('UPDATE ref_price_sync_state SET last_worker_seen=%s',(now,))
            cur.execute('SELECT enabled,requested,next_due,lease_until FROM ref_price_sync_state FOR UPDATE')
            enabled,requested,due,lease=cur.fetchone()
            if lease and lease>now: return 'leased'
            if not enabled and not requested: return 'disabled'
            if due and due>now: return 'not_due'
            cur.execute("UPDATE ref_price_sync_state SET lease_token=%s,lease_until=%s+interval '2 minutes',last_attempt=%s,status='running',requested=FALSE",(token,now,now))
    try:
        rows=fetch()  # No open DB transaction during network.
        with cn:
            with cn.cursor() as cur:
                cur.execute('SELECT lease_token FROM ref_price_sync_state FOR UPDATE')
                if cur.fetchone()[0]!=token: return 'superseded'
                sync_catalog(cn,rows,now)
                cur.execute("UPDATE ref_price_sync_state SET lease_token=NULL,lease_until=NULL,last_success=%s,next_due=CASE WHEN requested THEN %s ELSE %s+interval_hours*interval '1 hour' END,status='success',last_error_class=NULL",(now,now,now))
        return 'success'
    except Exception as exc:
        cn.rollback()
        with cn:
            with cn.cursor() as cur:
                cur.execute("UPDATE ref_price_sync_state SET lease_token=NULL,lease_until=NULL,status='failed',last_error_class=%s,next_due=%s+interval '15 minutes',requested=TRUE WHERE lease_token=%s",(type(exc).__name__,now,token))
        return 'failed'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--db',help='Explicit pricing-writer DSN required for apply/mapping')
    parser.add_argument('--link-local',type=int)
    parser.add_argument('--openrouter-id')
    args=parser.parse_args(argv)
    if args.link_local is not None:
        if not args.db or not args.openrouter_id: parser.error('mapping requires --db and --openrouter-id')
        from db import connect
        from db.model_pricing import link_model
        cn,_=connect.open_db(args.db)
        try:
            if not args.apply: cn.set_session(readonly=True)
            key=link_model(cn,args.link_local,args.openrouter_id,args.apply)
            if args.apply: cn.commit()
            with cn.cursor() as cur:
                cur.execute('SELECT catalog_key,revision,openrouter_id FROM ref_model_catalog WHERE catalog_key=%s',(key,))
                return dict(dry_run=not args.apply,canonical=cur.fetchone())
        finally: cn.close()
    if args.apply:
        if not args.db: parser.error('--apply requires explicit --db')
        from db import connect
        from datetime import datetime,timezone
        cn,_=connect.open_db(args.db)
        try:
            with cn:
                with cn.cursor() as cur: cur.execute('UPDATE ref_price_sync_state SET requested=TRUE,next_due=now()')
            return {'status':run_if_due(cn,datetime.now(timezone.utc))}
        finally: cn.close()
    rows=fetch_catalog()
    return {'dry_run':True,'models':len(rows),'valid':sum(r['status']=='valid' for r in rows)}


if __name__=='__main__':
    print(json.dumps(main()))
