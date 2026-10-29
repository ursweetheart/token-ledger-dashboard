/* Agent health tab: schedule, run-now with progress, latest results.
   Admin credential lives only in the password input (memory), never in localStorage. */
(function (global) {
  "use strict";
  var root = document.getElementById("agent-health-panel");
  if (!root) return;
  var api = global.TokenLedgerAPI;
  var form = document.getElementById("agent-health-admin");
  var runButton = document.getElementById("agent-health-run");
  var following = null, timer = null, label = null, labelSince = 0, shownRunAt = "";
  var MARK = { ok: "✅ đạt", warn: "⚠️ cảnh báo", fail: "❌ lỗi" };

  function el(id) { return document.getElementById("agent-health-" + id); }
  function message(text, isError) {
    el("message").textContent = text || "";
    el("message").classList.toggle("is-error", !!isError);
  }
  function vnTime(iso) {
    return iso ? new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }) : "—";
  }
  function cell(row, text) {
    var td = document.createElement("td");
    td.textContent = text == null || text === "" ? "—" : String(text);
    row.appendChild(td);
  }
  function pill(row, status, text) {
    var span = document.createElement("span");
    span.className = "agent-health-pill is-" + status;
    span.textContent = text;
    var td = document.createElement("td");
    td.appendChild(span);
    row.appendChild(td);
  }
  function renderRows(results) {
    var body = el("rows");
    body.replaceChildren();
    (results || []).forEach(function (r) {
      var tr = document.createElement("tr");
      cell(tr, r.agent_name);
      cell(tr, r.check_name);
      pill(tr, r.status, MARK[r.status] || r.status);
      cell(tr, r.http_status);
      cell(tr, r.latency_ms == null ? null : Number(r.latency_ms).toLocaleString("vi-VN"));
      cell(tr, r.reason);
      body.appendChild(tr);
    });
  }
  function credential() {
    var value = form.elements.credential.value.trim();
    if (!value) message("Hãy nhập khoá quản trị kết nối trước.", true);
    return value;
  }

  async function load() {
    var res = await api.agentHealth();
    if (!res.ok) { el("status").textContent = "Không tải được sức khỏe agent: " + res.message; return; }
    var data = res.data, input = form.elements.run_at;
    // Chỉ ghi đè khi người dùng chưa sửa ô. Tab tải lại sau mỗi lần chạy xong, và bản cũ (chỉ xét
    // focus) từng đổi giờ gõ dở về giờ cũ, nên Apply gửi lại giờ cũ (thử 29/10/2026).
    if (!input.value || input.value === shownRunAt) input.value = data.run_at;
    shownRunAt = data.run_at;
    var lines = [];
    if (data.last) {
      var kind = data.last.trigger === "manual" ? "chạy tay" : "theo lịch";
      lines.push("Lần chạy gần nhất: " + vnTime(data.last.finished_at || data.last.requested_at) + " · " + kind +
                 (data.last.status === "interrupted" ? " · ⚠️ bị ngắt giữa chừng, kết quả có thể thiếu" : ""));
      renderRows(data.last.results);
    } else {
      lines.push("Chưa có lần chạy nào.");
      renderRows([]);
    }
    if (data.schedule_missed_today) {
      lines.push("⚠️ Hôm nay đã qua giờ chạy " + data.run_at +
                 " nhưng lịch chưa chạy. Kiểm tra service agent-health-watch.");
    }
    el("status").textContent = lines.join("\n");
    if (data.active && following !== data.active.id) follow(data.active.id);
  }

  function stop() {
    clearTimeout(timer); timer = null; following = null; label = null;
    el("progress").hidden = true;
    runButton.disabled = false;
  }

  // Thanh đếm theo PHÉP KIỂM, không theo thời gian: có thể đứng ở 50% tới 3 phút lúc chờ LLM.
  // Số giây tính từ lúc phép kiểm hiện tại bắt đầu, đo bằng đồng hồ trình duyệt (không lệch giờ máy chủ).
  function follow(id) {
    clearTimeout(timer);
    following = id; label = null;
    runButton.disabled = true;
    el("progress").hidden = false;
    async function poll() {
      if (following !== id) return;
      var res = await api.agentHealthRun(id);
      if (following !== id) return;
      if (!res.ok) {
        el("progress-text").textContent = "Không đọc được tiến độ: " + res.message + " (thử lại sau 1 giây)";
        timer = setTimeout(poll, 1000);
        return;
      }
      var run = res.data, total = run.total || 0, done = run.done || 0;
      if (run.current_label !== label) { label = run.current_label; labelSince = Date.now(); }
      el("bar").max = Math.max(total, 1);
      el("bar").value = done;
      renderRows(run.results);
      if (run.status === "running" && label) {
        var tr = document.createElement("tr");
        cell(tr, label); cell(tr, null); pill(tr, "running", "⏳ đang chạy");
        [null, null, null].forEach(function (t) { cell(tr, t); });
        el("rows").appendChild(tr);
      }
      if (run.status === "done" || run.status === "interrupted") {
        stop();
        message(run.status === "done" ? "Đã chạy xong." : "⚠️ Lần chạy bị ngắt giữa chừng.",
                run.status !== "done");
        load();
        return;
      }
      var pct = total ? Math.floor(100 * done / total) : 0;
      el("progress-text").textContent = run.status === "queued"
        ? "Đang chờ service nhận việc (tối đa khoảng 5 giây)…"
        : pct + "% (" + done + "/" + total + ")" +
          (label ? " · Đang kiểm: " + label + " (" + Math.floor((Date.now() - labelSince) / 1000) + " giây)" : "");
      timer = setTimeout(poll, 1000);
    }
    poll();
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    var key = credential();
    if (!key) return;
    var runAt = form.elements.run_at.value.slice(0, 5);
    var res = await api.setAgentHealthSchedule(runAt, key);
    message(res.ok ? "Đã đặt giờ chạy " + res.data.run_at + " (giờ VN). Có hiệu lực trong vài giây."
                   : "Không đặt được giờ: " + res.message, !res.ok);
    if (res.ok) load();
  });

  runButton.addEventListener("click", async function () {
    var key = credential();
    if (!key) return;
    runButton.disabled = true;
    var res = await api.startAgentHealthRun(key);
    if (res.ok) { message("Đã xếp lần chạy."); follow(res.data.id); return; }
    if (res.status === 409 && res.detail && res.detail.id) {
      message("Đang có một lần chạy khác; đang theo dõi lần đó.");
      follow(res.detail.id);
      return;
    }
    runButton.disabled = false;
    message("Không chạy được: " + res.message, true);
  });

  // Tải lại mỗi lần mở tab: lúc trang vừa nạp, khoá đọc có thể chưa được nhập. Lần tải đầu đợi
  // `load` của cửa sổ, vì app.js (nạp sau file này) mới là chỗ chọn tab đang mở.
  var tab = document.querySelector('.tab[data-tab="agent-health"]');
  if (tab) tab.addEventListener("click", load);
  global.addEventListener("load", load);
})(window);
