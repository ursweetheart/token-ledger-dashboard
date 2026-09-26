/* Gateway identity usage is separate from the staff directory and its KPIs. */
(function (global) {
  "use strict";
  var generation = 0, lastScope = "", page = 0, range, agent;
  var size = 50;
  function cell(row, text) {
    var td = document.createElement("td");
    td.textContent = text == null ? "—" : String(text);
    row.appendChild(td);
  }
  async function load() {
    var current = ++generation;
    var status = document.getElementById("gateway-identities-status");
    var body = document.getElementById("gateway-identities-rows");
    var prev = document.getElementById("gateway-identities-prev");
    var next = document.getElementById("gateway-identities-next");
    if (!status || !body || !range || !range.start || !range.end) return;
    prev.disabled = next.disabled = true;
    body.replaceChildren();
    status.textContent = "Đang tải định danh Gateway…";
    var query = {start: range.start, end: range.end, limit: size, offset: page * size};
    var result = await global.TokenLedgerAPI.gatewayIdentities(query);
    if (current !== generation) return;
    if (!result.ok) { status.textContent = "Không tải được định danh Gateway: " + result.message; return; }
    if (agent) {
      var match = result.data.agents.find(function (a) { return a.name === agent; });
      if (!match) { status.textContent = "Agent này chưa được đăng ký theo cấu hình Gateway."; return; }
      query.agent_id = match.agent_id;
      result = await global.TokenLedgerAPI.gatewayIdentities(query);
      if (current !== generation) return;
      if (!result.ok) { status.textContent = "Không tải được định danh Gateway: " + result.message; return; }
    }
    var data = result.data;
    data.rows.forEach(function (item) {
      var tr = document.createElement("tr");
      cell(tr, item.agent);
      cell(tr, item.external_user_id || "Chưa quy được");
      cell(tr, item.kind === "gateway_observed" ? "Định danh quan sát" :
        item.kind === "service_account" ? "Tài khoản dịch vụ" : "Tài khoản chung");
      cell(tr, Number(item.calls).toLocaleString("vi-VN"));
      cell(tr, Number(item.total_tokens).toLocaleString("vi-VN"));
      body.appendChild(tr);
    });
    var note = data.agents.some(function (a) { return a.user_mode === "multiple"; }) ?
      " Chưa có danh bạ để tính tỷ lệ áp dụng." : "";
    status.textContent = data.agents.length ?
      (data.calls === 0 && data.total_tokens === 0 ? "Chưa có usage thành công trong kỳ. " : "") +
      data.total + " dòng · " + Number(data.calls).toLocaleString("vi-VN") + " request · " +
      Number(data.total_tokens).toLocaleString("vi-VN") + " token." + note +
      (data.agents.some(function (a) { return !a.is_running; }) ? " Có agent đã ngừng hoạt động; lịch sử được giữ." : "") :
      "Chưa có agent đăng ký qua gateway-agents.yaml.";
    prev.disabled = page === 0;
    next.disabled = (page + 1) * size >= data.total;
    prev.onclick = function () { if (page > 0) { page--; load(); } };
    next.onclick = function () { page++; load(); };
  }
  global.GatewayIdentityPanel = {
    render: function (dates, selectedAgent) {
      var key = JSON.stringify([dates, selectedAgent]);
      if (key !== lastScope) { page = 0; lastScope = key; }
      range = dates; agent = selectedAgent;
      load();
    }
  };
})(window);
