/* ═══════════════════════════════════════════════════════════════════════
   Agent Analytics · Token Ledger — engine data-driven
   Mô hình dữ liệu: state → days (nhập theo NGÀY) → rows + pricing.
   Mọi chỉ số/biểu đồ/bảng được TÍNH từ rows. Sửa dữ liệu/giá rồi bấm
   "💾 Lưu" ⇒ dashboard tính lại. (v5: chuyển từ nhập theo tháng → theo ngày.)
   ═══════════════════════════════════════════════════════════════════════ */
(function(){
"use strict";

/* ─── Hằng số ─── */
/* v20: localStorage CHỈ giữ lựa chọn người dùng, không còn giữ số liệu — xem
   PREF_KEYS. Đổi khoá một lần để bỏ state của bản trước, vốn đang chứa 345 KB
   dữ liệu backend. Từ nay không cần bump khoá theo mỗi lần cập nhật dữ liệu,
   vì không còn dữ liệu nào trong đó. */
var STORE = "agent-dash-prefs-v20";
var TAB_STORE = "agent-dash-tab";
var THEME_STORE = "agent-dash-theme";
var RANGE_PRESETS = [["7 ngày",7],["30 ngày",30],["90 ngày",90],["Tất cả",null]]; // preset time-range (kiểu Open WebUI)

/* Hạn mức CHỈ đến từ `ref_budget` qua /api/catalog — trước 17/08/2026 chỗ này
   là hằng số gõ tay bị ghi đè ở loadFromBackend() *nếu* backend trả lời, tức hai
   nguồn cho cùng một con số. Chúng trùng khớp lúc đó, nhưng trùng khớp hôm nay
   không phải bảo đảm: đổi hạn mức trên Google Cloud thì chỉ database biết.

   BA TRẠNG THÁI, KHÔNG PHẢI HAI. Đã đối chiếu `dim_agent` (8 agent) với
   `ref_budget` (7 dòng):
       6 agent  có budget_usd            -> hiện hạn mức USD, tính vào tổng
       Ralli    chỉ có budget_tokens     -> ĐÃ đặt, nhưng bằng token
       Tools Quizzer  không có dòng nào  -> CHƯA đặt
   Gộp hai nhóm sau thành một sẽ nói sai về Ralli. Và cả hai đều KHÔNG được suy
   ra 0 — 0 nghĩa là "hết hạn mức", khác hẳn "chưa đặt". */
var AGENT_MONTHLY_BUDGETS = [];
var BUDGET_ALERT_THRESHOLDS = [50,90,100];
var MONTHLY_BUDGET = 0;
var VND_RATE = 25200;
var EXCHANGE_RATE_META = { source:"Tỷ giá cấu hình", updated:"Cấu hình cục bộ" };
var INSIGHT_THRESHOLDS = {
  tokenPerRequestWarning:20,
  tokenPerRequestCritical:50,
  budgetPaceWarning:10,
  budgetNearLimit:90,
  concentrationWarning:50,
  concentrationCritical:70,
  errorWarning:1,
  errorCritical:3,
  latencyWarning:null,
  latencyCritical:null,
  quotaWarning:85,
  quotaCritical:100,
  adoptionWarning:60,
  adoptionCritical:30,
  inactivityDays:30
};
/* SÁU DÒNG "Đơn vị sử dụng <agent>" ĐÃ RỜI DANH SÁCH NÀY (30/08/2026).

   Chúng là hàng kỹ thuật của sáu project Google Cloud Console - loại agent
   không có cây tổ chức, nên không có phòng ban lẫn người dùng. Giấu chúng đi là
   giấu luôn lưu lượng của chúng: đo trên kỳ 31/07-30/08, sáu agent này chiếm
   21.327/23.626 request, tức 90% toàn dashboard KHÔNG hiện ở tab Phòng ban và
   không có mặt trong biểu đồ chi phí theo phòng ban.

   Quy ước thay thế: phòng ban của chúng là CHÍNH TÊN AGENT, người dùng là
   "Người dùng Agent <tên agent>". api.js đổi nhãn ngay ở primaryUnit(), nên
   chuỗi "Đơn vị sử dụng ..." không còn tới được chỗ này nữa.

   "Đang trong quá trình thử nghiệm" thì vẫn ở lại: đó là một đơn vị THẬT đang
   được dùng làm chỗ chứa tạm, không phải hàng kỹ thuật. */
var EXCLUDED_DEPARTMENTS = {
  "Đang trong quá trình thử nghiệm":true
};
/* Ô lọc "User" liệt kê NGƯỜI, không liệt kê tên agent.

   Bản trước 30/08/2026 chỉ nhận user của hai agent gõ cứng ("Sale Agent",
   "Chatbot Contact Center"). Database hiện tại KHÔNG có tài khoản nào thuộc hai
   agent đó — 892 tài khoản thuộc Trợ lý ảo Ralli và 45 thuộc Trợ Lý Ảo Hợp Đồng
   — nên ô lọc rỗng hoàn toàn: mở ra không có gì để chọn.

   Nay nhận mọi tài khoản, và renderFilters() cắt danh sách theo phòng ban đang
   chọn. Agent chạy bằng tài khoản dịch vụ thì "người dùng" là nhãn quy ước
   "Người dùng Agent <tên agent>" do addSyntheticAgentUsers() dựng — nhãn đó khác
   tên agent nên không rơi vào luật ngay dưới. */
function userFilterLabel(u){
  var agent = String((u && u.a) || "").trim();
  var label = String((u && (u.ug || u.user || u.login || u.n)) || "").trim();
  // Nhãn trùng y hệt tên agent nghĩa là chỗ này không có danh tính người nào.
  if(!label || label === agent) return "";
  return label;
}

/* ═══════════════ CÂY ĐƠN VỊ ═══════════════
   Nguồn dữ liệu usage đặt tên phòng ban tự do: mỗi agent trong file Excel là một khối
   riêng và mỗi khối dùng một quy ước viết tắt khác nhau, nên cùng một đơn vị xuất hiện
   dưới nhiều tên (PBH1 / Phòng Bán hàng 1, TMĐT / Thương mại điện tử, C4LED / TT C4LED).
   Cây đơn vị giờ lấy từ database qua /api/catalog, nên mỗi đơn vị chỉ xuất hiện MỘT lần.

   Cây Ralli và số user phân quyền lấy trực tiếp từ data/phong_ban_phan_quyen.xlsx,
   theo mức thụt lề trong sheet "Cơ cấu Tổ chức". Alias tiếp tục chuẩn hóa tên viết tắt
   giữa file usage và file phân quyền: PBH1 / Phòng Bán hàng 1, TMĐT / Thương mại điện tử,
   C4LED / TT C4LED.
   ═══════════════════════════════════════════ */
/* Cây đơn vị. RỖNG cho tới khi adoptOrgUnits() nhận dữ liệu từ /api/catalog.

   Trước 20/08/2026 chỗ này là 108 đơn vị GÕ CỨNG (7.207 ký tự) trong khi
   database có 130. Đó là phần bị bỏ sót của change serve-dashboard-from-
   database-only: đợt đó bỏ được SEED_DAYS, bảng giá và danh bạ, nhưng quên cây
   tổ chức - nên một sự thật về cơ cấu công ty vẫn sống trong mã giao diện.

   Đối chiếu trước khi bỏ (tools/doi_chieu_cay_don_vi.py): KHÔNG đơn vị nào lệch
   cha - đó là kiểu lệch nguy hiểm nhất vì nó không làm mọc thêm hay mất đi hàng
   nào, chỉ chuyển số sang nhánh khác. 5 đơn vị mọc thêm đều 0 tài khoản/0 token,
   3 đơn vị mất đi là tên cũ thời Excel không có dòng trong database. */
var ORG_UNITS = [];
/* UNIT_ALIASES đã bỏ 20/08/2026. Nó làm HAI việc:
     1. hoà giải viết tắt  PBH1 / Phòng Bán hàng 1 / Phòng BH1
     2. gộp hai cây tổ chức thành một cái nhìn công ty
   Việc (1) hết cần khi ghép bằng `unit_id`. Việc (2) chuyển vào database thành
   cột `dim_unit.canonical_unit_id` - 4 cặp, người dùng xác nhận 20/08/2026.
   Cách viết chuẩn của TTDL&DHS lấy đúng như database, không thêm dấu. */

/* Số tài khoản được cấp sẽ được dựng lại từ danh sách user Ralli đã làm sạch.
   Không dùng số demo hoặc số của agent khác cho các KPI/bảng người dùng. */
var DEPT_PROVISIONED = {};
/* Tỷ lệ áp dụng theo agent, do /api/adoption trả về. Rỗng khi không có backend —
   khi đó biểu đồ tự quay về cách tính cũ theo phòng ban. */
var ADOPTION_BY_AGENT = [];
/* Số liệu sử dụng ĐO ĐƯỢC theo từng tài khoản, từ /api/usage-by-account.
   Rỗng khi không có backend — khi đó mới quay về cách rải cũ. */
var REAL_BY_ACCOUNT = [];
/* Danh bạ thật từ /api/accounts - 937 tài khoản, cả Ralli lẫn TLA Hợp Đồng.
   Rỗng khi không có backend, khi đó mới quay về ralli-users.js. */
var REAL_ACCOUNTS = [];
/* Đã xoá 15/08: MODALITY (86/9/4/1 % theo loại nội dung) và USER_HEAT (ma trận
   4x6 lượt dùng theo nhóm). Cả hai là số GÕ TAY, không nguồn nào đo được chúng,
   và không nơi nào trong file này đọc tới - code chết từ lâu. Để lại thì sớm
   muộn có người nối vào một biểu đồ và số bịa lên thẳng màn hình.
   Cần thật thì phải có nguồn đo trước, không phải khai lại hằng số. */
var palette = ["#667eea","#3b82f6","#f59e0b","#10b981","#8b5cf6","#06b6d4","#ef4444","#64748b","#ec4899","#14b8a6"];

/* ═══════════════ DANH MỤC TÀI KHOẢN ═══════════════
   HAI CHẾ ĐỘ, và nhãn phải nói đúng chế độ đang chạy.

   CÓ DATABASE  danh bạ từ /api/accounts (937 tài khoản), số từng người từ
                /api/usage-by-account. Là SỐ ĐO, không phải phân bổ.
   KHÔNG CÓ     danh bạ từ ralli-users.js, số từng người rải từ tổng của phòng
                theo hàm băm tên đăng nhập. Là SỐ PHÂN BỔ.

   Nhãn dưới đây trước 15/08 luôn nói "số phân bổ" ở cả hai chế độ. Sau khi nối
   database, nó thành lời cảnh báo NGƯỢC: bảo người xem đừng tin những con số
   giờ đã là số đo thật. Một cảnh báo sai chỗ cũng nguy hiểm như thiếu cảnh báo.

     buildAccountCatalogue()      → danh tính
     applyAccountAllocation(rows) → chọn một trong hai chế độ trên
   ═════════════════════════════════════════════════════════ */
function accountDataLabel(){
  return REAL_BY_ACCOUNT.length
    ? "Số đo theo từng tài khoản"
    : "Số liệu phân bổ theo phòng ban";
}
function accountDataHint(){
  return REAL_BY_ACCOUNT.length
    ? "Số của từng tài khoản lấy trực tiếp từ nhật ký của Ralli và TLA Hợp Đồng,"
      + " không phải phân bổ. Sáu agent còn lại gọi bằng tài khoản dịch vụ nên"
      + " không có chiều người dùng."
    : "Nguồn usage hiện tại không có định danh user. Số theo tài khoản là số phân"
      + " bổ từ tổng thật của phòng ban, không phải số đo theo từng tài khoản.";
}
var USER_ACCOUNTS = [];

/* Băm tiền định: cùng chuỗi luôn cho cùng số. Không dùng Math.random để mọi lần
   render và mọi lần tải trang đều cho cùng kết quả. */
function stableHash(str){
  var h=2166136261, s=String(str);
  for(var i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); }
  return (h>>>0);
}
/* Các agent/model/nhóm thực tế phục vụ từng đơn vị, đọc từ dữ liệu trong state.

   Trước 17/08/2026 nhánh `else` ở đây dựng danh mục từ buildJuneExcelWeeks() +
   SEED_DAYS khi state chưa có. Không còn nguồn nhúng nào, nên chưa có dữ liệu
   thì trả về danh mục RỖNG — đúng hơn là dựng một danh mục từ số liệu tháng 6. */
function unitAgentProfiles(){
  var byUnit={}, sources=[];
  if(typeof state!=="undefined" && state && state.days) sources.push(state.days);
  sources.forEach(function(src){
    if(!src) return;
    Object.keys(src).forEach(function(day){
      (src[day]||[]).forEach(function(r){
        var unit=unitOfRow(r);
        if(!unit||isExcludedUnit(unit)||!r.a) return;
        var list=byUnit[unit.id]=byUnit[unit.id]||[];
        if(!list.some(function(p){return p.a===r.a&&p.m===r.m;})) list.push({a:r.a,m:r.m,ug:r.ug});
      });
    });
  });
  return byUnit;
}
/* Danh bạ dựng từ DATABASE (/api/accounts).

   Thay cho ralli-users.js - bản Excel 622 dòng, chỉ có người của Ralli. Hậu quả
   đo được trước khi đổi: kỳ 01-13/08 có 15 người phát sinh request mà bảng chỉ
   hiện 7, vì 8 người kia (phần lớn của TLA Hợp Đồng) không có dòng trong file.

   `weight` để 0 vì nhánh này KHÔNG rải số - applyRealAccountUsage() điền số đo
   thật. Trường đó chỉ còn nghĩa ở nhánh dữ liệu nhúng.

   Tài khoản dùng chung (admin, system, guest, test*) vẫn có mặt để tổng token
   không hụt, nhưng mang cờ `shared` để chỉ tiêu tỷ lệ áp dụng loại ra. */
function normalizeAgentName(name){
  return String(name||"").trim().toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}
/* Agent chạy bằng MỘT tài khoản dịch vụ, không cấp quyền cho ai — sáu project
   Google Cloud Console. KHÔNG đoán bằng tên agent: database đã trả lời sẵn.
   store.adoption() đặt kind:"service" cho agent không có dòng danh bạ nào, kèm
   ghi chú "agent loại này vốn không cấp quyền cho ai". Đó là câu trả lời của
   nguồn, không phải suy đoán của tầng hiển thị. */
function isServiceAgent(agent){
  var ten=String(agent||"").trim();
  if(!ten) return false;
  for(var i=0;i<(ADOPTION_BY_AGENT||[]).length;i++){
    var x=ADOPTION_BY_AGENT[i];
    if(x && String(x.agent||"").trim()===ten) return x.kind==="service";
  }
  return false;
}
/* Nhãn người dùng quy ước. Phải KHÁC tên agent, nếu không userFilterLabel() coi
   đây là "không có danh tính" và loại nó khỏi ô lọc. */
function serviceAgentUserLabel(agent){
  return "Người dùng Agent " + String(agent||"").trim();
}
/* Sáu agent Google Cloud Console không có phòng ban lẫn người dùng. Quy ước đã
   chốt: phòng ban là chính tên agent (api.js primaryUnit() đặt nhãn), người dùng
   là "Người dùng Agent <tên agent>" — dựng ở đây, đúng MỘT tài khoản cho mỗi
   agent, khớp với điều database nói: mẫu số 1, tử số 1.

   rows chỉ dùng để biết agent nào có mặt trong dữ liệu. Số liệu KHÔNG lấy từ
   đây — applyRealAccountUsage() điền từ tổng đo được của agent. */
function addSyntheticAgentUsers(list, rows){
  var out = (list || []).slice();
  var seen = {};
  out.forEach(function(u){
    var key = normalizeAgentName(u.a || u.user || u.login || u.n || "");
    if(key) seen[key] = true;
  });
  if(!Array.isArray(rows)) rows = [];
  rows.forEach(function(r){
    if(!r || !r.a) return;
    var agent = String(r.a).trim();
    if(!agent) return;
    if(!isServiceAgent(agent)) return;   // agent có người thật thì không chế ai cả
    var key = normalizeAgentName(agent);
    if(!key || seen[key]) return;
    var unit = unitOfRow ? unitOfRow(r) : null;
    out.push({
      id: "synthetic-agent:" + key.replace(/\s+/g, "-"),
      user: serviceAgentUserLabel(agent),
      login: "synthetic-" + key.replace(/\s+/g, "-"),
      n: serviceAgentUserLabel(agent),
      unitId: unit ? unit.id : "",
      d: unit ? unit.name : "—",
      a: agent,
      m: "",
      ug: serviceAgentUserLabel(agent),
      weight: 0,
      role: "AI Agent",
      accountType: "service",
      sourceStatus: "Tự tính 1 user",
      created: "",
      disabled: false,
      shared: true,
      inDirectory: false,
      req: 1,
      ti: 0,
      to: 0,
      last: r.day || (state && state.range ? state.range.end : ""),
      active: true,
      quotaPct: 100,
      byAgent: { [agent]: { req: 1, ti: 0, to: 0 } }
    });
    seen[key] = true;
  });
  return out;
}
function buildAccountCatalogueFromDb(){
  var list = REAL_ACCOUNTS.map(function(a){
    if(!a) return null;
    var kind = String(a.kind || "").trim();
    // Giữ mọi tài khoản real trong danh mục để cây đơn vị / bảng chi tiết phản
    // ánh thực tế của database. Điều kiện giới hạn user dropdown chỉ đặt ở UI
    // hiển thị, không cắt mất nguồn dữ liệu cho cây phòng ban.
    if(kind !== "real") return null;
    // Ưu tiên MÃ đơn vị (api.js đã quy về bản chuẩn); tên chỉ là đường lui.
    var unit=unitById(a.unit_id)||unitOf(a.unit_name)||null;
    var displayUser = String(a.full_name || a.username || a.agent || "").trim();
    return {
      id:a.account_id || displayUser || a.username || a.agent,
      user:a.username || displayUser,
      login:a.username || displayUser,
      n:a.full_name || displayUser || a.username || a.agent || "",
      unitId:unit?unit.id:"", d:a.unit_name||"—",
      a:a.agent||"", m:"", ug:displayUser || a.username || a.agent || "",
      weight:0,
      role:a.role||"", accountType:a.is_shared?"service":"person",
      sourceStatus:a.is_enabled===false?"Đã khoá":"Hoạt động",
      created:a.created_at||"",
      disabled:a.is_enabled===false,
      shared:!!a.is_shared, inDirectory:!!a.in_directory,
      req:0, ti:0, to:0, last:"", active:false, quotaPct:0
    };
  }).filter(Boolean).filter(function(u){ return u.unitId && !isExcludedUnit(unitById(u.unitId)); });
  return list;
}

/* Danh mục tài khoản — CHỈ từ database.

   Trước 17/08/2026 hàm này có một nhánh dự phòng 32 dòng dựng danh mục từ
   window.RALLI_USERS (file web/js/fallback/ralli-users.js, 121 KB) khi chưa có
   dữ liệu API. Nhánh đó rải request xuống từng người bằng `weight = 1 +
   hash(login) % 9` — con số hiện ra trông y hệt số đo: có người 40 request,
   người 7 request, xếp hạng được, vẽ biểu đồ được, mà toàn bộ đến từ băm tên
   đăng nhập.

   Nay không còn nhánh đó, và cũng không cần: REAL_ACCOUNTS rỗng chỉ xảy ra khi
   backend hỏng, và lúc đó renderError() đã chiếm màn hình nên renderAll() không
   chạy. Trả về mảng rỗng là đúng — không có dữ liệu thì không có danh mục. */
function buildAccountCatalogue(){
  if(!REAL_ACCOUNTS.length) return [];
  /* Thêm người dùng quy ước cho sáu agent Google Cloud Console. Hàm
     addSyntheticAgentUsers() đã có sẵn trong tệp này từ trước nhưng CHƯA TỪNG
     ĐƯỢC GỌI — grep ra đúng một lần xuất hiện là dòng khai báo. Vì thế sáu agent
     đó không có lấy một dòng tài khoản nào, dù chúng chiếm 90% lưu lượng. */
  return addSyntheticAgentUsers(buildAccountCatalogueFromDb(), allDayRows());
}
/* Số liệu ĐO ĐƯỢC của từng tài khoản, từ /api/usage-by-account.

   Thay cho cách rải bằng hàm băm ở applyAccountAllocation() bên dưới. Cách cũ
   ra đời khi chưa nguồn nào ghi ai gọi, nên nó chia tổng của phòng xuống từng
   người theo `weight = 1 + hash(login) % 9`. Con số hiện ra trông y hệt số đo:
   có người 40 request, người 7 request, xếp hạng được, vẽ biểu đồ được — mà
   toàn bộ đến từ băm tên đăng nhập.

   Nay Ralli và TLA Hợp Đồng đều ghi danh tính, và database giữ ở mức
   (ngày, người, agent, model). Ai có số thì lấy số thật; ai không có thì để 0
   chứ KHÔNG rải phần còn lại xuống — "không đo được" và "bằng không" phải
   trông khác nhau.

   Hệ quả phải biết: danh bạ hiển thị đang lấy từ ralli-users.js (622 dòng
   Excel) trong khi database có 937 tài khoản thật. Người của TLA Hợp Đồng
   phần lớn không có dòng trong danh bạ đó nên số của họ không hiện lên được ở
   tab này — con số bị bỏ lại được đếm và ghi vào console. */
var accountFallbackByName = 0;
function applyRealAccountUsage(rows){
  var byKey={}, byId={};
  USER_ACCOUNTS.forEach(function(u){
    u.req=0; u.ti=0; u.to=0; u.active=false; u.last=""; u.quotaPct=0; u.byAgent={};
    /* Sổ tách theo MODEL, song song với byAgent. Bản ghi tài khoản KHÔNG có
       trường model — một người dùng nhiều model, nên `u.m` luôn rỗng. Bộ lọc
       Model/Provider phải hỏi sổ này chứ không hỏi `u.m`. */
    u.byModel={};
    u.costDerived=0; u.costRows=0; u.costRowsPriced=0;
    if(u.id!=null) byId[u.id]=u;
    if(u.login) byKey[String(u.login).trim().toLowerCase()]=u;
  });
  var r=state&&state.range, bo=0, boLuot=0;
  REAL_BY_ACCOUNT.forEach(function(x){
    if(r&&(x.day<r.start||x.day>r.end)) return;
    /* GHÉP BẰNG `account_id` TRƯỚC. Nó là khoá số, cùng khoá mà database dùng -
       không phụ thuộc hoa/thường, khoảng trắng, hay việc app ghi tên kiểu nào.
       Đúng nguyên tắc db/migrations/sql/001_baseline.sql:161:
       "KHÔNG dùng tên đăng nhập làm khoá ngoại
       ... đã thấy ba dạng khác nhau cho cùng một tài khoản".
       Nhánh ghép theo tên giữ lại làm đường lui và có biến đếm, để nó không âm
       thầm gánh việc nếu một ngày `account_id` vắng mặt. */
    var u=byId[x.account_id];
    if(!u){
      u=byKey[String(x.username||"").trim().toLowerCase()]
        ||byKey[String(x.full_name||"").trim().toLowerCase()];
      if(u) accountFallbackByName++;
    }
    if(!u){ bo++; boLuot+=x.calls||0; return; }
    var req=x.calls||0, ti=x.input_tokens||0, to=x.output_tokens||0;
    /* TIỀN TÍNH Ở ĐÂY, MỨC TỪNG DÒNG - không cộng gộp token rồi mới nhân giá.
       Một tài khoản dùng nhiều model, và đơn giá chênh 12,5 lần (flash-lite
       $0,10 so với pro $1,25 cho mỗi triệu token vào), nên nhân tổng đã gộp với
       bất kỳ đơn giá nào cũng ra một con số không model nào tính như thế.
       Đó đúng là chỗ hỏng cũ: api.js dựng tài khoản với `m: ""`, model bị đánh
       rơi, `cost()` tra không ra và trả 0 - làm mọi phòng ban thật hiện `0 ₫`
       ngay cạnh 525,9 nghìn token.
       Đếm cả `costRowsPriced` để biết có dòng nào KHÔNG tra được giá không -
       khi đó phải hiện `—` chứ không phải một con số thiếu. */
    var pr = state.pricingById && state.pricingById[x.model_id];
    u.costRows++;
    if(pr){ u.costRowsPriced++; u.costDerived += ti/1e6*num(pr.i) + to/1e6*num(pr.o); }
    u.req+=req; u.ti+=ti; u.to+=to;
    var ag=x.agent||u.a, b=u.byAgent[ag]||(u.byAgent[ag]={req:0,ti:0,to:0});
    b.req+=req; b.ti+=ti; b.to+=to;
    var mn=state.modelNameById&&state.modelNameById[x.model_id];
    if(mn){ var bm=u.byModel[mn]||(u.byModel[mn]={req:0,ti:0,to:0});
            bm.req+=req; bm.ti+=ti; bm.to+=to; }
    if(!u.last||x.day>u.last) u.last=x.day;
  });
  /* NGƯỜI DÙNG QUY ƯỚC CỦA AGENT DỊCH VỤ — KHỐI NÀY NAY LÀ ĐƯỜNG LUI, KHÔNG
     CÒN LÀ ĐƯỜNG CHÍNH (sửa 03/09/2026).

     CÂU CŨ Ở ĐÂY ĐÃ SAI, và nó sai theo kiểu nguy hiểm: nó mô tả một giả định mà
     chính khối mã dưới đang dựa vào. Nguyên văn: *"/api/usage-by-account chỉ phủ
     nguồn BIẾT NGƯỜI DÙNG (ref_source.knows_user), nên tài khoản dịch vụ không có
     dòng nào ở đó — vòng lặp trên để chúng bằng 0."*

     Từ 03/09/2026 endpoint đó đọc `usage_by_account_resolved`, phủ CẢ 8 AGENT:
     1.453 dòng / 60 tài khoản, trong đó 1.057 dòng là `kind='service_account'`.
     Nên vòng lặp trên KHÔNG còn để chúng bằng 0 — chúng đã có số thật.

     VÌ SAO VẪN GIỮ KHỐI NÀY: phép gán dưới đây là `=` chứ không phải `+=`, nên nó
     GHI ĐÈ chứ không cộng dồn — không có nguy cơ đếm hai lần. Và đã đo 03/09: hai
     đường cho CÙNG một con số, 0/8 agent lệch trên cả `calls`, `input_tokens` lẫn
     `output_tokens`. Giữ lại làm đường lui phòng khi view mất dòng dịch vụ.

     THỨ ĐÃ ĐỔI THẬT: `u.costDerived`, `u.byModel`, `u.costRows` nay ĐƯỢC ĐIỀN cho
     tài khoản dịch vụ (trước đây rỗng, vì không có dòng nào để cộng). Khối này
     không đụng tới ba trường đó nên chúng giữ số vừa tính — và đó là cải thiện:
     sáu agent dịch vụ vốn CÓ tiêu tiền, trước đây chúng hiện 0. */
  var tongAgent={};
  (rows||[]).forEach(function(x){
    if(!x||!x.a) return;
    var t=tongAgent[x.a]||(tongAgent[x.a]={r:0,ti:0,to:0,day:""});
    t.r+=num(x.r); t.ti+=num(x.ti); t.to+=num(x.to);
    if(x.day&&x.day>t.day) t.day=x.day;
  });
  USER_ACCOUNTS.forEach(function(u){
    if(!u.shared||u.role!=="AI Agent") return;   // chỉ người dùng quy ước
    var t=tongAgent[u.a];
    if(!t) return;
    u.req=t.r; u.ti=t.ti; u.to=t.to; u.last=t.day||u.last;
    u.byAgent[u.a]={req:t.r, ti:t.ti, to:t.to};
  });
  USER_ACCOUNTS.forEach(function(u){ u.active=num(u.req)>0; });
  // quotaPct để 0: trước đây nó là 12+(hash%80), tức thẻ trạng thái "Cảnh báo"
  // bật lên theo hàm băm. Không nguồn nào có khái niệm hạn mức theo người, nên
  // để 0 và không ai bị gắn cảnh báo sai.
  /* Danh ba khong con la ralli-users.js (xoa 17/08/2026) - no den tu
     /api/accounts. Cau cu noi "danh ba hien thi van la ban Excel 622 dong", nen
     ai doc log nay se di sua mot tep khong con ton tai. */
  if(bo) console.warn("[TokenLedgerAPI] "+bo+" dong su dung ("+boLuot
    +" luot) khong ghep duoc vao tai khoan nao trong "+USER_ACCOUNTS.length
    +" tai khoan lay tu /api/accounts.");
}

/* Phân bổ số liệu THẬT xuống tài khoản, khoá theo CẶP (đơn vị, agent).
   Phải theo cặp, không chỉ theo đơn vị: nếu phân bổ tổng của phòng cho mọi tài khoản
   bất kể agent, thì một agent có 0 request trong kỳ vẫn nhận số khi drilldown, và
   ma trận cấp 1 (0 request) sẽ nói ngược với ma trận cấp 2. Khoá theo cặp giữ đồng
   thời hai bất biến: tổng theo phòng khớp, và tổng theo phòng × agent cũng khớp. */
function applyAccountAllocation(rows){
  // Có số đo thật thì dùng số đo. Cách rải bên dưới chỉ còn cho trường hợp mở
  // dashboard không có backend, khi dữ liệu nhúng vốn không có chiều người dùng.
  if(REAL_BY_ACCOUNT.length){ applyRealAccountUsage(rows); return; }
  var totals={};
  (rows||[]).forEach(function(r){
    var unit=unitOfRow(r);
    if(!unit||isExcludedUnit(unit)||!r.a) return;
    var key=unit.id+"::"+r.a;
    var t=totals[key]=totals[key]||{unitId:unit.id, agent:r.a, r:0, ti:0, to:0};
    t.r+=num(r.r); t.ti+=num(r.ti); t.to+=num(r.to);
  });
  var byUnit={};
  USER_ACCOUNTS.forEach(function(u){
    u.req=0; u.ti=0; u.to=0; u.active=false; u.last=""; u.quotaPct=0;
    // byAgent giữ phần phân bổ TÁCH THEO AGENT. Không có nó thì u.req là số trộn
    // của mọi agent, và ma trận cấp tài khoản buộc phải quy hết về một agent duy nhất.
    u.byAgent={};
    (byUnit[u.unitId]=byUnit[u.unitId]||[]).push(u);
  });
  function agentBucket(u, agent){
    var b=u.byAgent[agent];
    if(!b) b=u.byAgent[agent]={req:0, ti:0, to:0};
    return b;
  }
  function accountsFor(unitId){
    var out=[];
    [unitId].concat(unitDescendants(unitId).map(function(x){return x.id;})).forEach(function(id){
      (byUnit[id]||[]).forEach(function(u){ if(u.weight>0&&!u.disabled) out.push(u); });
    });
    return out;
  }
  Object.keys(totals).forEach(function(key){
    var t=totals[key];
    if(!t.r&&!t.ti&&!t.to) return;
    var all=accountsFor(t.unitId);
    // Ưu tiên tài khoản đúng agent; chỉ khi đơn vị không có tài khoản nào mang agent đó
    // mới rải cho toàn bộ đơn vị, để không làm mất số liệu.
    var pool=all.filter(function(u){ return u.a===t.agent; });
    if(!pool.length) pool=all;
    if(!pool.length) return;
    pool.sort(function(x,y){ return x.user.localeCompare(y.user); });
    var W=pool.reduce(function(sum,u){return sum+u.weight;},0);
    if(!W) return;
    ["r","ti","to"].forEach(function(field){
      var target=Math.round(t[field]), acctKey=field==="r"?"req":field, used=0;
      pool.forEach(function(u){
        var share=Math.floor(target*u.weight/W);
        u[acctKey]+=share; agentBucket(u,t.agent)[acctKey]+=share; used+=share;
      });
      // Dồn phần dư ⇒ tổng khớp chính xác. Phải dồn vào CẢ hai sổ (tổng và theo agent)
      // để Σ byAgent của một tài khoản luôn bằng đúng u.req của nó.
      var rest=target-used;
      pool[0][acctKey]+=rest; agentBucket(pool[0],t.agent)[acctKey]+=rest;
    });
  });
  USER_ACCOUNTS.forEach(function(u){
    u.active=num(u.req)>0;
    if(u.active){
      var h=stableHash("last:"+u.user);
      u.last=state&&state.range?state.range.end:"";
      u.quotaPct=Math.min(100, 12+(h%80));
    }
  });
}

/* ─── Bảng giá (USD / 1 triệu token) ───
   ĐÃ BỎ khối gõ tay ở đây (17/08/2026). Bảng giá chỉ đến từ `ref_price` qua
   /api/catalog — xem `state.pricing`, do loadFromBackend() điền.

   Khối cũ liệt kê 11 model với đơn giá suy từ hoá đơn Google. Nó đúng lúc viết,
   nhưng nó là nguồn thứ hai cho cùng một con số: `ref_price` trong database cũng
   giữ bảng giá, lấy từ Cloud Billing Catalog. Hai nguồn thì sớm muộn lệch nhau,
   và không có gì báo khi lệch — đổi giá ở Google thì chỉ database biết.

   Hai model OpenAI trong khối cũ ("GPT-4o", "GPT-4o mini") chưa từng phát sinh
   dữ liệu; chúng ở đó để nhập tay, mà luồng nhập tay cũng đã bỏ. */


/* ─── Tiện ích ─── */
function num(v){ var n = Number(v); return isNaN(n) ? 0 : n; }
function fmt(n){ return Math.round(num(n)).toLocaleString("vi-VN"); }
function fmtDecimal(n, digits){
  return num(n).toLocaleString("vi-VN", {minimumFractionDigits:0, maximumFractionDigits:digits==null?1:digits});
}
function fmtTok(n){
  n=num(n);
  if(n>=1e9) return fmtDecimal(n/1e9,1)+" tỷ token";
  if(n>=1e6) return fmtDecimal(n/1e6,1)+" triệu token";
  if(n>=1e3) return fmtDecimal(n/1e3,1)+" nghìn token";
  return fmt(n)+" token";
}
function fmtTokShort(n){ return fmtTok(n).replace(/ token$/,""); }
function fmtTokFull(n){ return fmt(n)+" token"; }
/* Định dạng số thống nhất cho scorecard: viết hẳn "nghìn / triệu / tỷ" thay vì
   K/M/B; đơn vị thật (token, VNĐ, request…) nằm trong ngoặc ở tên thẻ. */
function fmtCompactNum(n){
  n=num(n); var abs=Math.abs(n);
  if(abs>=1e9) return fmtDecimal(n/1e9,1)+" tỷ";
  if(abs>=1e6) return fmtDecimal(n/1e6,1)+" triệu";
  if(abs>=1e3) return fmtDecimal(n/1e3,1)+" nghìn";
  return fmt(n);
}
// Mức độ sử dụng quy đổi VNĐ nhưng bỏ ký hiệu ₫ vì đơn vị đã ghi ở tên thẻ.
function usageCompact(usdValue){ return fmtCompactNum(toVnd(usdValue)); }
// Ngày theo định dạng dd/mm/yyyy dùng cho tiêu đề và dòng "Kỳ dữ liệu".
function fmtDateUS(iso){
  var p=String(iso==null?"":iso).split("-");
  return p.length===3 ? (p[2]+"/"+p[1]+"/"+p[0]) : String(iso);
}
function usd(n){ return num(n).toLocaleString("vi-VN",{style:"currency",currency:"USD",minimumFractionDigits:2,maximumFractionDigits:2}); }
function toVnd(n){ return Math.round(num(n)*VND_RATE); }
function money(n){ return toVnd(n).toLocaleString("vi-VN",{style:"currency",currency:"VND",maximumFractionDigits:0}); }
function vnd(n){ return money(n); }
function moneyCompact(n){
  var value=toVnd(n), abs=Math.abs(value);
  if(abs>=1e9) return fmtDecimal(value/1e9,1)+" tỷ ₫";
  if(abs>=1e6) return fmtDecimal(value/1e6,1)+" triệu ₫";
  if(abs>=1e3) return fmtDecimal(value/1e3,1)+" nghìn ₫";
  return fmt(value)+" ₫";
}
function usdReference(n){ return usd(n)+" · "+EXCHANGE_RATE_META.source.toLowerCase()+" "+fmt(VND_RATE)+" VNĐ/USD"; }
function pct(a,b){ return b ? (num(a)/num(b)*100) : 0; }
function esc(s){ return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function set(id, html){ var e=document.getElementById(id); if(e) e.innerHTML = html; }
function setWithTitle(id, html, title){
  var e=document.getElementById(id); if(!e) return;
  e.innerHTML=html; e.title=title||"";
}
function setMoney(id, usdValue){
  var e=document.getElementById(id); if(!e) return;
  e.innerHTML=money(usdValue);
  e.title=usdReference(usdValue);
}
function setToken(id, tokenValue){
  var e=document.getElementById(id); if(!e) return;
  e.innerHTML=fmtTok(tokenValue);
  e.title=fmtTokFull(tokenValue);
}
/* Dưới ngưỡng này thì KHÔNG gắn dấu `≈` ở mức nhìn thấy ngay - tooltip vẫn nói đủ.
   224/1.189 dòng là suy ra nhưng chúng dồn cục, nên gắn dấu lên mọi ô có dính một
   dòng sẽ làm gần cả bảng có dấu, và một dấu hiệu xuất hiện khắp nơi thì hết là
   dấu hiệu. 2% chọn để Chatbot Contact Center (2,8%) vẫn được đánh dấu còn nhiễu
   lẻ thì không - đây là ngưỡng thẩm mỹ, sửa được, không phải hằng số thiêng. */
/* Agent CHƯA NỐI Google Billing, do api.js lấy từ `dim_agent.has_google_source`.
   Rỗng cho tới khi nạp xong - khi đó mọi phần suy ra được coi là "hoá đơn về
   trễ", tức phía an toàn: nói nhẹ hơn sự thật chứ không nặng hơn. */
var NO_BILLING_AGENTS = {};
var DERIVED_COST_VISIBLE_PCT = 2;

/* Lời giải thích cho một ô tiền. `est` là phần suy từ bảng giá trong `total`.

   NÓI TỶ LỆ, không chỉ nói "có phần suy ra": với Trợ lý ảo Ralli là 100% còn với
   Chatbot Contact Center là 2,8% - hai chuyện rất khác nhau mà cùng một câu sẽ
   làm chúng trông giống hệt.

   VÀ PHÂN BIỆT HAI LÝ DO. Hoá đơn về trễ thì vài ngày tự hết; agent chưa nối
   Google Billing thì suy ra mãi. `tla-ralli` thuộc loại thứ hai - $7,6643 chi phí
   thật không dòng hoá đơn nào ghi. Gộp hai thứ vào một nhãn "ước tính" là chôn
   mất một việc cần người xử lý. */
function costProvenanceTitle(total, agg){
  var base = usdReference(total);
  if(!agg) return base;
  var est = num(agg.costEst);
  if(!(est > 0)) return base;
  var pct = total > 0 ? 100 * est / total : 100,
      chua = num(agg.costEstNoBilling), tre = num(agg.costEstLate),
      dau = "Trong số này có " + moneyCompact(est) + " (" + pct.toFixed(0)
          + "%) suy từ bảng giá. ";
  if(chua > 0 && tre <= 0)
    dau = (pct >= 99.5 ? "TOÀN BỘ số này suy từ bảng giá. " : dau)
        + "Agent CHƯA NỐI Google Billing nên không có hoá đơn nào — việc này sẽ"
        + " không tự hết. ";
  else if(chua > 0)
    dau += "Trong đó " + moneyCompact(chua) + " của agent chưa nối Google Billing"
         + " (không tự hết), phần còn lại do hoá đơn Google về trễ ~1 ngày. ";
  else
    dau += "Hoá đơn Google về trễ khoảng một ngày; vài ngày nữa những dòng này sẽ"
         + " có hoá đơn. ";
  return dau + base;
}
function costIsMarked(total, est){
  return est > 0 && (total <= 0 || 100 * est / total >= DERIVED_COST_VISIBLE_PCT);
}
/* Ô tiền chung. Truyền `agg` (kết quả aggregate) thì tự lấy phần suy ra. */
function moneyCell(usdValue, cls, agg){
  var est = agg ? num(agg.costEst) : 0,
      dau = costIsMarked(usdValue, est) ? "≈ " : "";
  return "<td class='" + (cls || "num cost") + "' title='"
    + esc(costProvenanceTitle(usdValue, agg)) + "'>" + dau + money(usdValue) + "</td>";
}
function shortModel(m){ return String(m||"").replace("Gemini ",""); }
function emptyRow(cols){ return "<tr><td colspan='"+cols+"' class='subtle' style='text-align:center;padding:14px'>Không có dữ liệu khớp bộ lọc.</td></tr>"; }

function modelProvider(m){
  var s = String(m||"").toLowerCase();
  if(s.indexOf("gemini")>=0) return "Google AI Studio";
  if(s.indexOf("gpt")>=0 || /\bo\d/.test(s)) return "OpenAI";
  if(s.indexOf("claude")>=0) return "Anthropic";
  return "Khác";
}

/* ─── Ngày tháng (cho global time range + nhập theo ngày) ─── */
function pad2(n){ return (n<10?"0":"")+n; }
function parseISO(s){ var p=String(s).split("-"); return new Date(Date.UTC(+p[0], (+p[1])-1, +p[2])); }
function toISO(d){ return d.getUTCFullYear()+"-"+pad2(d.getUTCMonth()+1)+"-"+pad2(d.getUTCDate()); }
function addDays(d,n){ return new Date(d.getTime()+n*86400000); }
function dayDiff(aISO,bISO){ return Math.round((parseISO(bISO)-parseISO(aISO))/86400000); }
function dayLabel(iso){ var p=String(iso).split("-"); return p.length===3? (p[2]+"/"+p[1]) : iso; }
/* Tiền: LẤY TỪ HOÁ ĐƠN nếu có, chỉ ước tính khi chưa có.
   Trước 15/08 hàm này luôn nhân lại token với đơn giá, kể cả ở những ngày đã có
   hoá đơn thật trong database. Nhân lại thì sai theo hai hướng cùng lúc: bảng
   giá là giá niêm yết nên không có chiết khấu cam kết, và token cache bị tính
   theo giá input đầy đủ. Đã đo trên 66 dòng có hoá đơn kỳ 01-13/08: hoá đơn
   $26,9370, còn nhân lại ra $26,36 - lệch 2,1% ngay cả khi bảng giá đúng.
   `cached` chỉ được cộng ở nhánh ước tính, và chỉ khi nó nằm NGOÀI input
   (api.js đã lọc sẵn) - xem ghi chú "ba nghĩa của cached" ở đó. */
/* Tiền của MỘT dòng, hoặc null khi KHÔNG tính được.

   Phân biệt hai chuyện mà bản trước 20/08/2026 gộp làm một:
       0     đã đo, và bằng không
       null  không có cách nào tính ra
   Tiền chỉ tồn tại ở hoá đơn Google (`r.cost`), mà hoá đơn ở mức project nên
   KHÔNG có chiều người dùng - `/api/usage-by-account` không trả `cost_usd`, và
   đó là đúng chứ không phải thiếu sót. Đường còn lại là ước tính từ bảng giá,
   cần `r.m` để tra; đối tượng tài khoản có `m: ""` nên tra không ra.
   Hệ quả của việc trả 0: mọi phòng ban THẬT trên tab Phòng ban hiện `0 ₫` trong
   khi có tới 525,9 nghìn token - một con số bịa ra, đúng loại lỗi "không đo
   được trông y hệt bằng không" mà database này sinh ra để chống. */
function costOrNull(r){
  if(r.cost!=null) return num(r.cost);
  var p = state.pricing[r.m]; if(!p) return null;
  return num(r.ti)/1e6*num(p.i) + num(r.to)/1e6*num(p.o)
       + num(r.cached)/1e6*num(p.c||0);
}
/* Giữ nguyên hợp đồng cũ - trả số - để mọi phép CỘNG đang có không đổi hành vi.
   Chỗ nào cần phân biệt "không đo được" thì gọi costOrNull(). */
function cost(r){ var v = costOrNull(r); return v == null ? 0 : v; }
function isExcludedDepartment(name){ return !!EXCLUDED_DEPARTMENTS[String(name||"").trim()]; }

/* "Chưa quy được" là SỌT ĐỰNG những dòng usage không lần ra được đơn vị, không
   phải một phòng ban. Nó có thật trong database (`__unattributed_<agent_id>`,
   is_technical) và PHẢI tiếp tục hiện trong bảng — 2.544 request của nó là số
   thật, giấu đi là giấu mất một phần lưu lượng.

   Nhưng nó KHÔNG được dự thi "Phòng năng suất nhất": đứng đầu bảng xếp hạng
   phòng ban bằng một cái sọt thì con số đúng mà câu trả lời sai.

   Vì sao không nhét vào EXCLUDED_DEPARTMENTS: khoá đó đi qua isExcludedUnit(),
   thứ mà groupRowsByUnit / deptTreeNode / matrixTree / buildDeptUsageIndex đều
   gọi — thêm vào đó là xoá nó khỏi TOÀN BỘ dashboard, tức đúng cái việc vừa nói
   là không được làm. Đây là phép lọc riêng cho bảng xếp hạng. */
var UNATTRIBUTED_UNIT_NAME = "Chưa quy được";
function isUnattributedUnit(u){
  if(!u) return false;
  return String(u.name||"").trim()===UNATTRIBUTED_UNIT_NAME ||
         String(u.id||"").indexOf("__unattributed")===0;
}

/* ═══════════════ TRUY VẤN CÂY ĐƠN VỊ ═══════════════ */
var unitIndex = {}, unitChildIndex = {}, autoUnitSeq = 0;
/* Dựng lại chỉ mục cây. Gọi ở mức module (lúc đó ORG_UNITS còn rỗng) và gọi LẠI
   sau khi nạp xong dữ liệu - cây đến từ /api/catalog chứ không còn gõ cứng. */
function buildUnitIndex(){
  unitIndex = {}; unitChildIndex = {};
  ORG_UNITS.forEach(function(u){
    unitIndex[u.id] = u;
    var p = u.parent || "";
    (unitChildIndex[p] = unitChildIndex[p] || []).push(u);
  });
}
buildUnitIndex();
/* Thay ORG_UNITS bằng cây từ database, rồi dựng lại mọi thứ phụ thuộc nó.

   `units` do api.js giao đã GỘP sẵn hai cây tổ chức qua `canonical_unit_id`, đã
   nối lại con của bản trùng, đã bỏ dòng kỹ thuật. app.js không cần biết database
   có hai cây - đó là việc của lớp dịch.

   Trước 20/08/2026 chỗ này là mảng 108 đơn vị gõ cứng cộng 33 dòng UNIT_ALIASES,
   trong khi database có 130 dòng. Đối chiếu trước khi thay (tools/
   doi_chieu_cay_don_vi.py): không đơn vị nào lệch cha, và gốc báo cáo suy từ
   database ra đúng 15 đơn vị - trùng khít bản gõ cứng. */
function adoptOrgUnits(units){
  if(!units || !units.length) return false;
  ORG_UNITS = units.map(function(u){
    return {id:u.id, name:u.name, parent:u.parent, level:u.level,
            agentId:u.agentId, reportAggregate:!!u.reportAggregate};
  });
  buildUnitIndex();
  rebuildProvisionedFromDirectory();
  return true;
}
/* Phân giải chuỗi phòng ban tự do về một đơn vị. Chuỗi lạ KHÔNG bị loại: tự sinh một
   đơn vị cấp 1 để không mất số liệu và không gom sai vào đơn vị khác. */
/* Đơn vị của MỘT DÒNG usage. Ưu tiên mã, chỉ rơi về tên khi không có mã.

   api.js gắn `unitId` (đã quy về bản chuẩn) lên từng dòng từ 20/08/2026. Ghép
   bằng mã thì đổi nhãn tiếng Việt không làm gãy gì; ghép bằng tên thì gãy, và
   gãy LẶNG LẼ - dòng không tra ra đơn vị sẽ rơi vào một đơn vị tự sinh
   (`app.js:591`) chứ không báo lỗi, nên số vẫn hiện ra, chỉ là hiện sai chỗ.

   Nhánh theo tên giữ lại để phòng backend cũ chưa trả `unitId`. Đếm số lần nó
   được dùng, không để nó âm thầm gánh việc - xem `unitFallbackByName`. */
var unitFallbackByName = 0;
function unitOfRow(r){
  if(r && r.unitId){
    var hit = unitIndex[r.unitId];
    if(hit) return hit;
  }
  unitFallbackByName++;
  return unitOf(r && r.d);
}
function unitOf(deptString){
  var key = String(deptString==null?"":deptString).trim();
  if(!key || key==="—") return null;
  // Khớp lỏng: bỏ khoảng trắng thừa quanh dấu phẩy để chịu được lệch dấu cách.
  var loose = key.replace(/\s*,\s*/g, ",").toLowerCase();
  for(var i=0;i<ORG_UNITS.length;i++){
    if(ORG_UNITS[i].name.trim().toLowerCase()===loose) return ORG_UNITS[i];
  }
  var autoId = "auto:" + key;
  if(!unitIndex[autoId]){
    var unit = {id:autoId, name:key, parent:null, level:1, auto:true};
    unitIndex[autoId] = unit;
    (unitChildIndex[""] = unitChildIndex[""] || []).push(unit);
    autoUnitSeq++;
  }
  return unitIndex[autoId];
}
function unitById(id){ return unitIndex[id] || null; }
function unitName(id){ var u=unitIndex[id]; return u?u.name:"—"; }
function unitChildren(unitId){ return (unitChildIndex[unitId||""] || []).slice(); }
function unitRoots(){ return unitChildren(""); }
/* Các phòng/đơn vị hiển thị ở cấp đầu của dashboard. Hai dòng tổng hợp
   "Toàn công ty" và "Tổng công ty Rạng Đông" vẫn giữ trong cây để tính đúng 887/807,
   nhưng không chiếm hai cấp drilldown trước khi người dùng thấy phòng ban thực tế. */
/* Cấp 1 của báo cáo: bỏ qua các CẤP GOM thuần tuý.

   'Toàn công ty' và 'Tổng công ty Rạng Đông' có thật trong cây, nhưng mọi phòng
   ban đều nằm dưới cả hai - để chúng làm cấp 1 thì người xem phải bung hai lần
   mới thấy thứ đầu tiên phân biệt được với nhau.

   Trước 20/08/2026 hai dòng đó được nhận ra bằng hai MÃ GÕ CỨNG `"company"` và
   `"rd-corp"`, tức một quyết định về cách công ty đọc báo cáo sống trong mã giao
   diện. Giờ database đánh dấu bằng `dim_unit.is_report_aggregate`. */
function isReportAggregate(u){ return !!(u && u.reportAggregate); }
function reportingRoots(){
  var out=[];
  function xet(list){
    list.forEach(function(u){
      if(isReportAggregate(u)) xet(unitChildren(u.id));   // đi xuyên qua cấp gom
      else out.push(u);
    });
  }
  xet(unitRoots());
  return out;
}
function reportingRootOf(unitId){
  var ids={}; reportingRoots().forEach(function(u){ids[u.id]=true;});
  var path=unitPath(unitId);
  for(var i=0;i<path.length;i++) if(ids[path[i].id]) return path[i];
  return path[path.length-1]||unitById(unitId);
}
/* Đường đi từ gốc tới đơn vị, dùng cho breadcrumb và thụt lề bảng. */
function unitPath(unitId){
  var out=[], cur=unitIndex[unitId], guard=0;
  while(cur && guard++ < 10){ out.unshift(cur); cur = cur.parent ? unitIndex[cur.parent] : null; }
  return out;
}
function unitDescendants(unitId){
  var out=[], stack=unitChildren(unitId);
  while(stack.length){ var u=stack.shift(); out.push(u); stack=stack.concat(unitChildren(u.id)); }
  return out;
}
function isExcludedUnit(unit){ return !unit || isExcludedDepartment(unit.name); }
/* Đếm 622 tài khoản Ralli theo phòng trực tiếp, sau đó cộng vào toàn bộ cấp cha.
   Nhờ đó company/PBH/vùng/đội đều có mẫu số đúng nhưng mỗi tài khoản chỉ tồn tại một lần. */
/* Số tài khoản ĐƯỢC CẤP QUYỀN theo đơn vị, cộng dồn lên mọi cấp cha.

   Đếm từ danh bạ THẬT: chỉ người có trong danh bạ của app (`in_directory`) và
   không phải tài khoản dùng chung. Đó đúng là định nghĩa "được cấp quyền", và là
   MẪU SỐ của tỷ lệ áp dụng - tử số phải lọc y hệt, xem deptRowHtml.

   Đổi tên 20/08/2026 (cũ: `rebuildRalliProvisioned`) vì nó đếm MỌI tài khoản chứ
   không riêng Trợ lý ảo Ralli - tên cũ nói sai phạm vi.

   Ghép bằng `unit_id` chứ không bằng `unit_name`: tên phòng ban do app tự khai,
   đổi nhãn là hụt mẫu số mà không có gì báo. */
function rebuildProvisionedFromDirectory(){
  DEPT_PROVISIONED={};
  REAL_ACCOUNTS
    .filter(function(a){ return a.in_directory && !a.is_shared; })
    .forEach(function(a){
      var unit=unitById(a.unit_id)||unitOf(a.unit_name);
      if(!unit||isExcludedUnit(unit)) return;
      unitPath(unit.id).forEach(function(node){
        DEPT_PROVISIONED[node.id]=(DEPT_PROVISIONED[node.id]||0)+1;
      });
    });
}
rebuildProvisionedFromDirectory();
/* Số tài khoản được cấp: khai báo ở cấp lá, cấp cha cộng dồn từ con.
   Trả về null khi không có dữ liệu — KHÔNG suy ra từ số user active. */
function provisionedOf(unitId){
  if(!unitId) return null;
  if(Object.prototype.hasOwnProperty.call(DEPT_PROVISIONED,unitId)) return DEPT_PROVISIONED[unitId];
  var kids=unitChildren(unitId);
  if(kids.length){
    var sum=0, any=false;
    kids.forEach(function(k){ var v=provisionedOf(k.id); if(v!=null){ sum+=v; any=true; } });
    return any?sum:null;
  }
  return null;
}
function directProvisionedOf(unitId){
  var total=provisionedOf(unitId);
  if(total==null) return null;
  var assigned=unitChildren(unitId).reduce(function(sum,k){
    var childTotal=provisionedOf(k.id);
    return sum+(childTotal==null?0:childTotal);
  },0);
  return Math.max(0,total-assigned);
}

/* ─── State (day-based) ─── */
var state;
/* ─── LỰA CHỌN NGƯỜI DÙNG vs DỮ LIỆU: hai thứ khác nhau ───────────────────
   `localStorage` CHỈ giữ lựa chọn của người dùng. Số liệu MUST NOT được ghi
   vào đó.

   Danh sách dưới đây là DANH SÁCH CHO PHÉP, không phải danh sách loại trừ. Đó
   là điểm cốt yếu: thêm một trường dữ liệu mới vào `state` về sau sẽ KHÔNG tự
   động bị ghi xuống. Danh sách loại trừ thì đòi mọi người sau này phải nhớ bổ
   sung vào đó — và một lần quên là số liệu lại rò ra cache.

   VÌ SAO PHẢI LÀM VIỆC NÀY
   ------------------------
   Trước 17/08/2026, `saveState()` ghi TOÀN BỘ `state` gồm cả `state.days`.
   loadFromBackend() cố ý không gọi saveState(), nhưng 9 chỗ khác thì có (đổi bộ
   lọc, sửa bảng giá, bung cây phòng ban), nên chỉ cần một cú bấm là dữ liệu
   backend nằm trong localStorage. Đã đo trên trình duyệt thật: 345 KB, 224
   ngày, 1.154 dòng. Và khi backend chết thì màn hình hiện CHÍNH cache đó -
   không phải dữ liệu nhúng - nên xoá SEED_DAYS mà không sửa chỗ này thì không
   đóng được đường dữ liệu cũ nào. */
var PREF_KEYS = ["range", "filters", "activeDay",
                 "deptExpanded", "deptExpandedInit", "deptSearch",
                 "matrixExpanded", "matrixSearch", "pmCollapsed"];

/* State rỗng: KHÔNG dữ liệu, chỉ lựa chọn mặc định.
   `days`/`dayOrder` để rỗng và `pricing` để rỗng — cả ba chỉ được điền từ
   database qua loadFromBackend(). Trước đây hàm này trộn buildJuneExcelWeeks()
   với SEED_DAYS, tức mở trang là đã có số trên màn hình trước khi hỏi ai. */
function defaultState(){
  return { days:{}, dayOrder:[], activeDay:null,
    range:null,
    filters:{dept:"",user:"",provider:"",model:"",agent:""},
    deptExpanded:defaultDeptExpanded(), deptExpandedInit:1, deptSearch:"",
    matrixExpanded:{}, matrixSearch:"", pmCollapsed:{}, pricing:{}, pricingById:{} };
}
/* Cấp 1 của cây giờ đã là phòng ban thật (xem buildDeptRows dùng reportingRoots),
   nên mở dashboard là thấy ngay danh sách phòng ban mà không cần bung sẵn cấp nào —
   giống hệt ma trận tab Agents. */
function defaultDeptExpanded(){ return {}; }
/* Đọc LỰA CHỌN đã lưu, phủ lên state rỗng. Chỉ nhận đúng các khoá trong
   PREF_KEYS — mọi khoá khác trong cache cũ bị bỏ, kể cả `days` của bản trước. */
function loadState(){
  var s = defaultState();
  var raw;
  try{ raw = localStorage.getItem(STORE); }catch(e){ return s; }
  if(!raw) return s;
  var p;
  try{ p = JSON.parse(raw); }catch(e){ return s; }
  if(!p || typeof p !== "object") return s;

  PREF_KEYS.forEach(function(k){ if(p[k] !== undefined) s[k] = p[k]; });

  // Chuẩn hoá lại từng khoá: cache có thể do phiên bản cũ ghi, hoặc bị sửa tay.
  if(!s.filters || typeof s.filters!=="object") s.filters={dept:"",user:"",provider:"",model:"",agent:""};
  if(!s.deptExpanded||typeof s.deptExpanded!=="object") s.deptExpanded={};
  if(!s.matrixExpanded||typeof s.matrixExpanded!=="object") s.matrixExpanded={};
  if(typeof s.matrixSearch!=="string") s.matrixSearch="";
  if(typeof s.deptSearch!=="string") s.deptSearch="";
  // Cây nhà cung cấp → model mặc định MỞ, nên chỉ lưu những nhánh bị thu lại.
  if(!s.pmCollapsed||typeof s.pmCollapsed!=="object") s.pmCollapsed={};
  // Chỉ seed trạng thái mở mặc định MỘT lần. Không có cờ này thì người dùng thu gọn
  // hết rồi tải lại trang sẽ bị bung ra lần nữa.
  if(!s.deptExpandedInit){ s.deptExpanded=defaultDeptExpanded(); s.deptExpandedInit=1; }
  // Khoá đơn vị không còn hợp lệ sau khi chuẩn hoá cây thì loại bỏ. Cây phòng ban
  // giờ cũng dùng khoá "<unitId>::direct" nên kiểm theo phần trước "::".
  Object.keys(s.deptExpanded).forEach(function(id){
    if(!unitById(String(id).split("::")[0])) delete s.deptExpanded[id];
  });
  // Khoá "<unitId>::direct" là nút gom tài khoản trực thuộc, không phải một đơn vị
  // trong ORG_UNITS ⇒ kiểm theo phần trước "::" để không bị xoá oan khi tải lại.
  Object.keys(s.matrixExpanded).forEach(function(id){
    if(!unitById(String(id).split("::")[0])) delete s.matrixExpanded[id];
  });
  if(isExcludedDepartment(s.filters.dept)) s.filters.dept="";
  // `range` để null nếu chưa hợp lệ: loadFromBackend() sẽ đặt nó theo khoảng ngày
  // THẬT của database, thay vì gán một kỳ cứng có thể nằm ngoài dữ liệu.
  if(!s.range || !s.range.start || !s.range.end) s.range = null;
  return s;
}

/* Ghi ĐÚNG các khoá trong PREF_KEYS. Không JSON.stringify(state) nữa: state có
   chứa `days` (hàng nghìn dòng số liệu), và ghi nó xuống là tạo ra một nguồn dữ
   liệu cũ mà lần mở sau sẽ đọc lên rồi vẽ như số mới. */
function saveState(){
  try{
    var p = {};
    PREF_KEYS.forEach(function(k){ if(state[k] !== undefined) p[k] = state[k]; });
    localStorage.setItem(STORE, JSON.stringify(p));
  }catch(e){}
}

/* ─── Chọn phạm vi rows theo kỳ (time range) + bộ lọc ─── */
function dayRows(iso){ if(!state.days[iso]) state.days[iso]=[]; return state.days[iso]; }
function allDayRows(){ var out=[]; state.dayOrder.forEach(function(d){ out = out.concat(state.days[d]||[]); }); return out; }
function scopeBase(){
  var rs=parseISO(state.range.start), re=parseISO(state.range.end);
  if(re<rs){ var t=rs; rs=re; re=t; }
  var out=[];
  state.dayOrder.forEach(function(d){
    var dd=parseISO(d);
    if(dd>=rs && dd<=re){ (state.days[d]||[]).forEach(function(r){ out.push(r); }); }
  });
  return out;
}
function applyFilters(rows){
  var f = state.filters;
  // Lọc phòng ban theo đơn vị chuẩn hoá, không so chuỗi thô: nếu so chuỗi thì chọn
  // "Phòng Bán hàng 1" sẽ bỏ mất các dòng ghi "PBH1" dù bảng đã gộp chúng làm một.
  var wantIds=null;
  if(f.dept){
    var want=unitOf(f.dept);
    if(want){
      wantIds={};
      [want].concat(unitDescendants(want.id)).forEach(function(u){ wantIds[u.id]=true; });
    }
  }
  return rows.filter(function(r){
    if(wantIds){ var u=unitOfRow(r); if(!u||!wantIds[u.id]) return false; }
    if(f.user && r.ug !== f.user) return false;
    if(f.provider && modelProvider(r.m) !== f.provider) return false;
    if(f.model && r.m !== f.model) return false;
    if(f.agent && r.a !== f.agent) return false;
    return true;
  });
}
function scopedRows(){ return applyFilters(scopeBase()); }
function allAgents(){
  var seen={}, out=[]; allDayRows().forEach(function(r){ if(r.a && !seen[r.a]){ seen[r.a]=1; out.push(r.a); } }); return out;
}
function distinct(arr){ var seen={}, out=[]; arr.forEach(function(x){ if(x!=null && x!=="" && !seen[x]){ seen[x]=1; out.push(x); } }); return out; }
// Tổng người dùng ĐÃ CẤP là snapshot: lấy tổng lớn nhất của một ngày để không cộng trùng giữa các tháng.
function provisionedTotal(){
  var max=0;
  state.dayOrder.forEach(function(d){
    var total=applyFilters(state.days[d]||[]).reduce(function(s,r){return s+num(r.u);},0);
    if(total>max) max=total;
  });
  return max;
}

/* ─── Ngày dữ liệu min/max (cho preset time range) ─── */
/* Mốc đầu/cuối của dữ liệu THẬT. Trước 17/08/2026 hai hàm này lùi về hằng số
   SEED_DAY = "2026-07-01" khi dayOrder rỗng — tức BỊA một ngày ra khi không có
   dữ liệu nào, và mọi thứ tính từ nó trông như số đo. Giờ dayOrder rỗng chỉ xảy
   ra khi chưa nạp được, và lúc đó renderError() đã chiếm màn hình rồi, nên lùi
   về hôm nay là đủ an toàn và không giả vờ biết gì về dữ liệu. */
function today0(){ var d=new Date(); return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())); }
function minDataDate(){ return state.dayOrder.length ? parseISO(state.dayOrder[0]) : today0(); }
function maxDataDate(){ return state.dayOrder.length ? parseISO(state.dayOrder[state.dayOrder.length-1]) : today0(); }
function normalizeRange(){ if(parseISO(state.range.start) > parseISO(state.range.end)){ var t=state.range.start; state.range.start=state.range.end; state.range.end=t; } }

/* ─── So sánh kỳ trước / cùng kỳ năm trước ───
   Kỳ trước = L ngày ngay trước range hiện tại (L = độ dài range).
   Cùng kỳ năm trước = dịch range lùi 365 ngày. Áp cùng bộ lọc. ─── */
function rangeLenDays(){ return dayDiff(state.range.start, state.range.end) + 1; }
function shiftedAgg(offsetDays){
  var s=addDays(parseISO(state.range.start), offsetDays), e=addDays(parseISO(state.range.end), offsetDays);
  var out=[];
  state.dayOrder.forEach(function(d){ var dd=parseISO(d); if(dd>=s && dd<=e){ (state.days[d]||[]).forEach(function(r){ out.push(r); }); } });
  return aggregate(applyFilters(out));
}
function previousPeriodWindow(){
  var len=rangeLenDays(), rangeStart=parseISO(state.range.start), rangeEnd=parseISO(state.range.end);
  var lastOfRangeMonth=new Date(Date.UTC(rangeEnd.getUTCFullYear(),rangeEnd.getUTCMonth()+1,0));
  if(rangeStart.getUTCDate()===1&&rangeStart.getUTCMonth()===rangeEnd.getUTCMonth()&&rangeEnd.getUTCDate()===lastOfRangeMonth.getUTCDate()){
    var priorEnd=new Date(Date.UTC(rangeStart.getUTCFullYear(),rangeStart.getUTCMonth(),0));
    var priorStart=new Date(Date.UTC(priorEnd.getUTCFullYear(),priorEnd.getUTCMonth(),1));
    return {start:toISO(priorStart),end:toISO(priorEnd)};
  }
  var immediateStart=addDays(rangeStart,-len);
  var immediateEnd=addDays(parseISO(state.range.start),-1), available=[];
  state.dayOrder.forEach(function(d){
    var dd=parseISO(d);
    if(dd>=immediateStart&&dd<=immediateEnd) available.push(d);
  });
  // Nếu kỳ liền trước có ít hơn một nửa số ngày, dùng kỳ dữ liệu đầy đủ gần nhất.
  if(available.length<Math.ceil(len/2)){
    var prior=state.dayOrder.filter(function(d){return d<state.range.start;});
    if(prior.length){
      immediateEnd=parseISO(prior[prior.length-1]);
      immediateStart=addDays(immediateEnd,-(len-1));
    }
  }
  return {start:toISO(immediateStart),end:toISO(immediateEnd)};
}
function previousPeriodRows(){
  var w=previousPeriodWindow(), out=[];
  state.dayOrder.forEach(function(d){
    if(d>=w.start&&d<=w.end) out=out.concat(state.days[d]||[]);
  });
  return applyFilters(out);
}
function previousPeriodAgg(){
  return aggregate(previousPeriodRows());
}
function samePeriodWindow(){
  return { start:toISO(addDays(parseISO(state.range.start),-365)),
           end:toISO(addDays(parseISO(state.range.end),-365)) };
}
function periodWindowLabel(w){
  var s=parseISO(w.start), e=parseISO(w.end);
  if(s.getUTCFullYear()===e.getUTCFullYear()&&s.getUTCMonth()===e.getUTCMonth()){
    return "tháng "+(s.getUTCMonth()+1)+"/"+s.getUTCFullYear();
  }
  return dayLabel(w.start)+"–"+dayLabel(w.end);
}
function previousPeriodLabel(){ return periodWindowLabel(previousPeriodWindow()); }
function samePeriodLabel(){ return periodWindowLabel(samePeriodWindow()); }
/* ─── Baseline so sánh: kỳ trước và cùng kỳ năm trước ───
   Scorecard viết gọn: mũi tên + màu cho chiều biến động, % thay đổi, KT/CK cho kỳ gốc.
   Tên kỳ đầy đủ và giá trị gốc → giá trị hiện tại nằm trong tooltip. ─── */
var DELTA_BASIS = {
  KT: { abbr:"KT", full:"kỳ trước",            label:previousPeriodLabel },
  CK: { abbr:"CK", full:"cùng kỳ (năm trước)", label:samePeriodLabel }
};
function deltaBaseline(realBase, cur, mockFactor){
  // Chỉ sử dụng dữ liệu thật; không dựng baseline bằng hệ số.
  if(realBase != null && realBase > 0) return { v:realBase, mock:false };
  return { v:0, mock:false };
}
function deltaLine(basisKey, cur, b, betterUp, fmtFn){
  var basis=DELTA_BASIS[basisKey]||DELTA_BASIS.KT, period=basis.label();
  var tip="so với "+basis.full+(period?" ("+period+")":"");
  if(b.v==null || b.v<=0){
    return "<div class='delta-line d-dim' title='"+esc(tip+": chưa có dữ liệu")+"'>– <span class='delta-basis'>"+
      basis.abbr+"</span> chưa có dữ liệu</div>";
  }
  var diff=cur-b.v, p=diff/b.v*100, flat=Math.abs(p)<0.5, up=diff>0;
  // Màu biểu thị trực tiếp hướng biến động theo quy ước dashboard:
  // tăng = xanh, giảm = đỏ, gần như không đổi = trung tính.
  // betterUp chỉ còn được giữ trong chữ ký hàm để tương thích với các lời gọi hiện tại.
  var cls = flat ? "d-neutral" : (up ? "d-green" : "d-red");
  var arrow = flat ? "→" : (up ? "▲" : "▼");
  var percent = flat ? "0%" : (Math.abs(p).toFixed(0)+"%");
  // Giá trị của kỳ gốc hiện ngay cạnh nhãn KT/CK. Trước đây nó chỉ nằm trong
  // tooltip, nên "▲ 75%" không nói được là tăng từ đâu lên đâu — người đọc
  // phải rê chuột mới biết 75% đó là từ 4 lên 7 hay từ 4 nghìn lên 7 nghìn.
  var baseText = fmtFn ? fmtFn(b.v) : String(b.v);
  // Chi tiết đầy đủ (tên kỳ, giá trị gốc → hiện tại) vẫn giữ trong tooltip.
  var detail = tip+": "+(b.mock?"≈":"")+baseText+" → "+(fmtFn?fmtFn(cur):String(cur));
  return "<div class='delta-line "+cls+"' title='"+esc(detail)+"'>"+arrow+" "+
    percent+" <span class='delta-basis'>"+basis.abbr+"</span>"+
    " <span class='delta-base-val'>"+esc((b.mock?"≈":"")+baseText)+"</span></div>";
}
function renderDelta(id, cur, prev, same, betterUp, fmtFn, mockPrev, mockSame){
  var el=document.getElementById(id); if(!el) return;
  var pb=deltaBaseline(prev, cur, mockPrev), sb=deltaBaseline(same, cur, mockSame);
  el.innerHTML = deltaLine("KT", cur, pb, betterUp, fmtFn) + deltaLine("CK", cur, sb, betterUp, fmtFn);
}
function renderSingleDelta(id, cur, prev, fmtFn){
  var el=document.getElementById(id); if(!el) return;
  el.innerHTML=deltaLine("KT",cur,deltaBaseline(prev,cur,0),null,fmtFn);
}

/* ─── Tổng hợp ─── */
/* `costEst` / `costInv` — TIỀN NÀY TỪ ĐÂU RA (thêm 20/08/2026)

   28,2% số tiền hiển thị trên dashboard không đến từ hoá đơn nào: $114,4465 trên
   $406,4321 của kỳ 01/01-17/08. Nó được nhân ra từ `ref_price` khi
   `usage_resolved.cost_usd` là NULL, và trước hôm nay không ô nào nói điều đó.

   Không rải đều, nên trung bình cả kỳ không thay được con số của từng chỗ:
       Trợ lý ảo Ralli           100,0% suy ra   (chưa nối Google Billing)
       Trợ Lý Ảo Hợp Đồng         77,7%
       Chatbot Contact Center      2,8%
   Và 22/228 ngày có hơn một nửa tiền là suy ra — ngày mới nhất luôn 100%, vì
   Google phát hành hoá đơn trễ khoảng một ngày.

   Đây là ĐIỂM NGHẼN DUY NHẤT: 7 chỗ gọi aggregate() nuôi mọi con số tiền trên cả
   6 tab, nên đếm ở đây là phủ hết. */
function aggregate(rows){
  var a = {u:0,c:0,ti:0,to:0,r:0,cached:0,think:0,cost:0,erW:0,latW:0,latR:0,
           e4:0,e5:0,e429:0,eKnown:0,lat99W:0,lat99R:0,
           costEst:0, costInv:0, costRowsInv:0, costRowsEst:0, costRowsUnknown:0,
           costEstNoBilling:0, costEstLate:0};
  rows.forEach(function(row){
    a.u+=num(row.u); a.c+=num(row.c); a.ti+=num(row.ti); a.to+=num(row.to);
    a.r+=num(row.r); a.cached+=num(row.cached); a.think+=num(row.think);
    var _c=cost(row);
    a.cost+=_c; a.erW+=num(row.er)*num(row.r);
    if(row.cost!=null){ a.costInv+=_c; a.costRowsInv++; }
    else if(costOrNull(row)!=null){
      a.costEst+=_c; a.costRowsEst++;
      /* HAI LÝ DO, KHÔNG MỘT. Trước đó phân biệt bằng `costRowsInv===0`, và điều
         kiện đó gộp nhầm "agent này không bao giờ có hoá đơn" với "kỳ này chưa có
         hoá đơn nào". Chọn riêng ngày 17/08 là mọi agent đều 0 dòng hoá đơn, nên
         màn hình báo "chưa nối billing" cho cả 7 agent đã nối. */
      if(NO_BILLING_AGENTS[row.a]) a.costEstNoBilling+=_c; else a.costEstLate+=_c;
    }
    // Dòng không có hoá đơn VÀ không tra được giá: không cộng vào đâu cả, nhưng
    // phải đếm - nếu không thì `cost` hụt đúng phần đó mà không gì nói ra.
    else a.costRowsUnknown++;
    if(num(row.lat)>0&&num(row.r)>0){a.latW+=num(row.lat)*num(row.r);a.latR+=num(row.r);}
    // Mã lỗi đếm theo SỐ LƯỢT, không theo tỷ lệ: cộng số lượt thì đúng ở mọi
    // mức gộp, còn cộng tỷ lệ thì phải nhớ trọng số và rất dễ sai.
    a.e4+=num(row.e4); a.e5+=num(row.e5); a.e429+=num(row.e429);
    // eKnown = số lượt mà ta THỰC SỰ biết mã trả về. Nguồn Google có; Ralli
    // không đi qua GCP nên không có. Thiếu ô này thì "0 lỗi" và "không biết có
    // lỗi hay không" trông giống hệt nhau.
    a.eKnown+=num(row.eKnown);
    if(num(row.lat99)>0&&num(row.r)>0){a.lat99W+=num(row.lat99)*num(row.r);a.lat99R+=num(row.r);}
  });
  // CỘNG CẢ `cached`. Với nguồn hoá đơn, token cache là một SKU riêng nằm NGOÀI
  // input, nên ti + to bỏ sót nó: 224,6/851,9 triệu = 26% tổng token. api.js chỉ
  // truyền `cached` khi nó nằm ngoài input, nên cộng ở đây không bao giờ đếm hai
  // lần - xem ghi chú "ba nghĩa của cached" trong api.js.
  a.tokens = a.ti + a.to + a.cached;
  a.er = a.r ? a.erW/a.r : 0;
  a.latAvailable = a.latR>0;
  a.lat = a.latAvailable ? a.latW/a.latR : 0;
  a.codeAvailable = a.eKnown>0;
  a.lat99Available = a.lat99R>0;
  a.lat99 = a.lat99Available ? a.lat99W/a.lat99R : 0;
  return a;
}
function groupAgg(rows, keyFn){
  var map={}, order=[];
  rows.forEach(function(row){
    var k = keyFn(row); if(k==null || k==="") return;
    if(!map[k]){ map[k]={rows:[], models:{}, depts:{}, agents:{}}; order.push(k); }
    map[k].rows.push(row);
    if(row.m) map[k].models[row.m]=1;
    if(row.d && row.d!=="—") map[k].depts[row.d]=1;
    if(row.a) map[k].agents[row.a]=1;
  });
  return order.map(function(k){
    var g=map[k], ag=aggregate(g.rows);
    ag.key=k; ag.models=Object.keys(g.models); ag.depts=Object.keys(g.depts); ag.agents=Object.keys(g.agents);
    return ag;
  });
}

/* ─── Actionable insight rules ─── */
function insight(ruleId, severity, evidence, driver, recommendation, score){
  return {ruleId:ruleId,severity:severity,evidence:evidence||"",driver:driver||"",recommendation:recommendation||"",score:num(score)};
}
function severityRank(s){ return s==="critical"?3:s==="warning"?2:s==="normal"?1:0; }
function topGroup(rows, keyFn, metric){
  var groups=groupAgg(rows,keyFn).filter(function(g){return num(g[metric])>0;}).sort(function(a,b){return num(b[metric])-num(a[metric]);});
  if(!groups.length) return null;
  var total=groups.reduce(function(s,g){return s+num(g[metric]);},0);
  return {key:groups[0].key,value:num(groups[0][metric]),share:pct(groups[0][metric],total)};
}
function budgetAgentKey(name){
  return String(name||"").trim().toLowerCase();
}
function agentBudgetConfig(name){
  var key=budgetAgentKey(name);
  for(var i=0;i<AGENT_MONTHLY_BUDGETS.length;i++){
    var item=AGENT_MONTHLY_BUDGETS[i], names=[item.agent].concat(item.aliases||[]);
    if(names.some(function(candidate){return budgetAgentKey(candidate)===key;})) return item;
  }
  return null;
}
/* Ngân sách cấu hình là mức THÁNG, còn chi phí được cộng theo khoảng thời gian đang chọn.
   Quy đổi mẫu số theo số ngày của từng tháng giao với khoảng để hai vế cùng độ dài:
   T6+T7 = 30/30 + 31/31 = 2,0 tháng; 15/6→15/7 = 16/30 + 15/31 ≈ 1,02 tháng. */
function budgetMonthsInRange(){
  var start=parseISO(state.range.start), end=parseISO(state.range.end);
  if(!(start<=end)) return 0;
  var months=0, cursor=new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), 1));
  while(cursor<=end){
    var monthStart=cursor, monthEnd=new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth()+1, 0));
    var from=monthStart>start?monthStart:start, to=monthEnd<end?monthEnd:end;
    if(from<=to) months += (dayDiff(toISO(from), toISO(to))+1) / monthEnd.getUTCDate();
    cursor=new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth()+1, 1));
  }
  return months;
}
function configuredBudgetSummary(rows){
  var costs={}, matchedRows=[];
  (rows||[]).forEach(function(row){
    var config=agentBudgetConfig(row.a);
    if(!config) return;
    costs[config.agent]=(costs[config.agent]||0)+cost(row);
    matchedRows.push(row);
  });
  var months=budgetMonthsInRange();
  var agents=AGENT_MONTHLY_BUDGETS.map(function(config){
    var spend=costs[config.agent]||0, budget=config.usd*months;
    return {agent:config.agent,cost:spend,budget:budget,rate:pct(spend,budget)};
  });
  return {
    cost:agents.reduce(function(sum,item){return sum+item.cost;},0),
    budget:MONTHLY_BUDGET*months,
    months:months,
    agents:agents,
    rows:matchedRows
  };
}
/* ─── Cảnh báo agent tiêu vượt mặt bằng ─── */
/* NGƯỠNG ĐẶT TÊN, không rải số 1.3 giữa mã. Biên bản 25/07 chốt 30%. */
var AGENT_COST_OUTLIER_RATIO = 1.30;
/* Dưới ngần này agent thì trung bình không nói lên điều gì: với 2 agent, mức
   trung bình bị chính agent đang xét kéo lên, nên "vượt 30%" gần như luôn đúng
   về số học mà vô nghĩa về ý nghĩa. Không chặn hẳn — vẫn hiện, nhưng nói rõ mẫu
   nhỏ để người đọc tự trừ hao. */
var AGENT_COST_SAMPLE_MIN = 3;

/* `averageAgentCost = tổng chi phí agent hoạt động / số agent hoạt động`
   (design.md §7). "Hoạt động" = CÓ CẢ chi phí lẫn request trong kỳ; agent có
   request mà chưa quy được tiền không được kéo mẫu số xuống. */
function agentCostOutliers(rows){
  var groups = groupAgg(rows, function(r){ return r.a; })
    .filter(function(g){ return g.cost > 0 && g.r > 0; });
  var total = groups.reduce(function(s,g){ return s + g.cost; }, 0);
  var avg = groups.length ? total / groups.length : 0;
  var flagged = groups
    .filter(function(g){ return g.cost > avg * AGENT_COST_OUTLIER_RATIO; })
    .sort(function(a,b){ return b.cost - a.cost; });
  return { agents:groups, sample:groups.length, avg:avg, flagged:flagged,
           small: groups.length < AGENT_COST_SAMPLE_MIN };
}

function renderAgentCostAlerts(rows){
  var el = document.getElementById("co-alert-body"); if(!el) return;
  var o = agentCostOutliers(rows);
  var ky = dayLabel(state.range.start) + " → " + dayLabel(state.range.end);
  var mau = document.getElementById("co-alert-note");

  if(!o.sample){
    el.innerHTML = emptyRow(5);
    if(mau) mau.textContent = "Chưa agent nào vừa có chi phí vừa có request trong kỳ này.";
    return;
  }
  if(mau){
    mau.textContent = "Mức trung bình " + moneyCompact(o.avg) + " tính trên " + o.sample
      + " agent hoạt động trong kỳ " + ky + ". Ngưỡng cảnh báo: vượt "
      + Math.round((AGENT_COST_OUTLIER_RATIO - 1) * 100) + "%."
      + (o.small ? " MẪU NHỎ (dưới " + AGENT_COST_SAMPLE_MIN
                 + " agent) — mức trung bình bị chính agent đang xét kéo lên, đọc dè chừng." : "");
  }
  if(!o.flagged.length){
    el.innerHTML = "<tr><td colspan='5' class='subtle' style='text-align:center;padding:14px'>"
      + "Không agent nào vượt mặt bằng " + Math.round((AGENT_COST_OUTLIER_RATIO - 1) * 100)
      + "% trong kỳ này.</td></tr>";
    return;
  }
  el.innerHTML = o.flagged.map(function(g){
    var vuot = o.avg > 0 ? (g.cost / o.avg - 1) * 100 : 0;
    return "<tr data-alert-agent=\"" + escAttr(g.key) + "\" title='Bấm để lọc dashboard theo agent này'>"
      + "<td>" + esc(g.key) + "</td>"
      /* moneyCell tự gắn dấu ≈ và lời giải thích khi tiền suy từ bảng giá —
         spec `visible-data-provenance` buộc mọi ô tiền tự khai nguồn, và cảnh
         báo này đứng hay đổ hoàn toàn dựa vào con số đó. */
      + moneyCell(g.cost, "num cost", g)
      + "<td class='num'>" + moneyCompact(o.avg) + "</td>"
      + "<td class='num text-red'>+" + fmtDecimal(vuot, 0) + "%</td>"
      + "<td class='num'>" + fmt(g.r) + "</td></tr>";
  }).join("");
}

function bindAgentCostAlerts(){
  var tb = document.getElementById("co-alert-body"); if(!tb) return;
  if(tb.getAttribute("data-alert-bound")) return;
  tb.setAttribute("data-alert-bound","1");
  tb.addEventListener("click", function(ev){
    var tr = ev.target && ev.target.closest ? ev.target.closest("tr[data-alert-agent]") : null;
    if(!tr) return;
    state.filters.agent = tr.getAttribute("data-alert-agent");
    renderAll();
  });
}

function reachedBudgetThreshold(rate){
  var reached=0;
  BUDGET_ALERT_THRESHOLDS.forEach(function(threshold){if(rate>=threshold) reached=threshold;});
  return reached;
}
function dataDaysElapsed(){
  var start=parseISO(state.range.start), end=parseISO(state.range.end), last=null;
  state.dayOrder.forEach(function(d){var day=parseISO(d);if(day>=start&&day<=end&&(!last||day>last))last=day;});
  return last?Math.max(1,dayDiff(state.range.start,toISO(last))+1):0;
}
function tokenInsight(A, prevA, rows){
  if(!prevA || prevA.tokens<=0 || prevA.r<=0 || A.r<=0) return insight("token-anomaly","unavailable");
  var tokenGrowth=(A.tokens-prevA.tokens)/prevA.tokens*100;
  var curPerReq=A.tokens/A.r, prevPerReq=prevA.tokens/prevA.r;
  var perReqGrowth=(curPerReq-prevPerReq)/prevPerReq*100;
  var top=topGroup(rows,function(r){return r.a;},"tokens");
  var driver=top?(top.key+" chiếm "+top.share.toFixed(0)+"% token trong kỳ."):"";
  var perReqComparison=fmtTok(prevPerReq)+" → "+fmtTok(curPerReq)+" (+"+perReqGrowth.toFixed(0)+"%).";
  if(perReqGrowth>=INSIGHT_THRESHOLDS.tokenPerRequestCritical){
    return insight("token-per-request","critical","Token/request tăng so với kỳ trước: "+perReqComparison,driver,"Kiểm tra prompt, context và giới hạn output của agent dẫn đầu.",perReqGrowth);
  }
  if(perReqGrowth>=INSIGHT_THRESHOLDS.tokenPerRequestWarning){
    return insight("token-per-request","warning","Token/request tăng so với kỳ trước: "+perReqComparison,driver,"Rà soát các request có context lớn bất thường.",perReqGrowth);
  }
  var tokenDirection=Math.abs(tokenGrowth)<0.5?"không đổi":(tokenGrowth>0?"tăng":"giảm");
  var tokenPercent=Math.abs(tokenGrowth)<0.5?"0%":((tokenGrowth>0?"+":"−")+Math.abs(tokenGrowth).toFixed(0)+"%");
  return insight("token-growth","normal","Token "+tokenDirection+" so với kỳ trước: "+fmtTok(prevA.tokens)+" → "+fmtTok(A.tokens)+" ("+tokenPercent+"); mức dùng/request chưa vượt ngưỡng.",driver,"",Math.abs(tokenGrowth));
}
function budgetInsight(A, rows){
  if(MONTHLY_BUDGET<=0) return insight("budget-pace","unavailable");
  var elapsed=dataDaysElapsed(), totalDays=rangeLenDays();
  var configured=configuredBudgetSummary(rows), spend=configured.cost, budget=configured.budget;
  if(!elapsed || !totalDays || spend<=0 || budget<=0) return insight("budget-pace","unavailable");
  var budgetPct=pct(spend,budget), timePct=pct(elapsed,totalDays);
  var forecast=spend/elapsed*totalDays, forecastPct=pct(forecast,budget);
  var top=topGroup(configured.rows,function(r){return r.a;},"cost");
  var driver=top?(top.key+" đóng góp "+top.share.toFixed(0)+"% chi phí."):"";
  var evidence="Dự kiến cuối kỳ "+money(forecast)+" / ngân sách "+money(budget)+" ("+forecastPct.toFixed(0)+"%).";
  if(forecastPct>100){
    return insight("budget-forecast","critical",evidence,driver,"Mở tab Chi phí để rà soát agent/model vượt ngân sách.",forecastPct-100);
  }
  if(forecastPct>=INSIGHT_THRESHOLDS.budgetNearLimit || budgetPct-timePct>=INSIGHT_THRESHOLDS.budgetPaceWarning){
    return insight("budget-pace","warning",evidence,driver,"Theo dõi burn rate và điều chỉnh hạn mức trước cuối kỳ.",Math.max(forecastPct-INSIGHT_THRESHOLDS.budgetNearLimit,budgetPct-timePct));
  }
  return insight("budget-pace","normal","Chi tiêu đang trong ngân sách; forecast "+money(forecast)+".",driver,"",100-forecastPct);
}
function concentrationInsight(rows){
  var top=topGroup(rows,function(r){return r.a;},"cost");
  if(!top) return insight("cost-concentration","unavailable");
  var severity=top.share>=INSIGHT_THRESHOLDS.concentrationCritical?"critical":top.share>=INSIGHT_THRESHOLDS.concentrationWarning?"warning":"normal";
  var recommendation=severity==="normal"?"":"Mở tab Agents/Chi phí để kiểm tra tải và hạn mức.";
  return insight("cost-concentration",severity,top.key+" chiếm "+top.share.toFixed(0)+"% tổng chi phí.","",recommendation,top.share);
}
function reliabilityInsight(A, rows){
  if(A.r<=0) return insight("error-rate","unavailable");
  var top=groupAgg(rows,function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.er-a.er;})[0];
  var severity=A.er>=INSIGHT_THRESHOLDS.errorCritical?"critical":A.er>=INSIGHT_THRESHOLDS.errorWarning?"warning":"normal";
  var driver=top&&top.er>0?(top.key+" có tỷ lệ lỗi cao nhất "+top.er.toFixed(1)+"%."):"";
  var recommendation=severity==="normal"?"":"Kiểm tra response code và request lỗi trong tab Hiệu năng.";
  var errorResult=insight("error-rate",severity,"Tỷ lệ lỗi "+A.er.toFixed(1)+"% trên "+fmt(A.r)+" request.",driver,recommendation,A.er);
  if(A.latAvailable&&INSIGHT_THRESHOLDS.latencyWarning!=null){
    var latSeverity=A.lat>=INSIGHT_THRESHOLDS.latencyCritical?"critical":A.lat>=INSIGHT_THRESHOLDS.latencyWarning?"warning":"normal";
    var latencyResult=insight("latency",latSeverity,"Độ trễ "+A.lat.toFixed(1)+" giây so với SLO cấu hình.","",latSeverity==="normal"?"":"Kiểm tra agent/provider chậm trong tab Hiệu năng.",A.lat);
    return severityRank(latencyResult.severity)>severityRank(errorResult.severity)?latencyResult:errorResult;
  }
  return errorResult;
}
function quotaInsight(utilizationPct){
  if(utilizationPct==null||isNaN(Number(utilizationPct))) return insight("quota","unavailable");
  var q=num(utilizationPct);
  var severity=q>=INSIGHT_THRESHOLDS.quotaCritical?"critical":q>=INSIGHT_THRESHOLDS.quotaWarning?"warning":"normal";
  return insight("quota",severity,"Mức sử dụng quota đạt "+q.toFixed(0)+"%.","",severity==="normal"?"":"Kiểm tra RPM/TPM và điều chỉnh hạn mức trước khi phát sinh lỗi 429.",q);
}
function adoptionInsight(A, provisioned){
  if(provisioned<=0) return insight("adoption","unavailable");
  var rate=pct(A.u,provisioned);
  var severity=rate<INSIGHT_THRESHOLDS.adoptionCritical?"critical":rate<INSIGHT_THRESHOLDS.adoptionWarning?"warning":"normal";
  var inactive=Math.max(0,provisioned-A.u);
  return insight("adoption",severity,fmt(A.u)+"/"+fmt(provisioned)+" tài khoản đã sử dụng; "+fmt(inactive)+" chưa dùng.","",severity==="normal"?"":"Mở tab User để rà soát tài khoản chưa hoạt động.",100-rate);
}
function inactivityInsight(activeCount, createdCount){
  if(createdCount<=0) return insight("agent-inactivity","unavailable");
  var idle=Math.max(0,createdCount-activeCount), share=pct(idle,createdCount);
  var severity=share>=50?"critical":idle>0?"warning":"normal";
  return insight("agent-inactivity",severity,activeCount+"/"+createdCount+" agent có request; "+idle+" agent chưa hoạt động.","",idle?"Rà soát owner, nhu cầu sử dụng hoặc ngừng agent không cần thiết.":"",share);
}
function agentActivityInsight(){
  var end=maxDataDate(), start=addDays(end,-(INSIGHT_THRESHOLDS.inactivityDays-1));
  var recent=[];
  state.dayOrder.forEach(function(d){var day=parseISO(d);if(day>=start&&day<=end)recent=recent.concat(state.days[d]||[]);});
  recent=applyFilters(recent);
  var created=distinct(applyFilters(allDayRows()).map(function(r){return r.a;}).filter(Boolean));
  var active=distinct(recent.filter(function(r){return r.r>0;}).map(function(r){return r.a;}));
  var result=inactivityInsight(active.length,created.length);
  if(result.severity!=="unavailable") result.evidence=active.length+"/"+created.length+" agent có request trong "+INSIGHT_THRESHOLDS.inactivityDays+" ngày; "+Math.max(0,created.length-active.length)+" agent chưa hoạt động.";
  return result;
}
function renderCardInsight(valueId, candidates){
  var value=document.getElementById(valueId); if(!value) return;
  var card=value.closest(".metric-card"); if(!card) return;
  var existing=card.querySelector(".metric-insight");
  candidates=(candidates||[]).filter(function(x){return x&&x.severity!=="unavailable";});
  if(!candidates.length){ if(existing)existing.remove(); card.classList.remove("insight-normal","insight-warning","insight-critical"); return; }
  candidates.sort(function(a,b){return severityRank(b.severity)-severityRank(a.severity)||b.score-a.score;});
  var chosen=candidates[0], label=chosen.severity==="critical"?"CẢNH BÁO":chosen.severity==="warning"?"CẦN THEO DÕI":"ỔN ĐỊNH";
  if(!existing){existing=document.createElement("div");existing.className="metric-insight";card.appendChild(existing);}
  existing.setAttribute("data-rule",chosen.ruleId);
  existing.innerHTML="<span class='insight-status'>"+label+"</span><div class='insight-evidence'>"+esc(chosen.evidence)+(chosen.driver?" "+esc(chosen.driver):"")+"</div>"+(chosen.recommendation?"<div class='insight-action'>→ "+esc(chosen.recommendation)+"</div>":"");
  card.classList.remove("insight-normal","insight-warning","insight-critical");
  card.classList.add("insight-"+chosen.severity);
}

/* ═══════════════ CHART HELPERS ═══════════════ */
var charts = {};
function chart(id, cfg){
  if(typeof Chart === "undefined") return;
  var cv = document.getElementById(id); if(!cv) return;
  if(charts[id]) charts[id].destroy();
  charts[id] = new Chart(cv.getContext("2d"), cfg);
}
/* Huỷ chart và nêu rõ lý do trống, thay vì để lại canvas rỗng không giải thích. */
function emptyChart(canvasId, legendId, message){
  if(charts[canvasId]){ charts[canvasId].destroy(); delete charts[canvasId]; }
  if(legendId) set(legendId, "<span class='metric-na'>"+esc(message)+"</span>");
}
function gridColor(){ return currentTheme()==="light" ? "#e2e8f0" : "#1e293b"; }
function wrapAxisLabel(label, maxChars){
  var words=String(label==null?"":label).split(/\s+/), lines=[], line="";
  maxChars=maxChars||24;
  words.forEach(function(word){
    var next=line?line+" "+word:word;
    if(line&&next.length>maxChars){ lines.push(line); line=word; }
    else line=next;
  });
  if(line) lines.push(line);
  return lines.length>1?lines:lines[0]||"";
}
/* Nhãn giá trị in ngay cuối mỗi thanh ngang: người xem đọc được con số mà không phải rê
   chuột từng thanh, giống cột "tỷ trọng" trong bảng chi phí. Chỉ dùng cho thanh NGANG —
   thanh dọc hẹp hơn nhiều nên chữ sẽ chồng lên nhau. */
function barValueLabels(fmtFn){
  return {
    id:"bar-value-labels",
    afterDatasetsDraw:function(chartInstance){
      var meta=chartInstance.getDatasetMeta(0);
      if(!meta||meta.hidden) return;
      var ctx=chartInstance.ctx, area=chartInstance.chartArea,
          values=chartInstance.data.datasets[0].data||[];
      ctx.save();
      ctx.fillStyle=currentTheme()==="light"?"#334155":"#cbd5e1";
      ctx.font="600 10px Inter, sans-serif";
      ctx.textAlign="left";
      ctx.textBaseline="middle";
      meta.data.forEach(function(bar,i){
        var v=values[i];
        // Chặn ở mép phải để nhãn của thanh dài nhất không bị cắt mất.
        ctx.fillText(fmtFn?fmtFn(v,i):fmt(v), Math.min(bar.x+7, area.right+6), bar.y);
      });
      ctx.restore();
    }
  };
}
function mkBar(id, labels, data, o){
  o = o || {};
  var numericTick=o.money?function(v){return moneyCompact(v);}:o.tokens?function(v){return fmtTokShort(v);}:undefined;
  var categoryTick=function(v){return wrapAxisLabel(this.getLabelForValue(v),26);};
  var valueLabel=o.money?moneyCompact:o.tokens?fmtTokShort:
    o.percent?function(v){return fmtDecimal(v,1)+"%";}:fmt;
  chart(id, {
    type:"bar",
    data:{ labels:labels, datasets:[{ data:data, backgroundColor:o.colors||"#667eea", borderRadius:4, maxBarThickness:o.horizontal?22:44 }] },
    plugins:o.horizontal?[barValueLabels(valueLabel)]:[],
    options:{ indexAxis:o.horizontal?"y":"x",
      // Chừa lề phải để nhãn giá trị của thanh dài nhất vẫn nằm trong khung; nhãn tiền
      // và token dài hơn nhãn số thường nên cần nhiều chỗ hơn.
      layout:o.horizontal?{padding:{right:(o.money||o.tokens)?76:46}}:{},
      plugins:{ legend:{display:false}, tooltip:{ callbacks:{ label:function(c){ var v=o.horizontal?c.parsed.x:c.parsed.y; return o.money?[money(v),usd(v)+" · "+EXCHANGE_RATE_META.source]:(o.tokens?fmtTokFull(v):fmt(v)); } } } },
      scales:{
        // Thanh ngang: khoá xoay nhãn trục giá trị. Sau khi chừa lề phải cho nhãn giá trị,
        // Chart.js thấy trục hẹp đi nên tự xoay chéo chữ — để nằm ngang và tự bớt mốc.
        x:{ grid:{ color:gridColor(), display:!o.horizontal },
            ticks:{ callback:o.horizontal?numericTick:categoryTick, maxRotation:o.horizontal?0:50 } },
        y:{ grid:{ color:gridColor(), display:!!o.horizontal }, ticks:{ callback:o.horizontal?categoryTick:numericTick, autoSkip:false } }
      } }
  });
}
/* descs (tuỳ chọn): một dòng giải nghĩa cho từng mục chú thích. Dùng khi nhãn là
   thuật ngữ mà người đọc non-IT không tự hiểu, ví dụ mã phản hồi 4xx/5xx/429. */
function mkDonut(id, labels, data, legendId, fmtVal, colors, descs){
  colors = colors || palette;
  chart(id, {
    type:"doughnut",
    data:{ labels:labels, datasets:[{ data:data, backgroundColor:colors, borderWidth:0 }] },
    /* Chart.js vẽ tooltip BÊN TRONG canvas, mà canvas donut chỉ rộng 132–168px nên
       chữ dài bị xén cụt. Hai việc để tooltip luôn nằm gọn: bỏ phần lặp lại tên ở
       dòng giá trị (dòng tiêu đề đã có tên rồi), và ngắt dòng tiêu đề khi quá dài. */
    options:{ cutout:"62%", plugins:{ legend:{display:false},
      tooltip:{ callbacks:{
        title:function(items){ return items.length?wrapAxisLabel(items[0].label,16):""; },
        label:function(c){ return fmtVal?fmtVal(c.parsed):fmt(c.parsed); }
      } } } }
  });
  if(legendId){
    var tot = data.reduce(function(s,x){ return s+num(x); },0);
    set(legendId, labels.map(function(l,i){
      var head = esc(l)+" · "+pct(data[i],tot).toFixed(0)+"%";
      if(!descs||!descs[i]) return "<span class='li'><span class='dot' style='background:"+colors[i%colors.length]+"'></span>"+head+"</span>";
      return "<span class='li'><span class='dot' style='background:"+colors[i%colors.length]+"'></span>"+
        "<span class='li-text'><b>"+head+"</b><span class='li-desc'>"+esc(descs[i])+"</span></span></span>";
    }).join(""));
  }
}
function mkPolar(id, labels, data, legendId, fmtVal, colors){
  colors = colors || palette;
  chart(id, {
    type:"polarArea",
    data:{ labels:labels, datasets:[{ data:data, backgroundColor:colors.map(function(c){return c+"cc";}), borderColor:colors, borderWidth:1 }] },
    options:{
      scales:{ r:{ beginAtZero:true, max:100, ticks:{display:false}, pointLabels:{display:false},
        grid:{color:gridColor()}, angleLines:{color:gridColor()} } },
      plugins:{ legend:{display:false},
        tooltip:{ callbacks:{ label:function(c){ return c.label+": "+(fmtVal?fmtVal(c.raw):fmt(c.raw)); } } } }
    }
  });
  if(legendId){
    set(legendId, labels.map(function(l,i){
      return "<span class='li'><span class='dot' style='background:"+colors[i%colors.length]+"'></span>"+esc(l)+" · "+(fmtVal?fmtVal(data[i]):fmt(data[i]))+"</span>";
    }).join(""));
  }
}
function mkLine(id, labels, datasets, isMoney){
  chart(id, {
    type:"line",
    data:{ labels:labels, datasets:datasets },
    options:{ plugins:{ legend:{ display:datasets.length>1, position:"bottom" },
      tooltip:{callbacks:{label:function(c){return isMoney?[c.dataset.label+": "+money(c.parsed.y),usd(c.parsed.y)+" · "+EXCHANGE_RATE_META.source]:c.dataset.label+": "+fmt(c.parsed.y);}}} },
      scales:{ y:{ grid:{color:gridColor()}, ticks:{ callback:isMoney?function(v){return moneyCompact(v);}:undefined } }, x:{ grid:{display:false} } } }
  });
}

/* ═══════════════ RENDER: TỔNG QUAN ═══════════════ */
function renderOverview(rows){
  var A=aggregate(rows), prevRows=previousPeriodRows(), prevA=aggregate(prevRows);
  var byAgent=groupAgg(rows,function(r){return r.a;});
  var active=byAgent.filter(function(g){return g.r>0;});
  var prevActive=groupAgg(prevRows,function(r){return r.a;}).filter(function(g){return g.r>0;});
  var created=allAgents().length;
  var byUnit=groupAgg(rows.filter(function(r){return r.d&&r.d!=="—";}),function(r){return r.d;}).filter(function(g){return g.r>0;});
  var prevUnits=groupAgg(prevRows.filter(function(r){return r.d&&r.d!=="—";}),function(r){return r.d;}).filter(function(g){return g.r>0;});
  var accounts=filterAccounts(), activeUsers=accounts.filter(function(u){return u.active&&!u.disabled;}).length;
  var inactiveUsers=accounts.length-activeUsers;
  var costPerUser=activeUsers?A.cost/activeUsers:0;
  var topAgent=active.slice().sort(function(a,b){return b.cost-a.cost;})[0];
  var topRequest=active.slice().sort(function(a,b){return b.r-a.r;})[0];
  var topUnit=byUnit.slice().sort(function(a,b){return b.cost-a.cost;})[0];
  var topError=active.slice().sort(function(a,b){return b.er-a.er;})[0];

  /* Scorecard dùng chung một format số: nghìn / triệu / tỷ viết bằng chữ,
     đơn vị nằm trong ngoặc ở tên thẻ nên giá trị không lặp lại đơn vị. */
  set("m-ov-agents",active.length+"/"+created);
  set("m-ov-units",fmtCompactNum(byUnit.length));
  set("m-ov-users",fmtCompactNum(activeUsers));
  setWithTitle("m-ov-requests",fmtCompactNum(A.r),fmt(A.r)+" request");
  setWithTitle("m-ov-tokens",fmtCompactNum(A.tokens),fmtTokFull(A.tokens));
  /* Thẻ tiền nói độ tin CỦA KỲ ĐANG CHỌN, không của toàn bộ dữ liệu. Tỷ lệ suy ra
     lệch rất mạnh theo ngày - 22/228 ngày có hơn một nửa là suy ra, ngày mới nhất
     luôn 100% - nên một con số trung bình cả kỳ sẽ nói dối về chính kỳ đang xem.
     Đúng cái bẫy đã mắc 17/08: tính tỷ lệ trên 224 ngày trong khi thẻ chỉ hiện kỳ
     được chọn, báo 28% cạnh một con số mà tỷ lệ thật là 32%. `A` ở đây là
     aggregate() của CHÍNH tập dòng đang hiện, nên không lệch được. */
  setWithTitle("m-ov-cost",
    (costIsMarked(A.cost, A.costEst) ? "≈ " : "") + usageCompact(A.cost),
    money(A.cost) + " · " + costProvenanceTitle(A.cost, A));
  setWithTitle("m-ov-costuser",usageCompact(costPerUser),money(costPerUser)+" / user hoạt động");
  set("m-ov-error",A.er.toFixed(1).replace(".",","));

  renderSingleDelta("d-ov-agents",active.length,prevActive.length,fmt);
  renderSingleDelta("d-ov-units",byUnit.length,prevUnits.length,fmt);
  renderSingleDelta("d-ov-users",activeUsers,0,fmt);
  renderSingleDelta("d-ov-requests",A.r,prevA.r,fmtCompactNum);
  renderSingleDelta("d-ov-tokens",A.tokens,prevA.tokens,fmtCompactNum);
  renderSingleDelta("d-ov-cost",A.cost,prevA.cost,moneyCompact);
  renderSingleDelta("d-ov-costuser",costPerUser,0,moneyCompact);
  renderSingleDelta("d-ov-error",A.er,prevA.er,function(v){return v.toFixed(1)+"%";});

  set("i-ov-agents",Math.max(0,created-active.length)+" agent chưa hoạt động trong kỳ.");
  set("i-ov-units",topUnit?esc(topUnit.key)+" dẫn đầu, chiếm "+pct(topUnit.cost,A.cost).toFixed(0)+"% mức sử dụng.":"Chưa có phòng ban phát sinh sử dụng.");
  set("i-ov-users",fmt(activeUsers)+" đang dùng · "+fmt(inactiveUsers)+" tài khoản không hoạt động.");
  set("i-ov-requests",topRequest?esc(topRequest.key)+" chiếm "+pct(topRequest.r,A.r).toFixed(0)+"% request.":"Chưa có request trong kỳ.");
  set("i-ov-tokens",topAgent?esc(topAgent.key)+" chiếm "+pct(topAgent.tokens,A.tokens).toFixed(0)+"% token.":"Chưa có token trong kỳ.");
  set("i-ov-cost",topAgent?esc(topAgent.key)+" chiếm "+pct(topAgent.cost,A.cost).toFixed(0)+"% tổng mức sử dụng.":"Chưa phát sinh mức sử dụng.");
  set("i-ov-costuser","Bình quân trên "+fmt(activeUsers)+" user hoạt động.");
  /* Nói thẳng phần suy ra ra màn hình, không chỉ giấu trong tooltip: đây là thẻ
     tiền chính, và người đọc báo cáo hiếm khi trỏ chuột. */
  if(A.costEst>0)
    set("i-ov-cost", "Trong đó " + moneyCompact(A.costEst) + " ("
      + (A.cost>0 ? (100*A.costEst/A.cost).toFixed(0) : "100")
      + "%) suy từ bảng giá vì chưa có hoá đơn.");
  set("i-ov-error",topError&&topError.er>0?esc(topError.key)+" cao nhất: "+topError.er.toFixed(1)+"%.":"Không ghi nhận lỗi.");

  set("ov-cost-total",moneyCompact(A.cost));
  set("ov-token-total",fmtTok(A.tokens));
  set("ov-request-total",fmtCompactNum(A.r)+" request");
  /* Không request nào thì KHÔNG có tỷ lệ để mà hiện. `aggregate()` trả `er = 0`
     khi `r = 0`, nên "100-er" sẽ ra 100% - một kỳ không ai gọi trông thành một kỳ
     hoàn hảo. Cùng lý do với chuỗi `success` trong trendSeries(). */
  set("ov-success-total",A.r?fmtDecimal(100-A.er,2)+"% thành công":"Chưa có request nào");
  set("ov-success-value",(100-A.er).toFixed(1)+"%");

  renderOverviewDetail(rows,active);
  renderOverviewAlerts(A,rows,active,topAgent,inactiveUsers);
}

/* Bảng chi tiết: mỗi PHÒNG BAN là một record; các phòng ban dùng chung một
   project (AI Agent) chia sẻ một ô "AI Agent" đã merge bằng rowspan.
   Thứ tự cột giữ nguyên: AI Agent · Phòng ban · User · Request · Token ·
   Mức độ sử dụng · Tỷ lệ lỗi · Mức độ ổn định. */
function deptDisplayName(dept){
  var unit=unitOf(dept), name=unit?unit.name:String(dept==null?"":dept).trim();
  return (name && name!=="—") ? name : "Chưa gán phòng ban";
}
/* Chia lưu lượng của MỘT agent xuống các phòng ban của nó.

   Agent chạy bằng tài khoản dịch vụ (sáu project Google Cloud Console): không có
   gì để chia. Cả agent là một "phòng ban" mang chính tên nó, và các dòng usage đã
   mang đúng nhãn đó rồi — api.js primaryUnit() đặt.

   Hai agent có người thật (Trợ lý ảo Ralli, Trợ Lý Ảo Hợp Đồng): /api/usage KHÔNG
   có chiều đơn vị, mọi dòng của một agent mang CÙNG một nhãn. Đó là gốc của lỗi
   được báo — primaryUnit() cũ chọn hàng kỹ thuật level 0 nên nhãn ấy là "Chưa quy
   được", dù hai agent này có cây tổ chức đầy đủ. Sửa nhãn xong thì nó thành "Toàn
   công ty": đúng hơn, nhưng vẫn chưa phải phòng ban.

   Chiều phòng ban THẬT nằm ở /api/usage-by-account, mỗi dòng có unit_id.

   TỪ 03/09/2026 NÓ PHỦ CẢ 8 AGENT, không còn chỉ những nguồn biết người dùng.
   Câu cũ ở đây viết *"chỉ những nguồn biết người dùng (ref_source.knows_user)"* —
   đúng cho tới 02/09, sai từ 03/09: endpoint nay đọc `usage_by_account_resolved`,
   1.453 dòng / 60 tài khoản / 8 agent.

   Phần CHƯA QUY ĐƯỢC vẫn đứng RIÊNG thành một hàng mang đúng tên đó, thay vì gán
   bừa cho một phòng ban nào — nhưng nay nó nhỏ hơn hẳn và ĐO ĐƯỢC: `kind` bằng
   'whole_agent' (1,7%) hoặc 'unattributed' (0,5%), tổng 2,2%. Sáu agent dịch vụ
   KHÔNG còn nằm trong phần đó: chúng quy về đúng một tài khoản `svc.<code>`.

   Request, Token và User của mỗi hàng đều là SỐ ĐO. Riêng TIỀN thì chia theo tỷ
   lệ request và có dấu xấp xỉ: hoá đơn Google ghi theo project chứ không ghi
   phòng ban, nên mọi cách chia tiền xuống phòng ban đều là suy luận. */
function overviewDeptRows(agentKey, agentRows){
  var theoNhan=groupAgg(agentRows,function(r){ return deptDisplayName(r.d); });
  if(isServiceAgent(agentKey) || !REAL_BY_ACCOUNT.length) return theoNhan;

  var g=aggregate(agentRows);
  var theoPhong={}, order=[], doDuoc={r:0,ti:0,to:0};
  filterAccounts().forEach(function(u){
    var b=u.byAgent&&u.byAgent[agentKey];
    if(!b||!num(b.req)) return;
    var goc=reportingRootOf(u.unitId);
    var ten=goc?goc.name:UNATTRIBUTED_UNIT_NAME;
    var o=theoPhong[ten];
    if(!o){ o=theoPhong[ten]={r:0,ti:0,to:0,u:0}; order.push(ten); }
    o.r+=num(b.req); o.ti+=num(b.ti); o.to+=num(b.to); o.u++;
    doDuoc.r+=num(b.req); doDuoc.ti+=num(b.ti); doDuoc.to+=num(b.to);
  });
  // Không quy được dòng nào về phòng ban thì giữ nguyên cách cũ — đừng dựng một
  // bảng chỉ có mỗi hàng "Chưa quy được" rồi gọi đó là cải tiến.
  if(!order.length) return theoNhan;

  // Phần agent có mà số đo theo người chưa với tới. Kẹp ở 0: hai nguồn đếm hai
  // tập khác nhau nên về nguyên tắc có thể lệch, và một hàng ÂM thì vô nghĩa.
  var conLai={r:Math.max(0,num(g.r)-doDuoc.r),
              tokens:Math.max(0,num(g.tokens)-(doDuoc.ti+doDuoc.to))};

  function hang(ten, r, tokens, soUser, laConLai){
    var phan=num(g.r)>0 ? r/num(g.r) : 0;
    return {key:ten, u:soUser, r:r, ti:0, to:0, tokens:tokens,
            cost:num(g.cost)*phan, costEst:num(g.costEst)*phan,
            costEstNoBilling:num(g.costEstNoBilling)*phan,
            costEstLate:num(g.costEstLate)*phan,
            costRowsInv:num(g.costRowsInv),
            // Tỷ lệ lỗi đo ở mức (ngày, agent), KHÔNG có chiều phòng ban. Dùng
            // chung con số của agent và nói rõ trong tooltip, thay vì bịa ra một
            // tỷ lệ riêng cho từng phòng.
            er:num(g.er), erKeAgent:true,
            tienChiaTheoRequest:true, laChuaQuyDuoc:!!laConLai};
  }

  var out=order.sort(function(a,b){ return theoPhong[b].r-theoPhong[a].r; })
    .map(function(ten){
      var o=theoPhong[ten];
      return hang(ten, o.r, o.ti+o.to, o.u, ten===UNATTRIBUTED_UNIT_NAME);
    });
  if(conLai.r>0 || conLai.tokens>0){
    var da=out.filter(function(x){ return x.key===UNATTRIBUTED_UNIT_NAME; })[0];
    if(da){ da.r+=conLai.r; da.tokens+=conLai.tokens; }
    else out.push(hang(UNATTRIBUTED_UNIT_NAME, conLai.r, conLai.tokens, 0, true));
  }
  return out;
}
function renderOverviewDetail(rows,active){
  var agents=active.slice().sort(function(a,b){return b.cost-a.cost;});
  var html="", totals={u:0,r:0,tokens:0,cost:0,erW:0,costEst:0,costRowsInv:0,costEstNoBilling:0,costEstLate:0};
  agents.forEach(function(g){
    var agentRows=rows.filter(function(r){return r.a===g.key;});
    var byDept=overviewDeptRows(g.key,agentRows)
      .sort(function(a,b){
        // "Chưa quy được" luôn xuống cuối: nó không phải phòng ban, để nó đứng
        // đầu bảng thì đọc như thể nó là phòng dùng nhiều nhất.
        if(!!a.laChuaQuyDuoc!==!!b.laChuaQuyDuoc) return a.laChuaQuyDuoc?1:-1;
        return (b.cost-a.cost)||(b.r-a.r)||a.key.localeCompare(b.key,"vi");
      });
    if(!byDept.length) return;
    totals.u+=g.u; totals.r+=g.r; totals.tokens+=g.tokens; totals.cost+=g.cost; totals.erW+=g.er*g.r;
    // Cộng cả phần suy ra: quên hai dòng này thì hàng Tổng cộng KHÔNG BAO GIỜ
    // mang dấu `≈`, và đó là kiểu hỏng không ném lỗi - chỉ im lặng nói thiếu.
    totals.costEst+=num(g.costEst); totals.costRowsInv+=num(g.costRowsInv);
    totals.costEstNoBilling+=num(g.costEstNoBilling);
    totals.costEstLate+=num(g.costEstLate);
    var usingDepts=byDept.filter(function(d){return d.r>0;}).length;
    var agentCell="<td class='detail-agent-cell' rowspan='"+byDept.length+"'>"+
      "<span class='detail-agent-name'>"+esc(g.key)+"</span>"+
      "<span class='detail-agent-sub'>"+fmt(usingDepts)+"/"+fmt(byDept.length)+" phòng ban đang dùng</span>"+
      "<span class='detail-agent-sub'>"+fmtCompactNum(g.r)+" request · "+moneyCompact(g.cost)+"</span></td>";
    byDept.forEach(function(d,i){
      // Phòng ban đã được cấp quyền nhưng chưa gọi request nào: vẫn giữ đúng
      // một dòng theo yêu cầu, chỉ làm mờ để không lấn át các dòng có số liệu.
      var idle=d.r<=0&&d.tokens<=0&&d.cost<=0, stable=Math.max(0,100-d.er);
      var cls=(i===0?"detail-group-start":"")+(idle?" detail-idle":"");
      html+="<tr class='"+cls.trim()+"'>"+
        (i===0?agentCell:"")+
        "<td><span class='detail-dept-name'>"+esc(d.key)+"</span>"+
          (idle?"<span class='detail-idle-tag'>chưa phát sinh</span>":"")+"</td>"+
        "<td class='num'>"+fmt(d.u)+"</td>"+
        "<td class='num' title='"+esc(fmt(d.r)+" request")+"'>"+fmtCompactNum(d.r)+"</td>"+
        "<td class='num' title='"+esc(fmtTokFull(d.tokens))+"'>"+fmtCompactNum(d.tokens)+"</td>"+
        "<td class='num cost' title='"+esc(
            (d.tienChiaTheoRequest
              ? "Chia theo tỷ lệ request của phòng ban. Hoá đơn Google ghi theo"
                +" project chứ không ghi phòng ban, nên con số này là SUY RA. "
              : "")+costProvenanceTitle(d.cost,d))+"'>"+
          (d.tienChiaTheoRequest||costIsMarked(d.cost,d.costEst)?"≈ ":"")+moneyCompact(d.cost)+"</td>"+
        "<td class='num"+(d.er>=2?" text-red":"")+"'"+
          (d.erKeAgent?" title='"+esc("Tỷ lệ lỗi đo ở mức (ngày, agent), không có"
            +" chiều phòng ban — đây là tỷ lệ của cả agent.")+"'":"")+">"+
          d.er.toFixed(1)+"%</td>"+
        // Không có request thì không có cơ sở đo độ ổn định — để trống thay vì 100%.
        "<td>"+(d.r>0
          ?"<div class='overview-success-cell'><span><i style='width:"+stable.toFixed(1)+"%'></i></span><b>"+stable.toFixed(1)+"%</b></div>"
          :"<span class='subtle'>—</span>")+"</td>"+
      "</tr>";
    });
  });
  if(html){
    var totalEr=totals.r?totals.erW/totals.r:0, totalStable=Math.max(0,100-totalEr);
    html+="<tr class='detail-total-row'><td>Tổng cộng</td><td>"+fmt(agents.length)+" AI Agent</td>"+
      "<td class='num'>"+fmt(totals.u)+"</td><td class='num'>"+fmtCompactNum(totals.r)+"</td>"+
      "<td class='num' title='"+esc(fmtTokFull(totals.tokens))+"'>"+fmtCompactNum(totals.tokens)+"</td>"+
      "<td class='num cost' title='"+esc(costProvenanceTitle(totals.cost,totals))+"'>"+(costIsMarked(totals.cost,totals.costEst)?"≈ ":"")+moneyCompact(totals.cost)+"</td>"+"<td class='num'>"+totalEr.toFixed(1)+"%</td>"+
      "<td><div class='overview-success-cell'><span><i style='width:"+totalStable.toFixed(1)+"%'></i></span><b>"+totalStable.toFixed(1)+"%</b></div></td></tr>";
  }
  set("ov-detail-tbody",html||emptyRow(8));
}
function renderOverviewAlerts(A,rows,active,topAgent,inactiveUsers){
  var configured=configuredBudgetSummary(rows);
  var budgetPct=pct(configured.cost,configured.budget), budgetThreshold=reachedBudgetThreshold(budgetPct), alerts=[];
  alerts.push({
    cls:budgetPct>=100?"danger":budgetPct>=90?"warning":"info",
    icon:budgetPct>=100?"⚠":"ℹ",
    title:budgetThreshold?"Ngân sách đã chạm mốc "+budgetThreshold+"%":"Theo dõi ngân sách agent",
    text:"Đã sử dụng "+budgetPct.toFixed(0)+"% ngân sách đã cấu hình ("+money(configured.cost)+" / "+money(configured.budget)+"). Cảnh báo tại 50%, 90% và 100%."
  });
  configured.agents.filter(function(item){return reachedBudgetThreshold(item.rate)>0;})
    .sort(function(a,b){return b.rate-a.rate;})
    .forEach(function(item){
      var threshold=reachedBudgetThreshold(item.rate);
      alerts.push({
        cls:item.rate>=100?"danger":item.rate>=90?"warning":"info",
        icon:item.rate>=100?"⚠":"●",
        title:item.rate>=100?item.agent+" đã vượt ngân sách":item.agent+" chạm mốc "+threshold+"%",
        text:"Đã dùng "+item.rate.toFixed(0)+"% ("+money(item.cost)+" / "+money(item.budget)+")."
      });
    });
  var errTop=active.slice().sort(function(a,b){return b.er-a.er;})[0];
  alerts.push({
    cls:errTop&&errTop.er>=2?"danger":errTop&&errTop.er>0?"warning":"ok",
    icon:errTop&&errTop.er>0?"⚠":"✓",
    title:errTop&&errTop.er>0?"Agent có tỷ lệ lỗi cao":"Tỷ lệ lỗi ổn định",
    text:errTop&&errTop.er>0?errTop.key+" đang ở mức "+errTop.er.toFixed(1)+"%.":"Mức độ ổn định toàn hệ thống đạt "+(100-A.er).toFixed(1)+"%."
  });
  alerts.push({
    cls:topAgent&&pct(topAgent.cost,A.cost)>=40?"warning":"info",icon:"●",title:"Mức tập trung sử dụng",
    text:topAgent?topAgent.key+" chiếm "+pct(topAgent.cost,A.cost).toFixed(0)+"% tổng mức sử dụng.":"Chưa có dữ liệu sử dụng."
  });
  alerts.push({
    cls:inactiveUsers>0?"info":"ok",icon:"👤",title:"Tài khoản không hoạt động",
    text:fmt(inactiveUsers)+" tài khoản chưa phát sinh hoạt động; xem danh sách tại tab User."
  });
  set("ov-alerts",alerts.map(function(a){
    return "<div class='overview-alert-item "+a.cls+"'><span class='overview-alert-icon'>"+a.icon+"</span><div><b>"+esc(a.title)+"</b><p>"+esc(a.text)+"</p></div><time>"+dayLabel(state.range.end)+"</time></div>";
  }).join(""));
}
function chartsOverview(rows){
  var A=aggregate(rows), tl=trendSeries();
  mkOverviewLine("c-ov-cost-trend",tl.labels,tl.cost,"money","#38bdf8");
  mkOverviewLine("c-ov-token-trend",tl.labels,tl.tokens,"tokens","#84cc16");
  mkOverviewLine("c-ov-request-trend",tl.labels,tl.requests,"number","#a78bfa");
  mkOverviewLine("c-ov-success-trend",tl.labels,tl.success,"percent","#22c55e");
  mkDonut("c-ov-success",["Trả kết quả tốt","Lỗi"],[Math.max(0,100-A.er),Math.max(0,A.er)],null,function(v){return v.toFixed(1)+"%";},["#22c55e","#ef4444"]);
  var byAgent=groupAgg(rows,function(r){return r.a;}).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;}).slice(0,8);
  mkDonut("c-ov-agent-share",byAgent.map(function(g){return g.key;}),byAgent.map(function(g){return g.cost;}),"lg-ov-agent-share",moneyCompact);
  /* THEO REQUEST, không theo tiền (biên bản 25/07, mục 2.3). Lý do đổi: tiền của
     một phòng ban là số SUY RA — 28,2% tiền trên dashboard nhân từ `ref_price` chứ
     không từ hoá đơn, và phần suy ra dồn vào ít phòng ban. Xếp hạng đơn vị bằng một
     đại lượng suy ra thì thứ hạng đổi theo chỗ hoá đơn về sớm hay muộn. Request thì
     đếm được trực tiếp, không phụ thuộc hoá đơn. */
  var byUnit=groupAgg(rows.filter(function(r){return r.d&&r.d!=="—";}),function(r){return r.d;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.r-a.r;}).slice(0,8);
  mkBar("c-ov-unit-req",byUnit.map(function(g){return g.key;}),byUnit.map(function(g){return g.r;}),{horizontal:true,colors:"#a78bfa"});
  buildOverviewWeekHeatmap();
}
function mkOverviewLine(id,labels,data,kind,color){
  var tick=kind==="money"?function(v){return moneyCompact(v);}:kind==="tokens"?function(v){return fmtTokShort(v);}:
    kind==="percent"?function(v){return fmtDecimal(v,0)+"%";}:function(v){return fmt(v);};
  chart(id,{
    type:"line",
    data:{labels:labels,datasets:[{data:data,borderColor:color,backgroundColor:color+"22",fill:true,tension:.34,borderWidth:2,pointRadius:data.length<=8?3:1.5,pointBackgroundColor:color}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){
      return kind==="money"?money(c.parsed.y):kind==="tokens"?fmtTokFull(c.parsed.y):
        kind==="percent"?fmtDecimal(c.parsed.y,2)+"% thành công":fmt(c.parsed.y)+" request";
    }}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:7}},y:{beginAtZero:true,grid:{color:gridColor()},ticks:{callback:tick,maxTicksLimit:5}}}}
  });
}
function buildOverviewWeekHeatmap(){
  var available=state.dayOrder.filter(function(d){return d>=state.range.start&&d<=state.range.end;});
  var endIso=available.length?available[available.length-1]:state.range.end;
  var end=parseISO(endIso), dates=[];
  var daysSinceMonday=(end.getUTCDay()+6)%7;
  var monday=addDays(end,-daysSinceMonday);
  for(var offset=0;offset<7;offset++){
    dates.push(toISO(addDays(monday,offset)));
  }
  var rowsByDate=dates.map(function(d){return applyFilters(state.days[d]||[]);});
  var agentTotals={};
  rowsByDate.forEach(function(dayRows){
    dayRows.forEach(function(r){if(r.a&&num(r.r)>0) agentTotals[r.a]=(agentTotals[r.a]||0)+num(r.r);});
  });
  var agents=Object.keys(agentTotals).sort(function(a,b){return agentTotals[b]-agentTotals[a];}).slice(0,7);
  var matrix=agents.map(function(agent){
    return rowsByDate.map(function(dayRows){
      return dayRows.reduce(function(total,r){return total+(r.a===agent?num(r.r):0);},0);
    });
  });
  var weekdays=["CN","T2","T3","T4","T5","T6","T7"];
  var labels=dates.map(function(d){return weekdays[parseISO(d).getUTCDay()]+" "+dayLabel(d);});
  buildHeatmap("heatmap-ov-week",labels,agents,matrix);
  var table=document.getElementById("heatmap-ov-week");
  if(table){
    Array.prototype.forEach.call(table.querySelectorAll("tbody tr"),function(tr,ri){
      Array.prototype.forEach.call(tr.querySelectorAll(".hm-cell"),function(td,ci){
        td.title=(agents[ri]||"Agent")+" · "+(labels[ci]||"Ngày")+": "+fmt((matrix[ri]||[])[ci]||0)+" request";
      });
    });
  }
}
function trendSeries(){
  var dates=state.dayOrder.filter(function(d){return d>=state.range.start&&d<=state.range.end;});
  var aggs=dates.map(function(d){return aggregate(applyFilters(state.days[d]||[]));});
  var costData=aggs.map(function(a){return +a.cost.toFixed(4);});
  return {
    dates:dates,labels:dates.map(dayLabel),data:costData,cost:costData,
    tokens:aggs.map(function(a){return a.tokens;}),
    requests:aggs.map(function(a){return a.r;}),
    /* NULL chứ không phải 100 cho ngày không có request nào. `aggregate()` trả
       `er = 0` khi `r = 0`, nên 100-er sẽ ra 100% - một ngày không ai gọi trông
       thành một ngày hoàn hảo. Chart.js vẽ `null` thành chỗ đứt, đúng nghĩa
       "không đo được". */
    success:aggs.map(function(a){return a.r?+(100-a.er).toFixed(2):null;})
  };
}

/* ═══════════════ RENDER: PHÒNG BAN & USER ═══════════════ */
/* Gom usage row theo đơn vị đã chuẩn hoá (không theo chuỗi r.d thô nữa). */
function groupRowsByUnit(rows){
  var map={};
  (rows||[]).forEach(function(r){
    var unit=unitOfRow(r);
    if(!unit||isExcludedUnit(unit)) return;
    var g=map[unit.id]=map[unit.id]||{unit:unit,rows:[],agents:{}};
    g.rows.push(r);
    if(r.a) g.agents[r.a]=1;
  });
  return map;
}
/* Tài khoản thuộc một đơn vị và toàn bộ cây con của nó, đã áp bộ lọc toàn cục. */
function accountsUnderUnit(unitId, pool){
  var ids={};
  [unitId].concat(unitDescendants(unitId).map(function(u){return u.id;})).forEach(function(i){ ids[i]=true; });
  return (pool||filterAccounts()).filter(function(u){ return ids[u.unitId]; });
}
/* Ô tỷ lệ áp dụng: dùng đúng ngưỡng đã cấu hình, không đặt ngưỡng mới.
   Thiếu mẫu số => nêu rõ chưa có dữ liệu, không suy ra 100%, không chia cho zero. */
/* `outside` = tài khoản CÓ request nhưng KHÔNG nằm trong danh bạ, nên không thuộc
   mẫu số. Không cộng vào tử số - cộng thì tỷ lệ vượt 100%, đúng lỗi vừa sửa - nhưng
   phải NÓI RA trong tooltip: hàng 'Chưa quy được' hiện 0/1 · 0% cạnh 2.544 request,
   và nếu không giải thích thì con số đúng đó vẫn đọc ra như một con số sai.
   Cùng khái niệm với cột `outside_directory` mà backend/store.py adoption() trả về. */
function adoptionCell(activeCount, provisioned, outside){
  if(provisioned==null||provisioned<=0) return "<td class='num'><span class='metric-na'>—</span></td>";
  var rate=activeCount/provisioned*100;
  var cls=rate<INSIGHT_THRESHOLDS.adoptionCritical?"text-red":
    (rate<INSIGHT_THRESHOLDS.adoptionWarning?"text-orange":"text-green");
  var title=fmt(activeCount)+" tài khoản có request / "+fmt(provisioned)+" tài khoản được cấp";
  if(outside>0) title+=" · thêm "+fmt(outside)+" tài khoản có request nhưng không có"
    +" trong danh bạ nên không tính vào tỷ lệ này";
  return "<td class='num "+cls+"' title='"+esc(title)+"'>"+
    fmt(activeCount)+"/"+fmt(provisioned)+" · "+rate.toFixed(0)+"%</td>";
}
function naCell(){ return "<td class='num'><span class='metric-na'>—</span></td>"; }
function sortAccounts(list){
  return list.slice().sort(function(a,b){ return num(b.req)-num(a.req)||a.user.localeCompare(b.user); });
}
function usageUnderUnit(unitId, rows){
  var ids={};
  [unitId].concat(unitDescendants(unitId).map(function(u){return u.id;})).forEach(function(id){ids[id]=true;});
  var scoped=(rows||[]).filter(function(r){var u=unitOfRow(r);return u&&ids[u.id];});
  var agents={}; scoped.forEach(function(r){if(r.a)agents[r.a]=1;});
  return {agg:aggregate(scoped),agents:Object.keys(agents),hasRows:scoped.length>0};
}

/* ═══════════════ CÂY CHI TIẾT PHÒNG BAN → TÀI KHOẢN ═══════════════
   Gộp bảng "Chi tiết theo phòng ban" và bảng "Người dùng TLA HD" thành MỘT cây,
   dùng đúng cách trình bày của ma trận Phòng ban × Project ở tab Agents:
   nhãn cấp, đường nối cây, dải màu theo phòng ban gốc, dòng meta dưới tên.
   Khác ma trận ở chỗ các cột là chỉ số usage + quota chứ không phải từng agent. */
function deptSearching(){ return !!String(state.deptSearch||"").trim(); }
function deptIsOpen(id){ return deptSearching() || !!(state.deptExpanded||{})[id]; }
function deptPool(){
  var pool=filterAccounts();
  var q=String(state.deptSearch||"").trim().toLowerCase();
  if(!q) return pool;
  return pool.filter(function(u){
    return [u.user,u.n,u.login,u.d,unitName(u.unitId)].join(" ").toLowerCase().indexOf(q)>=0;
  });
}
/* Giữ lại đơn vị nếu nó có tài khoản, có đơn vị con được giữ, có usage thật trong kỳ,
   hoặc có số tài khoản được cấp. Nhờ vậy phòng ban phát sinh usage nhưng chưa có
   tài khoản Ralli nào vẫn hiện, thay vì biến mất khỏi bảng. */
function accountsByUnitIndex(pool){
  var m={};
  (pool||[]).forEach(function(u){ (m[u.unitId]||(m[u.unitId]=[])).push(u); });
  return m;
}
function deptTreeNode(unit, byUnit, usageIds){
  if(isExcludedUnit(unit)) return null;
  var kids=unitChildren(unit.id).map(function(k){ return deptTreeNode(k,byUnit,usageIds); })
    .filter(function(n){ return !!n; });
  kids.sort(function(a,b){ return a.unit.name.localeCompare(b.unit.name,"vi"); });
  var direct=byUnit[unit.id]||[];
  var accounts=[];
  kids.forEach(function(n){ accounts=accounts.concat(n.accounts); });
  accounts=accounts.concat(direct);
  var keep=accounts.length>0||kids.length>0||usageIds[unit.id]||provisionedOf(unit.id)!=null;
  if(!keep) return null;
  return {unit:unit, kids:kids, direct:sortAccounts(direct), accounts:accounts};
}
/* Tài khoản gắn THẲNG vào một cấp gom ("Toàn công ty", "Tổng công ty Rạng Đông").

   reportingRoots() đi XUYÊN QUA hai cấp đó để cấp 1 của bảng là phòng ban thật —
   đúng ý, nhưng nó cũng làm những tài khoản treo ngay trên chính hai cấp ấy không
   còn nhánh nào để đứng vào. Đo 30/08/2026 trên database thật: 74 tài khoản thuộc
   "Tổng công ty Rạng Đông" và 10 thuộc "Toàn công ty" — 84/937 — KHÔNG hiện ở bất
   kỳ hàng nào của cây, trong khi thẻ đếm phía trên vẫn nói 937. Cây ra đúng 853
   hàng tài khoản, và 853 + 84 = 937.

   Nên cho chúng một nhánh riêng ở cấp 1 mang đúng tên cấp gom, thay vì gán bừa vào
   một phòng ban nào đó — database nói chúng thuộc cấp gom thì bảng phải nói thế.

   HÀNG NÀY KHÔNG ĐƯỢC TRA usageIndex HAY provisionedOf. Cả hai đều cộng dồn lên
   cấp cha, nên với "Tổng công ty Rạng Đông" chúng trả về số của TOÀN BỘ công ty;
   đặt cạnh các phòng ban là cộng đôi cả bảng — đúng thứ mà reportingRoots() sinh
   ra để tránh. Cờ ownAccountsOnly bắt deptRowHtml tính từ chính tài khoản trực
   thuộc. */
function aggregateDirectNodes(byUnit){
  var out=[];
  (function xet(list){
    list.forEach(function(u){
      if(!isReportAggregate(u)) return;
      var direct=(byUnit[u.id]||[]).slice();
      if(direct.length) out.push({unit:u, kids:[], direct:sortAccounts(direct), accounts:direct});
      xet(unitChildren(u.id));
    });
  })(unitRoots());
  return out;
}
/* Gốc báo cáo của một đơn vị: tổ tiên đầu tiên KHÔNG phải cấp gom — đúng cấp mà
   reportingRoots() coi là cấp 1 của bảng. Trả null khi không có phòng ban thật
   nào trên đường đi: đơn vị nằm THẲNG trên cấp gom, hoặc là sọt "Chưa quy được". */
function reportingRootOf(unitId){
  var duong=unitPath(unitId);
  for(var i=0;i<duong.length;i++){
    if(isUnattributedUnit(duong[i])) return null;
    if(!isReportAggregate(duong[i])) return duong[i];
  }
  return null;
}

/* XẾP HẠNG PHÒNG BAN THEO SỐ ĐO CÓ CHIỀU ĐƠN VỊ.

   Không dùng `rows` (/api/usage) được: bảng đó KHÔNG có cột đơn vị. api.js gán
   mỗi dòng cho "đơn vị chính" của agent, mà primaryUnit() chọn đơn vị có level
   nhỏ nhất — với mọi agent đó đều là một hàng KỸ THUẬT. Sáu agent rơi vào
   "Đơn vị sử dụng ..." (đã nằm trong EXCLUDED_DEPARTMENTS), còn Ralli và TLA Hợp
   Đồng rơi vào "Chưa quy được" (level 0). Kết quả đo 30/08/2026: groupRowsByUnit()
   trả về ĐÚNG MỘT nhóm, tên "Chưa quy được", 2.299 request. Nói cách khác thẻ
   "Phòng năng suất nhất" chưa bao giờ nêu tên một phòng ban thật.

   Chiều đơn vị thật nằm ở /api/usage-by-account: mỗi dòng mang unit_id, và
   applyRealAccountUsage() đã gộp sẵn vào từng tài khoản. Cộng theo gốc báo cáo là
   ra bảng xếp hạng đúng — cùng nguồn với cây bên dưới nên hai chỗ không nói ngược
   nhau. Tài khoản không quy được về phòng ban nào (sọt "Chưa quy được", hoặc gắn
   thẳng vào cấp gom) bị bỏ ra: chúng không phải phòng ban, đúng như tên gọi. */
function deptRankByAccounts(pool){
  var theoGoc={};
  (pool||[]).forEach(function(u){
    var goc=reportingRootOf(u.unitId);
    if(!goc) return;
    var o=theoGoc[goc.id]||(theoGoc[goc.id]={unit:goc, r:0});
    o.r+=num(u.req);
  });
  return Object.keys(theoGoc).map(function(k){ return theoGoc[k]; })
    .sort(function(a,b){ return b.r-a.r; });
}
/* Đơn vị nào có usage thật trong kỳ (cộng dồn lên mọi cấp cha). */
function deptUsageUnitIds(rows){
  var ids={};
  (rows||[]).forEach(function(r){
    var u=unitOfRow(r);
    if(!u||isExcludedUnit(u)) return;
    unitPath(u.id).forEach(function(n){ ids[n.id]=true; });
  });
  return ids;
}
/* Usage cộng dồn theo unitId, dựng MỘT lần cho mỗi lần vẽ. Mỗi dòng usage được cộng
   vào chính đơn vị của nó và mọi cấp cha, nên tra cứu một hàng là O(1) thay vì quét
   lại toàn bộ sổ usage cho từng hàng — cây bung sâu vẫn bung tức thì. */
function buildDeptUsageIndex(rows){
  var map={};
  (rows||[]).forEach(function(r){
    var u=unitOfRow(r);
    if(!u||isExcludedUnit(u)) return;
    var rq=num(r.r), c=cost(r), ti=num(r.ti), to=num(r.to), ca=num(r.cached),
        erW=num(r.er)*rq;
    /* Tách phần tiền SUY RA khỏi phần lấy từ hoá đơn. `cost(r)` ước tính từ bảng
       giá bất cứ khi nào `r.cost` là NULL - tức những ngày hoá đơn chưa về - và
       trước 20/08/2026 ô hiện ra không phân biệt hai loại.
       Đo trên kỳ 19/07-17/08: Chatbot Contact Center $15,30 hoá đơn + $1,58 suy
       ra; Phân Loại Phản Hồi Tiếp Thị $6,02 + $2,68; Trợ lý ảo Ralli $0,00 hoá
       đơn + $2,51 suy ra - agent này chưa nối Google Billing nên TOÀN BỘ số tiền
       của nó là suy ra, mà màn hình không nói gì. */
    var est = (r.cost == null) ? c : 0;
    unitPath(u.id).forEach(function(n){
      var m=map[n.id]||(map[n.id]={r:0,ti:0,to:0,cached:0,tokens:0,cost:0,costEst:0,erW:0,rowCount:0,agentSet:{}});
      m.r+=rq; m.ti+=ti; m.to+=to; m.cached+=ca; m.cost+=c; m.costEst+=est;
      m.erW+=erW; m.rowCount++;
      if(r.a) m.agentSet[r.a]=1;
    });
  });
  Object.keys(map).forEach(function(id){
    var m=map[id];
    // Cùng lý do với aggregate(): token cache của hoá đơn nằm ngoài input.
    m.tokens=m.ti+m.to+m.cached; m.er=m.r?m.erW/m.r:0;
    m.agents=Object.keys(m.agentSet).length;
  });
  return map;
}
/* Chỉ số của MỘT hàng đơn vị. Ưu tiên usage thật; đơn vị không có dòng usage riêng
   (vùng/đội) thì lấy phần đã phân bổ xuống tài khoản, để tổng cấp con khớp cấp cha. */
function deptUnitMetrics(unit, usageIndex, accounts){
  // unit === null: người gọi CỐ Ý không tra chỉ mục cộng dồn, phải tính từ chính
  // danh sách tài khoản. Xem ghi chú ở aggregateDirectNodes().
  var hit=unit&&usageIndex&&usageIndex[unit.id];
  // Nhánh này có dòng usage thật. Tiền tính được, NHƯNG có thể trộn hoá đơn với
  // phần suy ra của những ngày hoá đơn chưa về - `costEst` nói phần đó bao nhiêu.
  if(hit&&hit.rowCount>0)
    return {agg:hit, agents:hit.agents, costKnown:true,
            costDerived: num(hit.costEst)>0, costEst: num(hit.costEst)};
  var a={r:0,ti:0,to:0,tokens:0,cost:0,er:0}, agentMap={}, rows=0, priced=0;
  (accounts||[]).forEach(function(u){
    a.r+=num(u.req); a.ti+=num(u.ti); a.to+=num(u.to);
    // Tiền SUY RA, đã tính sẵn ở mức dòng trong applyRealAccountUsage().
    a.cost+=num(u.costDerived);
    rows+=num(u.costRows); priced+=num(u.costRowsPriced);
    if(u.a&&u.a!=="—") agentMap[u.a]=1;
  });
  a.tokens=a.ti+a.to;
  /* Ba trạng thái, không phải hai:
       không lưu lượng nào          -> `0 ₫` ĐÚNG, đó là số thật
       mọi dòng đều tra được giá    -> con số suy ra
       có dòng KHÔNG tra được giá   -> `—`, vì con số sẽ thiếu đúng phần đó
     Nói `0 ₫` cạnh `525,9 nghìn token` là một khẳng định sai; mà nói một con số
     thiếu vài dòng cũng vậy, chỉ khó thấy hơn. */
  // Nhánh này KHÔNG có dòng hoá đơn nào - toàn bộ số tiền là suy từ bảng giá.
  return {agg:a, agents:Object.keys(agentMap).length,
          costDerived: rows>0, costEst: a.cost,
          costKnown: (rows>0 && priced===rows) || (a.r===0 && a.tokens===0)};
}
/* Ô tiền của một hàng đơn vị. Ba trạng thái, mỗi trạng thái một câu khác nhau.

   VÌ SAO TIỀN SUY RA PHẢI TỰ KHAI LÀ SUY RA
   Tiền của hàng đơn vị KHÔNG lấy từ hoá đơn được: hoá đơn Google tính theo
   project và không ghi ai gọi, nên /api/usage-by-account không có cột cost_usd.
   Con số ở đây nhân token với ref_price - mà ref_price lấy từ chính Cloud
   Billing Catalog của Google (`price_source='google'`), nên nó dựng lại rất sát:
   đối chiếu 965 dòng có cả hai vế cho lệch tổng −0,1% và lệch trung vị 0,0%.
   Sát đến vậy vẫn KHÔNG phải hoá đơn, và người đọc có quyền biết mình đang xem
   con số nào. Dấu `≈` và tooltip làm đúng việc đó.

   Trước 20/08/2026 ô này in `0 ₫` cho mọi phòng ban thật - xem deptUnitMetrics. */
function deptCostCell(m, g){
  if(!m.costKnown)
    return "<td class='num cost' title='"+esc("Chưa tính được: có dòng sử dụng mang model"
      +" không tra được đơn giá trong bảng giá")+"'><span class='metric-na'>—</span></td>";
  if(!m.costDerived)   // toàn bộ từ hoá đơn Google
    return "<td class='num cost' title='"+esc(usdReference(g.cost))+"'>"
      +moneyCompact(g.cost)+"</td>";
  /* Có phần suy ra. NÓI ĐỦ BAO NHIÊU, không chỉ nói "có" — với Trợ lý ảo Ralli
     thì toàn bộ là suy ra, với Chatbot Contact Center chỉ 9%. Hai chuyện rất
     khác nhau mà cùng một dấu `≈` sẽ làm chúng trông giống hệt. */
  var est=num(m.costEst), pct=g.cost>0 ? 100*est/g.cost : 100;
  return "<td class='num cost' title='"+esc(
      (pct>=99.5 ? "Toàn bộ số này SUY TỪ BẢNG GIÁ, không có dòng hoá đơn nào."
                 : "Trong số này có "+moneyCompact(est)+" ("+pct.toFixed(0)
                   +"%) suy từ bảng giá, phần còn lại lấy từ hoá đơn.")
      +" Hoá đơn Google tính theo project nên không chia được theo phòng ban. "
      +usdReference(g.cost))+"'>≈ "+moneyCompact(g.cost)+"</td>";
}
function deptQuotaCell(u){
  var c=accountCost(u), q=Math.max(0,Math.min(100,num(u.quotaPct)));
  var quotaUsd=q>0?c/(q/100):5;
  return "<td class='quota-cell'><div class='quota-gauge'><div class='quota-gauge-fill' style='width:"+q+
    "%;background:"+quotaColor(q)+"'></div></div><span class='quota-text'>"+q.toFixed(0)+"%</span>"+
    "<span class='quota-detail'>"+moneyCompact(c)+" / "+moneyCompact(quotaUsd)+"</span></td>";
}
/* Dòng meta dưới tên: đơn vị thì nói gồm bao nhiêu con, tài khoản thì nói login,
   vai trò và trạng thái — chính là hai cột đã có trong bảng Người dùng TLA HD cũ. */
function deptMeta(row){
  if(row.tier==="account"){
    var u=row.account, st=accountStatus(u);
    var roleClass=u.role==="Admin"?"badge-admin":"badge-user";
    return "<span class='dept-login'>"+esc(u.login||u.user)+"</span>"+
      "<span class='"+roleClass+"'>"+esc(u.role)+"</span>"+
      "<span class='user-status "+st.cls+"'>"+st.label+"</span>";
  }
  if(!row.accounts.length) return "<span class='mx-warn'>chưa có user</span>";
  var parts=[];
  if(row.unitCount) parts.push(row.unitCount+" đơn vị");
  parts.push(fmt(row.accounts.length)+" tài khoản");
  return parts.join(" · ");
}
function deptRowHtml(row, usageIndex, light){
  var cls="mx-row mx-d"+row.depth+" mx-"+row.tier+(row.open?" mx-open":"")+
    (row.expandable?" mx-clickable":"");
  var html="<tr class='"+cls+"'"+(row.expandable?" data-unit='"+esc(row.key)+"'":"")+">"+
    "<td class='mx-name' style='"+matrixNameStyle(row,light)+"'>"+
    (row.depth>1?"<i class='mx-elbow' style='left:"+matrixGuideX(row.depth-1)+"px'></i>":"")+
    "<span class='drill-caret"+(row.expandable?"":" drill-leaf")+"'>"+
      (row.expandable?(row.open?"▼":"▶"):"·")+"</span>"+
    "<span class='mx-text'><span class='mx-label'>"+
      "<span class='mx-tier mx-tier-"+row.tier+"'>"+MATRIX_TIER_LABEL[row.tier]+"</span>"+
      esc(row.label)+"</span>"+
    "<span class='mx-meta'>"+deptMeta(row)+"</span></span></td>";

  if(row.tier==="account"){
    var u=row.account, tokens=num(u.ti)+num(u.to), c=accountCost(u);
    html+="<td class='num'>"+(u.a&&u.a!=="—"?1:0)+"</td>"+
      adoptionCell(u.active&&!u.disabled?1:0,1)+
      "<td class='num'>"+fmt(u.req)+"</td>"+
      "<td class='num' title='"+esc(fmtTokFull(tokens))+"'>"+fmtCompactNum(tokens)+"</td>"+
      "<td class='num cost' title='"+esc(usdReference(c))+"'>"+moneyCompact(c)+"</td>"+
      naCell()+deptQuotaCell(u)+"</tr>";
    return html;
  }
  var m=deptUnitMetrics(row.ownAccountsOnly?null:row.unit,usageIndex,row.accounts), g=m.agg;
  /* TỬ SỐ VÀ MẪU SỐ PHẢI ĐẾM CÙNG MỘT TẬP.
     Mẫu số `DEPT_PROVISIONED` (rebuildRalliProvisioned) chỉ tính tài khoản
     `in_directory && !is_shared` - đúng định nghĩa "được cấp quyền". Tử số
     trước 20/08/2026 không lọc gì, nên tài khoản CÓ request mà KHÔNG có trong
     danh bạ vẫn vào tử số dù không có trong mẫu số: hàng 'Chưa quy được' hiện
     3/1 = 300%.
     backend/store.py adoption() không mắc lỗi này - nó tách hẳn
     `outside_directory` ra cột riêng thay vì cộng vào tử số. scripts/audit_db.py
     có phép kiểm "Ty le ap dung khong vuot 100%" và nó vẫn ĐẠT, vì phép kiểm đó
     soi database chứ không soi frontend. */
  var eligible=row.accounts.filter(function(u){return u.inDirectory&&!u.shared;});
  var activeCount=eligible.filter(function(u){return u.active&&!u.disabled;}).length;
  var outsideCount=row.accounts.filter(function(u){
    return u.active&&!u.disabled&&!(u.inDirectory&&!u.shared);
  }).length;
  // Cấp "Trực thuộc" chỉ gom tài khoản gắn thẳng vào đơn vị nên mẫu số là chính nó,
  // không phải số cấp phát của cả đơn vị cha.
  var prov=(row.tier==="direct"||row.ownAccountsOnly)?eligible.length:provisionedOf(row.unit.id);
  html+="<td class='num'>"+fmt(m.agents)+"</td>"+
    adoptionCell(activeCount,prov,outsideCount)+
    "<td class='num'>"+fmt(g.r)+"</td>"+
    "<td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtCompactNum(g.tokens)+"</td>"+
    deptCostCell(m, g)+
    "<td class='num"+(g.er>2?" text-red":"")+"'>"+num(g.er).toFixed(1)+"%</td>"+
    naCell()+"</tr>";
  return html;
}
function buildDeptRows(rows){
  // Dùng CHUNG gốc với ma trận tab Agents: bỏ qua hai hàng tổng hợp "Toàn công ty" và
  // "Tổng công ty Rạng Đông" để cấp 1 là phòng ban thật, không tốn hai cấp bung vô ích.
  var byUnit=accountsByUnitIndex(deptPool()), usageIds=deptUsageUnitIds(rows), out=[];
  var roots=reportingRoots();
  roots.forEach(function(root,i){
    var node=deptTreeNode(root,byUnit,usageIds);
    if(node) flattenMatrixTree(node,1,[],true,i,null,out,deptIsOpen);
  });
  aggregateDirectNodes(byUnit).forEach(function(node,j){
    var at=out.length;
    flattenMatrixTree(node,1,[],true,roots.length+j,null,out,deptIsOpen);
    // flattenMatrixTree đẩy hàng đơn vị TRƯỚC rồi mới tới các hàng tài khoản,
    // nên out[at] chính là hàng cấp gom vừa dựng.
    if(out[at]) out[at].ownAccountsOnly=true;
  });
  return out;
}
function renderDeptTree(rows){
  var table=document.getElementById("dept-tree-table"); if(!table) return;
  var light=currentTheme()==="light", treeRows=buildDeptRows(rows);
  var usageIndex=buildDeptUsageIndex(rows);
  var html="<thead><tr><th class='mx-th-name'>Phòng ban / Đơn vị · Tài khoản</th>"+
    "<th class='num'>AI Agent</th><th class='num'>User hoạt động / Tổng</th>"+
    "<th class='num'>Request</th><th class='num'>Token</th>"+
    "<th class='num'>Mức độ sử dụng</th><th class='num'>Tỷ lệ lỗi</th>"+
    "<th>Quota kỳ hiện tại</th></tr></thead><tbody>";
  if(!treeRows.length){
    html+="<tr><td class='mx-empty' colspan='8'>"+
      (deptSearching()?"Không có tài khoản nào khớp từ khóa.":"Chưa có phòng ban nào trong phạm vi đang lọc.")+
      "</td></tr>";
  }
  treeRows.forEach(function(row){ html+=deptRowHtml(row,usageIndex,light); });
  html+="</tbody>";
  table.innerHTML=html;
  bindDeptTree(table);
  var units=treeRows.filter(function(r){return r.kind==="unit";}).length;
  var accts=treeRows.filter(function(r){return r.tier==="account";}).length;
  set("dept-tree-note","Đang hiện "+fmt(units)+" hàng đơn vị và "+fmt(accts)+
    " hàng tài khoản. Bung thêm một cấp để thấy chi tiết sâu hơn.");
}
/* Toggle bung/thu. Trạng thái nằm trong state.deptExpanded nên giữ nguyên qua các lần
   đổi bộ lọc hoặc khoảng thời gian. Listener gắn một lần trên bảng. */
function bindDeptTree(table){
  if(table.getAttribute("data-dept-bound")) return;
  table.setAttribute("data-dept-bound","1");
  table.addEventListener("click", function(ev){
    var tr=ev.target&&ev.target.closest?ev.target.closest("tr[data-unit]"):null;
    if(!tr) return;
    var id=tr.getAttribute("data-unit");
    state.deptExpanded=state.deptExpanded||{};
    if(state.deptExpanded[id]) delete state.deptExpanded[id];
    else state.deptExpanded[id]=true;
    refreshDeptTree();
  });
}
/* Vẽ lại RIÊNG cây — bung một hàng không nên dựng lại toàn bộ biểu đồ của dashboard. */
function refreshDeptTree(){
  if(deptLastRows) renderDeptTree(deptLastRows);
  bindDeptToolbar();
  saveState();
}
function deptAnyOpen(){
  var open=state.deptExpanded||{};
  for(var k in open) if(Object.prototype.hasOwnProperty.call(open,k)) return true;
  return false;
}
function bindDeptToolbar(){
  var search=document.getElementById("dept-search");
  if(search){
    if(search.value!==(state.deptSearch||"")) search.value=state.deptSearch||"";
    if(!search.getAttribute("data-dept-bound")){
      search.setAttribute("data-dept-bound","1");
      search.oninput=function(){ state.deptSearch=this.value; refreshDeptTree(); };
    }
  }
  var btn=document.getElementById("dept-expand");
  if(btn){
    btn.textContent=deptAnyOpen()?"Thu gọn tất cả":"Mở tất cả phòng ban";
    btn.disabled=deptSearching();
    if(!btn.getAttribute("data-dept-bound")){
      btn.setAttribute("data-dept-bound","1");
      btn.onclick=function(){
        var opened=deptAnyOpen();
        state.deptExpanded={};
        if(!opened) reportingRoots().forEach(function(u){ state.deptExpanded[u.id]=true; });
        refreshDeptTree();
      };
    }
  }
}
function renderDepartments(rows){
  deptLastRows=rows;
  var pool=filterAccounts();
  /* "Năng suất nhất" = phòng tạo ra nhiều lượt dùng nhất, không xếp theo tiền.
     Xếp từ số đo theo tài khoản, KHÔNG từ `rows` — xem deptRankByAccounts(). */
  var xepHang=deptRankByAccounts(pool);
  var coHoatDong=xepHang.filter(function(x){ return x.r>0; });
  // Mẫu số là tổng của CHÍNH nguồn này. Lấy tổng của `rows` thì tử số và mẫu số
  // đếm hai tập khác nhau, và tỷ lệ hiện ra không nói về cái gì cả.
  var tongQuyDuoc=xepHang.reduce(function(t,x){ return t+x.r; },0);

  set("m-dep-count", coHoatDong.length);
  if(coHoatDong.length){
    set("m-dep-top", esc(coHoatDong[0].unit.name));
    set("m-dep-top-def", "<b>"+fmt(coHoatDong[0].r)+" request · "+
      pct(coHoatDong[0].r,tongQuyDuoc).toFixed(0)+
      "%</b> lượt dùng quy được về phòng ban trong kỳ.");
  } else { set("m-dep-top","—"); set("m-dep-top-def","Chưa phòng ban nào phát sinh lượt dùng."); }
  set("m-dep-users",fmtCompactNum(pool.length));

  renderDeptTree(rows);
  bindDeptToolbar();
  set("dep-alloc-note","<span title='"+esc(accountDataHint())+"'>· "+accountDataLabel()+"</span>");
}
function chartsDepartments(rows){
  // Gom theo đơn vị chuẩn hoá để mỗi phòng chỉ có MỘT lát bánh.
  var byUnitId=groupRowsByUnit(rows);
  var units=Object.keys(byUnitId).map(function(id){
    var g=byUnitId[id];
    return {unit:g.unit, agg:aggregate(g.rows)};
  }).filter(function(g){return g.agg.r>0;}).sort(function(a,b){return b.agg.cost-a.agg.cost;});

  var costGroups=units.filter(function(g){return g.agg.cost>0;}), costLabels=[], costValues=[];
  costGroups.slice(0,5).forEach(function(g){ costLabels.push(g.unit.name); costValues.push(+g.agg.cost.toFixed(2)); });
  if(costGroups.length>5){
    costLabels.push("Phòng ban khác");
    costValues.push(+costGroups.slice(5).reduce(function(sum,g){return sum+g.agg.cost;},0).toFixed(2));
  }
  if(!costLabels.length) emptyChart("c-dep-cost","lg-dep-cost","Chưa có phòng ban nào phát sinh chi phí trong kỳ.");
  else mkDonut("c-dep-cost",costLabels,costValues,"lg-dep-cost",money);

  // Tỷ lệ tài khoản được sử dụng = tài khoản có request / tài khoản được cấp.
  // Đây là tỷ lệ NỘI BỘ từng dòng, các dòng KHÔNG cộng lại thành 100% — nên vẽ bằng
  // thanh ngang thang 0–100%, không dùng biểu đồ chia phần (tròn/polar).
  //
  // KHOÁ THEO AGENT, không theo phòng ban. Mẫu số "số tài khoản được cấp" là khái
  // niệm của từng agent: Ralli và TLA HĐ cấp cho người, sáu agent còn lại chạy bằng
  // một tài khoản dịch vụ nên mẫu số là 1. Ép nó vào cây phòng ban thì sáu agent kia
  // vĩnh viễn không có mẫu số, và trước 14/08 biểu đồ này trắng vì đúng lý do đó.
  //
  // Số lấy từ /api/adoption và là chỉ tiêu TÍCH LUỸ trên toàn bộ dữ liệu, KHÔNG đổi
  // theo thanh trượt ngày — "đã từng dùng chưa" không phải câu hỏi theo ngày. Ghi chú
  // dưới biểu đồ nói rõ khoảng thời gian để không ai đọc nhầm thành số của kỳ đang xem.
  var pool=filterAccounts(), missing=[], adoption, missingNote;
  if(ADOPTION_BY_AGENT.length){
    adoption=ADOPTION_BY_AGENT.map(function(r){
      return {key:r.agent, active:r.active, prov:r.provisioned,
              value:Math.min(100,Math.round(r.rate_pct))};
    }).sort(function(a,b){return a.value-b.value;}).slice(0,12);
    var moc=ADOPTION_BY_AGENT.filter(function(r){return r.from_day;});
    var tu=moc.length?moc.map(function(r){return r.from_day;}).sort()[0]:"";
    var den=moc.length?moc.map(function(r){return r.to_day;}).sort().pop():"";
    var chung=ADOPTION_BY_AGENT.reduce(function(s,r){return s+(r.shared_excluded||0);},0);
    var ngoai=ADOPTION_BY_AGENT.reduce(function(s,r){return s+(r.outside_directory||0);},0);
    missingNote="Tỷ lệ tích luỹ trên toàn bộ dữ liệu ("+tu+" → "+den+"), không đổi theo kỳ đang chọn."
      +(chung?" Đã loại "+chung+" tài khoản dùng chung và tài khoản thử.":"")
      +(ngoai?" "+ngoai+" tài khoản có phát sinh request nhưng không còn trong danh bạ, chưa tính vào tử số.":"");
  }else{
    // Không có backend: giữ nguyên cách tính cũ theo phòng ban để dashboard mở bằng
    // dữ liệu nhúng vẫn chạy như trước.
    adoption=units.map(function(g){
      var prov=provisionedOf(g.unit.id);
      if(prov==null||prov<=0){ missing.push(g.unit.name); return null; }
      var active=accountsUnderUnit(g.unit.id,pool).filter(function(u){return u.active;}).length;
      return {key:g.unit.name, active:active, prov:prov,
              value:Math.min(100,Math.round(active/prov*100))};
    }).filter(Boolean).sort(function(a,b){return a.value-b.value;}).slice(0,8);
    missingNote=missing.length
      ? "Chưa tính được "+missing.length+" phòng do nguồn TLA Ralli chưa có số tài khoản được cấp: "+missing.join(", ")+"."
      : "";
  }
  if(!adoption.length){
    emptyChart("c-dep-adopt","lg-dep-adopt",
      missingNote||"Chưa có phòng ban nào khai báo số tài khoản được cấp.");
  }else{
    mkAdoptionBar("c-dep-adopt",adoption);
    set("lg-dep-adopt",esc(missingNote));
  }
}
/* Thanh ngang tỷ lệ áp dụng: thang cố định 0–100% để so ngang giữa các phòng, màu theo
   đúng ngưỡng cảnh báo đang dùng ở bảng chi tiết. */
function mkAdoptionBar(id, items){
  var colorOf=function(rate){
    return rate<INSIGHT_THRESHOLDS.adoptionCritical ? "#ef4444"
      : (rate<INSIGHT_THRESHOLDS.adoptionWarning ? "#f59e0b" : "#10b981");
  };
  chart(id, {
    type:"bar",
    data:{ labels:items.map(function(i){return i.key;}),
      datasets:[{ data:items.map(function(i){return i.value;}), borderRadius:4, maxBarThickness:22,
        backgroundColor:items.map(function(i){return colorOf(i.value);}) }] },
    // Nhãn ghi kèm số tài khoản: "66% · 28/42" nói đủ cả tỷ lệ lẫn quy mô mẫu số.
    plugins:[barValueLabels(function(v,i){
      var it=items[i];
      return it? v+"% · "+fmt(it.active)+"/"+fmt(it.prov) : v+"%";
    })],
    options:{ indexAxis:"y",
      layout:{padding:{right:96}},
      plugins:{ legend:{display:false},
        tooltip:{ callbacks:{ label:function(c){
          var it=items[c.dataIndex];
          return it.value+"% — "+fmt(it.active)+"/"+fmt(it.prov)+" tài khoản được cấp có phát sinh request";
        } } } },
      scales:{
        x:{ beginAtZero:true, max:100, grid:{color:gridColor()},
            ticks:{stepSize:25, callback:function(v){return v+"%";}} },
        y:{ grid:{display:false},
            ticks:{autoSkip:false, callback:function(v){return wrapAxisLabel(this.getLabelForValue(v),26);}} }
      } }
  });
}

/* ═══════════════ RENDER: AGENTS ═══════════════ */
function agentModelListHtml(models){
  var names=distinct((models||[]).filter(function(name){return name&&name!=="—";}))
    .sort(function(a,b){return a.localeCompare(b,"vi");});
  if(!names.length) return "<span class='metric-na'>—</span>";
  // Mọi model đều gắn badge, kể cả khi agent chỉ dùng một model. Trả text trần cho
  // trường hợp một model làm cùng một cột hiển thị hai kiểu khác nhau.
  var list="<div class='agent-model-list'>"+
    names.map(function(name){ return "<span>"+esc(name)+"</span>"; }).join("")+"</div>";
  if(names.length===1) return list;
  return "<div class='agent-model-count'>"+fmt(names.length)+" model</div>"+list;
}
function renderAgents(rows){
  var byAgent = groupAgg(rows, function(r){return r.a;});
  var active = byAgent.filter(function(g){return g.r>0;});
  var A = aggregate(rows);
  // Đơn vị đã nằm trong ngoặc ở tên thẻ nên giá trị chỉ còn con số, số lớn viết
  // nghìn/triệu bằng chữ — cùng quy ước với các tab khác.
  var avgCost = active.length ? A.cost/active.length : 0;
  set("m-ag-active", active.length + "/" + allAgents().length);
  set("m-ag-idle", fmtCompactNum(allAgents().length - active.length));
  setWithTitle("m-ag-req", fmtCompactNum(A.r), fmt(A.r)+" lượt gọi");
  setWithTitle("m-ag-cost", usageCompact(avgCost), money(avgCost)+" · "+usdReference(avgCost));
  var top = active.slice().sort(function(a,b){return b.tokens-a.tokens;}).slice(0,5);
  set("ag-top", top.map(function(g,i){ return "<tr><td class='rank'>"+(i+1)+"</td><td>"+esc(g.key)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td></tr>"; }).join("") || emptyRow(3));
  byAgent.sort(function(a,b){return b.cost-a.cost;});
  set("ag-tbody", byAgent.map(function(g){
    var idle = g.r===0;
    var model = agentModelListHtml(g.models);
    var dept = g.depts[0]||"—";
    return "<tr><td"+(idle?" class='subtle'":"")+">"+esc(g.key)+"</td><td class='subtle'>"+esc(dept)+"</td><td class='agent-model-cell"+(idle?" subtle":"")+"'>"+model+"</td>"+
      "<td class='num"+(idle?" subtle":"")+"'>"+(idle?"0":fmt(g.u))+"</td><td class='num"+(idle?" subtle":"")+"'>"+fmt(g.r)+"</td>"+
      "<td class='num"+(idle?" subtle":"")+"' title='"+esc(fmtTokFull(g.tokens))+"'>"+(idle?"0":fmtTok(g.tokens))+"</td><td class='num"+(g.er>2?" text-red":(idle?" subtle":""))+"'>"+(idle?"—":fmtDecimal(g.er,1)+"%")+"</td>"+
      "<td class='num"+(idle?" subtle":"")+"'>"+(idle||!g.latAvailable?"—":fmtDecimal(g.lat,1)+"s")+"</td>"+
      "<td>"+(idle?"<span class='badge badge-inactive'>Chưa dùng</span>":"<span class='badge badge-active'>Đang chạy</span>")+"</td></tr>";
  }).join("") || emptyRow(9));
  buildAgentDeptHeatmap(rows);
}
function chartsAgents(rows){
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.r-a.r;});
  // Gộp phần đuôi thành "Agent khác" để lát bánh không vụn — cùng quy tắc với biểu đồ phòng ban.
  var labels=[], values=[];
  byAgent.slice(0,6).forEach(function(g){ labels.push(g.key); values.push(g.r); });
  if(byAgent.length>6){
    labels.push("Agent khác");
    values.push(byAgent.slice(6).reduce(function(s,g){return s+num(g.r);},0));
  }
  if(!labels.length){
    emptyChart("c-ag-usage","lg-ag-usage","Chưa có agent nào phát sinh request trong kỳ.");
    return;
  }
  mkDonut("c-ag-usage", labels, values, "lg-ag-usage", fmt);
}
function renderAgentBudgetChart(rows){
  var items=configuredBudgetSummary(rows).agents;
  var labels=items.map(function(item){return item.agent;});
  var rates=items.map(function(item){return +item.rate.toFixed(2);});
  var spentColors=items.map(function(item){
    return item.rate>=100?"#ef4444":item.rate>=90?"#f97316":item.rate>=50?"#eab308":"#38bdf8";
  });
  var maxRate=Math.max.apply(null,rates.concat([100]));
  var yMax=Math.max(110,Math.ceil(maxRate/10)*10+10);
  var budgetThresholds=[
    {value:50,label:"50%",color:"#eab308",dash:[6,5]},
    {value:90,label:"90%",color:"#f97316",dash:[6,5]},
    {value:100,label:"100%",color:"#ef4444",dash:[]}
  ];
  var thresholdPlugin={
    id:"agent-budget-thresholds",
    beforeDatasetsDraw:function(chartInstance){
      var ctx=chartInstance.ctx, xScale=chartInstance.scales.x, area=chartInstance.chartArea;
      ctx.save();
      budgetThresholds.forEach(function(threshold){
        var x=xScale.getPixelForValue(threshold.value);
        ctx.beginPath();
        ctx.setLineDash(threshold.dash);
        ctx.strokeStyle=threshold.color;
        ctx.lineWidth=threshold.value===100?2:1.5;
        ctx.moveTo(x,area.top);
        ctx.lineTo(x,area.bottom);
        ctx.stroke();
      });
      ctx.restore();
    },
    afterDraw:function(chartInstance){
      var ctx=chartInstance.ctx, xScale=chartInstance.scales.x, area=chartInstance.chartArea;
      ctx.save();
      ctx.font="600 10px Inter, sans-serif";
      ctx.textAlign="center";
      ctx.textBaseline="bottom";
      budgetThresholds.forEach(function(threshold){
        ctx.fillStyle=threshold.color;
        ctx.fillText(threshold.label,xScale.getPixelForValue(threshold.value),area.top-5);
      });
      ctx.restore();
    }
  };
  var valueLabelPlugin={
    id:"agent-budget-value-labels",
    afterDatasetsDraw:function(chartInstance){
      var meta=chartInstance.getDatasetMeta(0);
      if(!meta||meta.hidden) return;
      var ctx=chartInstance.ctx;
      ctx.save();
      ctx.fillStyle=currentTheme()==="light"?"#334155":"#cbd5e1";
      ctx.font="600 10px Inter, sans-serif";
      ctx.textAlign="left";
      ctx.textBaseline="middle";
      meta.data.forEach(function(bar,index){
        var item=items[index];
        ctx.fillText(item.rate.toFixed(0)+"%",Math.min(bar.x+7,chartInstance.chartArea.right+8),bar.y);
      });
      ctx.restore();
    }
  };
  chart("c-co-agent-budget",{
    type:"bar",
    data:{
      labels:labels,
      datasets:[
        {label:"Ngân sách đã dùng",data:rates,backgroundColor:spentColors,borderRadius:5,maxBarThickness:28}
      ]
    },
    plugins:[thresholdPlugin,valueLabelPlugin],
    options:{
      indexAxis:"y",
      interaction:{mode:"nearest",intersect:true},
      layout:{padding:{top:18,right:36}},
      plugins:{
        legend:{display:false},
        tooltip:{callbacks:{
          label:function(context){
            var item=items[context.dataIndex];
            return item.rate.toFixed(0)+"% · "+money(item.cost)+" / "+money(item.budget)+" ("+usd(item.cost)+" / "+usd(item.budget)+")";
          }
        }}
      },
      scales:{
        x:{beginAtZero:true,max:yMax,grid:{color:gridColor()},ticks:{stepSize:25,callback:function(v){return v+"%";}}},
        y:{grid:{display:false},ticks:{autoSkip:false,callback:function(v){return wrapAxisLabel(this.getLabelForValue(v),26);}}}
      }
    }
  });
}
/* ═══════════════ MA TRẬN PHÒNG BAN × PROJECT ═══════════════
   Hàng = cây phòng ban (Phòng ban → Vùng → Đội → Tài khoản), bung TẠI CHỖ theo kiểu
   accordion giống bảng "Chi tiết theo phòng ban". Cột = project (mỗi agent là 1 project
   theo hợp đồng dữ liệu Excel).

   Giá trị ở MỌI cấp đều cộng từ các tài khoản nằm dưới nút đó. Các tập tài khoản của
   những nút anh em là rời nhau, nên hàng cha luôn bằng đúng tổng các hàng con đang mở.
   Con số vẫn là số thật chứ không phải ước lượng: applyAccountAllocation khoá phân bổ
   theo cặp (đơn vị, agent) và dồn phần dư, nên tổng theo phòng và tổng theo phòng × agent
   đều khớp usage gốc.
   ══════════════════════════════════════════════════════════ */
var MATRIX_INDENT_STEP = 24;    // px thụt lề mỗi cấp
var MATRIX_GUIDE_OFFSET = 19;   // px từ mép trái tới đường nối dọc của cấp 1
var MATRIX_GROUP_COLORS = ["#6366f1","#0ea5e9","#10b981","#f59e0b","#ec4899","#8b5cf6"];
var MATRIX_TIER_LABEL = {root:"Phòng ban", unit:"Đơn vị", direct:"Trực thuộc", account:"Tài khoản"};
var matrixLastRows = null;      // rows của kỳ đang xem, để bung/tìm kiếm không phải renderAll
var deptLastRows = null;        // tương tự cho cây chi tiết phòng ban ở tab Phòng ban & User

function matrixGuideX(level){ return MATRIX_GUIDE_OFFSET + (level-1)*MATRIX_INDENT_STEP; }
function matrixSearching(){ return !!String(state.matrixSearch||"").trim(); }
/* Đang tìm kiếm thì mở sẵn mọi nhánh, nếu không người dùng phải tự bung mới thấy kết quả. */
function matrixIsOpen(id){ return matrixSearching() || !!(state.matrixExpanded||{})[id]; }

/* Tài khoản trong phạm vi: bộ lọc chung của dashboard + ô tìm kiếm riêng của ma trận. */
function matrixPool(){
  var pool=filterAccounts();
  var q=String(state.matrixSearch||"").trim().toLowerCase();
  if(!q) return pool;
  return pool.filter(function(u){
    return [u.user,u.n,u.login,u.d,unitName(u.unitId)].join(" ").toLowerCase().indexOf(q)>=0;
  });
}
function matrixAgents(rows){
  var seen={}, out=[];
  (rows||[]).forEach(function(r){ if(r.a&&!seen[r.a]){ seen[r.a]=1; out.push(r.a); } });
  return out.sort(function(a,b){ return a.localeCompare(b,"vi"); });
}
/* Phần phân bổ của MỘT tài khoản cho ĐÚNG một agent. u.req là số trộn của mọi agent
   nên không dùng được ở đây — phải đọc sổ tách theo agent. */
function accountAgentReq(account, agent){
  var b=account.byAgent&&account.byAgent[agent];
  return b?num(b.req):0;
}
function matrixValues(accounts, agents){
  return agents.map(function(agent){
    var sum=0;
    for(var i=0;i<accounts.length;i++) sum+=accountAgentReq(accounts[i],agent);
    return sum;
  });
}

/* Dựng cây, mỗi nút gom sẵn danh sách tài khoản bên dưới nó.
   Nút không có tài khoản nào trong phạm vi thì bỏ hẳn, cho bảng không đầy hàng rỗng. */
function matrixTree(unit, pool){
  if(isExcludedUnit(unit)) return null;
  var kids=unitChildren(unit.id).map(function(k){ return matrixTree(k,pool); })
    .filter(function(n){ return !!n; });
  kids.sort(function(a,b){ return a.unit.name.localeCompare(b.unit.name,"vi"); });
  var direct=pool.filter(function(u){ return u.unitId===unit.id; });
  var accounts=[];
  kids.forEach(function(n){ accounts=accounts.concat(n.accounts); });
  accounts=accounts.concat(direct);
  if(!accounts.length) return null;
  return {unit:unit, kids:kids, direct:sortAccounts(direct), accounts:accounts};
}

function matrixAccountRow(acct, depth, guides, isLast, group, parent){
  return {
    key:"acct:"+acct.user, depth:depth, tier:"account", kind:"account",
    label:acct.n||acct.user, account:acct, accounts:[acct], unitCount:0,
    expandable:false, open:false, guides:guides,
    lastOfParent:isLast, group:group, parent:parent
  };
}
/* Làm phẳng cây thành danh sách hàng theo trạng thái đang mở.
   guides = tọa độ các đường dọc của tổ tiên còn nhánh phía dưới; đường của hàng cuối
   cùng chỉ vẽ nửa chiều cao, đúng quy ước tree view.

   MỖI LẦN BUNG CHỈ RA MỘT LOẠI CẤP. Một đơn vị có thể vừa có đơn vị con vừa có tài
   khoản gắn thẳng vào nó; để lẫn hai loại trong cùng một cấp thì tài khoản nằm ngang
   hàng với đơn vị, tức sai cấp. Gặp trường hợp đó thì gom tài khoản vào một nút
   "Trực thuộc" riêng, đẩy xuống thêm một cấp. */
function flattenMatrixTree(node, depth, guides, isLast, group, parent, out, isOpen){
  isOpen = isOpen || matrixIsOpen;
  var hasKids=node.kids.length>0, hasDirect=node.direct.length>0;
  var groupDirect=hasKids&&hasDirect;
  var childCount=node.kids.length+(groupDirect?1:node.direct.length);
  var row={
    key:node.unit.id, depth:depth, tier:depth===1?"root":"unit", kind:"unit",
    label:node.unit.name, accounts:node.accounts, unitCount:node.kids.length,
    expandable:childCount>0, open:isOpen(node.unit.id), unit:node.unit,
    guides:guides, lastOfParent:isLast, group:group, parent:parent
  };
  out.push(row);
  if(!row.open) return;
  var childGuides=guides.concat(depth>1&&!isLast ? [matrixGuideX(depth-1)] : []);
  node.kids.forEach(function(kid,i){
    flattenMatrixTree(kid, depth+1, childGuides, i===childCount-1, group, row, out, isOpen);
  });
  if(!hasDirect) return;

  if(!groupDirect){
    node.direct.forEach(function(acct,i){
      out.push(matrixAccountRow(acct, depth+1, childGuides,
        i===node.direct.length-1, group, row));
    });
    return;
  }
  // Nút gom luôn là con CUỐI của đơn vị, nên đường dọc của nó chỉ vẽ nửa chiều cao
  // và các tài khoản bên dưới không phải kéo dài đường của cấp trên nữa.
  var key=node.unit.id+"::direct";
  var groupRow={
    key:key, depth:depth+1, tier:"direct", kind:"unit", label:node.unit.name,
    accounts:node.direct, unitCount:0, expandable:true, open:isOpen(key), unit:node.unit,
    guides:childGuides, lastOfParent:true, group:group, parent:row
  };
  out.push(groupRow);
  if(!groupRow.open) return;
  node.direct.forEach(function(acct,i){
    out.push(matrixAccountRow(acct, depth+2, childGuides,
      i===node.direct.length-1, group, groupRow));
  });
}
/* Usage THẬT theo (đơn vị, agent), cộng dồn lên toàn bộ tổ tiên. Dùng cho những phòng
   ban chưa có tài khoản Ralli nào — không có nguồn này thì chúng biến mất khỏi ma trận
   và bảng sẽ thiếu phần lớn lưu lượng của kỳ. */
function matrixUsageIndex(rows){
  var map={};
  (rows||[]).forEach(function(r){
    var u=unitOfRow(r);
    if(!u||isExcludedUnit(u)||!r.a) return;
    unitPath(u.id).forEach(function(node){
      var m=map[node.id]=map[node.id]||{};
      m[r.a]=(m[r.a]||0)+num(r.r);
    });
  });
  return map;
}
/* Đơn vị nào có ít nhất một tài khoản trước khi áp ô tìm kiếm — dùng để phân biệt
   "phòng ban chưa hề có tài khoản Ralli" với "có nhưng bị từ khóa lọc hết". */
function unitsHavingAccounts(basePool){
  var set={};
  (basePool||[]).forEach(function(u){
    unitPath(u.unitId).forEach(function(n){ set[n.id]=true; });
  });
  return set;
}
function buildMatrixRows(pool, usage, agents){
  var out=[];
  var hasAccounts=unitsHavingAccounts(filterAccounts());
  var q=String(state.matrixSearch||"").trim().toLowerCase();
  var roots=reportingRoots();
  /* Cùng lỗ hổng với cây chi tiết phòng ban: tài khoản treo THẲNG trên cấp gom
     không có nhánh nào để đứng, vì reportingRoots() đi xuyên qua cấp gom. Xem
     ghi chú đầy đủ ở aggregateDirectNodes().
     Ở bảng này không có chuyện cộng đôi: renderMatrixTree() lấy số của mỗi hàng
     từ matrixValues(row.accounts, ...), tức từ chính tài khoản của hàng, chứ
     không tra một chỉ mục cộng dồn nào. */
  aggregateDirectNodes(accountsByUnitIndex(pool)).forEach(function(node,j){
    flattenMatrixTree(node, 1, [], true, roots.length+j, null, out);
  });
  roots.forEach(function(root,i){
    if(isExcludedUnit(root)) return;
    var node=matrixTree(root,pool);
    if(node){ flattenMatrixTree(node, 1, [], true, i, null, out); return; }
    // Có tài khoản nhưng từ khóa lọc hết ⇒ ẩn hẳn, KHÔNG rơi xuống nhánh "chưa có
    // tài khoản" bên dưới, vì như thế sẽ dán nhãn sai cho phòng ban.
    if(hasAccounts[root.id]) return;
    if(q && root.name.toLowerCase().indexOf(q)<0) return;
    // Chưa có tài khoản Ralli ⇒ vẫn hiện phòng ban dưới dạng hàng lá với số usage thật,
    // và nói rõ là không bung được, thay vì im lặng bỏ qua lưu lượng của phòng đó.
    // Giữ hàng theo ĐÚNG quy tắc của cây chi tiết phòng ban (xem deptTreeNode): có dòng
    // usage HOẶC có số cấp phát trong tổ chức — kể cả khi mọi số đều bằng 0. Trước đây
    // ma trận loại luôn phòng usage toàn 0 nên hụt 7 phòng so với bảng kia.
    var byAgent=usage[root.id];
    if(!byAgent && provisionedOf(root.id)==null) return;
    var values=agents.map(function(a){ return num((byAgent||{})[a]||0); });
    out.push({key:root.id, depth:1, tier:"root", kind:"unit", label:root.name,
      accounts:[], unitCount:0, expandable:false, open:false, guides:[],
      lastOfParent:true, group:i, parent:null, fixedValues:values, noAccounts:true});
  });
  return out;
}

/* ── Trình bày phân cấp: thụt lề, đường nối cây, dải màu theo phòng ban gốc ── */
function matrixGuideColor(light){ return light ? "rgba(100,116,139,.38)" : "rgba(148,163,184,.30)"; }
function matrixNameStyle(row, light){
  var pad=row.depth===1 ? 10 : matrixGuideX(row.depth-1)+14;
  var css="padding-left:"+pad+"px;border-left-color:"+
    MATRIX_GROUP_COLORS[row.group%MATRIX_GROUP_COLORS.length]+";";
  if(row.depth<2) return css;
  var c=matrixGuideColor(light), line="linear-gradient("+c+","+c+")";
  var layers=[], sizes=[], spots=[];
  row.guides.forEach(function(x){ layers.push(line); sizes.push("1px 100%"); spots.push(x+"px 0"); });
  layers.push(line);
  sizes.push(row.lastOfParent?"1px 50%":"1px 100%");
  spots.push(matrixGuideX(row.depth-1)+"px 0");
  return css+"background-image:"+layers.join(",")+";background-size:"+sizes.join(",")+
    ";background-position:"+spots.join(",")+";background-repeat:no-repeat;";
}
/* Dòng phụ dưới tên: hàng này là cấp gì, gồm bao nhiêu con, và chiếm bao nhiêu phần
   của hàng cha — để quan hệ "tổng con = cha" nhìn thấy được ngay trên bảng. */
function matrixMeta(row){
  var share=row.share!=null
    ? " · <span class='mx-share'>"+fmtDecimal(row.share,1)+"% của "+esc(row.parent.label)+"</span>"
    : "";
  if(row.tier==="account")
    return esc(row.account.login||row.account.user)+share;
  if(row.noAccounts)
    return "<span class='mx-warn'>chưa có user</span>";
  var parts=[];
  if(row.unitCount) parts.push(row.unitCount+" đơn vị");
  parts.push(fmt(row.accounts.length)+" tài khoản");
  return parts.join(" · ")+share+
    (row.open?" · <span class='mx-share'>∑ con = 100%</span>":"");
}
/* Số hiện ĐẦY ĐỦ chứ không rút gọn "1 nghìn": cả bảng dựa trên việc người xem cộng
   được các hàng con ra hàng cha, mà số rút gọn thì không cộng kiểm được. */
function matrixCellHtml(value, max, light, extraClass){
  var norm=max?value/max:0;
  var txt=value>0 ? (value>=100000 ? fmtDecimal(value/1000,0)+" nghìn" : fmt(value)) : "·";
  var col=value>0 ? (light?"#1e293b":"#e2e8f0") : (light?"#94a3b8":"#475569");
  return "<td class='hm-cell"+(extraClass?" "+extraClass:"")+"' style='background:"+
    intensityColor(norm,light)+";color:"+col+"'"+
    (value>0?" title='"+esc(fmt(value)+" request")+"'":"")+">"+txt+"</td>";
}

function renderMatrixTree(rows, agents){
  var table=document.getElementById("matrix-tree-table"); if(!table) return;
  var light=currentTheme()==="light";

  // Chuẩn hóa độ đậm theo TỪNG CẤP: gộp chung thì mọi hàng tài khoản sẽ nhạt như nhau.
  var maxBy={}, maxTotalBy={};
  rows.forEach(function(row){
    row.values=row.fixedValues || matrixValues(row.accounts, agents);
    row.total=row.values.reduce(function(s,v){ return s+v; },0);
    row.normKey=row.tier==="account" ? "account" : ("d"+row.depth);
    row.values.forEach(function(v){ if(v>(maxBy[row.normKey]||0)) maxBy[row.normKey]=v; });
    if(row.total>(maxTotalBy[row.normKey]||0)) maxTotalBy[row.normKey]=row.total;
  });
  rows.forEach(function(row){
    row.share=row.parent&&row.parent.total>0 ? row.total/row.parent.total*100 : null;
  });

  /* Cột không phát sinh request nào trong kỳ ⇒ đánh dấu idle. Không có dấu này thì
     một cột trắng trơn đọc ra như "thiếu dữ liệu", trong khi sự thật là agent đó
     không được dùng trong kỳ — đúng nhãn Idle mà bảng chi tiết agent đang dùng. */
  var colTotals=agents.map(function(_,i){
    return rows.reduce(function(s,r){ return s+(r.depth===1?r.values[i]:0); },0);
  });
  var idleAgents=agents.filter(function(_,i){ return !colTotals[i]; });

  var html="<thead><tr><th class='mx-th-name'>Phòng ban / Đơn vị</th>";
  agents.forEach(function(a,i){
    html+="<th class='num mx-th-agent"+(colTotals[i]?"":" mx-col-idle")+"'>"+esc(a)+
      (colTotals[i]?"":"<span class='mx-idle-tag'>không dùng trong kỳ</span>")+"</th>";
  });
  html+="<th class='num mx-th-total'>Tổng</th></tr></thead><tbody>";

  if(!rows.length){
    html+="<tr><td class='mx-empty' colspan='"+(agents.length+2)+"'>"+
      (matrixSearching()?"Không có tài khoản nào khớp từ khóa.":"Chưa có tài khoản nào trong phạm vi đang lọc.")+
      "</td></tr>";
  }
  rows.forEach(function(row){
    var cls="mx-row mx-d"+row.depth+" mx-"+row.tier+(row.open?" mx-open":"")+
      (row.expandable?" mx-clickable":"");
    html+="<tr class='"+cls+"'"+(row.expandable?" data-unit='"+esc(row.key)+"'":"")+">"+
      "<td class='mx-name' style='"+matrixNameStyle(row,light)+"'>"+
      (row.depth>1?"<i class='mx-elbow' style='left:"+matrixGuideX(row.depth-1)+"px'></i>":"")+
      "<span class='drill-caret"+(row.expandable?"":" drill-leaf")+"'>"+
        (row.expandable?(row.open?"▼":"▶"):"·")+"</span>"+
      "<span class='mx-text'><span class='mx-label'>"+
        "<span class='mx-tier mx-tier-"+row.tier+"'>"+MATRIX_TIER_LABEL[row.tier]+"</span>"+
        esc(row.label)+"</span>"+
      "<span class='mx-meta'>"+matrixMeta(row)+"</span></span></td>";
    row.values.forEach(function(v){ html+=matrixCellHtml(v, maxBy[row.normKey]||0, light); });
    html+=matrixCellHtml(row.total, maxTotalBy[row.normKey]||0, light, "mx-total");
    html+="</tr>";
  });
  html+="</tbody>";
  table.innerHTML=html;
  bindMatrixTree(table);
  return idleAgents;
}

/* Toggle bung/thu. Trạng thái nằm trong state.matrixExpanded nên giữ nguyên qua các
   lần đổi bộ lọc hoặc khoảng thời gian. Listener gắn một lần trên bảng. */
function bindMatrixTree(table){
  if(table.getAttribute("data-mx-bound")) return;
  table.setAttribute("data-mx-bound","1");
  table.addEventListener("click", function(ev){
    var tr=ev.target&&ev.target.closest?ev.target.closest("tr[data-unit]"):null;
    if(!tr) return;
    var id=tr.getAttribute("data-unit");
    state.matrixExpanded=state.matrixExpanded||{};
    if(state.matrixExpanded[id]) delete state.matrixExpanded[id];
    else state.matrixExpanded[id]=true;
    refreshMatrix();
  });
}
/* Vẽ lại RIÊNG ma trận. Bung một hàng không nên dựng lại toàn bộ biểu đồ của dashboard. */
function refreshMatrix(){
  if(matrixLastRows) buildAgentDeptHeatmap(matrixLastRows);
  saveState();
}
function matrixAnyOpen(){
  var open=state.matrixExpanded||{};
  for(var k in open) if(Object.prototype.hasOwnProperty.call(open,k)) return true;
  return false;
}
function bindMatrixToolbar(){
  var search=document.getElementById("matrix-search");
  if(search){
    if(search.value!==(state.matrixSearch||"")) search.value=state.matrixSearch||"";
    if(!search.getAttribute("data-mx-bound")){
      search.setAttribute("data-mx-bound","1");
      search.oninput=function(){ state.matrixSearch=this.value; refreshMatrix(); };
    }
  }
  var btn=document.getElementById("matrix-expand");
  if(btn){
    var anyOpen=matrixAnyOpen();
    btn.textContent=anyOpen?"Thu gọn tất cả":"Mở tất cả phòng ban";
    btn.disabled=matrixSearching();
    if(!btn.getAttribute("data-mx-bound")){
      btn.setAttribute("data-mx-bound","1");
      btn.onclick=function(){
        var opened=matrixAnyOpen();
        state.matrixExpanded={};
        if(!opened) reportingRoots().forEach(function(u){ state.matrixExpanded[u.id]=true; });
        refreshMatrix();
      };
    }
  }
}

/* Ghi chú kiểm chứng: tổng ma trận có bằng tổng usage thật của kỳ không.
   Nêu thẳng phần lệch thay vì im lặng, vì lệch nghĩa là có đơn vị phát sinh usage
   nhưng chưa có tài khoản Ralli nào để phân bổ xuống. */
function renderMatrixNote(rows, scopeRows, idleAgents){
  var shown=0;
  rows.forEach(function(r){ if(r.depth===1) shown+=r.total; });
  var real=0;
  (scopeRows||[]).forEach(function(r){
    var u=unitOfRow(r);
    if(u&&!isExcludedUnit(u)&&r.a) real+=num(r.r);
  });
  var accounts=0, blind=0;
  rows.forEach(function(r){
    if(r.depth!==1) return;
    accounts+=r.accounts.length;
    if(r.noAccounts) blind++;
  });
  // Dưới cấp mà file usage ghi nhận, phần chia cho từng đơn vị/tài khoản là số PHÂN BỔ.
  var allocated=" · <span title='"+esc(accountDataHint())+"'>ⓘ "+accountDataLabel()+"</span>";
  // Nêu tên project cột rỗng, để không ai phải đoán cột trắng là lỗi hay là không dùng.
  if(idleAgents&&idleAgents.length) allocated=" · <span class='mx-warn'>"+
    idleAgents.length+" project không phát sinh request trong kỳ: "+
    esc(idleAgents.join(", "))+"</span>"+allocated;
  var note;
  if(matrixSearching()){
    note="Đang lọc · "+fmt(accounts)+" tài khoản khớp · "+fmt(shown)+" request"+allocated;
  } else if(state.filters&&state.filters.dept){
    note=fmt(shown)+" request trong phạm vi lọc · "+fmt(accounts)+" tài khoản"+allocated;
  } else if(shown===real){
    note="ⓘ Tổng ma trận "+fmt(shown)+" request — khớp đúng tổng usage của kỳ"+
      (blind?", trong đó "+blind+" phòng chưa có user":"")+"."+allocated;
  } else {
    note="⚠ Ma trận "+fmt(shown)+" / usage "+fmt(real)+" request — lệch "+fmt(real-shown)+
      " thuộc đơn vị chưa phân bổ được xuống tài khoản."+allocated;
  }
  set("matrix-note", note);
}

function buildAgentDeptHeatmap(rows){
  matrixLastRows=rows;
  var agents=matrixAgents(rows);
  var matrixRows=buildMatrixRows(matrixPool(), matrixUsageIndex(rows), agents);
  bindMatrixToolbar();
  var idleAgents=renderMatrixTree(matrixRows, agents);
  renderMatrixNote(matrixRows, rows, idleAgents);
}
/* ═══════════════ RENDER: PROVIDERS ═══════════════ */
function renderProviders(rows){
  var byProv = groupAgg(rows, function(r){return modelProvider(r.m);}).filter(function(g){return g.r>0||g.tokens>0;}).sort(function(a,b){return b.tokens-a.tokens;});
  var totTok = aggregate(rows).tokens;
  // Đơn vị đã nằm trong ngoặc ở tên thẻ nên giá trị chỉ còn con số, và số lớn viết
  // "nghìn / triệu" bằng chữ cho thống nhất với các tab khác.
  set("m-pv-count", fmtCompactNum(byProv.length));
  if(byProv.length){
    var top=byProv[0];
    set("m-pv-share", pct(top.tokens,totTok).toFixed(0)+"%");
    set("m-pv-share-def", "<b>"+esc(top.key)+"</b> đang gánh phần lớn lưu lượng của kỳ.");
    set("m-pv-models", fmtCompactNum(top.models.length));
    /* Đây là số model CÓ PHÁT SINH REQUEST của provider dẫn đầu, không phải toàn bộ
       model bên đó khai báo trong bảng giá — thẻ "Tổng số model đã khai báo" mới là số
       khai báo. Chú thích nói rõ tiêu chí; danh sách tên model để trong tooltip vì liệt
       kê thẳng trên thẻ thì chiếm 3-4 dòng mà người xem hiếm khi cần đọc hết. */
    setWithTitle("m-pv-models-def",
      top.models.length
        ? "<b>= model của "+esc(top.key)+" có ≥1 request trong kỳ.</b>"
        : "Chưa ghi nhận model nào có lưu lượng.",
      top.models.length ? top.models.join(", ") : "");
    setWithTitle("m-pv-cost", usageCompact(top.cost), money(top.cost)+" · "+usdReference(top.cost));
    set("m-pv-latency", top.latAvailable?fmtDecimal(top.lat,1):"Chưa có dữ liệu");
  } else {
    set("m-pv-share","—"); set("m-pv-share-def","—");
    set("m-pv-models","—"); set("m-pv-models-def","—");
    set("m-pv-cost","—"); set("m-pv-latency","—");
  }
  renderProviderModelTree(rows);
}

/* ═══════════════ CÂY NHÀ CUNG CẤP → MODEL ═══════════════
   Gộp bảng "Chi tiết theo provider" và "Chi tiết theo model" thành MỘT cây hai cấp,
   đúng quan hệ thật: nhà cung cấp đưa ra model. Hàng cha là nhà cung cấp, hàng con
   là từng model của bên đó — kể cả model đã khai báo trong bảng giá mà chưa dùng,
   để thấy được phần đang bỏ phí nằm ở nhà cung cấp nào. */
function pmIsOpen(key){ return !(state.pmCollapsed||{})[key]; }   // mặc định MỞ
function providerModelIndex(rows){
  var byProv={}, byModel={}, models={};
  groupAgg(rows,function(r){return modelProvider(r.m);}).forEach(function(g){ byProv[g.key]=g; });
  groupAgg(rows,function(r){return r.m;}).forEach(function(g){ byModel[g.key]=g; });
  // Bảng giá là danh mục đầy đủ; bổ sung thêm model có usage mà chưa khai báo giá.
  Object.keys(state.pricing).forEach(function(m){ (models[modelProvider(m)]=models[modelProvider(m)]||[]).push(m); });
  Object.keys(byModel).forEach(function(m){
    var p=modelProvider(m), list=models[p]=models[p]||[];
    if(list.indexOf(m)<0) list.push(m);
  });
  var provs=Object.keys(models).sort(function(a,b){
    return (byProv[b]?byProv[b].tokens:0)-(byProv[a]?byProv[a].tokens:0) || a.localeCompare(b,"vi");
  });
  provs.forEach(function(p){
    models[p].sort(function(a,b){
      return (byModel[b]?byModel[b].tokens:0)-(byModel[a]?byModel[a].tokens:0) || a.localeCompare(b,"vi");
    });
  });
  return {provs:provs, models:models, byProv:byProv, byModel:byModel};
}
function pmNumCells(g, priceHtml){
  var idle=!g || (g.r<=0 && g.tokens<=0);
  return "<td class='num'>"+(g?fmt(g.agents.length):"0")+"</td>"+
    "<td class='num'>"+(g?fmt(g.r):"0")+"</td>"+
    "<td class='num' title='"+esc(g?fmtTokFull(g.ti):"0 token")+"'>"+(g?fmtCompactNum(g.ti):"0")+"</td>"+
    "<td class='num' title='"+esc(g?fmtTokFull(g.to):"0 token")+"'>"+(g?fmtCompactNum(g.to):"0")+"</td>"+
    "<td class='num cost' title='"+esc(g?usdReference(g.cost):"")+"'>"+moneyCompact(g?g.cost:0)+"</td>"+
    "<td class='num subtle'>"+priceHtml+"</td>"+
    "<td class='num"+(g&&g.er>2?" text-red":"")+"'>"+(idle?"<span class='subtle'>—</span>":fmtDecimal(g.er,1)+"%")+"</td>";
}
function renderProviderModelTree(rows){
  var table=document.getElementById("pm-tree-table"); if(!table) return;
  var idx=providerModelIndex(rows), light=currentTheme()==="light";
  var html="<thead><tr><th class='mx-th-name'>Nhà cung cấp / Model</th>"+
    "<th class='num'>Số Agent đang dùng</th><th class='num'>Lượt gọi</th>"+
    "<th class='num'>Token vào</th><th class='num'>Token ra</th>"+
    "<th class='num'>Mức độ sử dụng</th><th class='num'>Đơn giá vào / ra</th>"+
    "<th class='num'>Tỷ lệ lỗi</th></tr></thead><tbody>";
  var shownProv=0, shownModel=0;
  idx.provs.forEach(function(p,i){
    var g=idx.byProv[p], list=idx.models[p], open=pmIsOpen(p);
    var used=list.filter(function(m){ var mg=idx.byModel[m]; return mg&&(mg.r>0||mg.tokens>0); }).length;
    shownProv++;
    html+="<tr class='mx-row mx-d1 mx-root mx-clickable' data-pm='"+esc(p)+"'>"+
      "<td class='mx-name' style='"+matrixNameStyle({depth:1,group:i,guides:[]},light)+"'>"+
      "<span class='drill-caret'>"+(open?"▼":"▶")+"</span>"+
      "<span class='mx-text'><span class='mx-label'>"+
        "<span class='mx-tier mx-tier-root'>NHÀ CUNG CẤP</span>"+esc(p)+"</span>"+
      "<span class='mx-meta'>"+fmt(used)+"/"+fmt(list.length)+" model đang được dùng</span></span></td>"+
      pmNumCells(g,"—")+"</tr>";
    if(!open) return;
    list.forEach(function(m,j){
      var mg=idx.byModel[m], pr=state.pricing[m]||{i:0,o:0};
      var idle=!mg||(mg.r<=0&&mg.tokens<=0);
      var price=(num(pr.i)||num(pr.o)) ? moneyCompact(pr.i)+" / "+moneyCompact(pr.o) : "chưa đặt giá";
      shownModel++;
      html+="<tr class='mx-row mx-d2 mx-unit"+(idle?" detail-idle":"")+"' >"+
        "<td class='mx-name' style='"+matrixNameStyle({depth:2,group:i,guides:[],lastOfParent:j===list.length-1},light)+"'>"+
        "<i class='mx-elbow' style='left:"+matrixGuideX(1)+"px'></i>"+
        "<span class='drill-caret drill-leaf'>·</span>"+
        "<span class='mx-text'><span class='mx-label'>"+
          "<span class='mx-tier mx-tier-model'>MODEL</span>"+esc(m)+"</span>"+
        "<span class='mx-meta'>"+(idle?"<span class='mx-warn'>chưa dùng trong kỳ</span>":fmt(mg.agents.length)+" agent đang dùng")+"</span></span></td>"+
        pmNumCells(mg,price)+"</tr>";
    });
  });
  html+="</tbody>";
  table.innerHTML=html;
  bindProviderModelTree(table);
  set("pm-tree-note","Đang hiện "+fmt(shownProv)+" nhà cung cấp và "+fmt(shownModel)+
    " model. Model chưa phát sinh lượt dùng nào được làm mờ.");
  var btn=document.getElementById("pm-expand");
  if(btn){
    var anyOpen=idx.provs.some(function(p){ return pmIsOpen(p); });
    btn.textContent=anyOpen?"Thu gọn tất cả":"Mở tất cả nhà cung cấp";
    if(!btn.getAttribute("data-pm-bound")){
      btn.setAttribute("data-pm-bound","1");
      btn.onclick=function(){
        var open=providerModelIndex(scopedRows()).provs.some(function(p){ return pmIsOpen(p); });
        state.pmCollapsed={};
        if(open) providerModelIndex(scopedRows()).provs.forEach(function(p){ state.pmCollapsed[p]=true; });
        renderProviderModelTree(scopedRows()); saveState();
      };
    }
  }
}
function bindProviderModelTree(table){
  if(table.getAttribute("data-pm-bound")) return;
  table.setAttribute("data-pm-bound","1");
  table.addEventListener("click", function(ev){
    var tr=ev.target&&ev.target.closest?ev.target.closest("tr[data-pm]"):null;
    if(!tr) return;
    var key=tr.getAttribute("data-pm");
    state.pmCollapsed=state.pmCollapsed||{};
    if(state.pmCollapsed[key]) delete state.pmCollapsed[key];
    else state.pmCollapsed[key]=true;
    renderProviderModelTree(scopedRows()); saveState();
  });
}
function chartsProviders(rows){
  var byProv = groupAgg(rows, function(r){return modelProvider(r.m);}).filter(function(g){return g.tokens>0;}).sort(function(a,b){return b.tokens-a.tokens;});
  mkDonut("c-pv-share", byProv.map(function(g){return g.key;}), byProv.map(function(g){return g.tokens;}), "lg-pv-share", fmtTokFull);
  // Mức độ sử dụng chuyển từ thanh ngang sang biểu đồ tròn để đọc được ngay tỷ trọng
  // giữa các nhà cung cấp, cùng ngôn ngữ hình với biểu đồ token bên cạnh.
  var byCost = byProv.filter(function(g){return g.cost>0;}).slice().sort(function(a,b){return b.cost-a.cost;});
  mkDonut("c-pv-cost", byCost.map(function(g){return g.key;}), byCost.map(function(g){return +g.cost.toFixed(4);}), "lg-pv-cost", moneyCompact);
}

/* ═══════════════ RENDER: MODEL ═══════════════ */
function renderModels(rows){
  var used = groupAgg(rows, function(r){return r.m;}).filter(function(g){return g.tokens>0||g.r>0;});
  var allModels = Object.keys(state.pricing);
  set("m-md-total", allModels.length);
  set("m-md-total-def", "Đã dùng trong kỳ: "+used.length+"/"+allModels.length+".");
  var usedNames={}; used.forEach(function(g){ usedNames[g.key]=1; });
  var unused = allModels.filter(function(m){ return !usedNames[m]; });
  set("m-md-unused", unused.length);
  set("m-md-unused-def", unused.length? "<b>"+esc(unused.join(", "))+"</b> đã khai báo nhưng 0 request." : "Mọi model đều có lượt dùng.");
  var priced = allModels.map(function(m){ var p=state.pricing[m]; return {m:m, avg:(num(p.i)+num(p.o))/2, i:num(p.i), o:num(p.o)}; }).filter(function(x){ return x.avg>0; }).sort(function(a,b){return a.avg-b.avg;});
  if(priced.length){
    var cheap=priced[0], exp=priced[priced.length-1];
    set("m-md-cheap", esc(shortModel(cheap.m))); set("m-md-cheap-def", "<b>"+esc(cheap.m)+"</b> — "+money(cheap.i)+" token vào / "+money(cheap.o)+" token ra / 1 triệu token.");
    set("m-md-exp", esc(shortModel(exp.m))); set("m-md-exp-def", "<b>"+esc(exp.m)+"</b> — "+money(exp.i)+" token vào / "+money(exp.o)+" token ra / 1 triệu token.");
  }
  var A = aggregate(rows);
  set("m-md-cache", (A.ti? A.cached/A.ti*100:0).toFixed(0)+"%");
  // Thẻ "Token suy luận" đã gỡ khỏi giao diện: chưa xác nhận được agent nào thực sự bật
  // suy luận mở rộng, nên con số luôn bằng 0 và chỉ gây hiểu nhầm. Trường A.think vẫn
  // được tính trong aggregate() nên khi cần dựng lại thẻ thì không phải sửa gì thêm.
  // Bảng chi tiết model cũ đã được gộp vào cây "nhà cung cấp → model"
  // (xem renderProviderModelTree), nên ở đây chỉ còn phần thẻ chỉ số.
}
function chartsModels(rows){
  var used = groupAgg(rows, function(r){return r.m;}).filter(function(g){return g.tokens>0;}).sort(function(a,b){return b.tokens-a.tokens;});
  mkBar("c-md-token", used.map(function(g){return shortModel(g.key);}), used.map(function(g){return g.tokens;}), {tokens:true});
  var byCost = used.slice().sort(function(a,b){return b.cost-a.cost;});
  mkBar("c-md-cost", byCost.map(function(g){return shortModel(g.key);}), byCost.map(function(g){return +g.cost.toFixed(2);}), {money:true, colors:"#764ba2"});
}

/* ═══════════════ RENDER: USER ═══════════════ */
function renderUsers(rows){
  var accounts=filterAccounts();
  // Hai nhóm phải BÙ TRỪ NHAU tuyệt đối: inactive = phần còn lại của active, chứ không
  // phải !u.active. Định nghĩa cũ để lọt tài khoản vừa active vừa disabled ra ngoài cả
  // hai nhóm, khiến "đang dùng + bỏ không" hụt so với tổng.
  var isActiveUser=function(u){ return u.active&&!u.disabled; };
  var active=accounts.filter(isActiveUser);
  var inactive=accounts.filter(function(u){ return !isActiveUser(u); });
  var disabled=accounts.filter(function(u){return u.disabled;});
  var neverUsed=inactive.filter(function(u){return !u.last;}).length;
  var dormant=inactive.filter(function(u){return u.last&&dayDiff(u.last,state.range.end)>30;}).length;
  var datedAccounts=accounts.filter(function(u){return !!u.created;});
  var newInRange=datedAccounts.filter(function(u){return u.created>=state.range.start&&u.created<=state.range.end;}).length;
  /* Đếm theo PHÒNG BAN, không theo đơn vị ghi trên tài khoản: cột "Phòng ban" của nguồn
     TLA Ralli trộn nhiều cấp (đội, vùng, chi nhánh, trung tâm), đếm thô sẽ ra 86 "phòng
     ban" trong khi thực tế chỉ là các đội trực thuộc vài phòng. reportingRootOf() quy mỗi
     đơn vị về phòng ban cấp đầu (bỏ qua hai cấp gộp Toàn công ty / Tổng công ty). */
  var units=distinct(accounts.map(function(u){
    var root=reportingRootOf(u.unitId);
    return root?root.id:u.d;
  })).length;
  set("m-us-total",fmtCompactNum(accounts.length));
  set("m-us-total-def","Đã dùng trong kỳ: <b>"+fmt(active.length)+"/"+fmt(accounts.length)+" ("+pct(active.length,accounts.length).toFixed(0)+"%)</b> · Đã khoá: "+fmt(disabled.length)+".");
  /* Hai thẻ "đang dùng" và "bỏ không" là một cặp đối nhau nên phải CÙNG ĐƠN VỊ (%),
     nếu không người đọc sẽ cộng 25% với 465 tài khoản. Phần trăm nhóm bỏ không lấy
     bằng 100 − nhóm đang dùng (đã làm tròn) để hai thẻ luôn cộng đúng 100%. */
  var activePctRounded=accounts.length?Math.round(pct(active.length,accounts.length)):0;
  /* KHÔNG hiện 0%/100% cho kỳ không có chiều người dùng. Chiều "ai gọi" chỉ có
     từ 14/03/2026; chọn kỳ trước đó thì hoá đơn vẫn có token thật nhưng không
     ai quy được về người - hiện "0% đang dùng" là nói ngược sự thật. */
  var ir=identityRange();
  var ngoaiTam=!!(ir && (state.range.end<ir.from || state.range.start>ir.to));
  if(ngoaiTam){
    set("m-us-adoption","—");
    set("m-us-adoption-def","Kỳ đang chọn nằm ngoài khoảng có dữ liệu định danh ("
      +dayLabel(ir.from)+" → "+dayLabel(ir.to)+").");
    set("m-us-inactive","—");
    set("m-us-inactive-def","Chưa đo được ai đã dùng trong kỳ này, không phải không ai dùng.");
  }else{
    set("m-us-adoption",activePctRounded+"%");
    set("m-us-adoption-def","<b>"+fmt(active.length)+"/"+fmt(accounts.length)+"</b> tài khoản đã dùng.");
    set("m-us-inactive",(accounts.length?100-activePctRounded:0)+"%");
    set("m-us-inactive-def","<b>"+fmt(inactive.length)+"/"+fmt(accounts.length)+"</b> tài khoản · chưa từng dùng: "+
      fmt(neverUsed)+" · ngừng >30 ngày: "+fmt(dormant)+".");
  }
  set("m-us-new",datedAccounts.length?fmtCompactNum(newInRange):"—");
  set("m-us-new-def",datedAccounts.length
    ?"Tài khoản được tạo trong khoảng thời gian đang chọn."
    :"Nguồn TLA Ralli chưa có ngày cấp tài khoản.");
  set("m-us-units",fmtCompactNum(units));
  set("user-active-chip","Đã dùng: "+fmt(active.length));
  set("user-total-chip","Tổng: "+fmt(accounts.length));
  renderInactiveAccounts(inactive);
}
/* ─── Bảng chi tiết từng tài khoản (track theo username) — theo bộ lọc phòng/nhóm/agent/model ─── */
function filterAccounts(){
  var f=state.filters;
  // Bộ lọc phòng ban so theo unitId để tài khoản của đơn vị con cũng khớp phòng ban cha.
  var wantUnit=f.dept?unitOf(f.dept):null;
  var wantIds=null;
  if(wantUnit){
    wantIds={};
    [wantUnit].concat(unitDescendants(wantUnit.id)).forEach(function(u){ wantIds[u.id]=true; });
  }
  return USER_ACCOUNTS.filter(function(u){
    if(isExcludedDepartment(u.d)) return false;
    if(wantIds && !wantIds[u.unitId]) return false;
    var userKey = u.ug || u.user || u.login || u.n || u.a || "";
    if(f.user && userKey!==f.user) return false;
    if(f.agent && u.a!==f.agent) return false;
    /* HỎI SỔ ĐO THEO MODEL, KHÔNG HỎI `u.m`.

        buildAccountCatalogueFromDb() đặt `m:""` cho MỌI tài khoản, và đúng như
        thế: /api/accounts không có trường model, vì một người dùng nhiều model.
        Nhưng hai dòng cũ ở đây so `u.m` với tên model đang chọn, nên chọn bất
        kỳ Model hay Provider nào cũng loại sạch 937/937 tài khoản — cây phòng
        ban hiện "chưa có user" ở mọi hàng và thẻ đếm về "Tổng: 0", trong khi
        USER_ACCOUNTS vẫn đủ 937. Không có lỗi nào báo ra; nó trông y hệt
        "database chưa có ai".

        Nay hỏi `byModel`, dựng từ /api/usage-by-account ở applyRealAccountUsage().
        Nghĩa của bộ lọc cũng thành thứ đọc được: "những tài khoản CÓ DÙNG model
        này trong kỳ" — tài khoản không phát sinh request nào thì không thuộc về
        model nào cả, và bị loại là đúng. */
    if(f.provider && !accountUsesProvider(u, f.provider)) return false;
    if(f.model && !(u.byModel && u.byModel[f.model])) return false;
    return true;
  });
}
/* Tài khoản có dùng model nào của provider này trong kỳ không. */
function accountUsesProvider(u, provider){
  var bm=u&&u.byModel;
  if(!bm) return false;
  for(var m in bm){ if(modelProvider(m)===provider) return true; }
  return false;
}
function accountCost(u){ return cost(u); }
function quotaColor(q){ return q>=85?"#ef4444":q>=65?"#f97316":q>=45?"#f59e0b":"#10b981"; }
function accountStatus(u){
  if(u.disabled) return {label:"Vô hiệu hóa",cls:"user-status-disabled"};
  if(!u.active) return {label:"Không hoạt động",cls:"user-status-inactive"};
  if(u.quotaPct>=85) return {label:"Cảnh báo",cls:"user-status-warning"};
  return {label:"Hoạt động",cls:"user-status-active"};
}

/* Bảng tài khoản không hoạt động: nêu HAI MỐC — bắt đầu ngừng dùng và mốc chốt của
   kỳ đang xem — kèm luôn số ngày đã tính sẵn, thay vì một nhãn "x ngày trước" mà
   người đọc không truy ra được ngày cụ thể. */
/* Mốc bắt đầu ngừng dùng. Nguồn TLA Ralli KHÔNG lưu thời điểm dùng lần cuối cho tài
   khoản chưa từng hoạt động, nên với nhóm đó mốc bắt đầu lùi về đầu kỳ đang xem và
   được ghi rõ là suy ra — không bịa một ngày cụ thể. */
function inactiveSince(u){
  if(u.last) return {iso:u.last, exact:true};
  return {iso:state.range.start, exact:false};
}
function renderInactiveAccounts(accounts){
  var tb=document.getElementById("user-inactive-tbody"); if(!tb) return;
  var endIso=state.range.end;
  // Ngừng lâu nhất lên trước; mốc đo được xếp trước mốc suy ra để phần chắc chắn nằm trên.
  var all=(accounts||[]).slice().sort(function(a,b){
    var sa=inactiveSince(a), sb=inactiveSince(b);
    if(sa.exact!==sb.exact) return sa.exact?-1:1;
    return sa.iso.localeCompare(sb.iso)||a.user.localeCompare(b.user);
  });
  var rows=all.slice(0,12), neverUsed=0, noCreated=0;
  all.forEach(function(u){ if(!u.last) neverUsed++; if(!u.created) noCreated++; });
  tb.innerHTML=rows.map(function(u){
    var since=inactiveSince(u), days=Math.max(0,dayDiff(since.iso,endIso));
    // Ngày cấp lấy thẳng từ u.created. Nguồn hiện chưa có trường này nên đa số rỗng —
    // hiện "chưa có dữ liệu" thay vì suy ra một ngày không có thật.
    var createdCell=u.created
      ? fmtDateUS(u.created)
      : "<span class='metric-na'>chưa có dữ liệu</span>";
    return "<tr><td>"+esc(u.d)+"</td>"+
      "<td class='user-id'><span class='user-real-name'>"+esc(u.n)+"</span>"+
        "<span class='user-account'>"+esc(u.login)+"</span></td>"+
      "<td class='date-cell'>"+createdCell+"</td>"+
      "<td class='date-cell'>"+fmtDateUS(since.iso)+
        (since.exact?"":"<span class='inactive-tag'>chưa từng dùng</span>")+"</td>"+
      "<td class='date-cell'>"+fmtDateUS(endIso)+"</td>"+
      "<td class='num"+(days>30?" text-red":"")+"'>"+fmt(days)+"</td></tr>";
  }).join("") || emptyRow(6);
  var note=[];
  if(all.length>rows.length) note.push("Hiện "+fmt(rows.length)+" tài khoản ngừng lâu nhất trong tổng số "+fmt(all.length)+".");
  if(all.length) note.push("Mốc chốt là ngày cuối của kỳ đang xem ("+fmtDateUS(endIso)+").");
  if(neverUsed) note.push(fmt(neverUsed)+" tài khoản chưa từng ghi nhận hoạt động — nguồn TLA Ralli không lưu "+
    "thời điểm dùng lần cuối cho nhóm này, nên mốc bắt đầu lấy theo đầu kỳ ("+fmtDateUS(state.range.start)+").");
  if(noCreated) note.push("Cột Thời gian được cấp trống với "+fmt(noCreated)+" tài khoản vì file TLA Ralli chưa "+
    "xuất cột ngày cấp; bổ sung cột đó vào nguồn thì bảng tự điền.");
  set("user-inactive-note", note.join(" "));
}
/* Người dùng hoạt động theo ngày.

   CÓ DATABASE thì đây là số ĐẾM ĐƯỢC: bao nhiêu tài khoản khác nhau phát sinh
   request trong ngày đó, lấy từ /api/usage-by-account.

   ĐỔI HÀNH VI 03/09/2026 — biểu đồ này nay phủ 8/8 agent, trước chỉ 2/8.
   Endpoint đọc `usage_by_account_resolved` thay vì `usage_by_account`, nên sáu
   agent chạy bằng một tài khoản dịch vụ ĐÃ CÓ MẶT, mỗi agent đúng một tài khoản.
   Đường cong vì thế NHẢY LÊN — đó là dữ liệu mới, không phải lỗi.

   Đếm là đếm TÀI KHOẢN, không phải đếm người ngoài đời: một agent dịch vụ đóng
   góp đúng 1, dù nó phục vụ cả công ty. Muốn đếm riêng người thật thì lọc
   `kind = 'real'` — cột đó có trong mỗi dòng trả về.

   Trước 15/08 nó là một công thức:
       dau = tổng_tài_khoản × (0,10 + 0,16 × lượt_ngày / lượt_lớn_nhất)
   Công thức ấy hợp lý ở thời điểm viết - không nguồn nào ghi userId - nhưng nó
   cho ra đường cong mượt trông y hệt số đo. Đã đo lại: thực tế 1–5 người/ngày,
   trong khi công thức vẽ 133–244. Sai gấp khoảng 50 lần.

   Không có backend thì vẫn dùng công thức cũ, vì dữ liệu nhúng không có chiều
   người dùng - và cờ `estimated` nói rõ đang ở nhánh nào. */
function dauSeries(){
  var accounts=filterAccounts(), total=accounts.length;
  /* 30 ngày LỊCH tính lùi từ ngày cuối kỳ, KHÔNG phải "30 ngày có dữ liệu".
     Trước 15/08 nó lọc dayOrder rồi slice(-30) - ngày không có lưu lượng bị bỏ
     hẳn khỏi trục, nên cửa sổ lặng lẽ kéo dài quá 30 ngày và trục hoành nhảy
     cóc qua những ngày trống. Nay ngày trống vẫn đứng đúng chỗ với giá trị 0,
     và nhãn "30 ngày tính đến <ngày cuối>" nói đúng thứ đang vẽ. */
  var dates=[], _end=parseISO(state.range.end);
  for(var _i=29;_i>=0;_i--){
    var _d=toISO(addDays(_end,-_i));
    if(_d>=state.range.start&&_d<=state.range.end) dates.push(_d);
  }
  if(REAL_BY_ACCOUNT.length){
    // Chỉ đếm tài khoản nằm trong bộ lọc đang xem, để biểu đồ khớp với các thẻ
    // KPI ngay trên nó thay vì luôn đếm toàn công ty.
    var trongLoc={};
    accounts.forEach(function(u){ if(u.login) trongLoc[String(u.login).toLowerCase()]=1; });
    var theoNgay={};
    REAL_BY_ACCOUNT.forEach(function(x){
      var k=String(x.username||"").toLowerCase();
      if(!trongLoc[k]) return;
      (theoNgay[x.day]=theoNgay[x.day]||{})[k]=1;
    });
    return {dates:dates, total:total, estimated:false,
            dau:dates.map(function(d){ return Object.keys(theoNgay[d]||{}).length; })};
  }
  var requests=dates.map(function(d){return aggregate(applyFilters(state.days[d]||[])).r;});
  var maxReq=Math.max.apply(null,requests.concat([1]));
  var dau=requests.map(function(r){return Math.min(total,Math.round(total*(0.10+0.16*r/maxReq)));});
  return {dates:dates, total:total, dau:dau, estimated:true};
}
/* Khoảng ngày CÓ chiều người dùng, đọc từ chính dữ liệu đã nạp.
   Ralli và TLA Hợp Đồng bắt đầu ghi danh tính từ 14/03/2026; trước đó hoá đơn
   vẫn ghi nhận lưu lượng nhưng KHÔNG nguồn nào ghi ai gọi. */
function identityRange(){
  if(!REAL_BY_ACCOUNT.length) return null;
  var min=null, max=null;
  REAL_BY_ACCOUNT.forEach(function(x){
    if(!min||x.day<min) min=x.day;
    if(!max||x.day>max) max=x.day;
  });
  return {from:min, to:max};
}

function chartsUsers(rows){
  var s=dauSeries(), labels=s.dates.map(dayLabel);
  var kyLabel=dayLabel(state.range.start)+" → "+dayLabel(state.range.end);

  /* KỲ KHÔNG CÓ CHIỀU NGƯỜI DÙNG thì KHÔNG vẽ 0.
     Đây là cái bẫy đắt nhất của bộ dữ liệu này: "không đo được" và "bằng không"
     trông giống hệt nhau trên biểu đồ. Chọn kỳ 29/01–28/02 thì hoá đơn ghi
     85.040.150 token thật, nhưng chiều danh tính chỉ có từ 14/03 - vẽ ra sẽ
     thành "0% nhân viên dùng AI", tức nói ngược hẳn sự thật.
     Mẫu số cũng sai theo: 937 là số tài khoản HÔM NAY, mà tài khoản Ralli sớm
     nhất mới được tạo 02/04/2026. */
  var ir=identityRange();
  var coDinhDanh=s.dau.some(function(v){ return v>0; });
  var coLuuLuong=aggregate(rows).tokens>0 || aggregate(rows).r>0;
  if(REAL_BY_ACCOUNT.length && !coDinhDanh && coLuuLuong){
    /* Nói ĐÚNG lý do, vì hai lý do dẫn tới cùng một biểu đồ rỗng:
         (a) kỳ này chỉ có agent chạy bằng tài khoản dịch vụ - khái niệm "người
             dùng" không tồn tại, chứ không phải đo hụt
         (b) có agent cấp quyền cho người, nhưng không dòng nào quy được về ai
       Kỳ 29/01–28/02 là trường hợp (a): ba agent chạy đều has_org_tree = 0. */
    var agentKy={}; (rows||[]).forEach(function(r){ if(r.a) agentKy[r.a]=1; });
    var agentNguoi=ADOPTION_BY_AGENT.filter(function(x){return x.kind==="people";});
    var chayTrongKy=agentNguoi.filter(function(x){return agentKy[x.agent];});
    var tenDichVu=Object.keys(agentKy).sort().join(", ");
    var vi = chayTrongKy.length
      ? "Kỳ đang chọn ("+kyLabel+") có agent cấp quyền cho người dùng nhưng không"
        + " dòng nào quy được về ai."
      : "Kỳ đang chọn ("+kyLabel+") chưa có agent nào cấp quyền cho người dùng."
        + (tenDichVu?" Chỉ "+tenDichVu+" chạy, và chúng gọi bằng tài khoản dịch"
           +" vụ nên không có khái niệm \"người dùng\".":"")
        + (agentNguoi.length?" Hai agent có chiều người dùng ("
           +agentNguoi.map(function(x){return x.agent;}).join(", ")+")":"")
        + (ir?" chỉ có dữ liệu từ "+dayLabel(ir.from)+" đến "+dayLabel(ir.to)+".":".");
    vi += " Hoá đơn vẫn ghi nhận lưu lượng trong kỳ này — 0 ở đây nghĩa là KHÔNG"
        + " ÁP DỤNG, không phải không ai dùng.";
    emptyChart("c-us-dau","nt-us-dau",vi);
    emptyChart("c-us-idle","nt-us-idle",vi);
    emptyChart("c-us-adopt-all","lg-us-adopt-all",vi);
    set("nt-us-adopt-all","");
    return;
  }
  /* Biểu đồ chỉ vẽ 30 ngày CUỐI của kỳ (dauSeries slice(-30)), nên ghi chú phải
     nói đúng cửa sổ ĐANG VẼ chứ không phải cả kỳ - chọn kỳ 6 tháng mà ghi chú
     đề tên cả 6 tháng thì người đọc tưởng đường cong phủ hết. */
  var veLabel=s.dates.length
    ? dayLabel(s.dates[0])+" → "+dayLabel(s.dates[s.dates.length-1]) : kyLabel;
  var thieu=s.dates.length&&veLabel!==kyLabel
    ? " ("+s.dates.length+" ngày cuối của kỳ "+kyLabel+")" : "";
  set("nt-us-dau","Đang vẽ "+veLabel+thieu
      +(ir?" · chiều người dùng có từ "+dayLabel(ir.from)+" đến "+dayLabel(ir.to):"")
      +(s.estimated?" · SỐ ƯỚC LƯỢNG (không có backend)":""));
  set("nt-us-idle","Đang vẽ "+veLabel+thieu+" · = tổng đã cấp − người hoạt động trong ngày.");

  var avg=s.dau.length?s.dau.reduce(function(a,b){return a+b;},0)/s.dau.length:0;
  mkLine("c-us-dau",labels,[
    {label:"Người dùng hoạt động",data:s.dau,borderColor:"#3b82f6",backgroundColor:"rgba(59,130,246,.12)",fill:true,tension:.35,pointRadius:2},
    {label:"Trung bình kỳ ("+fmt(avg)+")",data:s.dates.map(function(){return Math.round(avg);}),
      borderColor:"#f59e0b",borderDash:[5,4],fill:false,pointRadius:0,borderWidth:2},
    {label:"Tổng đã cấp",data:s.dates.map(function(){return s.total;}),borderColor:"#64748b",borderDash:[6,4],fill:false,pointRadius:0}
  ],false);
  // Tài khoản đã cấp nhưng không mở công cụ trong ngày = tổng đã cấp − người hoạt động.
  var idle=s.dau.map(function(d){return Math.max(0,s.total-d);});
  mkBar("c-us-idle",labels,idle,{colors:"#f59e0b"});

  /* Bánh tròn toàn công ty: hai phần BÙ NHAU nên cộng đúng 100%. Dùng đúng định nghĩa
     active/inactive của các thẻ KPI phía trên để bánh và thẻ không nói khác nhau. */
  var accounts=filterAccounts();
  var activeCount=accounts.filter(function(u){return u.active&&!u.disabled;}).length;
  if(!accounts.length){
    emptyChart("c-us-adopt-all","lg-us-adopt-all","Chưa có tài khoản nào trong phạm vi đang lọc.");
    set("nt-us-adopt-all","");
  }else{
    mkDonut("c-us-adopt-all",["Đang dùng","Chưa dùng"],[activeCount,accounts.length-activeCount],
      "lg-us-adopt-all",
      function(v){ return fmt(v)+"/"+fmt(accounts.length)+" tài khoản"; },
      ["#10b981","#f59e0b"]);
    set("nt-us-adopt-all","Kỳ "+kyLabel+" · mẫu số là "+fmt(accounts.length)+" tài khoản đã cấp"+
      (state.filters.dept?" trong phạm vi đang lọc":"")+
      "; đang dùng = có ≥1 request trong kỳ và tài khoản chưa bị khoá.");
  }
}

/* ═══════════════ RENDER: CHI PHÍ ═══════════════ */
function renderCost(rows){
  var A = aggregate(rows);
  var configured=configuredBudgetSummary(rows);
  // Đơn vị nằm trong ngoặc ở tên thẻ; giá trị viết gọn theo nghìn/triệu, số đầy đủ
  // và quy đổi USD vẫn xem được qua tooltip + dòng mô tả.
  setWithTitle("m-co-total", usageCompact(A.cost), money(A.cost)+" · "+usdReference(A.cost));
  set("m-co-vnd", usdReference(A.cost));
  set("m-co-budget", pct(configured.cost,configured.budget).toFixed(0)+"%");
  set("m-co-budget-def", "<b>= chi phí agent có ngân sách ÷ ngân sách quy đổi cho khoảng đang chọn</b> = <span title='"+esc(usdReference(configured.cost))+"'>"+money(configured.cost)+"</span> / <span title='"+esc(usdReference(configured.budget))+"'>"+money(configured.budget)+"</span>.");
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;});
  var top2 = byAgent.slice(0,2).reduce(function(s,g){return s+g.cost;},0);
  set("m-co-conc", pct(top2,A.cost).toFixed(0)+"%");
  var perK = A.r? A.cost/(A.r/1000):0;
  setWithTitle("m-co-perk", usageCompact(perK), money(perK)+" / 1.000 lượt gọi · "+usdReference(perK));
  var prevA=shiftedAgg(-rangeLenDays()), sameA=shiftedAgg(-365);
  renderDelta("d-co-total", A.cost, prevA.cost, sameA.cost, false, moneyCompact, 0.88, 0.57);
  var budget=budgetInsight(A,rows), concentration=concentrationInsight(rows);
  renderCardInsight("m-co-total",[budget,concentration]);
  renderCardInsight("m-co-budget",[budget]);
  renderCardInsight("m-co-conc",[concentration]);
  renderCostTable(rows);
}
function costKeyFn(){
  var gb = document.getElementById("co-groupby").value;
  return gb==="dept" ? function(r){return r.d;} : gb==="model" ? function(r){return r.m;} : function(r){return r.a;};
}
function renderCostTable(rows){
  var gb = document.getElementById("co-groupby").value;
  var col1 = gb==="dept"?"Phòng ban":gb==="model"?"Model":"Agent";
  var el1=document.getElementById("co-col1"); if(el1) el1.textContent=col1;
  var dt=document.getElementById("co-dim-title"); if(dt) dt.textContent="Phân bổ chi phí theo "+col1;
  var keyFn=costKeyFn();
  var groups = groupAgg(rows.filter(function(r){var k=keyFn(r);return k&&k!=="—";}), keyFn).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;});
  var total = groups.reduce(function(s,g){return s+g.cost;},0);
  /* Đơn giá thực tế tính trên 1 TRIỆU TOKEN — cùng đơn vị với bảng giá của nhà cung cấp,
     nên đối chiếu được thẳng với giá niêm yết. Chia theo lượt gọi thì mỗi agent có độ dài
     prompt khác nhau, con số không so ngang được giữa các agent. */
  set("co-tbody", groups.map(function(g){
    return "<tr><td>"+esc(g.key)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td><td class='num'>"+fmt(g.r)+"</td>"+(g.tokens?moneyCell(g.cost/(g.tokens/1e6),"num",{costEst:num(g.costEst)/(g.tokens/1e6),costRowsInv:g.costRowsInv}):"<td class='num'>—</td>")+moneyCell(g.cost,null,g)+"<td><div class='progress-bar'><div class='progress-fill' style='width:"+pct(g.cost,total).toFixed(0)+"%'></div><span class='progress-text'>"+pct(g.cost,total).toFixed(0)+"%</span></div></td></tr>";
  }).join("") || emptyRow(6));
}
/* ─── Chi phí theo thời gian, tách theo phòng ban ───
   Mỗi phòng ban là một đường. Giữ Top-8 theo tổng chi phí, phần đuôi gộp thành một
   đường "Phòng ban khác" để biểu đồ không thành búi chỉ. */
function deptCostTrend(){
  var dates=state.dayOrder.filter(function(d){return d>=state.range.start&&d<=state.range.end;});
  var totals={};
  var perDay=dates.map(function(d){
    var m={};
    applyFilters(state.days[d]||[]).forEach(function(r){
      var u=unitOfRow(r);
      if(!u||isExcludedUnit(u)) return;
      var c=cost(r);
      m[u.name]=(m[u.name]||0)+c;
      totals[u.name]=(totals[u.name]||0)+c;
    });
    return m;
  });
  var names=Object.keys(totals).filter(function(n){return totals[n]>0;})
    .sort(function(a,b){return totals[b]-totals[a];});
  var top=names.slice(0,8), rest=names.slice(8);
  var series=top.map(function(n){
    return {key:n, data:perDay.map(function(m){return +(m[n]||0).toFixed(4);})};
  });
  if(rest.length){
    series.push({key:"Phòng ban khác", data:perDay.map(function(m){
      return +rest.reduce(function(s,n){return s+(m[n]||0);},0).toFixed(4);
    })});
  }
  return {labels:dates.map(dayLabel), series:series};
}

/* Icon con mắt cho chú thích bật/tắt đường (kiểu Kibana). Vẽ inline SVG để không
   phụ thuộc font icon bên ngoài và vẫn đổi màu theo currentColor của chú thích. */
var EYE_SHOW="<svg viewBox='0 0 24 24' width='13' height='13' fill='none' stroke='currentColor' "+
  "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"+
  "<path d='M1.5 12S5 5 12 5s10.5 7 10.5 7-3.5 7-10.5 7S1.5 12 1.5 12z'/><circle cx='12' cy='12' r='3'/></svg>";
var EYE_HIDE="<svg viewBox='0 0 24 24' width='13' height='13' fill='none' stroke='currentColor' "+
  "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"+
  "<path d='M9.9 5.2A10.9 10.9 0 0 1 12 5c7 0 10.5 7 10.5 7a19 19 0 0 1-3.4 4.4'/>"+
  "<path d='M6.3 6.4A19 19 0 0 0 1.5 12S5 19 12 19a10.7 10.7 0 0 0 4.4-.9'/>"+
  "<path d='M9.9 9.9a3 3 0 0 0 4.2 4.2'/><path d='M2 2l20 20'/></svg>";

/* Chú thích tự dựng thay cho legend mặc định của Chart.js: bấm để ẩn/hiện đường,
   đường đang ẩn thì mờ đi và đổi sang icon mắt gạch chéo. */
function renderToggleLegend(chartId, legendId, fmtVal){
  var host=document.getElementById(legendId), ch=charts[chartId];
  if(!host||!ch) return;
  host.innerHTML=ch.data.datasets.map(function(d,i){
    var shown=ch.isDatasetVisible(i);
    var total=d.data.reduce(function(s,v){return s+num(v);},0);
    return "<button type='button' class='legend-toggle"+(shown?"":" is-hidden")+"' data-idx='"+i+"' "+
      "aria-pressed='"+(shown?"false":"true")+"' title='"+esc(shown?"Ẩn đường này":"Hiện lại đường này")+"'>"+
      "<span class='dot' style='background:"+d.borderColor+"'></span>"+
      "<span class='legend-name'>"+esc(d.label)+"</span>"+
      "<span class='legend-val'>"+(fmtVal?fmtVal(total):fmt(total))+"</span>"+
      "<span class='legend-eye'>"+(shown?EYE_SHOW:EYE_HIDE)+"</span></button>";
  }).join("");
  if(host.getAttribute("data-toggle-bound")) return;
  host.setAttribute("data-toggle-bound","1");
  host.addEventListener("click", function(ev){
    var btn=ev.target&&ev.target.closest?ev.target.closest(".legend-toggle"):null;
    if(!btn) return;
    var c=charts[chartId]; if(!c) return;
    var i=+btn.getAttribute("data-idx");
    c.setDatasetVisibility(i, !c.isDatasetVisible(i));
    c.update();
    renderToggleLegend(chartId, legendId, fmtVal);
  });
}
function mkToggleLine(id, labels, series, legendId, fmtVal, emptyMsg){
  if(!series.length||!labels.length){ emptyChart(id, legendId, emptyMsg||"Chưa có dữ liệu trong kỳ."); return; }
  var datasets=series.map(function(s,i){
    var c=palette[i%palette.length];
    return {label:s.key, data:s.data, borderColor:c, backgroundColor:c+"22",
      fill:false, tension:.32, borderWidth:2,
      pointRadius:s.data.length<=10?3:1.5, pointBackgroundColor:c, pointHoverRadius:5};
  });
  chart(id,{
    type:"line",
    data:{labels:labels, datasets:datasets},
    options:{
      interaction:{mode:"index", intersect:false},
      plugins:{ legend:{display:false},
        tooltip:{ callbacks:{ label:function(c){
          return c.dataset.label+": "+(fmtVal?fmtVal(c.parsed.y):fmt(c.parsed.y));
        } } } },
      scales:{ x:{grid:{display:false},ticks:{maxTicksLimit:8}},
        y:{beginAtZero:true,grid:{color:gridColor()},
          ticks:{callback:function(v){return moneyCompact(v);},maxTicksLimit:6}} }
    }
  });
  renderToggleLegend(id, legendId, fmtVal);
}

function chartsCost(rows){
  renderAgentBudgetChart(rows);
  /* Vẽ MỖI LẦN chartsCost chạy, tức mỗi lần đổi khoảng ngày hoặc bộ lọc — mục 6.6
     đòi cảnh báo phải bám theo bộ lọc, và cách chắc nhất là tính lại từ chính
     `rows` đã lọc thay vì giữ một bản tính sẵn. */
  renderAgentCostAlerts(rows);
  bindAgentCostAlerts();
  // Xu hướng chung trước, rồi mới tách theo phòng ban — cùng mạch đọc tổng → chi tiết.
  var tl=trendSeries();
  mkOverviewLine("c-co-trend", tl.labels, tl.cost, "money", "#38bdf8");
  set("co-trend-total", moneyCompact(aggregate(rows).cost));
  var trend=deptCostTrend();
  mkToggleLine("c-co-dept-trend", trend.labels, trend.series, "lg-co-dept-trend", moneyCompact,
    "Chưa có phòng ban nào phát sinh chi phí trong kỳ.");
  var keyFn=costKeyFn();
  var groups = groupAgg(rows.filter(function(r){var k=keyFn(r);return k&&k!=="—";}), keyFn).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;});
  var labels=[], values=[];
  groups.slice(0,5).forEach(function(g){labels.push(g.key);values.push(+g.cost.toFixed(2));});
  if(groups.length>5){
    labels.push("Mục khác");
    values.push(+groups.slice(5).reduce(function(sum,g){return sum+g.cost;},0).toFixed(2));
  }
  mkDonut("c-co-dim",labels,values,"lg-co-dim",money);
}

/* ═══════════════ RENDER: HIỆU NĂNG ═══════════════ */
function renderPerformance(rows){
  var A = aggregate(rows);
  // Đơn vị nằm trong ngoặc ở tên thẻ; phần trăm vẫn giữ ký hiệu % ở giá trị, số thập
  // phân dùng dấu phẩy theo chuẩn tiếng Việt.
  // Ba nhóm mã lỗi lấy từ số lượt THẬT do Google Monitoring đo, không còn tách
  // tổng tỷ lệ lỗi theo hệ số cố định. Không có dữ liệu mã trả về thì nói thẳng
  // là chưa có, chứ không suy ra một con số trông có vẻ hợp lý.
  var chuaCo = "<span class='metric-na'>Chưa có dữ liệu</span>";
  // Mẫu số là eKnown chứ không phải tổng lượt gọi. Ralli không đi qua Google
  // nên không ai biết nó lỗi bao nhiêu; đưa nó vào mẫu số là ngầm khai rằng
  // 7.924 lượt đó đều thành công.
  set("m-pf-success", A.codeAvailable
    ? fmtDecimal(pct(A.eKnown-A.e4-A.e5-A.e429, A.eKnown),1)+"%" : chuaCo);
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.cost-a.cost;});
  set("pf-tbody", byAgent.map(function(g){
    var model = agentModelListHtml(g.models);
    // Agent không có nguồn đo mã trả về thì để gạch ngang. "100% thành công"
    // và "chưa đo được" là hai điều khác hẳn nhau.
    var thanhCong = g.codeAvailable ? fmtDecimal(pct(g.eKnown-g.e4-g.e5-g.e429, g.eKnown),1)+"%" : "—";
    var tyLeLoi   = g.codeAvailable ? fmtDecimal(pct(g.e4+g.e5+g.e429, g.eKnown),1)+"%" : "—";
    return "<tr><td>"+esc(g.key)+"</td><td class='agent-model-cell'>"+model+"</td><td class='num'>"+fmt(g.r)+"</td>"+
      "<td class='num'>"+thanhCong+"</td>"+
      "<td class='num"+(g.codeAvailable&&g.er>2?" text-red":"")+"'>"+tyLeLoi+"</td></tr>";
  }).join("") || emptyRow(5));
}
function chartsPerformance(rows){
  // Chỉ vẽ agent có nguồn đo mã trả về. Vẽ agent chưa đo được thành cột 0%
  // là khẳng định nó không lỗi lần nào — điều không ai kiểm chứng được.
  var byAgent = groupAgg(rows, function(r){return r.a;})
    .filter(function(g){return g.r>0 && g.codeAvailable;})
    .sort(function(a,b){return b.er-a.er;});
  mkBar("c-pf-err", byAgent.map(function(g){return g.key;}), byAgent.map(function(g){return +g.er.toFixed(2);}), {horizontal:true, percent:true,
    colors: byAgent.map(function(g){ return g.er>2?"#ef4444":g.er>1?"#f59e0b":"#667eea"; }) });
  var A = aggregate(rows);
  /* Nhãn dùng đúng tên của bốn thẻ chỉ số ngay phía trên (Lỗi phía Client / Lỗi phía
     Provider / Lỗi giới hạn tốc độ request) để người xem đối chiếu được ngay; phần giải nghĩa dài
     đã nằm ở dòng mô tả của các thẻ đó nên không lặp lại dưới chú giải nữa.

     Khi không có dữ liệu mã trả về (Ralli không đi qua Google Cloud), biểu đồ rút
     xuống hai lát: thành công / lỗi. Vẽ đủ bốn lát bằng cách chia tỷ lệ tổng là
     bịa ra một cơ cấu lỗi mà không ai đo được. */
  var pctFmt = function(v){ return fmtDecimal(v,2)+"%"; };
  if(A.codeAvailable){
    mkDonut("c-pf-code",
      ["2xx · Thành công","4xx · Lỗi phía Client","5xx · Lỗi phía Provider","429 · Lỗi giới hạn tốc độ request"],
      [pct(A.eKnown-A.e4-A.e5-A.e429, A.eKnown), pct(A.e4,A.eKnown),
       pct(A.e5,A.eKnown), pct(A.e429,A.eKnown)], "lg-pf-code",
      pctFmt, ["#10b981","#f59e0b","#ef4444","#8b5cf6"]);
  } else {
    mkDonut("c-pf-code", ["Thành công","Lỗi (chưa rõ mã)"],
      [100-A.er, A.er], "lg-pf-code", pctFmt, ["#10b981","#94a3b8"]);
  }
}

/* ═══════════════ HEATMAP (theme-aware) ═══════════════ */
function intensityColor(v, light){ if(v<=0) return light ? "#eef2f7" : "#0f172a"; var a=0.12+v*0.72; return "rgba(102,126,234,"+a.toFixed(2)+")"; }
function buildHeatmap(tableId, cols, rows, matrix){
  var table = document.getElementById(tableId); if(!table) return;
  var light = currentTheme()==="light";
  var max=0; matrix.forEach(function(r){ r.forEach(function(v){ if(v>max) max=v; }); });
  var html = "<thead><tr><th class='row-h'></th>";
  cols.forEach(function(c){ html += "<th class='col-h'>"+esc(c)+"</th>"; });
  html += "</tr></thead><tbody>";
  rows.forEach(function(rl, ri){
    html += "<tr><th class='row-h'>"+esc(rl)+"</th>";
    (matrix[ri]||[]).forEach(function(v){
      var norm = max? v/max:0;
    var txt = v>0 ? (v>=1000?fmtDecimal(v/1000,1)+" nghìn":fmt(v)) : "·";
      var col = v>0 ? (light ? "#1e293b" : "#e2e8f0") : (light ? "#94a3b8" : "#475569");
      html += "<td class='hm-cell' style='background:"+intensityColor(norm,light)+";color:"+col+"'>"+txt+"</td>";
    });
    html += "</tr>";
  });
  html += "</tbody>";
  table.innerHTML = html;
}

/* ═══════════════ GLOBAL TIME RANGE (kiểu Open WebUI) ═══════════════ */
function presetRange(n){
  var end = maxDataDate();
  var start = (n==null) ? minDataDate() : addDays(end, -(n-1));
  return { start:toISO(start), end:toISO(end) };
}
/* ─── Ô ngày: gõ tay hoặc chọn lịch ───
   Riêng hai ô text của bộ lọc nhận dd/mm/yyyy và cũng chấp nhận yyyy-mm-dd.
   Nhập sai thì giữ nguyên khoảng đang xem và báo lỗi ngay tại chỗ. */
function fmtRangeDateVI(iso){
  var p=String(iso==null?"":iso).split("-");
  return p.length===3 ? (p[2]+"/"+p[1]+"/"+p[0]) : String(iso);
}
function parseTypedDate(text){
  var t=String(text==null?"":text).trim();
  if(!t) return null;
  var m=t.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);      // dd/mm/yyyy
  var y,mo,d;
  if(m){ d=+m[1]; mo=+m[2]; y=+m[3]; }
  else {
    m=t.match(/^(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})$/);        // yyyy-mm-dd
    if(!m) return null;
    y=+m[1]; mo=+m[2]; d=+m[3];
  }
  if(mo<1||mo>12||d<1||d>31) return null;
  var dt=new Date(Date.UTC(y,mo-1,d));
  // Chặn ngày tràn tháng (31/02 → 03/03) thay vì nhận bừa.
  if(dt.getUTCFullYear()!==y||dt.getUTCMonth()!==mo-1||dt.getUTCDate()!==d) return null;
  return toISO(dt);
}
function rangeHint(msg){
  var e=document.getElementById("range-hint"); if(!e) return;
  e.textContent=msg||"";
  e.className="range-hint"+(msg?" error":"");
  if(msg) setTimeout(function(){ if(e.textContent===msg){ e.textContent=""; e.className="range-hint"; } },4000);
}
function applyRangeEdge(edge, iso){
  if(!iso){ renderRange(); return; }
  state.range[edge]=iso; normalizeRange(); rangeHint(""); renderAll();
}
function bindRangeField(edge){
  var pick=document.getElementById("range-"+edge), text=document.getElementById("range-"+edge+"-text");
  if(pick) pick.onchange=function(){ if(this.value) applyRangeEdge(edge,this.value); };
  if(!text) return;
  text.onchange=function(){
    var iso=parseTypedDate(this.value);
    if(iso) applyRangeEdge(edge,iso);
    else { rangeHint("Ngày không hợp lệ — nhập theo dd/mm/yyyy."); renderRange(); }
  };
  text.onkeydown=function(ev){ if(ev.key==="Enter"){ ev.preventDefault(); this.blur(); } };
}
function renderRange(){
  var s=document.getElementById("range-start"), e=document.getElementById("range-end");
  if(s) s.value = state.range.start;
  if(e) e.value = state.range.end;
  var st=document.getElementById("range-start-text"), et=document.getElementById("range-end-text");
  if(st) st.value = fmtRangeDateVI(state.range.start);
  if(et) et.value = fmtRangeDateVI(state.range.end);
  var host=document.getElementById("range-presets"); if(!host) return;
  host.innerHTML="";
  RANGE_PRESETS.forEach(function(p){
    var r=presetRange(p[1]);
    var active = r.start===state.range.start && r.end===state.range.end;
    var b=document.createElement("button"); b.className="time-btn"+(active?" active":""); b.textContent=p[0];
    b.onclick=function(){ state.range={start:r.start,end:r.end}; renderAll(); };
    host.appendChild(b);
  });
}
/* Quý trước = quý liền trước quý chứa ngày dữ liệu mới nhất. */
function prevQuarterRange(){
  var end=maxDataDate(), y=end.getUTCFullYear(), q=Math.floor(end.getUTCMonth()/3);
  if(q===0){ y-=1; q=3; } else { q-=1; }
  var sm=q*3;
  return {
    label:"Q"+(q+1)+"/"+y,
    start:toISO(new Date(Date.UTC(y,sm,1))),
    end:toISO(new Date(Date.UTC(y,sm+3,0)))
  };
}
function renderStatus(){
  set("status-period", esc(fmtRangeDateVI(state.range.start)+" → "+fmtRangeDateVI(state.range.end)));
  set("header-data-date", esc(fmtDateUS(toISO(maxDataDate()))));
}


/* ═══════════════ BỘ LỌC ═══════════════ */
function buildDepartmentFilterOptions(rows){
  var names=[], seen={};
  var allUnits = Array.isArray(ORG_UNITS) ? ORG_UNITS.slice() : [];

  if(!allUnits.length && rows && rows.length){
    rows.forEach(function(r){
      var u=unitOfRow(r);
      if(!u || isExcludedUnit(u)) return;
      var root=reportingRootOf(u.id)||u;
      if(!seen[root.name]){ seen[root.name]=true; names.push(root.name); }
    });
    return names.sort();
  }

  allUnits.forEach(function(u){
    if(!u || isExcludedUnit(u)) return;
    if(!seen[u.name]){ seen[u.name]=true; names.push(u.name); }
  });

  /* ORG_UNITS chỉ có đơn vị đến từ cây tổ chức trong database. Sáu project Google
     Cloud Console không có cây, nên phòng ban của chúng — theo quy ước, chính là
     tên agent — sống dưới dạng đơn vị "auto:" do unitOf() dựng khi gặp dòng usage
     đầu tiên. Thiếu vòng lặp này thì bảng bên dưới CÓ hàng cho chúng mà ô lọc
     phòng ban lại KHÔNG có tên để chọn.

     "Chưa quy được" ở lại ngoài: nó là sọt đựng, không phải phòng ban. */
  (typeof unitRoots === "function" ? unitRoots() : []).forEach(function(u){
    if(!u || !u.auto || isExcludedUnit(u) || isUnattributedUnit(u)) return;
    if(!seen[u.name]){ seen[u.name]=true; names.push(u.name); }
  });

  return names.sort();
}
/* CHỈ DỰNG LẠI <option> KHI DANH SÁCH THẬT SỰ ĐỔI.

   renderFilters() chạy trong MỌI renderAll(), mà renderAll() lại được gọi từ
   chính onchange của select này. Bản cũ gán `el.innerHTML` vô điều kiện: nó đập
   bỏ và dựng lại toàn bộ <option> NGAY TRONG lúc trình duyệt còn đang xử lý sự
   kiện change của đúng phần tử đó. Cây <option> mới mang thuộc tính `selected`
   dựng từ `val`, nên trình duyệt đồng bộ `el.value` về theo nó và lựa chọn
   người dùng vừa bấm bị ghi đè. Lần bấm kế tiếp rơi đúng vào giá trị mà select
   đang giữ ⇒ KHÔNG sinh sự kiện change ⇒ dashboard đứng im. Triệu chứng đúng
   như báo: chọn lần đầu ăn, chọn lần sau không làm mới.

   Danh sách lựa chọn hầu như không đổi giữa hai lần vẽ, nên so chữ ký trước;
   giống thì không đụng vào DOM, chỉ đặt lại `value`. Và gắn onchange MỘT lần
   thay vì gắn lại sau mỗi lần vẽ.

   Mỗi <option> mang `value` tường minh: không có nó thì trình duyệt lấy phần
   chữ làm giá trị, mà phần chữ bị cắt và gộp khoảng trắng — tên đơn vị có hai
   dấu cách liền nhau sẽ không bao giờ khớp lại được với `state.filters`. */
function escAttr(s){ return esc(s).replace(/"/g,"&quot;"); }
function fillSelect(id, opts, val, allLabel){
  var el=document.getElementById(id); if(!el) return;
  var sig=JSON.stringify([allLabel].concat(opts));
  if(el.getAttribute("data-opt-sig")!==sig){
    el.innerHTML = "<option value=\"\">"+esc(allLabel)+"</option>" +
      opts.map(function(o){ return "<option value=\""+escAttr(o)+"\">"+esc(o)+"</option>"; }).join("");
    el.setAttribute("data-opt-sig", sig);
  }
  var muon = val==null ? "" : String(val);
  if(el.value!==muon) el.value=muon;
  if(!el.getAttribute("data-filter-bound")){
    el.setAttribute("data-filter-bound","1");
    el.onchange = function(){
      var key=id.split("-")[1];
      state.filters[key] = this.value;
      // Đổi phòng ban ⇒ đường đi drilldown của ma trận không còn hợp lệ, đưa về cấp gốc.
      // Đổi phòng ban lọc thì cây ma trận đang bung không còn nghĩa gì, thu về gốc.
      if(key==="dept") state.matrixExpanded={};
      renderAll();
    };
  }
}
/* ─── Dòng nào quy được về một người dùng ─── */
/* Dùng lại `userFilterLabel`: nó đã biết trả "" khi nhãn TRÙNG TÊN AGENT — tức
   chỗ đó không có danh tính người nào, chỉ có tên agent. Viết lại phép nhận
   biết ở đây là tạo cơ hội cho hai chỗ lệch nhau. */
function rowHasUserIdentity(r){
  return !!userFilterLabel({ a: r && r.a, ug: r && r.ug });
}

/* Phần bị bộ lọc user LOẠI vì nguồn không ghi được người dùng.
   Áp mọi bộ lọc khác TRỪ user (cùng thủ thuật renderFilters đang dùng cho ô
   User), rồi đếm phần không có danh tính. */
function userScopeGap(){
  if(!state.filters.user) return null;
  var giu = state.filters.user;
  state.filters.user = "";
  var trongPhamVi;
  try { trongPhamVi = scopedRows(); } finally { state.filters.user = giu; }
  var thieu = trongPhamVi.filter(function(r){ return !rowHasUserIdentity(r); });
  if(!thieu.length) return null;
  var a = aggregate(thieu);
  var agents = distinct(thieu.map(function(r){ return r.a; }).filter(Boolean));
  return { rows: thieu.length, requests: a.r, tokens: a.tokens, agents: agents };
}

function renderUserScopeNote(){
  var box = document.getElementById("user-scope-note");
  var txt = document.getElementById("user-scope-text");
  if(!box || !txt) return;
  var g = userScopeGap();
  if(!g){ box.hidden = true; txt.textContent = ""; return; }
  box.hidden = false;
  /* Nói bằng con số, không nói chung chung. "Một số dòng bị bỏ" thì người đọc
     không biết là 3 dòng hay 3.000. */
  txt.innerHTML = "Đang lọc theo user <b>" + esc(state.filters.user) + "</b>. "
    + "<b>" + fmt(g.rows) + " dòng</b> (" + fmt(g.requests) + " request, "
    + fmtTok(g.tokens) + ") bị bỏ ra ngoài vì nguồn <b>không ghi được người dùng</b> — "
    + "không phải vì chúng bằng không. "
    + (g.agents.length
        ? "Thuộc " + (g.agents.length === 1
            ? "agent " + esc(g.agents[0])
            : g.agents.length + " agent: " + esc(g.agents.slice(0,3).join(", "))
              + (g.agents.length > 3 ? "…" : ""))
          + ". "
        : "")
    + "Bỏ lọc user để thấy lại phần này.";
}

function renderFilters(){
  var rows=allDayRows();
  var deptNames = buildDepartmentFilterOptions(rows);
  if(state.filters.dept && deptNames.indexOf(state.filters.dept)<0){ state.filters.dept=""; }
  fillSelect("f-dept", deptNames, state.filters.dept, "Tất cả phòng ban");
  /* Ô lọc User CẮT THEO PHÒNG BAN ĐANG CHỌN. Chọn một phòng ban rồi mở ô User
     mà vẫn thấy cả 937 người là bắt người dùng tự lọc bằng mắt. filterAccounts()
     đã áp đúng luật phòng ban (so theo unitId nên đơn vị con cũng khớp phòng ban
     cha), nên dùng lại nó — nhưng KHÔNG áp chính bộ lọc User, nếu không danh sách
     tự thu về đúng một tên và không đổi sang ai được nữa. */
  var userPool=(function(){
    var giu=state.filters.user;
    state.filters.user="";
    try{ return filterAccounts(); } finally { state.filters.user=giu; }
  })();
  var userList = distinct(userPool.map(userFilterLabel).filter(Boolean));
  if(state.filters.user && userList.indexOf(state.filters.user)<0){ state.filters.user=""; }
  fillSelect("f-user", userList, state.filters.user, "Tất cả user");
  fillSelect("f-provider", distinct(rows.map(function(r){return modelProvider(r.m);})), state.filters.provider, "Tất cả provider");
  // Model phụ thuộc Provider đang chọn: chọn provider ⇒ chỉ hiện model của provider đó.
  var modelOpts = Object.keys(state.pricing);
  if(state.filters.provider){ modelOpts = modelOpts.filter(function(m){ return modelProvider(m)===state.filters.provider; }); }
  if(state.filters.model && modelOpts.indexOf(state.filters.model)<0){ state.filters.model=""; }
  fillSelect("f-model", modelOpts, state.filters.model, "Tất cả model");
  fillSelect("f-agent", distinct(rows.map(function(r){return r.a;})), state.filters.agent, "Tất cả agent");
}

/* ═══════════════ BẢNG GIÁ (sửa rồi bấm 💾 Lưu bảng giá) ═══════════════ */
function configMsg(t, err){ var e=document.getElementById("config-msg"); if(!e) return; e.textContent=t; e.className="config-msg"+(err?" error":""); setTimeout(function(){ if(e.textContent===t) e.textContent=""; },3500); }
function renderPricing(){
  var el=document.getElementById("price-grid"); if(!el) return;
  el.innerHTML = "<div class='ph'>Model</div><div class='ph' style='text-align:right'>Input USD/1M</div><div class='ph' style='text-align:right'>Output USD/1M</div><div></div>";
  Object.keys(state.pricing).forEach(function(m){
    var p=state.pricing[m];
    var name=document.createElement("div"); name.textContent=m;
    var i=priceInput(p.i, function(v){ state.pricing[m].i=v; });
    var o=priceInput(p.o, function(v){ state.pricing[m].o=v; });
    var x=document.createElement("button"); x.className="icon-x"; x.innerHTML="&times;"; x.title="Xoá model";
    x.onclick=function(){ if(Object.keys(state.pricing).length<=1){ configMsg("Cần giữ ít nhất 1 model.",true); return; } delete state.pricing[m]; renderPricing(); };
    el.appendChild(name); el.appendChild(i); el.appendChild(o); el.appendChild(x);
  });
}
function priceInput(val, on){ var i=document.createElement("input"); i.type="number"; i.step="0.01"; i.value=val; i.onchange=function(){ on(num(this.value)); }; return i; }

/* ═══════════════ BẢNG DỮ LIỆU NGUỒN (editable, theo ngày) ═══════════════ */
function td(child){ var t=document.createElement("td"); t.appendChild(child); return t; }

/* ═══════════════ CSV ═══════════════ */
function csv(v){ v=v==null?"":String(v); return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v; }
function exportCSV(){
  var rows=scopedRows();
  var period = state.range.start+" → "+state.range.end;
  /* Cột `Nguồn tiền` là bắt buộc, không phải trang trí: 28,2% số tiền trên
     dashboard suy từ bảng giá chứ không từ hoá đơn. Số mang ra khỏi màn hình mà
     mất dấu vết thì người nhận file không có cách nào biết - và file CSV thường
     đi xa hơn màn hình, vào bảng tính rồi vào báo cáo. */
  /* `sep=,` là dòng chỉ thị Excel hiểu ở mọi vùng miền (kể cả Excel tiếng Việt,
     nơi dấu phẩy thập phân khiến Excel mặc định tách cột bằng dấu chấm phẩy) -
     thiếu dòng này thì Excel tiếng Việt gộp cả dòng vào một cột duy nhất. BOM
     (`﻿`) đứng đầu file để Excel nhận đúng UTF-8, không thì "Kỳ", "Phòng
     ban", "Chi phí VNĐ" hiện thành ký tự vỡ. */
  var lines=["sep=,",
             "Kỳ,Agent,Phòng ban,Model,Provider,Users,Chat,Token in,Token out,"
            +"Request,Lỗi %,Chi phí USD,Chi phí VNĐ,Tỷ giá cấu hình,Nguồn tiền"];
  rows.forEach(function(r){
    var nguon = r.cost!=null ? "hoá đơn"
              : (costOrNull(r)!=null ? "suy từ bảng giá" : "không tính được");
    lines.push([period,r.a,r.d,r.m,modelProvider(r.m),r.u,r.c,r.ti,r.to,r.r,
                num(r.er).toFixed(2),cost(r).toFixed(2),toVnd(cost(r)),VND_RATE,
                nguon].map(csv).join(","));
  });
  var blob=new Blob(["﻿"+lines.join("\n")],{type:"text/csv;charset=utf-8;"});
  var url=URL.createObjectURL(blob); var a=document.createElement("a");
  a.href=url; a.download="token-ledger_"+state.range.start+"_"+state.range.end+".csv"; a.click(); URL.revokeObjectURL(url);
}

/* ═══════════════ RENDER TỔNG ═══════════════ */
var activeTab = "overview";
function renderChartsFor(tab, rows){
  rows = rows || scopedRows();
  switch(tab){
    case "overview": chartsOverview(rows); break;
    // Tab hợp nhất: phần phòng ban và phần user cùng nằm trong div#departments.
    case "departments": chartsDepartments(rows); chartsUsers(rows); break;
    case "agents": chartsAgents(rows); break;
    // Tab hợp nhất: phần nhà cung cấp và phần model cùng nằm trong div#providers.
    case "providers": chartsProviders(rows); chartsModels(rows); break;
    case "cost": chartsCost(rows); break;
    case "performance": chartsPerformance(rows); break;
  }
}
function renderAll(){
  renderRange();
  renderStatus();
  renderFilters();
  renderUserScopeNote();
  renderPricing();
  var rows = scopedRows();
  // Phân bổ lại số liệu tài khoản theo kỳ + bộ lọc hiện tại TRƯỚC mọi renderer,
  // để tổng ở cấp tài khoản luôn khớp tổng phòng ban của đúng phạm vi đang xem.
  applyAccountAllocation(rows);
  renderOverview(rows); renderDepartments(rows); renderAgents(rows); renderProviders(rows);
  renderModels(rows); renderUsers(rows); renderCost(rows); renderPerformance(rows);
  renderChartsFor(activeTab, rows);
  saveState();
}

/* ═══════════════ THEME (dark / sáng) ═══════════════ */
function currentTheme(){ return document.body.classList.contains("light-theme") ? "light" : "dark"; }
function applyTheme(t){
  document.body.classList.toggle("light-theme", t==="light");
  var b=document.getElementById("btn-theme"); if(b) b.textContent = (t==="light") ? "🌙 Tối" : "☀️ Sáng";
  if(typeof Chart !== "undefined"){
    Chart.defaults.color = (t==="light") ? "#475569" : "#94a3b8";
    Chart.defaults.borderColor = (t==="light") ? "#e2e8f0" : "#1e293b";
  }
  try{ localStorage.setItem(THEME_STORE, t); }catch(e){}
}

/* ═══════════════ WIRING ═══════════════ */
function init(){
  if(typeof Chart !== "undefined"){
    Chart.defaults.color = "#94a3b8";
    Chart.defaults.borderColor = "#1e293b";
    Chart.defaults.font.family = "Inter, sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
  }
  state = loadState();
  // Danh mục tài khoản dựng SAU khi state đã nạp, để lấy đúng agent/model của từng đơn vị.
  USER_ACCOUNTS = buildAccountCatalogue();

  // tabs
  try{
    var queryTab=new URLSearchParams(window.location.search).get("tab");
    var t=queryTab||localStorage.getItem(TAB_STORE);
    if(t&&document.getElementById(t)) activeTab=t;
  }catch(e){}
  document.querySelectorAll(".tab").forEach(function(t){
    t.classList.toggle("active", t.dataset.tab===activeTab);
    t.onclick=function(){
      activeTab=t.dataset.tab;
      document.querySelectorAll(".tab").forEach(function(x){ x.classList.toggle("active", x===t); });
      document.querySelectorAll(".tab-content").forEach(function(c){ c.classList.toggle("active", c.id===activeTab); });
      try{ localStorage.setItem(TAB_STORE, activeTab); }catch(e){}
      renderChartsFor(activeTab);
      window.scrollTo(0,0);
    };
  });
  document.querySelectorAll(".tab-content").forEach(function(c){ c.classList.toggle("active", c.id===activeTab); });

  // toolbar buttons
  document.getElementById("btn-config").onclick=function(){ document.getElementById("pricing-panel").classList.toggle("open"); };
  document.getElementById("btn-export").onclick=exportCSV;
  var themeBtn=document.getElementById("btn-theme");
  if(themeBtn) themeBtn.onclick=function(){ applyTheme(currentTheme()==="light"?"dark":"light"); renderAll(); };

  document.getElementById("f-reset").onclick=function(){ state.filters={dept:"",user:"",provider:"",model:"",agent:""}; renderAll(); };

  // global time range — mỗi mốc có 1 ô gõ tay (dd/mm/yyyy) + 1 ô lịch, luôn đồng bộ.
  bindRangeField("start"); bindRangeField("end");
  document.getElementById("co-groupby").onchange=function(){ var rows=scopedRows(); renderCostTable(rows); if(activeTab==="cost") chartsCost(rows); };

  // pricing: add model + lưu bảng giá
  var preset=document.getElementById("preset-model"), custom=document.getElementById("custom-model");
  preset.onchange=function(){ custom.style.display=this.value==="__custom__"?"inline-block":"none"; if(this.value==="__custom__") custom.focus(); };
  document.getElementById("add-model-btn").onclick=function(){
    var name = preset.value==="__custom__" ? custom.value.trim() : preset.value.trim();
    if(!name){ configMsg("Chọn model có sẵn hoặc nhập tên model.", true); return; }
    if(state.pricing[name]){ configMsg("Model \""+name+"\" đã có trong danh sách.", true); return; }
    state.pricing[name]={i:0,o:0};
    preset.value=""; custom.value=""; custom.style.display="none";
    configMsg("Đã thêm \""+name+"\" — điền giá rồi bấm 💾 Lưu bảng giá.", false);
    renderPricing();
  };
  var savePriceBtn=document.getElementById("save-price-btn");
  if(savePriceBtn) savePriceBtn.onclick=function(){ saveState(); renderAll(); configMsg("✅ Đã lưu bảng giá — dashboard đã cập nhật.", false); };

  // theme đã lưu (mặc định dark) — set trước khi vẽ chart để màu chart khớp
  var savedTheme="dark"; try{ savedTheme=localStorage.getItem(THEME_STORE)||"dark"; }catch(e){}
  try{
    var themeParam=new URLSearchParams(window.location.search).get("theme");
    if(themeParam==="light"||themeParam==="dark") savedTheme=themeParam;
  }catch(e){}
  applyTheme(savedTheme);

  /* NẠP TRƯỚC, VẼ SAU. Trước 17/08/2026 chỗ này gọi renderAll() ngay, tức vẽ
     số cũ ra màn hình rồi mới hỏi backend — và nếu backend không trả lời thì
     "không có gì xảy ra", số cũ ở lại và trông y hệt số mới. Đã đo: ba thẻ to
     nhất (request / token / tiền) trùng nhau giữa hai trạng thái, nên mắt không
     bắt được. Giờ chỉ vẽ khung, và renderAll() chỉ chạy khi đã có dữ liệu thật. */
  wireKeyGate();
  renderShell();
  loadFromBackend();
}

/* ─── Trạng thái nạp dữ liệu ──────────────────────────────────────────────
   Ba hàm dưới đây là CHỖ DUY NHẤT nói với người xem về tình trạng dữ liệu.
   Chúng viết vào #load-note và thanh trạng thái, không viết vào chỗ nào khác. */

function loadNote(level, icon, html){
  var box=document.getElementById("load-note");
  if(!box) return;
  box.className = "load-note" + (level ? " "+level : "");
  box.hidden = false;
  var i=document.getElementById("load-note-icon"), t=document.getElementById("load-note-text");
  if(i) i.textContent = icon;
  if(t) t.innerHTML = html;
}
function hideLoadNote(){
  var box=document.getElementById("load-note");
  if(box) box.hidden = true;
}
function setConnIndicator(level, text){
  var d=document.getElementById("conn-dot"), t=document.getElementById("conn-text");
  if(d) d.className = "status-dot" + (level ? " "+level : "");
  if(t) t.textContent = text;
}

/* Khung trống kèm "đang nạp". KHÔNG vẽ số, và KHÔNG vẽ biểu đồ rỗng: một biểu
   đồ rỗng trông giống "kỳ này không có dữ liệu", tức đúng loại nhập nhằng mà
   thay đổi này đang đi dọn. */
function renderShell(){
  setConnIndicator("warning", "Đang nối database…");
  loadNote("", "⏳", "Đang nạp dữ liệu từ database…");
}

/* Nạp hỏng. Bốn lý do, bốn câu trả lời khác nhau — trước đây cả bốn đều thành
   `null` nên trông y hệt nhau. MỌI nhánh đều KHÔNG hiện con số nào. */
/* ─── Ô nhập khoá ─────────────────────────────────────────────────────────
   HAI trạng thái, KHÔNG dùng chung lời:

       chưa nhập khoá bao giờ   -> "dashboard cần một khoá"      (mức warn)
       máy chủ trả 401          -> "khoá không đúng, nhập lại"   (mức error)

   Gộp hai câu này lại là nói sai chuyện đang xảy ra với người mở lần đầu: họ
   chưa làm gì sai cả. Và nó cũng khác hẳn "chưa bật backend" - ba tình huống,
   ba hành động: nhập khoá / nhập lại khoá / chạy uvicorn.

   Khoá sai thì XOÁ khỏi localStorage luôn. Giữ lại thì mỗi lần tải trang là
   một dòng 401 nữa trong log máy chủ, và người dùng thấy "khoá không đúng"
   cho một khoá họ không hề vừa nhập. */
function showKeyGate(sai){
  var box=document.getElementById("key-gate"),
      msg=document.getElementById("key-gate-msg"),
      inp=document.getElementById("key-input"),
      btn=document.getElementById("key-submit");
  if(!box || !msg || !inp || !btn){
    /* Thiếu markup thì phải nói ra, không im lặng bỏ qua - im lặng ở đây nghĩa
       là dashboard trắng trơn mà không có chữ nào giải thích. */
    loadNote("error","⛔","<b>Thiếu ô nhập khoá trong <code>index.html</code>.</b> "
           + "Dashboard cần <code>#key-gate</code>, <code>#key-input</code>, "
           + "<code>#key-submit</code>.");
    return;
  }
  box.className = "key-gate" + (sai ? " wrong" : "");
  box.hidden = false;
  msg.innerHTML = sai
    ? "<b>Khoá không đúng.</b> Máy chủ trả <b>HTTP 401</b>. "
      + "Khoá có thể đã bị đổi — hỏi lại người dựng dashboard rồi nhập lại."
    : "<b>Dashboard cần một khoá để đọc dữ liệu.</b> "
      + "Backend không trả số nào khi chưa có khoá — đây là chủ ý, không phải lỗi.";
  hideLoadNote();
  setConnIndicator("error", sai ? "Khoá không đúng" : "Chưa nhập khoá");
  var p=document.getElementById("status-period"); if(p) p.textContent = "—";
  var h=document.getElementById("header-data-date"); if(h) h.textContent = "—";
  inp.value = "";
  try{ inp.focus(); }catch(e){}
}

function hideKeyGate(){
  var box=document.getElementById("key-gate");
  if(box) box.hidden = true;
}

/* Gắn sự kiện ĐÚNG MỘT LẦN. Markup nằm tĩnh trong index.html chứ không bơm
   bằng innerHTML, nên không phải gắn lại sau mỗi lần vẽ - và không có nút nào
   bị nhân đôi handler. */
function wireKeyGate(){
  var inp=document.getElementById("key-input"),
      btn=document.getElementById("key-submit");
  if(!inp || !btn) return;
  function gui(){
    var v=(inp.value||"").trim();
    if(!v){ try{ inp.focus(); }catch(e){} return; }
    if(!window.TokenLedgerAPI || !window.TokenLedgerAPI.datKhoa(v)){
      var m=document.getElementById("key-gate-msg");
      if(m) m.innerHTML = "<b>Trình duyệt không cho lưu khoá.</b> "
        + "Cửa sổ ẩn danh hoặc thiết lập chặn lưu trữ. Mở bằng cửa sổ thường.";
      return;
    }
    hideKeyGate();
    renderShell();
    loadFromBackend();
  }
  btn.addEventListener("click", gui);
  inp.addEventListener("keydown", function(e){ if(e.key==="Enter") gui(); });
}

function renderError(err){
  var addr = (err && err.apiBase) || "—";
  var html;
  switch(err && err.kind){
    /* Hai nhánh này TỰ VẼ rồi thoát - chúng cần một ô nhập, không phải một
       đoạn chữ. Đặt trước mọi nhánh khác để không rơi vào `default`. */
    case "need-key":
      showKeyGate(false);
      return;
    case "unauthorized":
      if(window.TokenLedgerAPI) window.TokenLedgerAPI.datKhoa("");
      showKeyGate(true);
      return;
  }
  switch(err && err.kind){
    case "file-protocol":
      html = "<b>Đang mở bằng <code>file://</code> nên không gọi được API.</b><br>"
           + "Dashboard chỉ hiển thị dữ liệu từ database — không còn dữ liệu dự phòng "
           + "nhúng trong mã. Cần chạy hai lệnh:<br>"
           + "<code>docker compose up -d</code> · "
           + "<code>python -m uvicorn backend.main:app --port 8000</code> · "
           + "<code>cd web &amp;&amp; python -m http.server 8080 --bind 127.0.0.1</code><br>"
           + "rồi mở <code>http://127.0.0.1:8080</code>.";
      break;
    case "unreachable":
      html = "<b>Không nối được backend.</b> Đã thử <code>"+addr+"</code>.<br>"
           + "Kiểm: database đã lên chưa (<code>docker compose ps</code>), backend đã chạy "
           + "chưa (<code>python -m uvicorn backend.main:app --port 8000</code>). "
           + "Backend ở địa chỉ khác thì thêm <code>?api=http://may-khac:8000</code> vào URL.";
      break;
    case "endpoint-error":
      html = "<b>Backend trả về lỗi.</b> Endpoint <code>"+(err.endpoint||"?")+"</code> "
           + "trả mã HTTP <b>"+(err.httpStatus||"?")+"</b> tại <code>"+addr+"</code>.<br>"
           + "Xem log của uvicorn để biết nguyên nhân. Dashboard không hiện số vì "
           + "một phần dữ liệu bị thiếu thì tổng sẽ sai mà không nói ra.";
      break;
    case "empty-database":
      html = "<b>Nối được backend, nhưng database chưa có dữ liệu sử dụng.</b><br>"
           + "Khác với không nối được: máy chủ trả lời bình thường, chỉ là "
           + "<code>/api/health</code> không báo khoảng ngày nào cho usage.<br>"
           + "Nạp dữ liệu bằng <code>python scripts/rebuild_db.py</code>, "
           + "rồi soát bằng <code>python scripts/audit_db.py</code>.";
      break;
    default:
      html = "<b>Không nạp được dữ liệu.</b> <code>"+addr+"</code> — "
           + ((err && err.message) || "không rõ nguyên nhân") + ".";
  }
  setConnIndicator("error", "Không có dữ liệu");
  loadNote("error", "⛔", html);
  var p=document.getElementById("status-period"); if(p) p.textContent = "—";
  var h=document.getElementById("header-data-date"); if(h) h.textContent = "—";
}

/* ─── Nạp dữ liệu thật từ backend đọc database ───────────────────────────
   DATABASE LÀ NGUỒN DUY NHẤT. Không còn dữ liệu nhúng để rơi về, nên hàm này
   là đường duy nhất đưa số lên màn hình — và MỌI nhánh thất bại đều phải nói
   ra, không nhánh nào được im lặng.

   Chạy SAU renderShell(): màn hình có khung và chữ "đang nạp", chưa có số nào.
   renderAll() chỉ được gọi trong nhánh thành công.

   BA ĐƯỜNG THOÁT IM LẶNG ĐÃ BỊ BỎ (17/08/2026):
       if(!window.TokenLedgerAPI) return;      -> giờ báo lỗi ra màn hình
       if(!kq) return;                          -> giờ đọc kq.error rồi báo
       if(!kq.dayOrder.length) return;          -> giờ báo "database rỗng"

   Ba lệnh `return` đó nghĩa là "không làm gì cả", nên số cũ ở lại trên màn
   hình và trông y hệt số mới. Dấu hiệu duy nhất là một dòng console.warn -
   phải mở DevTools mới thấy, mà không ai mở DevTools khi đang đọc báo cáo. */
function loadFromBackend(){
  if(!window.TokenLedgerAPI){
    renderError({ kind: "unknown",
                  message: "js/api.js không nạp được — kiểm thẻ <script> trong index.html" });
    return;
  }
  window.TokenLedgerAPI.load().then(function(kt){
    if(!kt || !kt.ok){ renderError(kt && kt.error); return; }
    hideKeyGate();
    var kq = kt.data;
    if(!kq.dayOrder || !kq.dayOrder.length){
      renderError({ kind: "empty-database",
                    message: "backend trả về 0 ngày dữ liệu",
                    apiBase: window.TokenLedgerAPI.base() });
      return;
    }
    state.days=kq.days;
    state.dayOrder=kq.dayOrder;
    if(Object.keys(kq.pricing||{}).length) state.pricing=kq.pricing;
    /* Bản chỉ mục thứ hai của cùng bảng giá, khoá theo model_id. CHÉP RIÊNG,
       không suy ra từ state.pricing: bảng kia khoá theo TÊN model, mà
       /api/usage-by-account chỉ trả `model_id`. Quên dòng này thì tiền theo
       phòng ban im lặng rơi hết về '—' - đã dính đúng vậy lúc apply 20/08. */
    if(Object.keys(kq.pricingById||{}).length) state.pricingById=kq.pricingById;
    /* Bảng tra model_id -> TÊN model. Cùng cái bẫy vừa nói ở trên, khác chỗ dùng:
       applyRealAccountUsage() cần nó để dựng `u.byModel`, và bộ lọc Model/Provider
       hỏi `u.byModel`. Quên dòng này thì mọi tài khoản có byModel rỗng, và chọn
       một model bất kỳ sẽ loại sạch bảng — đúng triệu chứng cũ, chỉ khác nguyên do. */
    if(Object.keys(kq.modelNameById||{}).length) state.modelNameById=kq.modelNameById;
    if(kq.fxRate && kq.fxRate.vnd_per_usd) VND_RATE=kq.fxRate.vnd_per_usd;
    state.activeDay=kq.dayOrder[kq.dayOrder.length-1];
    // Kỳ đang chọn có thể nằm ngoài khoảng dữ liệu vừa nạp — kéo về cuối kỳ.
    if(!state.range || state.range.end>state.activeDay || state.range.start<kq.dayOrder[0]){
      state.range={start:kq.dayOrder[Math.max(0,kq.dayOrder.length-30)], end:state.activeDay};
    }
    // Tỷ lệ áp dụng theo agent, tính TÍCH LUỸ trên toàn bộ dữ liệu (không đổi
    // theo thanh trượt ngày). Không có backend thì để rỗng và biểu đồ tự quay
    // về cách tính cũ theo phòng ban.
    /* Ngân sách từ ref_budget — nguồn DUY NHẤT. `aliases` đã bỏ: nó tồn tại để
       khớp tên agent cũ trong dữ liệu nhúng, mà dữ liệu nhúng không còn. Đã đối
       chiếu: cả 8 tên trong `dim_agent` tra ra `ref_budget` không cần alias nào.

       api.js chỉ đưa vào đây những agent CÓ `budget_usd`, nên agent chưa đặt
       hạn mức (Tools Quizzer) và agent đặt bằng token (Ralli) không xuất hiện —
       đúng ý: chúng phải hiện là "chưa đặt hạn mức USD", KHÔNG phải 0. */
    AGENT_MONTHLY_BUDGETS = (kq.budgets||[]).map(function(b){
      return {agent:b.agent, usd:b.usd};
    });
    MONTHLY_BUDGET = AGENT_MONTHLY_BUDGETS.reduce(function(s,x){return s+num(x.usd);},0);
    ADOPTION_BY_AGENT=kq.adoption||[];
    REAL_BY_ACCOUNT=kq.byAccount||[];
    REAL_ACCOUNTS=kq.accounts||[];
    /* THỨ TỰ QUAN TRỌNG: nhận cây từ database TRƯỚC, rồi mới dựng danh mục tài
       khoản. buildAccountCatalogue() tra đơn vị của từng tài khoản, nên chạy nó
       trên cây cũ sẽ gán 937 tài khoản vào các đơn vị sắp bị thay. */
    NO_BILLING_AGENTS = kq.noBillingAgents || {};
    if(!adoptOrgUnits(kq.units)) rebuildProvisionedFromDirectory();
    USER_ACCOUNTS=buildAccountCatalogue();
    renderAll();
    renderDataProvenance(kq);
  });
}

/* ─── Nói rõ số liệu đang xem đáng tin đến đâu ─────────────────────────────
   Backend đã tính sẵn mọi thứ ở đây và đã gắn cảnh báo độ phủ vào chính
   /api/usage-by-account để người gọi không phải nhớ đi hỏi /api/health. Bỏ
   chúng ở tầng hiển thị là làm mất công đó, và làm người xem tin con số hơn
   mức nó đáng được. */
function renderDataProvenance(kq){
  var connRow = document.querySelector(".status-indicator");
  if(connRow) connRow.hidden = true;

  var wrap=document.getElementById("freshness-wrap");
  if(wrap) wrap.hidden = true;

  hideLoadNote();
}



if(document.readyState==="loading") document.addEventListener("DOMContentLoaded", init);
else init();
})();
