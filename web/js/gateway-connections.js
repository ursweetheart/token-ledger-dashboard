/* Admin credential stays in memory and is bound to a confirmed backend origin. */
(function (global) {
  'use strict';
  function base() {
    var value = new URLSearchParams(global.location.search).get('api');
    return (value || (global.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : global.location.origin)).replace(/\/+$/, '');
  }
  var credential = '', credentialOrigin = '', selected = null, preview = null, poll = null, drift = null;
  var root = document.getElementById('gateway-connections');
  if (!root) return;
  function el(id) { return document.getElementById('connection-' + id); }
  function message(text) { el('message').textContent = text; }
  function status(record) {
    var lines = [];
    if (record.draft) {
      lines.push(record.draft.name + ' (' + record.code + ')');
      lines.push('Bản nháp: ' + record.revision + ' · Đã áp dụng: ' + (record.applied_revision || 'Chưa áp dụng'));
      (record.keys || []).forEach(function (key) {
        lines.push('Key: ' + key.key_alias + ' · ' + key.status + ' · Hạn mức: ' +
          (key.budget.mode === 'unlimited' ? 'Không giới hạn' : key.budget.usd + ' USD'));
      });
      if (!(record.keys || []).length) lines.push('Chưa cấp Virtual Key.');
      if (record.operations && record.operations.length) record = record.operations[0];
      else lines.push('Chưa có thao tác áp dụng hoặc bằng chứng kết nối.');
    }
    if (record.status) {
      lines.push('Thao tác: ' + record.kind + ' · Trạng thái: ' + record.status + ' · Bước: ' + record.stage);
      var result = record.result || {};
      if (result.reporting) lines.push('Usage dashboard: ' + result.reporting);
      if (result.gateway) lines.push('Kiểm chứng Gateway: ' + result.gateway);
      if (result.external_agent) lines.push('Ứng dụng agent: ' + result.external_agent);
      if (result.reason) lines.push(result.reason);
      lines.push('Mã thao tác: ' + record.id);
    }
    el('status').textContent = lines.join('\n');
  }
  function clearKey() { el('issued-key').value = ''; el('key-once').hidden = true; }
  function logout() {
    credential = ''; credentialOrigin = ''; selected = null; preview = null; drift = null;
    clearTimeout(poll); clearKey(); el('workspace').hidden = true;
    el('provider-key').value = ''; el('test').elements.virtual_key.value = '';
    el('status').textContent = ''; el('preview-result').textContent = '';
  }
  async function request(path, body) {
    var origin = new URL(base()).origin;
    if (!credential || origin !== credentialOrigin) {
      logout(); throw new Error('Hãy nhập khoá quản trị cho địa chỉ backend này.');
    }
    var response = await global.fetch(base() + '/api/gateway-connections' + path, {
      method: body === undefined ? 'GET' : 'POST', redirect: 'error',
      headers: { Authorization: 'Bearer ' + credential, 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    var result = await response.json();
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) logout();
      throw new Error(typeof result.detail === 'string' ? result.detail : 'Thông tin không hợp lệ.');
    }
    return result;
  }
  function bind(id, event, action) {
    el(id).addEventListener(event, async function (e) {
      e.preventDefault();
      var control = e.currentTarget;
      if (control.tagName === 'BUTTON') control.disabled = true;
      try { await action(e); } catch (error) { message(error.message); }
      finally { if (control.tagName === 'BUTTON') control.disabled = id === 'apply' && !preview; }
    });
  }
  function field(name) { return el('form').elements[name]; }
  function budget() {
    if (field('budget_mode').value === 'unlimited') return { mode: 'unlimited' };
    var raw = field('budget_usd').value, amount = Number(raw);
    if (!raw.trim() || !Number.isFinite(amount) || amount < 0) throw new Error('Nhập hạn mức USD không âm hoặc chọn không giới hạn.');
    return { mode: 'finite', usd: amount };
  }
  function input() {
    return { code: field('code').value, name: field('name').value,
      user_mode: field('user_mode').value, reporting_start_date: field('reporting_start_date').value,
      active: field('active').checked, secret_ref: field('secret_ref').value,
      models: [{ alias: field('alias').value, upstream: field('upstream').value }],
      rpm: Number(field('rpm').value), tpm: Number(field('tpm').value), budget: budget(),
      quota_response_mode: field('quota_response_mode').value };
  }
  function addModel(model) {
    var group = document.createElement('div'); group.className = 'connection-extra-model';
    ['alias','upstream'].forEach(function (name) {
      var label = document.createElement('label'); label.textContent = name === 'alias' ? 'Model alias bổ sung' : 'Model Google bổ sung';
      var control = document.createElement('input'); control.setAttribute('data-model-field',name); control.required = true; control.className = 'text-input';
      control.value = model ? model[name] : ''; label.appendChild(control); group.appendChild(label);
    });
    var remove = document.createElement('button'); remove.type = 'button'; remove.className = 'btn btn-secondary'; remove.textContent = 'Bỏ model';
    remove.addEventListener('click',function () { group.remove(); preview = null; el('apply').disabled = true; });
    group.appendChild(remove); el('extra-models').appendChild(group);
  }
  function keyChoices(profile) {
    el('key-select').replaceChildren(new Option('Chọn key managed',''));
    (profile.keys || []).filter(function (key) { return key.status === 'active'; }).forEach(function (key) {
      el('key-select').add(new Option(key.key_alias,key.key_alias));
    });
  }
  function fill(profile) {
    selected = profile; preview = null; el('apply').disabled = true; clearKey();
    el('preview-result').textContent = ''; el('template').textContent = '';
    el('form').reset();
    el('extra-models').replaceChildren();
    keyChoices(profile || {});
    if (profile) {
      var p = profile.draft;
      ['code','name','user_mode','reporting_start_date','secret_ref','rpm','tpm','quota_response_mode'].forEach(function (key) { field(key).value = p[key]; });
      field('active').checked = p.active;
      field('alias').value = p.models[0].alias; field('upstream').value = p.models[0].upstream;
      p.models.slice(1).forEach(addModel);
      field('budget_mode').value = p.budget.mode; field('budget_usd').value = p.budget.usd === undefined ? '' : p.budget.usd;
    }
    field('code').disabled = !!profile;
    ['user_mode','reporting_start_date'].forEach(function (key) { field(key).disabled = !!(profile && profile.applied_revision); });
    if (profile) status(profile); else el('status').textContent = 'Agent mới: chưa lưu, chưa áp dụng, chưa có traffic.';
  }
  async function reload() {
    var list = await request('');
    var select = el('select'); select.replaceChildren(new Option('Agent mới', ''));
    list.profiles.forEach(function (p) { select.add(new Option(p.draft.name + ' (' + p.code + ')', p.code)); });
    el('legacy').textContent = 'Agent legacy chỉ xem: ' + list.legacy.map(function (p) { return p.name; }).join(', ');
    if (selected) { select.value = selected.code; fill(await request('/' + encodeURIComponent(selected.code))); }
  }
  function requireProfile() { if (!selected) throw new Error('Lưu bản nháp trước.'); return '/' + encodeURIComponent(selected.code); }
  function operationBody(extra) {
    requireProfile();
    return Object.assign({ expected_revision: selected.revision, idempotency_key: global.crypto.randomUUID() }, extra || {});
  }
  async function monitor(id) {
    var operation = await request('/operations/' + encodeURIComponent(id));
    status(operation);
    if (operation.status === 'queued' || operation.status === 'running' || operation.status === 'pending') {
      poll = global.setTimeout(function () { monitor(id).catch(function (e) { message(e.message); }); }, 2000);
    } else { message('Trạng thái: ' + operation.status); await reload(); }
  }
  bind('login', 'submit', async function () {
    logout(); credential = el('login').elements.credential.value;
    el('login').elements.credential.value = ''; credentialOrigin = new URL(base()).origin;
    await reload(); el('workspace').hidden = false; message('Đã mở quản trị: ' + credentialOrigin);
  });
  bind('logout', 'click', async function () { logout(); message('Đã đóng quản trị.'); });
  bind('reload', 'click', reload);
  bind('select', 'change', async function () { clearTimeout(poll); fill(el('select').value ? await request('/' + encodeURIComponent(el('select').value)) : null); });
  el('form').addEventListener('input', function () { preview = null; el('apply').disabled = true; });
  bind('form','submit',async function () {
    var p = input();
    el('extra-models').querySelectorAll('.connection-extra-model').forEach(function (group) {
      p.models.push({ alias: group.querySelector('[data-model-field=alias]').value, upstream: group.querySelector('[data-model-field=upstream]').value });
    });
    selected = await request('', { profile: p, expected_revision: selected ? selected.revision : 0 });
    await reload(); message('Đã lưu bản nháp; chưa áp dụng Gateway.');
  });
  bind('add-model','click',async function () { addModel(); preview = null; el('apply').disabled = true; });
  bind('import-secret','click',async function () {
    var value = el('provider-key').value; el('provider-key').value = '';
    var result = await request('/secrets', { value: value }); field('secret_ref').value = result.secret_ref;
    preview = null; el('apply').disabled = true; message('Đã lưu secret; lưu lại bản nháp để sử dụng tham chiếu.');
  });
  bind('preview','click',async function () {
    preview = await request(requireProfile() + '/preview', { expected_revision: selected.revision });
    el('preview-result').textContent = JSON.stringify(preview, null, 2); el('apply').disabled = false;
  });
  bind('apply','click',async function () {
    if (!preview) throw new Error('Xem thay đổi trước khi áp dụng.');
    var result = await request(requireProfile() + '/apply', operationBody({ preview_hash: preview.preview_hash }));
    preview = null; await monitor(result.operation.id);
  });
  bind('issue','click',async function () {
    clearKey(); var result = await request(requireProfile() + '/keys', operationBody({ budget: budget() }));
    el('issued-key').value = result.key; el('issued-key').type = 'password'; el('key-once').hidden = false;
    message('Đã cấp key. Nếu phản hồi bị mất, tải lại trạng thái và thu hồi key trước khi cấp thay thế.');
    selected = await request(requireProfile()); keyChoices(selected); status(selected);
  });
  bind('revoke','click',async function () {
    requireProfile(); selected = await request(requireProfile());
    var aliases = selected.keys.filter(function (k) { return k.status === 'active'; }).map(function (k) { return k.key_alias; });
    if (!aliases.length) throw new Error('Không có key managed đang hoạt động.');
    await request(requireProfile() + '/revoke', operationBody({ key_aliases: aliases })); clearKey(); await reload();
    message('Đã thu hồi key managed; giữ lịch sử. Key ngoài quản lý cần kiểm riêng.');
  });
  bind('revoke-one','click',async function () {
    var alias = el('key-select').value; if (!alias) throw new Error('Chọn key managed trước.');
    await request(requireProfile() + '/revoke',operationBody({ key_aliases:[alias] })); clearKey(); await reload();
  });
  bind('budget','click',async function () {
    var alias = el('key-select').value; if (!alias) throw new Error('Chọn key managed trước.');
    await request(requireProfile() + '/budget',operationBody({ key_alias:alias,budget:budget() })); await reload(); message('Đã cập nhật hạn mức của key.');
  });
  bind('reconcile','click',async function () {
    drift = await request(requireProfile() + '/reconcile',{ expected_revision:selected.revision });
    el('preview-result').textContent = JSON.stringify(drift,null,2); el('accept-drift').disabled = false;
  });
  bind('accept-drift','click',async function () {
    if (!drift) throw new Error('Xem thay đổi ngoài UI trước.');
    await request(requireProfile() + '/reconcile',{ expected_revision:selected.revision,accept_hash:drift.review_hash });
    drift = null; el('accept-drift').disabled = true; preview = null; el('apply').disabled = true;
    message('Đã chấp nhận baseline. Xem preview mới trước khi áp dụng cấu hình mong muốn.');
  });
  bind('recover','click',async function () {
    var operation = await request(requireProfile() + '/recover',operationBody());
    status(operation); await reload();
  });
  ['host','docker'].forEach(function (context) { bind('template-' + context,'click',async function () {
    var result = await request(requireProfile() + '/template', { context: context }); el('template').textContent = result.text;
  }); });
  bind('show-key','click',async function () { el('issued-key').type = el('issued-key').type === 'password' ? 'text' : 'password'; });
  bind('clear-key','click',async function () { clearKey(); });
  bind('test','submit',async function () {
    var value = el('test').elements.virtual_key.value; el('test').elements.virtual_key.value = '';
    var result = await request(requireProfile() + '/verify',operationBody({ virtual_key: value, accept_cost: el('test').elements.accept_cost.checked }));
    status(result); if (result.id) await monitor(result.id);
  });
  bind('external-test','submit',async function () {
    var result = await request(requireProfile() + '/external-verify',operationBody({ request_id:el('external-test').elements.request_id.value }));
    status(result); message('Đã đối chiếu log. Thiếu bằng chứng nguồn request hoặc route thì kết quả chưa xác minh.');
  });
  global.addEventListener('pagehide', logout);
})(window);
