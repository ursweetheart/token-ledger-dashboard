"""Pricing writes use an explicit restricted credential, never store.open_db."""
import os
import json
from contextlib import contextmanager
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from db.model_pricing import BUSINESS_TZ, parse_rate, select_price
from . import store


@contextmanager
def open_writer():
    dsn = os.environ.get('PRICING_WRITE_DSN')
    if not dsn:
        raise HTTPException(503, 'PRICING_WRITE_DSN is required (pricing tables only)')
    cn, ph = store.connect.open_db(dsn)
    try:
        with cn:
            yield cn, ph
    finally:
        cn.close()


def proposal(body):
    try:
        mode = body['mode']
        start = date.fromisoformat(body['from_day'])
        end = date.fromisoformat(body['to_day']) if body.get('to_day') else None
        if mode not in ('price','auto') or (end and end <= start):
            raise ValueError('invalid mode or date interval')
        reason = body.get('reason','').strip()
        if not reason or len(reason)>1000:
            raise ValueError('reason required (max 1000)')
        rates = {}
        for key, field in (('input','input_per_million'),('output','output_per_million'),('cache_read','cache_read_per_million')):
            value = body.get(field)
            if mode == 'auto':
                if value is not None: raise ValueError('auto must not carry rates')
            else:
                if value is not None and not isinstance(value,str): raise ValueError('rates must be decimal strings')
                rate = parse_rate(value)
                if key != 'cache_read' and rate is None: raise ValueError('input and output required')
                rates[key] = None if rate is None else str(rate)
        return mode,start,end,reason,rates
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(422,str(exc)) from exc


def usage_evidence(cn, start, end, model_ids):
    # Source rows, not SUM(cache), determine completeness. Current Gateway/app
    # facts do not retain modality or paid-tool evidence: leave those unknown.
    rows=store._rows(cn,"""WITH source_rows AS (
        SELECT ts_local::date AS day,agent_id,model_id,source,account_id,
               cached_tokens,prompt_tokens,completion_tokens
        FROM fact_call WHERE ts_local::date BETWEEN %s AND %s AND model_id=ANY(%s)
          AND (source='app' OR (source='gateway' AND outcome='success' AND cache_hit IS NOT TRUE))
        UNION ALL
        SELECT day,agent_id,model_id,'app',account_id,NULL,prompt_tokens,completion_tokens
        FROM fact_app_daily WHERE day BETWEEN %s AND %s AND model_id=ANY(%s))
        SELECT day,agent_id,model_id,source,account_id,count(*) AS source_rows,
               count(*) FILTER(WHERE cached_tokens IS NULL OR prompt_tokens IS NULL
                               OR completion_tokens IS NULL) AS cache_missing_rows
        FROM source_rows GROUP BY GROUPING SETS
          ((day,agent_id,model_id,source),(day,agent_id,model_id,source,account_id))""",
        (start,end,model_ids,start,end,model_ids))
    evidence={}
    for r in rows:
        key=(r['day'],r['agent_id'],r['model_id'],r['source'])
        if r['account_id'] is not None: key+=(r['account_id'],)
        evidence[key]=r
    billing=store._rows(cn,"""SELECT day,agent_id,model_id,count(*) AS source_rows,
        bool_and(COALESCE(sku_name ~* ' text$',FALSE)) AS text_only,
        count(*) FILTER(WHERE quantity IS NULL OR kind IS NULL
                        OR kind NOT IN ('input','output','cached')) AS cache_missing_rows,
        bool_or(sku_id IN ('54F8-C433-9340','5882-9C22-CC57')) AS identity_conflict
        FROM fact_billing_daily WHERE day BETWEEN %s AND %s AND model_id=ANY(%s)
        GROUP BY 1,2,3""",(start,end,model_ids))
    anchors=store._rows(cn,"SELECT unit_agent_id,account_id FROM account WHERE kind IN ('service_account','whole_agent')")
    for r in billing:
        r.update(cache_write=0,extra_billable=False if r['text_only'] else None)
        if r['identity_conflict']: r['text_only']=None
        key=(r['day'],r['agent_id'],r['model_id'],'billing')
        evidence[key]=r
        accounts=[a['account_id'] for a in anchors if a['unit_agent_id']==r['agent_id']]
        if len(accounts)==1: evidence[key+(accounts[0],)]=r
    return evidence


def attach_estimates(cn, rows, start, end, proposed=None):
    from db.model_pricing import adapt_usage, estimate_text
    if not rows: return rows
    ids=list({r['model_id'] for r in rows})
    versions=store._rows(cn,'SELECT v.*,c.local_model_id,c.price_last_verified_at,c.available FROM ref_model_price_version v JOIN ref_model_catalog c USING(catalog_key) WHERE c.local_model_id=ANY(%s) AND v.valid_from<=%s',(ids,end))
    interval=store._rows(cn,'SELECT interval_hours FROM ref_price_sync_state')[0]['interval_hours']
    now=datetime.now(BUSINESS_TZ)
    # Only documented Google catalog provenance qualifies as official.
    legacy=store._rows(cn,"SELECT * FROM ref_price WHERE model_id=ANY(%s) AND effective_from<=%s AND source='google'",(ids,end))
    for v in legacy:
        versions.append(dict(id=0,source='official',mode='price',valid_from=v['effective_from'],valid_to=None,status='valid',local_model_id=v['model_id'],pricing={'input':v['price_input'],'output':v['price_output'],'cache_read':v['price_cached']}))
    if proposed: versions.append(proposed)
    evidence=usage_evidence(cn,start,end,ids)
    grouped={model:[v for v in versions if v['local_model_id']==model] for model in ids}
    for r in rows:
        day=date.fromisoformat(r['day']) if isinstance(r['day'],str) else r['day']
        price=select_price(grouped[r['model_id']],day)
        key=(day,r['agent_id'],r['model_id'],r.get('token_source'))
        if 'account_id' in r: key+=(r['account_id'],)
        ev=evidence.get(key, {})
        value,status=(None,'missing_price')
        if price:
            value,status=estimate_text(adapt_usage(r,ev),price['pricing']) if price['status']=='valid' else (None,price['status'])
        automatic=price is not None and price['source']=='openrouter'
        verified=price.get('price_last_verified_at') if automatic else None
        stale=automatic and (verified is None or (now-verified).total_seconds()>interval*7200)
        r.update(estimated_cost_usd=store._f(value),estimate_source=price['source'] if price else None,
                 estimate_status=status,price_version_id=price['id'] if price else None,
                 estimate_stale=stale,price_last_verified_at=verified,
                 price_available=price.get('available') if automatic else None,
                 stale_priced_rows=int(value is not None and stale),
                 priced_rows=int(value is not None),unpriced_rows=int(value is None))
    return rows


def build_router(caller):
    router = APIRouter(prefix='/api/pricing')

    def writer(actor=Depends(caller)):
        if os.environ.get('PRICING_WRITE_ENABLED') != '1' or actor.kind == 'open_mode':
            raise HTTPException(403,'Pricing writes disabled; shared Dashboard key required')
        return actor

    @router.get('/history')
    def history(catalog_key: str, offset: int=Query(0,ge=0), limit: int=Query(50,ge=1,le=200), actor=Depends(caller)):
        with store.open_db() as (cn,_):
            return {'rows':store._rows(cn,'SELECT * FROM ref_model_price_version WHERE catalog_key=%s ORDER BY id DESC LIMIT %s OFFSET %s',(catalog_key,limit,offset))}

    @router.post('/preview')
    def preview(body: dict, catalog_key: str, actor=Depends(caller)):
        mode,start,end,reason,rates=proposal(body)
        with store.open_db() as (cn,_):
            model=store._rows(cn,'SELECT * FROM ref_model_catalog WHERE catalog_key=%s',(catalog_key,))
            if not model: raise HTTPException(404,'Unknown catalog key')
            model=model[0]
            rows=store._rows(cn,'SELECT * FROM usage_resolved WHERE model_id=%s AND day>=%s AND (%s::date IS NULL OR day<%s::date)',(model['local_model_id'],start,end,end)) if model['local_model_id'] else []
            last=max((r['day'] for r in rows),default=start)
            attach_estimates(cn,rows,start,last)
            old=sum(r['estimated_cost_usd'] or 0 for r in rows)
            unknown=sum(r['unpriced_rows'] for r in rows)
            proposed=dict(id=9223372036854775807,local_model_id=model['local_model_id'],source='manual',mode=mode,valid_from=start,valid_to=end,pricing=rates,status='valid')
            attach_estimates(cn,rows,start,last,proposed)
            return dict(revision=model['revision'],as_of=datetime.now(BUSINESS_TZ),rows_affected=len(rows),
                        agents_affected=len({r['agent_id'] for r in rows}),old_known_subtotal=old,
                        old_unknown_rows=unknown,new_known_subtotal=sum(r['estimated_cost_usd'] or 0 for r in rows),
                        new_unknown_rows=sum(r['unpriced_rows'] for r in rows),
                        warning='Point-in-time estimate, not invoice. Older overrides resume after a finite reset/override expires.')

    @router.post('/versions')
    def save(body: dict, catalog_key: str, actor=Depends(writer)):
        mode,start,end,reason,rates = proposal(body)
        if start < datetime.now(BUSINESS_TZ).date() and body.get('confirm_retroactive') is not True:
            raise HTTPException(409,'Explicit retroactive confirmation required')
        revision = body.get('expected_revision')
        if isinstance(revision,bool) or not isinstance(revision,int) or revision<0:
            raise HTTPException(422,'expected_revision required')
        with open_writer() as (cn,_):
            with cn.cursor() as cur:
                cur.execute('SELECT singleton FROM ref_price_sync_state FOR UPDATE')
            row=store._rows(cn,'SELECT revision FROM ref_model_catalog WHERE catalog_key=%s FOR UPDATE',(catalog_key,))
            if not row: raise HTTPException(404,'Unknown catalog key')
            if row[0]['revision']!=revision: raise HTTPException(409,'Price changed; preview again')
            saved=store._rows(cn,"INSERT INTO ref_model_price_version(catalog_key,source,mode,valid_from,valid_to,pricing,status,principal,reason) VALUES (%s,'manual',%s,%s,%s,%s::jsonb,'valid',%s,%s) RETURNING id",
                                  (catalog_key,mode,start,end,json.dumps(rates),actor.kind,reason))[0]
            with cn.cursor() as cur:
                cur.execute('UPDATE ref_model_catalog SET revision=revision+1 WHERE catalog_key=%s',(catalog_key,))
                cur.execute('UPDATE ref_price_sync_state SET generation=generation+1')
            cn.commit()
            return store._rows(cn,'SELECT * FROM ref_model_price_version WHERE id=%s',(saved['id'],))[0]

    @router.get('/models')
    def models(provider: str='', q: str='', offset: int=Query(0,ge=0), limit: int=Query(50,ge=1,le=200), actor=Depends(caller)):
        with store.open_db() as (cn,_):
            cond = "local_model_id IS NOT NULL AND (%s='' OR provider ILIKE %s) AND (catalog_key ILIKE %s OR display_name ILIKE %s)"
            params = [provider, provider, '%'+q+'%', '%'+q+'%']
            rows=store._rows(cn,f"SELECT * FROM ref_model_catalog WHERE {cond} ORDER BY local_model_id, provider, display_name, catalog_key LIMIT %s OFFSET %s",(*params,limit,offset))
            versions=store._rows(cn,'SELECT * FROM ref_model_price_version WHERE catalog_key=ANY(%s)',([r['catalog_key'] for r in rows],)) if rows else []
            today=datetime.now(BUSINESS_TZ).date()
            local_keys={r['local_model_id']:r['catalog_key'] for r in rows if r['local_model_id'] is not None}
            legacy=store._rows(cn,"SELECT * FROM ref_price WHERE model_id=ANY(%s) AND effective_from<=%s AND source='google'",(list(local_keys),today)) if local_keys else []
            for v in legacy:
                versions.append(dict(id=0,catalog_key=local_keys[v['model_id']],source='official',mode='price',valid_from=v['effective_from'],valid_to=None,status='valid',pricing={'input':v['price_input'],'output':v['price_output'],'cache_read':v['price_cached']}))
            interval=store._rows(cn,'SELECT interval_hours FROM ref_price_sync_state')[0]['interval_hours']
            for row in rows:
                prices=[v for v in versions if v['catalog_key']==row['catalog_key']]
                row['applied']=select_price(prices,today)
                row['automatic']=select_price([v for v in prices if v['source']!='manual'],today)
                row['manual']=max((v for v in prices if v['source']=='manual' and v['valid_from']<=today and (v['valid_to'] is None or today<v['valid_to'])),key=lambda v:v['id'],default=None)
                verified=row['price_last_verified_at']
                row['stale']=verified is None or (datetime.now(BUSINESS_TZ)-verified).total_seconds()>interval*7200
            return {'rows':rows,'offset':offset,'limit':limit,'write_enabled':os.environ.get('PRICING_WRITE_ENABLED')=='1' and actor.kind!='open_mode'}

    @router.get('/sync')
    def sync_state(actor=Depends(caller)):
        with store.open_db() as (cn,_):
            return store._rows(cn,'SELECT * FROM ref_price_sync_state')[0]

    @router.put('/sync')
    def settings(body: dict, actor=Depends(writer)):
        hours,enabled,revision=body.get('interval_hours'),body.get('enabled'),body.get('expected_revision')
        if type(hours) is not int or not 1<=hours<=168 or type(enabled) is not bool or type(revision) is not int:
            raise HTTPException(422,'enabled boolean, interval_hours 1..168 and expected_revision required')
        with open_writer() as (cn,_):
            rows=store._rows(cn,"UPDATE ref_price_sync_state SET enabled=%s,interval_hours=%s,next_due=now()+%s*interval '1 hour',revision=revision+1,principal=%s WHERE revision=%s RETURNING *",(enabled,hours,hours,actor.kind,revision))
            if not rows: raise HTTPException(409,'Schedule changed; reload')
            cn.commit()
            return store._rows(cn,'SELECT * FROM ref_price_sync_state')[0]

    @router.post('/sync',status_code=202)
    def enqueue(actor=Depends(writer)):
        with open_writer() as (cn,_):
            with cn.cursor() as cur:
                cur.execute("UPDATE ref_price_sync_state SET requested=TRUE,next_due=now(),status='queued',revision=revision+1,principal=%s",(actor.kind,))
            cn.commit()
            return store._rows(cn,'SELECT * FROM ref_price_sync_state')[0]

    return router
