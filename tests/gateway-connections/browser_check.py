"""Real Chromium UI check with deterministic HTTP fixtures, no provider traffic."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    with sync_playwright() as runtime:
        installed = Path.home()/'AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'
        browser = runtime.chromium.launch(headless=True,executable_path=str(installed) if installed.exists() else None)
        context = browser.new_context(viewport={'width':1360,'height':1000})
        context.add_init_script("localStorage.setItem('tokenledger.key:http://127.0.0.1:8000','reader-test');")
        page = context.new_page()
        profile = None
        captured = []
        operation={'id':'fixture-operation','kind':'apply','status':'applied','stage':'applied','result':{'reporting':'awaiting-refresh'}}
        def respond(route):
            nonlocal profile
            path = route.request.url.split('/api/',1)[1]
            payload = route.request.post_data_json if route.request.method=='POST' else None
            if path.startswith('gateway-connections'):
                captured.append({'url':route.request.url,'headers':route.request.headers,'payload':payload})
                if route.request.headers.get('authorization')!='Bearer browser-admin-only':
                    route.fulfill(status=401,json={'detail':'Admin required'}); return
                if path=='gateway-connections' and payload is not None:
                    revision=profile['revision']+1 if profile else 1
                    profile={'code':payload['profile']['code'],'revision':revision,'applied_revision':None,
                             'draft':payload['profile'],'applied':None,'keys':[],'operations':[],'audit':[]}
                    route.fulfill(json=profile); return
                if path=='gateway-connections':
                    route.fulfill(json={'profiles':[profile] if profile else [],'legacy':[]}); return
                if path=='gateway-connections/catalog':
                    route.fulfill(json={'providers':['anthropic','gemini'],
                                        'models':{'anthropic':['anthropic/claude-haiku-4-5'],'gemini':['gemini/test']}}); return
                if path.endswith('/preview'):
                    route.fulfill(json={'preview_hash':'reviewed','changes':{'agent':profile['code'],'instances':['litellm-1','litellm-2']}}); return
                if path.endswith('/template'):
                    route.fulfill(json={'text':'GATEWAY_API_KEY=<virtual-key>\nnetworks: [default, gateway]'}); return
                if path.endswith('/apply'):
                    profile['applied_revision']=profile['revision']; profile['applied']=profile['draft']
                    profile['operations']=[operation]
                    route.fulfill(json={'operation':operation}); return
                if '/operations/' in path:
                    route.fulfill(json=operation); return
                if path.endswith('/keys'):
                    profile['keys']=[{'key_alias':'fixture-key','status':'active','budget':payload['budget']}]
                    route.fulfill(json={'key':'sk-browser-fixture-only-key','key_alias':'fixture-key'}); return
                if path.endswith('/revoke'):
                    profile['keys'][0]['status']='revoked'; route.fulfill(json={'status':'revoked'}); return
                if path.endswith('/verify'):
                    operation.update(kind='verify',status='inconclusive',stage='evidence',result={'gateway':'inconclusive','reporting':'pending','reason':'Missing route evidence'})
                    route.fulfill(json=operation); return
                route.fulfill(json=profile); return
            if path=='health':
                route.fulfill(json={'ranges':{},'warnings':[]}); return
            route.fulfill(json={'rows':[]})
        page.route('**/api/**',respond)
        page.goto(ROOT.joinpath('web/index.html').as_uri()+'?api=http://127.0.0.1:8000&tab=connections')
        page.get_by_role('button',name='🔗 Kết nối agent',exact=True).click()
        panel=page.locator('#gateway-connections')
        panel.locator('#connection-login input').fill('browser-admin-only')
        panel.locator('#connection-login input').press('Enter')
        page.locator('#connection-workspace').wait_for(state='visible')
        form=page.locator('#connection-form')
        assert not form.evaluate('(form) => form.checkValidity()')
        # Provider-neutral form fed by the Gateway catalog.
        assert 'Google' not in form.inner_text()
        options=lambda: page.eval_on_selector_all('#connection-model-options option','(os) => os.map(o => o.value)')
        page.wait_for_function("document.querySelectorAll('#connection-model-options option').length > 0")
        assert {'anthropic/*','anthropic/claude-haiku-4-5','gemini/*','gemini/test'} <= set(options())
        page.locator('#connection-provider').select_option('gemini')
        assert set(options())=={'gemini/*','gemini/test'}
        page.locator('#connection-provider').select_option('')
        for name,value in {'code':'browser-agent','name':'Trợ lý kiểm thử','reporting_start_date':'2026-09-26',
                           'secret_ref':'KEY_MANAGED_TEST','alias':'test','upstream':'gemini/test'}.items():
            form.locator(f'[name={name}]').fill(value)
        panel.get_by_role('button',name='Thêm model',exact=True).click()
        form.locator('[data-model-field=alias]').fill('test-two')
        form.locator('[data-model-field=upstream]').fill('gemini/test-two')
        panel.get_by_role('button',name='Lưu bản nháp',exact=True).click()
        page.get_by_text('Đã lưu bản nháp; chưa áp dụng Gateway.',exact=True).wait_for()
        assert len(profile['draft']['models'])==2
        assert panel.locator('#connection-apply').is_disabled()
        panel.get_by_role('button',name='4. Xem thay đổi',exact=True).click()
        page.locator('#connection-preview-result').get_by_text('reviewed',exact=False).wait_for()
        assert not panel.locator('#connection-apply').is_disabled()
        form.locator('[name=name]').fill('Đổi bản nháp')
        assert panel.locator('#connection-apply').is_disabled()
        panel.get_by_role('button',name='Hướng dẫn Docker',exact=True).click()
        page.get_by_text('GATEWAY_API_KEY=<virtual-key>',exact=False).wait_for()
        panel.get_by_role('button',name='Lưu bản nháp',exact=True).click()
        page.get_by_text('Đã lưu bản nháp; chưa áp dụng Gateway.',exact=True).wait_for()
        panel.get_by_role('button',name='4. Xem thay đổi',exact=True).click()
        page.locator('#connection-preview-result').get_by_text('reviewed',exact=False).wait_for()
        panel.get_by_role('button',name='5. Áp dụng',exact=True).click()
        page.get_by_text('Trạng thái: applied',exact=True).wait_for()
        panel.get_by_role('button',name='Cấp key / key thay thế',exact=True).click()
        page.locator('#connection-key-once').wait_for(state='visible')
        assert page.locator('#connection-issued-key').input_value()=='sk-browser-fixture-only-key'
        panel.get_by_role('button',name='Đã lưu key',exact=True).click()
        assert page.locator('#connection-issued-key').input_value()==''
        assert 'sk-browser-fixture-only-key' not in page.evaluate('JSON.stringify(localStorage)')
        panel.get_by_role('button',name='Thu hồi tất cả key đã quản lý',exact=True).click()
        page.get_by_text('Đã thu hồi key managed; giữ lịch sử. Key ngoài quản lý cần kiểm riêng.',exact=True).wait_for()
        test=panel.locator('#connection-test'); test.locator('[name=virtual_key]').fill('sk-transient-test-key')
        test.locator('[name=test_model]').fill('gemini/test')
        test.locator('[name=accept_cost]').check(); test.get_by_role('button',name='Kiểm tra Gateway',exact=True).click()
        page.get_by_text('Trạng thái: inconclusive',exact=True).wait_for()
        assert test.locator('[name=virtual_key]').input_value()==''
        sent=[c['payload'] for c in captured if c['url'].endswith('/verify')][-1]
        assert sent['test_model']=='gemini/test' and sent['virtual_key']=='sk-transient-test-key'
        operation.update(status='verified',result={'gateway':'verified','reporting':'verified'})
        panel.get_by_role('button',name='Tải lại',exact=True).click()
        page.locator('#connection-status').get_by_text('Trạng thái: verified',exact=False).wait_for()
        assert all('browser-admin-only' not in request['url'] for request in captured)
        storage=page.evaluate('JSON.stringify(localStorage)')
        assert 'browser-admin-only' not in storage
        # Origin changes invalidate the in-memory credential before sending.
        page.evaluate("history.replaceState({},'', '?api=http://127.0.0.1:8001&tab=connections')")
        before=len(captured)
        panel.get_by_role('button',name='Tải lại',exact=True).click()
        page.get_by_text('Hãy nhập khoá quản trị cho địa chỉ backend này.',exact=True).wait_for()
        assert len(captured)==before and page.locator('#connection-workspace').is_hidden()
        # Reopen for screenshot at normal origin, no credential shown.
        page.evaluate("history.replaceState({},'', '?api=http://127.0.0.1:8000&tab=connections')")
        panel.locator('#connection-login input').fill('browser-admin-only')
        panel.get_by_role('button',name='Mở quản trị',exact=True).click()
        page.locator('#connection-workspace').wait_for(state='visible')
        page.locator('#connection-select').select_option('browser-agent')
        page.screenshot(path=str(ROOT/'.worktrees/gateway-connections-ui.png'),full_page=True)
        print('PASS: real Chromium login, provider catalog suggestions, multi-model draft, preview/apply, key issuance/revocation, inconclusive test with test model, template, credential memory/origin isolation')
        browser.close()


if __name__=='__main__':
    main()
