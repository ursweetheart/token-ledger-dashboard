/* Admin credential stays in memory and is bound to a confirmed backend origin. */
(function (global) {
  'use strict';
  function base() {
    var value = new URLSearchParams(global.location.search).get('api');
    return (value || (global.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : global.location.origin)).replace(/\/+$/, '');
  }
  var credential = '', credentialOrigin = '', selected = null, preview = null, poll = null, drift = null;
  // Form has edits not yet saved as a draft revision. Code that writes a form field
  // (import-secret, add/remove model) must set it too: programmatic writes fire no `input`.
  var dirty = false;
  var root = document.getElementById('gateway-connections');
  if (!root) return;
  function el(id) { return document.getElementById('connection-' + id); }
  function message(text) { el('message').textContent = text; }
  // Inconclusive is not a failure: missing evidence does not prove the route wrong.
  function mark(value) {
    if (['verified', 'applied', 'issued', 'refresh-complete'].indexOf(value) >= 0) return '✅ ';
    if (['failed', 'mismatch', 'recovery-required'].indexOf(value) >= 0) return '❌ ';
    if (value === 'inconclusive') return '⚠️ ';
    // Needs a request ID from the deployed app; nothing will change it on its own.
    if (value === 'awaiting-agent-request') return '➖ ';
    return '⏳ ';
  }
  // External-agent evidence is excluded: the pinned image can never verify it.
  function summary(result) {
    var checks = [result.gateway, result.reporting].filter(Boolean);
    var passed = checks.filter(function (v) { return v === 'verified'; }).length;
    if (checks.some(function (v) { return mark(v) === '❌ '; })) return '❌ Tổng kết: kết nối lỗi, xem lý do ở trên';
    if (checks.indexOf('inconclusive') >= 0) return '⚠️ Tổng kết: chưa đủ bằng chứng, hãy kiểm tra lại';
    if (passed === checks.length) return '✅ Tổng kết: kết nối Gateway đạt (' + passed + '/' + checks.length + ')';
    return '⏳ Tổng kết: đang chờ bằng chứng (' + passed + '/' + checks.length + ' mục đã đạt)';
  }
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
      lines.push(mark(record.status) + 'Thao tác: ' + record.kind + ' · Trạng thái: ' + record.status + ' · Bước: ' + record.stage);
      var result = record.result || {};
      if (result.reporting) lines.push(mark(result.reporting) + 'Usage dashboard: ' + result.reporting);
      if (result.gateway) lines.push(mark(result.gateway) + 'Kiểm chứng Gateway: ' + result.gateway);
      if (result.external_agent) lines.push(mark(result.external_agent) + 'Ứng dụng agent: ' + result.external_agent +
        (result.external_agent === 'awaiting-agent-request' ? ' (không tự đổi — cần Request ID từ app)' : ''));
      if (result.reason) lines.push(result.reason);
      lines.push('Mã thao tác: ' + record.id);
      if (record.kind === 'verify' && (result.gateway || result.reporting)) lines.push('─────────────', summary(result));
    }
    el('status').textContent = lines.join('\n');
  }
  function clearKey() { el('issued-key').value = ''; el('key-once').hidden = true; }
  function logout() {
    credential = ''; credentialOrigin = ''; selected = null; preview = null; drift = null;
    clearTimeout(poll); clearKey(); el('workspace').hidden = true;
    el('provider-key').value = ''; el('test').elements.virtual_key.value = '';
    el('status').textContent = ''; el('preview-summary').textContent = ''; el('preview-result').textContent = '';
    dirty = false;
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
  // Re-enable by state, not blindly: Apply needs a current preview, accepting drift needs a review.
  function enabled(id) {
    if (id === 'apply') return !!preview;
    if (id === 'accept-drift') return !!drift;
    return true;
  }
  function bind(id, event, action) {
    el(id).addEventListener(event, async function (e) {
      e.preventDefault();
      var control = e.currentTarget;
      if (control.tagName === 'BUTTON') control.disabled = true;
      try { await action(e); } catch (error) { message(error.message); }
      finally { if (control.tagName === 'BUTTON') control.disabled = !enabled(id); }
    });
  }
  function field(name) { return el('form').elements[name]; }
  // The form no longer matches the last preview: forget it, including what is on screen.
  function invalidate() {
    dirty = true; preview = null; el('apply').disabled = true;
    el('preview-summary').textContent = ''; el('preview-result').textContent = '';
  }
  // Routable chat models from the pinned Gateway; suggestions only, the worker re-checks on preview.
  var catalog = { providers: [], models: {} };
  function renderModels() {
    var provider = el('provider').value;
    var providers = provider ? [provider] : catalog.providers;
    var options = [];
    providers.forEach(function (p) {
      [p + '/*'].concat(catalog.models[p] || []).forEach(function (name) {
        var option = document.createElement('option'); option.value = name; options.push(option);
      });
    });
    el('model-options').replaceChildren.apply(el('model-options'), options);
  }
  async function loadCatalog() {
    var result = null;
    try { result = await request('/catalog'); }
    catch (error) { message('Chưa tải được danh mục model: ' + error.message); }
    catalog = result && Array.isArray(result.providers) && result.models ? result : { providers: [], models: {} };
    el('provider').replaceChildren(new Option('Tất cả provider', ''));
    catalog.providers.forEach(function (p) { el('provider').add(new Option(p, p)); });
    renderModels();
  }
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
      var label = document.createElement('label'); label.textContent = name === 'alias' ? 'Model alias bổ sung' : 'Model provider bổ sung';
      var control = document.createElement('input'); control.setAttribute('data-model-field',name); control.required = true; control.className = 'text-input';
      if (name === 'upstream') control.setAttribute('list', 'connection-model-options');
      control.value = model ? model[name] : ''; label.appendChild(control); group.appendChild(label);
    });
    var remove = document.createElement('button'); remove.type = 'button'; remove.className = 'btn btn-secondary'; remove.textContent = 'Bỏ model';
    remove.addEventListener('click',function () { group.remove(); invalidate(); });
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
    el('preview-summary').textContent = ''; el('preview-result').textContent = ''; el('template').textContent = '';
    el('form').reset(); renderModels();
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
    dirty = false;  // last: addModel() above rebuilt the extra models from the saved draft
  }
  async function reload() {
    var list = await request('');
    var select = el('select'); select.replaceChildren(new Option('Agent mới', ''));
    list.profiles.forEach(function (p) { select.add(new Option(p.draft.name + ' (' + p.code + ')', p.code)); });
    el('legacy').textContent = 'Agent legacy chỉ xem: ' + list.legacy.map(function (p) { return p.name; }).join(', ');
    if (selected) { select.value = selected.code; fill(await request('/' + encodeURIComponent(selected.code))); }
  }
  function requireProfile() { if (!selected) throw new Error('Bấm "4. Xem thay đổi" để lưu hồ sơ trước.'); return '/' + encodeURIComponent(selected.code); }
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
    await loadCatalog();
  });
  el('provider').addEventListener('change', renderModels);
  bind('logout', 'click', async function () { logout(); message('Đã đóng quản trị.'); });
  bind('reload', 'click', reload);
  bind('select', 'change', async function () { clearTimeout(poll); fill(el('select').value ? await request('/' + encodeURIComponent(el('select').value)) : null); });
  // The provider filter and the new-key box sit inside the form but are not part of the draft.
  var NOT_DRAFT = ['connection-provider', 'connection-provider-key'];
  el('form').addEventListener('input', function (e) {
    if (NOT_DRAFT.indexOf(e.target.id) >= 0) return;
    invalidate();
  });
  async function save() {
    var p = input();
    el('extra-models').querySelectorAll('.connection-extra-model').forEach(function (group) {
      p.models.push({ alias: group.querySelector('[data-model-field=alias]').value, upstream: group.querySelector('[data-model-field=upstream]').value });
    });
    selected = await request('', { profile: p, expected_revision: selected ? selected.revision : 0 });
    dirty = false;
    await reload();
  }
  // Fields an admin can change, compared against the applied profile. `code` never changes
  // once saved. A draft key missing from both lists fails browser_check.py (case 4.8).
  var SUMMARY_FIELDS = [['name', 'Tên'], ['active', 'Đang hoạt động'], ['user_mode', 'Người dùng'],
    ['reporting_start_date', 'Ngày bắt đầu báo cáo'], ['secret_ref', 'Tham chiếu khoá'], ['models', 'Model'],
    ['rpm', 'RPM'], ['tpm', 'TPM'], ['quota_response_mode', 'Khi hết hạn mức'], ['budget', 'Ngân sách']];
  var SUMMARY_IGNORED = ['code'];
  root.dataset.summaryFields = SUMMARY_FIELDS.map(function (f) { return f[0]; }).concat(SUMMARY_IGNORED).join(',');
  function shown(key, value) {
    if (value === undefined || value === null) return '(trống)';
    if (key === 'models') return value.map(function (m) { return m.alias + ' → ' + m.upstream; }).join(', ');
    if (key === 'budget') return value.mode === 'unlimited' ? 'Không giới hạn' : value.usd + ' USD';
    if (key === 'active') return value ? 'có' : 'không';
    return String(value);
  }
  function changeSummary(draft, applied) {
    var outside = 'Thay đổi ngoài UI (sửa tay file cấu hình, agent khác) không nằm ở đây: xem bằng nút "Xem thay đổi ngoài UI".';
    if (!applied) return ['Chưa áp dụng lần nào — toàn bộ cấu hình bên dưới là mới.', outside];
    var lines = SUMMARY_FIELDS.filter(function (f) {
      return JSON.stringify(draft[f[0]]) !== JSON.stringify(applied[f[0]]);
    }).map(function (f) { return f[1] + ': ' + shown(f[0], applied[f[0]]) + ' → ' + shown(f[0], draft[f[0]]); });
    if (!lines.length) return ['Không có thay đổi so với bản đang chạy.', outside];
    return ['Thay đổi so với bản đang chạy:'].concat(lines, [outside]);
  }
  // One flow for the button and for Enter in the form: save only unsaved edits, then preview
  // exactly that draft. A failed save stops here and leaves Apply disabled.
  async function saveThenPreview() {
    preview = null; el('apply').disabled = true;
    el('preview-summary').textContent = ''; el('preview-result').textContent = '';
    if (!el('form').reportValidity()) throw new Error('Kiểm lại các ô còn thiếu hoặc sai trong form.');
    var saved = '';
    if (dirty || !selected) { await save(); saved = 'Đã lưu bản nháp (revision ' + selected.revision + '). '; }
    preview = await request(requireProfile() + '/preview', { expected_revision: selected.revision });
    el('preview-summary').textContent = changeSummary(preview.profile || {}, selected.applied).join('\n');
    el('preview-result').textContent = JSON.stringify(preview, null, 2); el('apply').disabled = false;
    var open = (preview.changes && preview.changes.untagged_routes) || [];
    message(saved + (open.length ? '⚠️ Key của agent (models "*") cũng gọi được tuyến không tag: ' + open.join(', ') + ' — tiền sẽ tính vào khoá của tuyến đó.'
                                 : 'Xem trước xong; không có tuyến không tag.'));
  }
  // "4. Xem thay đổi" is the form's submit button: a form without one ignores Enter, so the
  // button and Enter both arrive here. bind() can only disable the form, so guard the button.
  bind('form', 'submit', async function () {
    el('preview').disabled = true;
    try { await saveThenPreview(); } finally { el('preview').disabled = false; }
  });
  bind('add-model','click',async function () { addModel(); invalidate(); });
  bind('import-secret','click',async function () {
    var value = el('provider-key').value; el('provider-key').value = '';
    var result = await request('/secrets', { value: value }); field('secret_ref').value = result.secret_ref;
    invalidate();
    message('Đã lưu secret vào tham chiếu; bấm "4. Xem thay đổi" để lưu và xem trước.');
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
    message('Đã thu hồi key ' + alias + '; giữ lịch sử.');
  });
  bind('budget','click',async function () {
    var alias = el('key-select').value; if (!alias) throw new Error('Chọn key managed trước.');
    await request(requireProfile() + '/budget',operationBody({ key_alias:alias,budget:budget() })); await reload(); message('Đã cập nhật hạn mức của key.');
  });
  bind('reconcile','click',async function () {
    drift = await request(requireProfile() + '/reconcile',{ expected_revision:selected.revision });
    el('preview-summary').textContent = ''; el('preview-result').textContent = JSON.stringify(drift,null,2); el('accept-drift').disabled = false;
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
    var body = { virtual_key: value, accept_cost: el('test').elements.accept_cost.checked };
    var testModel = el('test').elements.test_model.value.trim();
    if (testModel) body.test_model = testModel;
    var result = await request(requireProfile() + '/verify',operationBody(body));
    status(result); if (result.id) await monitor(result.id);
  });
  bind('external-test','submit',async function () {
    var result = await request(requireProfile() + '/external-verify',operationBody({ request_id:el('external-test').elements.request_id.value }));
    status(result); message('Đã đối chiếu log. Thiếu bằng chứng nguồn request hoặc route thì kết quả chưa xác minh.');
  });
  global.addEventListener('pagehide', logout);
})(window);
