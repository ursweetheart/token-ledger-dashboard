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

   ─── PHẢI CÓ KHOÁ (từ 21/08/2026) ────────────────────────────────────
   Backend trả 401 cho mọi endpoint không mang `Authorization: Bearer`.
   Người xem nhập khoá một lần, trình duyệt nhớ trong localStorage.
   KHOÁ KHÔNG BAO GIỜ ĐI QUA URL — xem khối `khoa()` bên dưới để biết vì sao.

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

  /* ─── KHOÁ ĐỌC API ────────────────────────────────────────────────────
     Backend từ chối mọi endpoint không mang `Authorization: Bearer <khoá>`.

     KHOÁ KHÔNG BAO GIỜ ĐI QUA URL. Ngay phía trên, `base()` đọc `?api=...`,
     nên lối "cứ thêm `?key=...` cho nhanh" là lối tự nhiên nhất và nó SAI:
     tham số truy vấn nằm trong nhật ký truy cập của máy chủ, trong lịch sử
     trình duyệt, và trong header `Referer` gửi sang bên thứ ba. Ba chỗ đó
     không xoá lại được. File này CỐ Ý không có dòng nào đọc `?key=`.

     Dùng `Authorization: Bearer` chứ không đặt tên riêng kiểu
     `X-Dashboard-Key`: ngày lên JWT theo người, header KHÔNG đổi tên - chỉ
     đổi thứ nằm sau chữ `Bearer`. Frontend viết một lần.

     localStorage gắn theo origin, nên mỗi máy nhập một lần. Không phải chỗ
     cất bí mật an toàn - nhưng khoá này vốn là khoá DÙNG CHUNG, ai xem được
     dashboard thì đã biết nó rồi. */
  /* KHOÁ CẤT THEO TỪNG ĐỊA CHỈ BACKEND, không cất một khoá dùng cho mọi nơi.

     Đây không phải chuyện tiện dụng, mà là bịt một lỗ do CHÍNH change này mở
     ra. `base()` ngay phía trên cho phép đổi địa chỉ backend bằng `?api=...`.
     Trước đây tham số đó chỉ quyết định ĐỌC DỮ LIỆU TỪ ĐÂU. Từ lúc trình duyệt
     giữ một bí mật, nó quyết định luôn GỬI BÍ MẬT ĐI ĐÂU:

         ai do gui link  dashboard?api=http://host-la:8000
         -> trinh duyet dinh kem khoa cua nguoi bam vao request toi host do
         -> khong canh bao nao, vi day van la mot tinh nang co that

     Cất theo địa chỉ thì một địa chỉ lạ đơn giản là KHÔNG có khoá nào: người
     dùng gặp ô nhập khoá và phải tự gõ vào — tức phải cố ý. Và nó cũng đúng
     hơn về bản chất: hai máy chủ khác nhau vốn là hai khoá khác nhau. */
  var KEY_PREFIX = "tokenledger.key:";

  function tenKho() { return KEY_PREFIX + base(); }

  function khoa() {
    try { return global.localStorage.getItem(tenKho()) || ""; }
    catch (e) { return ""; }   /* chế độ riêng tư / chặn cookie */
  }

  function datKhoa(v) {
    try {
      if (v) global.localStorage.setItem(tenKho(), v);
      else global.localStorage.removeItem(tenKho());
      return true;
    } catch (e) { return false; }
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
    var k = khoa(), headers = {};
    if (k) headers["Authorization"] = "Bearer " + k;
    return fetch(base() + path, { cache: "no-store", headers: headers }).then(
      function (r) {
        /* 401 là một loại RIÊNG, không gộp vào "endpoint-error". Hai tình
           huống này đòi hai hành động khác hẳn nhau: 401 là "nhập lại khoá",
           còn 500 là "đi xem log uvicorn". Gộp chung thì người xem đọc được
           một câu không giúp họ làm gì. */
        if (r.status === 401) {
          throw makeError("unauthorized", "khoa khong dung hoac da doi",
                          { endpoint: path, httpStatus: 401 });
        }
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

  /* Cây đơn vị cho app.js: MỘT cây, đã gộp sẵn, đã bỏ dòng kỹ thuật.

     dim_unit chứa HAI cây tổ chức - Trợ lý ảo Ralli 102 đơn vị một gốc, Trợ Lý
     Ảo Hợp Đồng 20 đơn vị bốn gốc - vì hai app mô hình hoá cùng một công ty theo
     hai kiểu. Cột `canonical_unit_id` (database, 20/08/2026) nói dòng nào là bản
     trùng của dòng nào. Gộp Ở ĐÂY, trong lớp dịch, để app.js chỉ thấy một cây.

     Con của bản trùng được NỐI LẠI vào bản chuẩn - 13 đơn vị có cha là một bản
     trùng, bỏ bước này thì chúng mất cha và rơi ra khỏi cây. */
  function orgTree(catalog) {
    var all = catalog.units || [];
    var byId = {};
    all.forEach(function (u) { byId[u.unit_id] = u; });

    function canonical(id) {
      var seen = {};
      while (id && byId[id] && byId[id].canonical_unit_id) {
        if (seen[id]) return id;         // vòng lặp: dừng, đừng treo trình duyệt
        seen[id] = 1;
        id = byId[id].canonical_unit_id;
      }
      return id;
    }
    /* Bảng tra CÔNG KHAI: mã đơn vị gốc -> mã bản chuẩn. Tài khoản và dòng usage
       mang mã gốc, mà cây đã bỏ bản trùng, nên không có bảng này thì chúng trỏ
       vào một đơn vị không còn tồn tại - và trỏ hụt thì lặng lẽ mất số. */
    var canonicalOf = {};
    all.forEach(function (u) { canonicalOf[u.unit_id] = canonical(u.unit_id); });

    var out = [];
    all.forEach(function (u) {
      if (u.is_technical) return;                       // dòng kỹ thuật đi đường riêng
      if (canonical(u.unit_id) !== u.unit_id) return;   // bản trùng: đã gộp
      out.push({
        id: u.unit_id,
        name: u.name,
        parent: u.parent_id ? canonical(u.parent_id) : null,
        level: u.level,
        agentId: u.agent_id,
        /* Cấp gom thuần tuý - báo cáo bắt đầu BÊN DƯỚI nó. Trước 20/08/2026
           app.js ghim cứng hai mã `company` và `rd-corp` cho việc này. */
        reportAggregate: !!u.is_report_aggregate
      });
    });
    return { units: out, canonicalOf: canonicalOf };
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
        unit = primaryUnit(catalog),
        tree = orgTree(catalog);
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
        /* Mã đơn vị, đã quy về bản chuẩn. app.js ghép usage vào đơn vị bằng mã
           này; `d` (TÊN) giữ lại để hiện ra và để đối chiếu khi lần lỗi.
           Ghép bằng tên thì gãy lặng lẽ mỗi khi app đổi nhãn tiếng Việt. */
        unitId: u ? (tree.canonicalOf[u.unit_id] || u.unit_id) : "",
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

    /* Cây đơn vị từ database, đã gộp hai cây thành một. app.js CHƯA dùng - nó
       vẫn đang chạy trên ORG_UNITS gõ cứng (108 đơn vị, app.js:67-177). Bước
       thay nằm ở nhóm 4-7 của change serve-department-metrics-from-database.
       Phơi sẵn ở đây để bước đó chỉ còn là đổi nguồn, không phải viết lại phép
       gộp: đã đối chiếu 20/08/2026, cây này cho ra ĐÚNG 15 gốc báo cáo mà bản
       gõ cứng đang cho. */
    /* Agent CHƯA NỐI Google Billing. Khác hẳn "hoá đơn chưa về": bên kia vài
       ngày là hết, bên này suy ra mãi cho tới khi ai đó nối billing cho project.
       `dim_agent.has_google_source` đã tách riêng chuyện này khỏi
       `gcp_project_id` từ 14/08/2026 - `tla-ralli` CÓ project nhưng chưa nối. */
    var noBilling = {};
    (catalog.agents || []).forEach(function (a) {
      if (!a.has_google_source) noBilling[a.name] = true;
    });

    return { days: days, dayOrder: dayOrder, pricing: pricing,
             pricingById: pricingById,
             units: tree.units, canonicalUnitOf: tree.canonicalOf,
             noBillingAgents: noBilling,
             budgets: budgets, fxRate: catalog.fx_rate || null };
  }

  global.TokenLedgerAPI = {
    base: base,

    /* Khoá đọc API. app.js gọi `datKhoa()` khi người dùng bấm nút, rồi gọi lại
       `load()`. File này vẫn KHÔNG vẽ gì - đó là hợp đồng ghi ở đầu file. */
    khoa: khoa,
    datKhoa: datKhoa,

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
      /* Chưa có khoá thì KHÔNG gọi endpoint dữ liệu nào, kể cả /api/health.
         Cứ gọi rồi nhận 401 cũng ra cùng màn hình, nhưng nó ghi một dòng 401
         vào log máy chủ mỗi lần ai đó mở trang - và tệ hơn: nó biến "chưa
         nhập khoá bao giờ" thành "khoá sai", tức nói sai chuyện đang xảy ra. */
      if (!khoa()) {
        return Promise.resolve({
          ok: false,
          error: {
            kind: "need-key",
            message: "chua nhap khoa doc API",
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
          /* Tài khoản mang `unit_id` GỐC, mà cây đã bỏ các bản trùng. Quy về bản
             chuẩn ngay tại đây - để app.js tự nhớ thì sớm muộn một chỗ quên, và
             tài khoản trỏ vào đơn vị không còn tồn tại sẽ lặng lẽ rơi khỏi bảng. */
          state.accounts = ((r[5] && r[5].rows) || []).map(function (a) {
            var cid = state.canonicalUnitOf[a.unit_id];
            return cid && cid !== a.unit_id
              ? Object.assign({}, a, { unit_id: cid, unit_id_raw: a.unit_id })
              : a;
          });
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
