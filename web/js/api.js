/* ═══════════════════════════════════════════════════════════════════════
   Nối dashboard với backend đọc database.

   Nạp TRƯỚC app.js. CHỈ BƠM DỮ LIỆU — không đụng vào giao diện: không thêm
   phần tử, không đổi chữ, không đổi màu. Dashboard trông y hệt như trước, chỉ
   khác là số bên trong đến từ database.

   Không gọi được backend thì file này trả về LÝ DO, không im lặng rút lui: xem
   `load()` ở cuối file. app.js quyết định vẽ lý do đó thế nào — file này không
   vẽ gì.

   Bật backend (PHẢI có, dashboard không còn dữ liệu dự phòng):
       docker compose up -d
       python -m uvicorn backend.main:app --port 8000

   Đổi địa chỉ backend: thêm ?api=http://may-khac:8000 vào URL, hoặc sửa
   DEFAULT_BASE bên dưới.

   ─── VÌ SAO PHẢI CHUYỂN ĐỔI ───────────────────────────────────────────
   Database nói bằng từ vựng của nó (agent_id, total_tokens, token_source).
   app.js nói bằng từ vựng cũ từ thời nhập Excel (a, m, ti, to). Chỗ dịch giữa
   hai bên nằm gọn trong file này, để app.js không phải sửa và database không
   phải bóp méo theo màn hình.

   ─── TỶ LỆ ÁP DỤNG KHÔNG THEO THANH TRƯỢT NGÀY ───────────────────────
   /api/adoption trả về chỉ tiêu TÍCH LUỸ trên toàn bộ dữ liệu, kèm from_day/
   to_day. Đó là chủ ý: "đã từng dùng chưa" ép vào một kỳ thì cùng một agent
   nhảy từ 49% xuống 7% chỉ vì đổi kỳ, mà con số nào cũng trông như phép đo.

   ─── BA CHỖ KHÔNG CÓ NGUỒN, VÀ ĐỂ 0 CHỨ KHÔNG BỊA ────────────────────
       ug   nhóm người dùng     — không nguồn nào ghi
       u    số user được cấp    — là ảnh chụp, không phải số đo theo ngày
       c    số cuộc chat        — không đo được
   Ba trường này để 0. Trước đây dashboard suy chúng ra bằng hệ số; số suy ra
   trông y hệt số đo, nên thà để trống còn hơn.
   ═══════════════════════════════════════════════════════════════════════ */
(function (global) {
  "use strict";

  var DEFAULT_BASE = "http://127.0.0.1:8000";

  function base() {
    try {
      var q = new URLSearchParams(global.location.search).get("api");
      if (q) return q.replace(/\/+$/, "");
    } catch (e) {}
    return DEFAULT_BASE;
  }

  /* Lỗi mang theo ĐỦ THÔNG TIN để phân loại được, không chỉ một câu chữ.
     `loai` là thứ app.js dùng để chọn thông báo; `endpoint` và `maHttp` là thứ
     người đọc cần để biết phải sửa ở đâu. */
  function makeError(kind, message, extra) {
    var e = new Error(message);
    e.kind = kind;
    e.apiBase = base();
    if (extra) for (var k in extra) if (extra.hasOwnProperty(k)) e[k] = extra[k];
    return e;
  }

  function fetchJson(path) {
    return fetch(base() + path, { cache: "no-store" }).then(
      function (r) {
        /* Máy chủ trả lời nhưng trả mã lỗi - KHÁC HẲN không nối được. Giữ
           riêng hai trường hợp này: một cái là "bật backend lên", cái kia là
           "backend đang lỗi ở endpoint nào đó". */
        if (!r.ok) {
          throw makeError("endpoint-error", path + " → HTTP " + r.status,
                          { endpoint: path, httpStatus: r.status });
        }
        return r.json();
      },
      function () {
        /* fetch chỉ reject khi KHÔNG tới được máy chủ: chưa bật, sai cổng,
           mạng chặn, hoặc CORS. Không phân biệt được sâu hơn từ trong trang -
           trình duyệt cố ý không nói, nên đừng đoán. */
        throw makeError("unreachable", "khong toi duoc " + base() + path,
                        { endpoint: path });
      });
  }

  /* Độ trễ và mã trả về đo ở mức (ngày, agent) — KHÔNG có chiều model.
     Gộp về khoá "ngày|agent" rồi gắn cho mọi dòng model của agent đó.

     Đây là chỗ duy nhất trong file này làm một việc không hoàn toàn đúng, nên
     nói thẳng: p95 gắn cho từng dòng model là p95 CỦA CẢ AGENT, không phải của
     riêng model đó. Cộng gộp lại theo trọng số request sẽ ra xấp xỉ đúng ở mức
     agent, nhưng đọc trên một dòng model đơn lẻ thì con số ấy không có nghĩa
     riêng. Google không đo độ trễ theo model, nên không có cách nào đúng hơn. */
  function perfByAgent(perf) {
    var out = {};
    function slot(k) {
      if (!out[k]) out[k] = { r: 0, e4: 0, e5: 0, e429: 0, lat: 0, lat99: 0,
                              enough: false };
      return out[k];
    }
    (perf.response_codes || []).forEach(function (x) {
      var d = slot(x.day + "|" + x.agent_id),
          code = String(x.response_code),
          n = x.calls || 0;
      d.r += n;
      if (code === "429") d.e429 += n;
      else if (code.charAt(0) === "4") d.e4 += n;
      else if (code.charAt(0) === "5") d.e5 += n;
    });
    (perf.latency || []).forEach(function (x) {
      var d = slot(x.day + "|" + x.agent_id);
      d.lat = x.p95_seconds || 0;
      d.lat99 = x.p99_seconds || 0;
      d.enough = !!x.enough_samples;
    });
    return out;
  }

  function thinkingByKey(thinking) {
    var out = {};
    (thinking.rows || []).forEach(function (x) {
      out[x.day + "|" + x.agent_id + "|" + x.model_id] = x.thinking_tokens || 0;
    });
    return out;
  }

  function primaryUnit(catalog) {
    /* Mỗi agent hiện ở cột "Đơn vị". Lấy đơn vị gốc của cây tổ chức agent đó;
       agent không có cây thì lấy chính dòng kỹ thuật. */
    var out = {};
    (catalog.units || []).forEach(function (u) {
      var cur = out[u.agent_id];
      if (!cur || (u.level || 0) < (cur.level || 0)) out[u.agent_id] = u;
    });
    return out;
  }

  function buildState(usage, perf, thinking, catalog) {
    var byAgent = perfByAgent(perf),
        think = thinkingByKey(thinking),
        unit = primaryUnit(catalog);
    var agentName = {};
    (catalog.agents || []).forEach(function (a) { agentName[a.agent_id] = a.name; });

    /* PHẢI CHIA số lượt lỗi cho các dòng model, KHÔNG lặp lại nguyên con số.

       app.js gộp bằng `a.e4 += row.e4` — cộng thẳng số lượt. Nếu mỗi dòng model
       của cùng một agent đều mang nguyên con số lỗi của cả agent thì tổng bị
       nhân lên đúng bằng số model. Đã đo: tab Hiệu năng báo tỉ lệ thành công
       91,9% trong khi số thật là 99,9% — sai gấp 81 lần, và nó trông hoàn toàn
       hợp lý trên màn hình.

       Chia theo tỷ lệ số lượt gọi của từng dòng, nên cộng lại đúng bằng con số
       của agent. Agent nào không có lượt gọi nào thì dồn hết vào dòng đầu để
       lỗi không biến mất. */
    var callsPerAgentDay = {};
    (usage.rows || []).forEach(function (x) {
      var k = x.day + "|" + x.agent_id;
      callsPerAgentDay[k] = (callsPerAgentDay[k] || 0) + (x.calls || 0);
    });
    var firstRowSeen = {};

    var days = {}, dayOrder = [];
    (usage.rows || []).forEach(function (x) {
      if (!days[x.day]) { days[x.day] = []; dayOrder.push(x.day); }
      var key = x.day + "|" + x.agent_id;
      var p = byAgent[key] || {};
      var u = unit[x.agent_id];
      var total = callsPerAgentDay[key] || 0;
      var share;
      if (total > 0) share = (x.calls || 0) / total;
      else { share = firstRowSeen[key] ? 0 : 1; firstRowSeen[key] = 1; }

      /* Độ trễ KHÔNG chia — nó là phân vị, không phải số đếm. app.js lấy trung
         bình có trọng số theo số lượt, nên lặp lại cùng một p95 trên mọi dòng
         của agent sẽ ra đúng p95 của agent đó. */
      var enough = !!p.enough;

      /* `cached` CÓ BA NGHĨA KHÁC NHAU TUỲ NGUỒN - cái bẫy đắt nhất của dữ
         liệu này, và dashboard đã dính:
             billing     SKU RIÊNG, NẰM NGOÀI input -> total = i + o + cached
             app         TẬP CON của prompt_tokens  -> total = i + o
             monitoring  không có phép đo nào       -> luôn NULL
         Chỉ chuyển tiếp `cached` khi nó nằm NGOÀI input. Nhờ vậy app.js cộng
         ti + to + cached là ra đúng tổng mà không cần biết nguồn nào.
         Trước 15/08 app.js chỉ cộng ti + to, tức đánh rơi toàn bộ token cache
         của hoá đơn: 224,6 / 851,9 triệu = 26% tổng token không lên màn hình. */
      var cachedOutsideInput = x.token_source === "billing" ? (x.cached_tokens || 0) : 0;

      days[x.day].push({
        a: x.agent || agentName[x.agent_id] || ("agent " + x.agent_id),
        d: u ? u.name : "—",
        m: x.model,
        ug: "", u: 0, c: 0,
        ti: x.input_tokens || 0,
        to: x.output_tokens || 0,
        r: x.calls != null ? x.calls : 0,
        /* er là TỶ LỆ (%) của cả agent - app.js lấy trung bình có trọng số theo
           số lượt nên không chia. */
        er: p.r ? (100 * ((p.e4 || 0) + (p.e5 || 0) + (p.e429 || 0)) / p.r) : 0,
        /* Dưới ngưỡng mẫu thì để 0: app.js coi lat=0 là "không có số liệu" và
           hiện '-' thay vì vẽ một con số vô nghĩa từ 3 lượt gọi. */
        lat: enough ? (p.lat || 0) : 0,
        lat99: enough ? (p.lat99 || 0) : 0,
        e4: (p.e4 || 0) * share,
        e5: (p.e5 || 0) * share,
        e429: (p.e429 || 0) * share,
        /* eKnown là SỐ LƯỢT biết được mã trả về, không phải cờ 0/1 - app.js
           cộng nó lại rồi dùng làm mẫu số. Để cờ thì mẫu số thành "số dòng". */
        eKnown: (p.r || 0) * share,
        cached: cachedOutsideInput,
        /* TIỀN LẤY TỪ HOÁ ĐƠN, không nhân lại token với đơn giá.
           NULL ở những ngày hoá đơn chưa về - khi đó app.js mới ước tính, và
           cột token_estimated nói rõ dòng nào là ước tính. */
        cost: x.cost_usd,
        think: think[x.day + "|" + x.agent_id + "|" + x.model_id] || 0,
        /* Ba trường dưới đây không thuộc hình dạng cũ — thêm vào để phần hiển
           thị nào cần thì biết con số này đáng tin đến đâu. app.js hiện không
           đọc chúng; chúng có mặt để không mất thông tin trong lúc dịch. */
        _source: x.token_source,
        _estimated: !!x.token_estimated,
        _latencyEnough: enough
      });
    });
    dayOrder.sort();

    /* Bảng giá lấy từ database (Cloud Billing Catalog), không gõ tay.

       HAI BẢN CHỈ MỤC CỦA CÙNG MỘT BẢNG GIÁ, vì hai nơi hỏi bằng hai khoá khác
       nhau và không nơi nào đổi được:
           pricing      khoá theo TÊN model - dòng /api/usage trả `model`
           pricingById  khoá theo model_id  - dòng /api/usage-by-account trả
                        `model_id` chứ không trả tên (xem backend/store.py)
       Dựng cả hai ở đây, trong lớp dịch, thay vì bắt app.js tự tra chéo. */
    var pricing = {}, pricingById = {};
    (catalog.models || []).forEach(function (m) {
      if (m.price_input != null || m.price_output != null) {
        // `c` chỉ dùng cho những ngày hoá đơn chưa về. Model nào chưa có giá
        // cache thì để 0 - thà thiếu một khoản nhỏ còn hơn bịa một đơn giá.
        var p = { i: m.price_input || 0, o: m.price_output || 0,
                  c: m.price_cached || 0 };
        pricing[m.name] = p;
        pricingById[m.model_id] = p;
      }
    });

    /* Ngân sách tháng lấy từ ref_budget qua /api/catalog, thay cho hằng số
       AGENT_MONTHLY_BUDGETS gõ tay trong app.js. Hai bên đang trùng khớp, nhưng
       trùng khớp hôm nay không phải bảo đảm: đổi hạn mức trên Google Cloud thì
       chỉ database biết. Agent chưa đặt hạn mức USD (Ralli đặt theo token) thì
       bỏ qua, không suy ra 0 - 0 nghĩa là "hết hạn mức", khác hẳn "chưa đặt". */
    var budgets = [];
    (catalog.agents || []).forEach(function (a) {
      if (a.budget_usd != null) budgets.push({ agent: a.name, usd: a.budget_usd });
    });

    return { days: days, dayOrder: dayOrder, pricing: pricing,
             pricingById: pricingById,
             budgets: budgets, fxRate: catalog.fx_rate || null };
  }

  global.TokenLedgerAPI = {
    base: base,

    /* Trả về Promise, LUÔN resolve - không bao giờ reject.
       Hình dạng kết quả:
           { ok: true,  data: <state> }
           { ok: false, error: { kind, message, apiBase, endpoint?, httpStatus? } }

       VÌ SAO KHÔNG resolve(null) NHƯ TRƯỚC
       ------------------------------------
       Trước 17/08/2026 mọi thất bại đều thành `null`, nên bốn tình huống rất
       khác nhau trông y hệt nhau ở phía gọi:

           backend chưa bật            -> null
           một endpoint trả 500        -> null
           database chưa có dữ liệu    -> null
           mở bằng file://             -> null

       Bốn cái đó cần bốn câu trả lời khác nhau cho người xem, mà `null` thì
       không mang nổi thông tin nào. Kết quả là dashboard giữ nguyên số cũ trên
       màn hình và chỉ ghi một dòng console.warn - phải mở DevTools mới thấy.

       VÌ SAO VẪN KHÔNG reject
       -----------------------
       Backend chưa chạy là chuyện thường, không phải ngoại lệ chương trình. Nếu
       reject thì mọi chỗ gọi phải bọc try/catch, và một lần quên là quay lại
       đúng chỗ cũ: thất bại im lặng. */
    load: function () {
      var health;
      /* Mở bằng file:// thì fetch tới http://127.0.0.1:8000 sẽ hỏng vì lý do
         khác hẳn (origin 'null', CORS), và cách khắc phục cũng khác - phải chạy
         máy chủ tĩnh, không phải bật backend. Bắt trường hợp này TRƯỚC khi thử
         gọi, để không báo sai nguyên nhân. */
      if (global.location && global.location.protocol === "file:") {
        return Promise.resolve({
          ok: false,
          error: {
            kind: "file-protocol",
            message: "dang mo bang file://, khong goi duoc API",
            apiBase: base()
          }
        });
      }
      return fetchJson("/api/health")
        .then(function (h) {
          health = h;
          var r = (h.ranges && h.ranges.usage) || {};
          if (!r.from) {
            throw makeError("empty-database",
                            "database chua co du lieu su dung",
                            { endpoint: "/api/health" });
          }
          var q = "?start=" + r.from + "&end=" + r.to;
          return Promise.all([fetchJson("/api/usage" + q),
                              fetchJson("/api/performance" + q),
                              fetchJson("/api/thinking" + q),
                              fetchJson("/api/catalog"),
                              fetchJson("/api/adoption"),
                              fetchJson("/api/accounts"),
                              fetchJson("/api/usage-by-account" + q)]);
        })
        .then(function (r) {
          var state = buildState(r[0], r[1], r[2], r[3]);
          state.health = health;
          state.adoption = (r[4] && r[4].rows) || [];
          state.accounts = (r[5] && r[5].rows) || [];
          state.byAccount = (r[6] && r[6].rows) || [];
          /* Cảnh báo độ phủ đi KÈM bảng theo người dùng, không để app.js phải
             nhớ sang hỏi /api/health - xem ghi chú ở backend/main.py. */
          state.accountWarnings = (r[6] && r[6].warnings) || [];
          return { ok: true, data: state };
        })
        .catch(function (e) {
          /* Vẫn ghi console cho người đang mở DevTools, NHƯNG console không còn
             là chỗ duy nhất biết chuyện: lý do được trả về để app.js hiện lên
             màn hình. File này KHÔNG vẽ gì - đó là hợp đồng ghi ở đầu file. */
          console.warn("[TokenLedgerAPI] " + (e.kind || "loi") + ": " + e.message);
          return {
            ok: false,
            error: {
              kind: e.kind || "unknown",
              message: e.message,
              apiBase: e.apiBase || base(),
              endpoint: e.endpoint,
              httpStatus: e.httpStatus
            }
          };
        });
    }
  };
})(window);
