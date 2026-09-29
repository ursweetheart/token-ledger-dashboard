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
        fail_save = False  # case 4.5: the next save is rejected
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
                    if fail_save:
                        route.fulfill(status=409,json={'detail':'Profile revision changed'}); return
                    # Like connection_store.save: a new revision, the applied profile is kept.
                    revision=profile['revision']+1 if profile else 1
                    kept={k:profile[k] for k in ('applied_revision','applied','keys','operations')} if profile else \
                         {'applied_revision':None,'applied':None,'keys':[],'operations':[]}
                    profile={'code':payload['profile']['code'],'revision':revision,'draft':payload['profile'],'audit':[],**kept}
                    route.fulfill(json=profile); return
                if path=='gateway-connections':
                    route.fulfill(json={'profiles':[profile] if profile else [],'legacy':[]}); return
                if path=='gateway-connections/catalog':
                    route.fulfill(json={'providers':['anthropic','gemini'],
                                        'models':{'anthropic':['anthropic/claude-haiku-4-5'],'gemini':['gemini/test']}}); return
                if path=='gateway-connections/secrets':
                    route.fulfill(json={'secret_ref':'KEY_MANAGED_ROTATED'}); return
                if path.endswith('/preview'):
                    # Like the worker: the previewed draft comes back, so old and new are distinguishable.
                    route.fulfill(json={'preview_hash':'reviewed','revision':profile['revision'],'profile':profile['draft'],
                                        'changes':{'agent':profile['code'],'instances':['litellm-1','litellm-2'],'untagged_routes':[]}}); return
                if path.endswith('/reconcile'):
                    route.fulfill(json={'accepted':True} if payload.get('accept_hash') else {'review_hash':'drift-review','changes':{}}); return
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
        # 4.1: there is no separate save button any more.
        assert panel.get_by_role('button',name='Lưu bản nháp',exact=True).count()==0  # vi-ok: UI text the check matches
        saves=lambda: sum(1 for c in captured if c['url'].endswith('/api/gateway-connections') and c['payload'] is not None)
        previews=lambda: [c['payload'] for c in captured if c['url'].endswith('/preview')]
        summary=page.locator('#connection-preview-summary')
        apply_button=panel.locator('#connection-apply')
        preview_button=panel.get_by_role('button',name='4. Xem thay đổi',exact=True)  # vi-ok: UI text the check matches
        def preview_now(expect_text):
            before=len(previews())
            preview_button.click()
            summary.get_by_text(expect_text,exact=False).wait_for()
            assert len(previews())==before+1
        # New agent: Xem thay đổi saves revision 1, then previews exactly that revision.
        preview_now('Chưa áp dụng lần nào')  # vi-ok: UI text the check matches
        assert saves()==1 and previews()[-1]['expected_revision']==1 and len(profile['draft']['models'])==2
        page.get_by_text('Đã lưu bản nháp (revision 1).',exact=False).wait_for()  # vi-ok: UI text the check matches
        assert not apply_button.is_disabled()
        form.locator('[name=name]').fill('Đổi bản nháp')
        assert apply_button.is_disabled()
        panel.get_by_role('button',name='Hướng dẫn Docker',exact=True).click()
        page.get_by_text('GATEWAY_API_KEY=<virtual-key>',exact=False).wait_for()
        # 1.5: Enter in the form runs the same save-then-preview flow as the button.
        before=len(previews())
        form.locator('[name=name]').press('Enter')
        summary.get_by_text('Chưa áp dụng lần nào',exact=False).wait_for()  # editing cleared the old one  # vi-ok: UI text the check matches
        assert len(previews())==before+1 and saves()==2 and profile['draft']['name']=='Đổi bản nháp'  # vi-ok: UI text the check matches
        apply_button.click()
        page.get_by_text('Trạng thái: applied',exact=True).wait_for()
        assert profile['applied']['name']=='Đổi bản nháp'  # vi-ok: UI text the check matches
        # 4.4: unchanged applied profile → no new revision, "no change" summary.
        preview_now('Không có thay đổi so với bản đang chạy')  # vi-ok: UI text the check matches
        assert saves()==2 and previews()[-1]['expected_revision']==2
        # 4.3: edit RPM without saving → the preview shows the NEW value, one revision later.
        form.locator('[name=rpm]').fill('20')
        preview_now('RPM: 15 → 20')
        assert saves()==3 and previews()[-1]['expected_revision']==3 and profile['draft']['rpm']==20
        assert summary.inner_text().count('→')==1, summary.inner_text()  # only RPM differs
        # 4.8: every draft key is compared or deliberately ignored; a new form field fails here.
        covered=set(panel.get_attribute('data-summary-fields').split(','))
        assert set(profile['draft'])<=covered, set(profile['draft'])-covered
        # 4.6: importing a provider key after a preview disables Apply; the next preview saves it.
        assert not apply_button.is_disabled()
        form.locator('#connection-provider-key').fill('provider-secret-fixture')
        panel.get_by_role('button',name='Lưu key và lấy tham chiếu',exact=True).click()  # vi-ok: UI text the check matches
        page.get_by_text('bấm "4. Xem thay đổi" để lưu và xem trước',exact=False).wait_for()  # vi-ok: UI text the check matches
        assert apply_button.is_disabled()
        preview_now('Tham chiếu khoá: KEY_MANAGED_TEST → KEY_MANAGED_ROTATED')  # vi-ok: UI text the check matches
        assert saves()==4 and profile['draft']['secret_ref']=='KEY_MANAGED_ROTATED'
        # 4.5: a rejected save shows the error, sends no preview, keeps Apply disabled.
        fail_save=True
        form.locator('[name=name]').fill('Sẽ bị từ chối')  # vi-ok: UI text the check matches
        before=len(previews())
        preview_button.click()
        page.get_by_text('Profile revision changed',exact=True).wait_for()
        assert len(previews())==before and apply_button.is_disabled()
        fail_save=False
        panel.get_by_role('button',name='Tải lại',exact=True).click()  # back to the saved draft  # vi-ok: UI text the check matches
        page.wait_for_function("document.querySelector('[name=name]').value==='Đổi bản nháp'")  # vi-ok: UI text the check matches
        # 4.7: after accepting a reviewed baseline the accept button stays disabled.
        accept=panel.locator('#connection-accept-drift')
        assert accept.is_disabled()
        panel.get_by_role('button',name='Xem thay đổi ngoài UI',exact=True).click()  # vi-ok: UI text the check matches
        page.wait_for_function("!document.querySelector('#connection-accept-drift').disabled")
        accept.click()
        page.get_by_text('Đã chấp nhận baseline.',exact=False).wait_for()  # vi-ok: UI text the check matches
        assert accept.is_disabled()
        # 4.9: the three credential fields ask the browser not to fill saved passwords.
        for selector in ('#connection-login [name=credential]','#connection-provider-key','#connection-test [name=virtual_key]'):
            assert page.locator(selector).get_attribute('autocomplete')=='new-password', selector
        panel.get_by_role('button',name='Cấp key / key thay thế',exact=True).click()
        page.locator('#connection-key-once').wait_for(state='visible')
        assert page.locator('#connection-issued-key').input_value()=='sk-browser-fixture-only-key'
        panel.get_by_role('button',name='Đã lưu key',exact=True).click()
        assert page.locator('#connection-issued-key').input_value()==''
        assert 'sk-browser-fixture-only-key' not in page.evaluate('JSON.stringify(localStorage)')
        # 3.2: revoking one selected key reports which key was revoked.
        page.locator('#connection-key-select').select_option('fixture-key')
        panel.get_by_role('button',name='Thu hồi key đã chọn',exact=True).click()  # vi-ok: UI text the check matches
        page.get_by_text('Đã thu hồi key fixture-key; giữ lịch sử.',exact=True).wait_for()  # vi-ok: UI text the check matches
        panel.get_by_role('button',name='Cấp key / key thay thế',exact=True).click()  # one active key for revoke-all  # vi-ok: UI text the check matches
        page.locator('#connection-key-once').wait_for(state='visible')
        panel.get_by_role('button',name='Đã lưu key',exact=True).click()  # vi-ok: UI text the check matches
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
        print('PASS: real Chromium login, provider catalog suggestions, multi-model draft, save-then-preview (button and Enter), '
              'change summary (never applied / no change / RPM / secret ref), rejected save sends no preview, baseline accept stays disabled, '
              'new-password credential fields, preview/apply, key issuance, single and bulk revocation messages, inconclusive test with test model, '
              'template, credential memory/origin isolation')
        browser.close()


if __name__=='__main__':
    main()
