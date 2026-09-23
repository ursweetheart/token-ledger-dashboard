"""Daily reference prices. No facts are changed; unknown is never free."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

BUSINESS_TZ = timezone(timedelta(hours=7))


def parse_rate(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('rate must be a decimal string')
    if len(str(value)) > 40:
        raise ValueError('rate too long')
    try:
        rate = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('invalid rate') from exc
    if not rate.is_finite() or rate < 0 or rate > 1000000 or rate.as_tuple().exponent < -12:
        raise ValueError('rate out of bounds (0..1000000, 12 decimals)')
    return rate


def match_model(raw, ids, aliases):
    # Only this reviewed provider alias; suffixes/variants are identities.
    candidates = set(aliases.get(raw, []))
    if raw.startswith('gemini/'):
        exact = 'google/' + raw[len('gemini/'):]
    elif raw.startswith(('gemini-', 'gemma-')):
        exact = 'google/' + raw
    else:
        exact = raw
    if exact in ids:
        candidates.add(exact)
    return next(iter(candidates)) if len(candidates) == 1 and candidates <= set(ids) else None


def select_price(versions, day):
    active = [v for v in versions if v['valid_from'] <= day
              and (v.get('valid_to') is None or day < v['valid_to'])]
    manual = max((v for v in active if v['source'] == 'manual'),
                 key=lambda v: v['id'], default=None)
    if manual and manual['mode'] == 'price':
        return manual
    official = [v for v in active if v['source'] == 'official']
    return max(official or [v for v in active if v['source'] == 'openrouter'],
               key=lambda v: (v['valid_from'], v['id']), default=None)


def estimate_text(usage, rates):
    if usage.get('cache_coverage') is not True or usage.get('input_includes_cache') not in (True, False):
        return None, 'incomplete'
    if usage.get('text_only_evidence') is not True or usage.get('extra_billable_evidence') is not False:
        return None, 'unsupported'
    counts = [usage.get(k) for k in ('input', 'output', 'cache_read', 'cache_write')]
    if any(n is None for n in counts):
        return None, 'incomplete'
    # PostgreSQL SUM(bigint) returns NUMERIC/Decimal, even for whole tokens.
    if any(isinstance(n, bool) or not isinstance(n, (int, Decimal))
           or (isinstance(n, Decimal) and (not n.is_finite() or n != n.to_integral_value()))
           or n < 0 for n in counts):
        return None, 'invalid_usage'
    inp, out, cache, write = map(int, counts)
    if write:
        return None, 'unsupported'
    if usage['input_includes_cache']:
        if cache > inp:
            return None, 'invalid_usage'
        inp -= cache
    total = Decimal(0)
    for count, key in ((inp, 'input'), (out, 'output'), (cache, 'cache_read')):
        if count:
            rate = parse_rate(rates.get(key))
            if rate is None:
                return None, 'missing_rate'
            total += count * rate / 1000000
    return total, 'estimated'


def adapt_usage(row, evidence):
    source = row.get('token_source')
    return dict(input=row.get('input_tokens'), output=row.get('output_tokens'),
                cache_read=row.get('cached_tokens'), cache_write=evidence.get('cache_write'),
                input_includes_cache=False if source=='billing' else evidence.get('input_includes_cache'),
                cache_coverage=bool(evidence.get('source_rows')) and evidence.get('cache_missing_rows')==0,
                text_only_evidence=evidence.get('text_only'),
                extra_billable_evidence=evidence.get('extra_billable'))


def parse_catalogs(*payloads):
    result, seen = [], set()
    for payload in payloads:
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
            raise ValueError('catalog requires data array')
        for raw in payload['data']:
            key = raw.get('id') if isinstance(raw, dict) else None
            if not isinstance(key, str) or '/' not in key or len(key) > 300 or key in seen:
                raise ValueError('invalid or duplicate exact model ID')
            seen.add(key)
            rates, status = {}, 'valid'
            source = raw.get('pricing') or {}
            try:
                for name, field in (('input','prompt'), ('output','completion'), ('cache_read','input_cache_read')):
                    value = parse_rate(source.get(field))
                    rates[name] = None if value is None else str(parse_rate(value * 1000000))
                if rates['input'] is None or rates['output'] is None:
                    status = 'missing'
                if any(parse_rate(v) not in (None, Decimal(0)) for k,v in source.items()
                       if k not in ('prompt','completion','input_cache_read','discount')):
                    status = 'unsupported'
            except (ValueError, AttributeError):
                status = 'unsupported'
            result.append(dict(openrouter_id=key, catalog_key='or:'+key,
                               provider=key.split('/',1)[0], display_name=raw.get('name') or key,
                               pricing=rates, status=status, metadata=raw))
    if not result:
        raise ValueError('empty catalog cannot mark all models unavailable')
    return result


def link_model(cn, model_id, external_id, apply=False):
    """Reviewed exact alias only. Caller commits; dry-run writes nothing."""
    with cn.cursor() as cur:
        # ponytail: serialize pricing writes; shard only if throughput requires it.
        if apply: cur.execute('SELECT singleton FROM ref_price_sync_state FOR UPDATE')
        cur.execute('SELECT source,raw_name,model_id FROM dim_model_alias')
        matches={mid for source,raw,mid in cur.fetchall()
                 if match_model(raw,{external_id},{'gemini-embedding-1.0':['google/gemini-embedding-001']})==external_id}
        if matches!={model_id}: raise ValueError('unresolved or colliding exact aliases')
        cur.execute('SELECT catalog_key,local_model_id,openrouter_id FROM ref_model_catalog WHERE local_model_id=%s OR openrouter_id=%s ORDER BY catalog_key'+(' FOR UPDATE' if apply else ''),(model_id,external_id))
        rows=cur.fetchall()
        local=next((r for r in rows if r[1]==model_id),None)
        external=next((r for r in rows if r[2]==external_id),None)
        if not local or not external or (local[2] and local[2]!=external_id) or (external[1] and external[1]!=model_id):
            raise ValueError('missing or conflicting canonical catalog')
        if local[0]==external[0]: return local[0]
        cur.execute("SELECT DISTINCT catalog_key FROM ref_model_price_version WHERE catalog_key=ANY(%s) AND source='manual'",([local[0],external[0]],))
        manual={r[0] for r in cur.fetchall()}
        if external[0] in manual: raise ValueError('external manual history requires operator resolution')
        if apply:
            cur.execute('UPDATE ref_model_price_version SET catalog_key=%s WHERE catalog_key=%s',(local[0],external[0]))
            cur.execute('UPDATE ref_model_catalog SET openrouter_id=NULL WHERE catalog_key=%s',(external[0],))
            cur.execute("UPDATE ref_model_catalog c SET openrouter_id=%s,provider=e.provider,display_name=e.display_name,metadata=e.metadata || jsonb_build_object('mapping_principal','operator_cli','mapping_at',now()),available=e.available,last_seen_at=e.last_seen_at,price_last_verified_at=e.price_last_verified_at,revision=c.revision+1 FROM ref_model_catalog e WHERE c.catalog_key=%s AND e.catalog_key=%s",(external_id,local[0],external[0]))
            cur.execute('DELETE FROM ref_model_catalog WHERE catalog_key=%s',(external[0],))
            cur.execute('UPDATE ref_price_sync_state SET generation=generation+1')
        return local[0]


def sync_catalog(cn, rows, observed_at):
    """Caller owns transaction and lease. No automatic identity merging."""
    import json
    if not rows or observed_at.tzinfo is None:
        raise ValueError('complete catalog and aware observation required')
    day = observed_at.astimezone(BUSINESS_TZ).date() + timedelta(days=1)
    counts = dict(new=0, changed=0, unavailable=0)
    with cn.cursor() as cur:
        cur.execute('SELECT singleton FROM ref_price_sync_state FOR UPDATE')
        for row in rows:
            cur.execute('SELECT catalog_key FROM ref_model_catalog WHERE openrouter_id=%s FOR UPDATE', (row['openrouter_id'],))
            old = cur.fetchone()
            if not old:
                # Tự liên kết với model local trong database nếu trùng khớp
                cur.execute('''
                    SELECT c.catalog_key
                    FROM ref_model_catalog c
                    JOIN dim_model m ON c.local_model_id = m.model_id
                    WHERE c.openrouter_id IS NULL
                      AND (
                           %s = m.name
                        OR %s = 'google/' || m.name
                        OR %s = 'google/' || replace(m.name, '1.0', '001')
                        OR EXISTS (
                            SELECT 1 FROM dim_model_alias a
                            WHERE a.model_id = m.model_id
                              AND (%s = a.raw_name OR (a.raw_name LIKE 'gemini/%%' AND %s = 'google/' || substr(a.raw_name, 8)))
                        )
                      )
                    LIMIT 1
                    FOR UPDATE
                ''', (row['openrouter_id'], row['openrouter_id'], row['openrouter_id'], row['openrouter_id'], row['openrouter_id']))
                matched = cur.fetchone()
                if matched:
                    key = matched[0]
                    cur.execute("UPDATE ref_model_catalog SET openrouter_id=%s, display_name=%s, provider=%s WHERE catalog_key=%s",
                                (row['openrouter_id'], row['display_name'], row['provider'], key))
                else:
                    key = row['catalog_key']
                    cur.execute('INSERT INTO ref_model_catalog(catalog_key,openrouter_id,provider,display_name,first_seen_at) VALUES (%s,%s,%s,%s,%s)',
                                (key,row['openrouter_id'],row['provider'],row['display_name'],observed_at))
                    counts['new'] += 1
            else:
                key = old[0]
            cur.execute('SELECT pricing,status FROM ref_model_price_version WHERE catalog_key=%s AND source=\'openrouter\' ORDER BY valid_from DESC,id DESC LIMIT 1', (key,))
            previous = cur.fetchone()
            changed = previous != (row['pricing'],row['status'])
            if changed:
                cur.execute('INSERT INTO ref_model_price_version(catalog_key,source,mode,valid_from,observed_at,pricing,status,principal,reason) VALUES (%s,\'openrouter\',\'price\',%s,%s,%s::jsonb,%s,\'catalog_worker\',\'catalog snapshot\')',
                            (key,day,observed_at,json.dumps(row['pricing']),row['status']))
                counts['changed'] += 1
            cur.execute('UPDATE ref_model_catalog SET available=TRUE,last_seen_at=%s,price_last_verified_at=CASE WHEN %s THEN %s ELSE price_last_verified_at END,metadata=%s::jsonb,display_name=%s,revision=revision+%s WHERE catalog_key=%s',
                        (observed_at,row['status']=='valid',observed_at,json.dumps(row['metadata']),row['display_name'],int(changed),key))
        cur.execute('UPDATE ref_model_catalog SET available=FALSE,revision=revision+1 WHERE openrouter_id IS NOT NULL AND available AND NOT(openrouter_id=ANY(%s))',
                    ([r['openrouter_id'] for r in rows],))
        counts['unavailable'] = cur.rowcount
        cur.execute('UPDATE ref_price_sync_state SET generation=generation+1')
    return counts
