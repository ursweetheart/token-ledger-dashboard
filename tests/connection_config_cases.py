"""Opt-in dependency-backed behavioral tests for connection rendering and budgets."""
import copy
import unittest
from backend.connection_config import (validate_profile, render_routes, render_registry,
    quota_metadata, integration_template, Conflict, load_yaml, deployment_env_digest,
    routable_catalog, verification_model, route_id)


def profile(code='support-helper'):
    return {'code':code,'name':'Support','user_mode':'single','reporting_start_date':'2026-09-26',
            'active':True,'secret_ref':'KEY_MANAGED_TEST','models':[{'alias':'test','upstream':'gemini/test'}],
            'rpm':15,'tpm':1000,'budget':{'mode':'finite','usd':10},'quota_response_mode':'batch'}


class ConfigTests(unittest.TestCase):
    def test_reject_invalid_fields(self):
        for name,value in [('rpm',True),('tpm',0),('secret_ref','../../file'),
                           ('quota_response_mode','single'),('budget',{'mode':'finite','usd':float('nan')})]:
            with self.subTest(name=name):
                p=profile(); p[name]=value
                with self.assertRaises(ValueError): validate_profile(p)
        p=profile(); p['models'][0]['alias']='*'
        with self.assertRaises(ValueError): validate_profile(p)

    def test_zero_and_unlimited_are_distinct(self):
        p=profile(); p['budget']['usd']=0
        self.assertEqual(validate_profile(p)['budget']['usd'],0)
        p['budget']={'mode':'unlimited'}
        self.assertEqual(validate_profile(p)['budget'],{'mode':'unlimited'})

    def test_unmanaged_configuration_preserved(self):
        original={'model_list':[{'model_name':'legacy','litellm_params':{'model':'gemini/legacy','tags':['legacy']}}],
                  'router_settings':{'enable_tag_filtering':True,'num_retries':0},
                  'general_settings':{'master_key':'os.environ/LITELLM_MASTER_KEY'}}
        untouched=copy.deepcopy(original)
        result,ids=render_routes(original,[profile()],[])
        self.assertEqual(original,untouched)
        self.assertEqual(result['model_list'][0],original['model_list'][0])
        self.assertEqual(result['general_settings'],original['general_settings'])
        rerender,newids=render_routes(result,[profile()],ids)
        self.assertEqual(rerender,result); self.assertEqual(ids,newids)

    def test_unmanaged_tag_takeover_blocked(self):
        original={'model_list':[{'model_name':'legacy','litellm_params':{'tags':['support-helper']}}],
                  'router_settings':{'enable_tag_filtering':True}}
        with self.assertRaises(Conflict): render_routes(original,[profile()],[])

    def test_registry_retains_other_agents(self):
        old=profile('other'); oldrow={k:old[k] for k in ['code','name','user_mode','reporting_start_date','active']}
        result=render_registry({'version':1,'agents':[oldrow]},[profile()])
        self.assertEqual({r['code'] for r in result['agents']},{'other','support-helper'})

    def test_unlimited_keeps_tags_and_audit(self):
        old={'tags':['support-helper'],'quota_usd':50,'other':'preserve'}
        result=quota_metadata(old,{'mode':'unlimited'},'admin','now')
        self.assertNotIn('quota_usd',result)
        self.assertEqual(result['tags'],old['tags']); self.assertEqual(result['other'],'preserve')
        self.assertEqual(old['quota_usd'],50)
        self.assertEqual(result['quota_log'][0]['from'],50)

    def test_template_two_networks_no_key(self):
        template=integration_template(profile(),'http://gateway-lb:4000','shared-network','docker')
        self.assertIn('- default',template); self.assertIn('- gateway',template)
        self.assertIn('svc.support-helper',template); self.assertIn('<virtual-key>',template)
        self.assertNotIn('KEY_MANAGED_TEST',template)

    def test_template_accepts_base_or_versioned_endpoint(self):
        for endpoint in ('http://gateway-lb:4000', 'http://gateway-lb:4000/',
                         'http://gateway-lb:4000/v1', 'http://gateway-lb:4000/v1/'):
            with self.subTest(endpoint=endpoint):
                text=integration_template(profile(),endpoint,'network','host')
                self.assertEqual(text.splitlines()[0],'GATEWAY_BASE_URL=http://gateway-lb:4000/v1')

    def test_login_rotation_does_not_invalidate_gateway(self):
        old=b'CONNECTION_ADMIN_KEY=old\nDASHBOARD_KEY=old\nKEY_MANAGED_TEST=provider\n'
        new=b'CONNECTION_ADMIN_KEY=new\nDASHBOARD_KEY=new\nKEY_MANAGED_TEST=provider\n'
        self.assertEqual(deployment_env_digest(old),deployment_env_digest(new))
        self.assertNotEqual(deployment_env_digest(old),deployment_env_digest(new.replace(b'provider',b'changed')))
        self.assertNotEqual(deployment_env_digest(old),deployment_env_digest(new+b'LITELLM_MASTER_KEY=changed\n'))

    def test_duplicate_yaml_rejected(self):
        with self.assertRaises(ValueError): load_yaml('version: 1\nversion: 2')


def with_models(*pairs):
    p=profile(); p['models']=[{'alias':a,'upstream':u} for a,u in pairs]
    return p


# Shapes measured from the pinned image's /public/litellm_model_cost_map on 2026-09-28.
COST_MAP={'claude-haiku-4-5':{'litellm_provider':'anthropic','mode':'chat'},
          'gemini/gemini-2.5-flash':{'litellm_provider':'gemini','mode':'chat'},
          'gemini-2.5-flash':{'litellm_provider':'vertex_ai-language-models','mode':'chat'},
          'amazon-nova/nova-micro-v1':{'litellm_provider':'bedrock_converse','mode':'chat'},
          'vertex_ai/claude-3-5-haiku@20241022':{'litellm_provider':'vertex_ai-anthropic_models','mode':'chat'},
          'text-embedding-3-small':{'litellm_provider':'openai','mode':'embedding'},
          'sample_spec':{'mode':'one of: chat, embedding, completion'}}
PROVIDERS=['anthropic','gemini','openai','vertex_ai']


class ProviderTests(unittest.TestCase):
    def test_catalog_uses_routing_prefix_not_provider_label(self):
        c=routable_catalog(COST_MAP,PROVIDERS)
        self.assertEqual(c['providers'],['anthropic','gemini'])
        self.assertEqual(c['models'],{'anthropic':['anthropic/claude-haiku-4-5'],'gemini':['gemini/gemini-2.5-flash']})

    def test_catalog_rejects_unexpected_shape(self):
        for cost_map,providers in [([],PROVIDERS),(COST_MAP,{}),('x',[])]:
            with self.subTest(cost_map=type(cost_map).__name__):
                with self.assertRaises(ValueError): routable_catalog(cost_map,providers)

    def test_any_provider_and_provider_wildcard_saved(self):
        for pairs in [[('anthropic/*','anthropic/*')],[('fast','anthropic/claude-haiku-4-5')],
                      [('gemini/*','gemini/*'),('pro','gemini/gemini-2.5-flash')]]:
            with self.subTest(pairs=pairs):
                validate_profile(with_models(*pairs))

    def test_bad_wildcards_rejected(self):
        for pairs in [[('*','*')],[('x','*')],[('x','gemini/*-flash')],[('foo/*','anthropic/*')],
                      [('any','anthropic/*')],[('*','gemini/test')],[('x','gemini')],[('x','/model')]]:
            with self.subTest(pairs=pairs):
                with self.assertRaises(ValueError): validate_profile(with_models(*pairs))

    def test_catalog_code_reserved(self):
        with self.assertRaises(ValueError): validate_profile(profile('catalog'))

    def test_wildcard_route_rendered_with_one_tag(self):
        p=with_models(('anthropic/*','anthropic/*'))
        result,ids=render_routes({'model_list':[],'router_settings':{'enable_tag_filtering':True}},[p],[])
        route=result['model_list'][0]
        self.assertEqual((route['model_name'],route['litellm_params']['model']),('anthropic/*','anthropic/*'))
        self.assertEqual(route['litellm_params']['tags'],[p['code']])
        self.assertEqual(route['model_info']['id'],route_id(p['code'],'anthropic/*'))

    def test_verification_model_choice(self):
        catalog=routable_catalog(COST_MAP,PROVIDERS)
        self.assertEqual(verification_model(with_models(('anthropic/*','anthropic/*'),('fast','gemini/gemini-2.5-flash')),None,None),('fast','fast'))
        wild=with_models(('anthropic/*','anthropic/*'))
        self.assertEqual(verification_model(wild,'anthropic/claude-haiku-4-5',catalog),('anthropic/claude-haiku-4-5','anthropic/*'))
        for requested in [None,'','gemini/gemini-2.5-flash','anthropic/not-in-catalog']:
            with self.subTest(requested=requested):
                with self.assertRaises(ValueError): verification_model(wild,requested,catalog)

    def test_template_never_shows_wildcard(self):
        text=integration_template(with_models(('anthropic/*','anthropic/*')),'http://gateway-lb:4000','n','host')
        self.assertIn('GATEWAY_MODEL=<provider>/<model>',text); self.assertNotIn('*',text)
