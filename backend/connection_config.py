"""Pure validation/rendering for managed Gateway connections. No side effects."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
import re

import yaml
from db.gateway_registry import parse_config

FIELDS = {'code', 'name', 'user_mode', 'reporting_start_date', 'active', 'secret_ref',
          'models', 'rpm', 'tpm', 'budget', 'quota_response_mode'}
CODE = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
REF = re.compile(r'[A-Z][A-Z0-9_]{1,95}\Z')
MODEL_NAME = re.compile(r'[A-Za-z0-9_./:-]+\Z')
# `GET /api/gateway-connections/catalog` shares the shape of `GET /{code}`.
RESERVED_CODES = {'catalog'}


class Conflict(ValueError):
    pass


class CatalogUnavailable(RuntimeError):
    pass


def is_wildcard(model):
    return model['upstream'].endswith('/*')


def routable_catalog(cost_map, providers):
    """Chat models LiteLLM can route, keyed by routing prefix.

    `litellm_provider` is not a routing prefix (e.g. `vertex_ai-language-models`),
    so the provider comes from the name and must appear in `/public/providers`.
    """
    if not isinstance(cost_map, dict) or not isinstance(providers, list):
        raise ValueError('Gateway catalog has an unexpected shape')
    allowed = {p for p in providers if isinstance(p, str)}
    models = {}
    for key, entry in cost_map.items():
        if not isinstance(entry, dict) or entry.get('mode') != 'chat':
            continue
        name = key if '/' in key else f"{entry.get('litellm_provider')}/{key}"
        provider = name.split('/', 1)[0]
        # Names the form cannot save (e.g. `@` in Vertex versions) are not suggested.
        if provider in allowed and MODEL_NAME.fullmatch(name):
            models.setdefault(provider, set()).add(name)
    return {'providers': sorted(models), 'models': {p: sorted(n) for p, n in sorted(models.items())}}


def concrete_alias(p):
    return next((m['alias'] for m in p['models'] if not is_wildcard(m)), None)


def verification_model(p, requested, catalog):
    """(model to call, alias of the route expected to serve it).

    Verification must name a real model; a wildcard pattern is not callable.
    """
    alias = concrete_alias(p)
    if alias:
        return alias, alias
    routes = {m['upstream'].split('/', 1)[0]: m['alias'] for m in p['models']}
    if not isinstance(requested, str) or not requested:
        raise ValueError('test_model: choose a concrete model for a wildcard-only profile')
    provider = requested.split('/', 1)[0]
    if provider not in routes or requested not in catalog['models'].get(provider, []):
        raise ValueError('test_model: must be a catalog model under one of the profile wildcard providers')
    return requested, routes[provider]


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def deployment_env_digest(content):
    """Dashboard login rotation does not change the deployed Gateway routes."""
    excluded = {'DASHBOARD_KEY', 'CONNECTION_ADMIN_KEY'}
    lines = []
    for line in content.decode('utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name = line.partition('=')[0].strip()
        if name not in excluded:
            lines.append(line)
    return digest(lines)


def load_yaml(text):
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError('Duplicate YAML key')
            result[key] = loader.construct_object(value_node, deep=deep)
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml.load(text, Loader=UniqueLoader)


def registry_row(profile):
    return {k: profile[k] for k in ('code', 'name', 'user_mode', 'reporting_start_date', 'active')}


def validate_budget(value):
    if not isinstance(value, dict) or set(value) - {'mode', 'usd'}:
        raise ValueError('budget: choose finite or unlimited explicitly')
    if value.get('mode') == 'unlimited' and set(value) == {'mode'}:
        return {'mode': 'unlimited'}
    amount = value.get('usd')
    if (value.get('mode') != 'finite' or isinstance(amount, bool) or
            not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0):
        raise ValueError('budget.usd: must be finite and nonnegative')
    return {'mode': 'finite', 'usd': float(amount)}


def validate_profile(value):
    if not isinstance(value, dict) or set(value) - FIELDS or FIELDS - set(value):
        raise ValueError('profile: missing or unknown fields')
    p = deepcopy(value)
    row = registry_row(p)
    parse_config(yaml.safe_dump({'version': 1, 'agents': [row]}))
    if p['code'] in RESERVED_CODES:
        raise ValueError(f'code: "{p["code"]}" is reserved')
    p['name'] = p['name'].strip()
    p['reporting_start_date'] = date.fromisoformat(str(p['reporting_start_date'])).isoformat()
    if not isinstance(p['secret_ref'], str) or not REF.fullmatch(p['secret_ref']):
        raise ValueError('secret_ref: invalid opaque reference')
    for field in ('rpm', 'tpm'):
        if type(p[field]) is not int or p[field] <= 0:
            raise ValueError(f'{field}: must be a positive integer')
    if p['quota_response_mode'] not in ('chat', 'batch'):
        raise ValueError('quota_response_mode: choose chat or batch')
    models = p['models']
    if not isinstance(models, list) or not models or len(models) > 20:
        raise ValueError('models: choose 1 to 20 explicit routes')
    aliases = set()
    for model in models:
        if not isinstance(model, dict) or set(model) != {'alias', 'upstream'}:
            raise ValueError('models: each entry requires alias and upstream')
        for field in ('alias', 'upstream'):
            text = model[field]
            if (not isinstance(text, str) or not text or len(text) > 200 or
                    not MODEL_NAME.fullmatch(text.replace('*', ''))):
                raise ValueError(f'models.{field}: model name required')
        provider, _, rest = model['upstream'].partition('/')
        if not provider or not rest or '*' in provider or ('*' in rest and rest != '*'):
            raise ValueError('models.upstream: use <provider>/<model> or <provider>/*')
        # How LiteLLM maps `*` between two different patterns is unmeasured on the pinned image.
        if ('*' in model['alias'] or rest == '*') and model['alias'] != model['upstream']:
            raise ValueError('models.alias: a provider wildcard alias must equal its upstream')
        if model['alias'] in aliases:
            raise ValueError('models.alias: duplicate')
        aliases.add(model['alias'])
    p['budget'] = validate_budget(p['budget'])
    return p


def route_id(code, alias):
    return 'connection-' + digest({'code': code, 'alias': alias})[:24]


def render_routes(original, profiles, ownership):
    """Only replace manifest-owned route IDs; preserve other configuration."""
    candidate = deepcopy(original)
    if candidate.get('router_settings', {}).get('enable_tag_filtering') is not True:
        raise ValueError('router_settings.enable_tag_filtering must be true')
    owned_ids = set(ownership)
    routes = candidate.get('model_list', [])
    actual_ids = [(r.get('model_info') or {}).get('id') for r in routes]
    if any(actual_ids.count(rid) > 1 for rid in owned_ids):
        raise Conflict('Duplicate owned route IDs')
    unmanaged = [r for r in routes if (r.get('model_info') or {}).get('id') not in owned_ids]
    managed_codes = {p['code'] for p in profiles}
    aliases = candidate.get('router_settings', {}).get('model_group_alias', {}) or {}
    for p in profiles:
        for model in p['models']:
            alias = model['alias']
            if alias in aliases and aliases[alias] != alias:
                raise Conflict('Model alias is redirected by unmanaged router configuration')
    for r in unmanaged:
        tags = (r.get('litellm_params') or {}).get('tags', [])
        if any(tag in managed_codes for tag in tags):
            raise Conflict('An unmanaged route already owns this agent tag; reconcile explicitly')
    new_ids = []
    for p in profiles:
        for model in p['models']:
            rid = route_id(p['code'], model['alias'])
            if rid in actual_ids and rid not in owned_ids:
                raise Conflict('Managed route ID collides with unmanaged configuration')
            unmanaged.append({'model_name': model['alias'], 'litellm_params': {
                'model': model['upstream'], 'api_key': 'os.environ/' + p['secret_ref'],
                'rpm': p['rpm'], 'tpm': p['tpm'], 'tags': [p['code']]}, 'model_info': {'id': rid}})
            new_ids.append(rid)
    candidate['model_list'] = unmanaged
    return candidate, new_ids


def render_registry(original, profiles):
    # Parse strictly before merging: duplicate keys and schema mistakes are errors.
    rows = parse_config(yaml.safe_dump(original))
    by_code = {row['code']: {**row, 'reporting_start_date': row['reporting_start_date'].isoformat()}
               for row in rows}
    by_code.update({p['code']: registry_row(p) for p in profiles})
    return {'version': 1, 'agents': [by_code[code] for code in sorted(by_code)]}


def quota_metadata(existing, budget, actor, timestamp):
    """LiteLLM replaces metadata: retain routing tags and unrelated fields."""
    metadata = deepcopy(existing or {})
    before = metadata.get('quota_usd')
    budget = validate_budget(budget)
    if budget['mode'] == 'unlimited':
        metadata.pop('quota_usd', None)
    else:
        metadata['quota_usd'] = budget['usd']
    previous_log = metadata.get('quota_log', [])
    if not isinstance(previous_log,list):
        raise Conflict('Existing quota audit log is malformed; repair explicitly')
    metadata['quota_log'] = [*previous_log, {
        'at': timestamp, 'by': actor, 'from': before, 'to': metadata.get('quota_usd')}]
    return metadata


def integration_template(p, endpoint, network, context):
    identity = 'svc.' + p['code'] if p['user_mode'] == 'single' else '<stable-login-from-agent-server>'
    endpoint = endpoint.rstrip('/').removesuffix('/v1') + '/v1'
    lines = [f'GATEWAY_BASE_URL={endpoint}', 'GATEWAY_API_KEY=<virtual-key>',
             f'GATEWAY_MODEL={concrete_alias(p) or "<provider>/<model>"}', f'X-User: {identity}', '',
             'Apply these values in the agent server; keep the existing fallback.',
             'Avoid retries at both layers. Recreate the agent container after env changes.',
             'Generated instructions do not change the deployed application.']
    if context == 'docker':
        lines += ['', yaml.safe_dump({'services': {'app': {'networks': ['default', 'gateway']}},
                   'networks': {'gateway': {'external': True, 'name': network}}}, sort_keys=False)]
    return '\n'.join(lines)
