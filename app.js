/* ═══════════════════════════════════════════════════════════════════════
   Agent Analytics · Token Ledger — engine data-driven
   Mô hình dữ liệu: state → days (nhập theo NGÀY) → rows + pricing.
   Mọi chỉ số/biểu đồ/bảng được TÍNH từ rows. Sửa dữ liệu/giá rồi bấm
   "💾 Lưu" ⇒ dashboard tính lại. (v5: chuyển từ nhập theo tháng → theo ngày.)
   ═══════════════════════════════════════════════════════════════════════ */
(function(){
"use strict";

/* ─── Hằng số ─── */
var STORE = "agent-dash-state-v19-du-lieu-13-08"; // v19: dữ liệu tới 13/08/2026 (billing + monitoring gộp 2 đợt + Ralli/TLA HĐ)
var TAB_STORE = "agent-dash-tab";
var THEME_STORE = "agent-dash-theme";
var RANGE_PRESETS = [["7 ngày",7],["30 ngày",30],["90 ngày",90],["Tất cả",null]]; // preset time-range (kiểu Open WebUI)
var AGENT_MONTHLY_BUDGETS = [
  {agent:"Trợ Lý Ảo Hợp Đồng",usd:20,aliases:["Chatbot hợp đồng"]},
  {agent:"Chatbot Contact Center",usd:30,aliases:["Contact Center"]},
  {agent:"Phân Loại Dữ Liệu CRM",usd:20,aliases:["CRM Feedback"]},
  {agent:"Phân Loại Phản Hồi Tiếp Thị",usd:20,aliases:["DMS Feedback"]},
  {agent:"Multi modal AI Invoice",usd:20,aliases:["Multi Modal"]},
  {agent:"Sale Agent",usd:50,aliases:["Sale agent"]}
]; // Theo cấu hình Google Cloud; Tools quizzer được loại khỏi danh sách.
var BUDGET_ALERT_THRESHOLDS = [50,90,100];
var MONTHLY_BUDGET = AGENT_MONTHLY_BUDGETS.reduce(function(sum,item){return sum+item.usd;},0);
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
var EXCLUDED_DEPARTMENTS = {"Đang trong quá trình thử nghiệm":true};
var EXCLUDED_AGENTS = {"tools quizzer":true,"tool quizzer":true,"tools quizz":true,"tool quizz":true};
var SEED_DAY = "2026-07-01";                   // ngày gắn dữ liệu tổng hợp tháng 7 (seed)

/* ═══════════════ CÂY ĐƠN VỊ ═══════════════
   Nguồn dữ liệu usage đặt tên phòng ban tự do: mỗi agent trong file Excel là một khối
   riêng và mỗi khối dùng một quy ước viết tắt khác nhau, nên cùng một đơn vị xuất hiện
   dưới nhiều tên (PBH1 / Phòng Bán hàng 1, TMĐT / Thương mại điện tử, C4LED / TT C4LED).
   ORG_UNITS + UNIT_ALIASES là nguồn sự thật duy nhất để mỗi đơn vị chỉ xuất hiện MỘT lần.

   Cây Ralli và số user phân quyền lấy trực tiếp từ data/phong_ban_phan_quyen.xlsx,
   theo mức thụt lề trong sheet "Cơ cấu Tổ chức". Alias tiếp tục chuẩn hóa tên viết tắt
   giữa file usage và file phân quyền: PBH1 / Phòng Bán hàng 1, TMĐT / Thương mại điện tử,
   C4LED / TT C4LED.
   ═══════════════════════════════════════════ */
var ORG_UNITS = [
  {id:"company",name:"Toàn công ty",parent:null,level:1,provisioned:887},
  {id:"rd-corp",name:"Tổng công ty Rạng Đông",parent:"company",level:2,provisioned:807},
  {id:"pbh1",name:"PBH1",parent:"rd-corp",level:3,provisioned:262},
  {id:"perm-004",name:"Vùng 1",parent:"pbh1",level:4,provisioned:58},
  {id:"perm-005",name:"Đội chuyên trách - Vùng 1",parent:"perm-004",level:5,provisioned:7},
  {id:"perm-006",name:"Đội 1 - Nam Định",parent:"perm-004",level:5,provisioned:6},
  {id:"perm-007",name:"Đội 2 - Thái Bình",parent:"perm-004",level:5,provisioned:6},
  {id:"perm-008",name:"Đội 3 - Hà Nam - Ninh Bình",parent:"perm-004",level:5,provisioned:5},
  {id:"perm-009",name:"Đội 4 - Thanh Hoá",parent:"perm-004",level:5,provisioned:13},
  {id:"perm-010",name:"Đội 5 - Nghệ An - Hà Tĩnh",parent:"perm-004",level:5,provisioned:11},
  {id:"perm-011",name:"Vùng 2",parent:"pbh1",level:4,provisioned:87},
  {id:"perm-012",name:"Đội chuyên trách - Vùng 2",parent:"perm-011",level:5,provisioned:4},
  {id:"perm-013",name:"Đội 1 - Hà Nội",parent:"perm-011",level:5,provisioned:10},
  {id:"perm-014",name:"Đội 2 - Hà Nội",parent:"perm-011",level:5,provisioned:8},
  {id:"perm-015",name:"Đội 3 - Hà Nội",parent:"perm-011",level:5,provisioned:10},
  {id:"perm-016",name:"Đội 4 - Bắc Ninh",parent:"perm-011",level:5,provisioned:8},
  {id:"perm-017",name:"Đội 5 - Bắc Giang - Lạng Sơn",parent:"perm-011",level:5,provisioned:10},
  {id:"perm-018",name:"Đội 6 - Hưng Yên",parent:"perm-011",level:5,provisioned:6},
  {id:"perm-019",name:"Đội 7 - Hải Dương - Hải Phòng",parent:"perm-011",level:5,provisioned:12},
  {id:"perm-020",name:"Đội 8 - Quảng Ninh",parent:"perm-011",level:5,provisioned:6},
  {id:"perm-021",name:"Vùng 3",parent:"pbh1",level:4,provisioned:73},
  {id:"perm-022",name:"Đội chuyên trách - Vùng 3",parent:"perm-021",level:5,provisioned:3},
  {id:"perm-023",name:"Đội 1 - HN2 - Sơn La - Điện Biên",parent:"perm-021",level:5,provisioned:18},
  {id:"perm-024",name:"Đội 2 - HN2 - Hoà Bình",parent:"perm-021",level:5,provisioned:8},
  {id:"perm-025",name:"Đội 3 - Vĩnh Phúc",parent:"perm-021",level:5,provisioned:5},
  {id:"perm-026",name:"Đội 4 - Thái Nguyên - Cao Bằng",parent:"perm-021",level:5,provisioned:5},
  {id:"perm-027",name:"Đội 5 - Phú Thọ",parent:"perm-021",level:5,provisioned:5},
  {id:"perm-028",name:"Đội 6 - Yên Bái - Tuyên Quang - Hà Giang - Lào Cai - Lai Châu",parent:"perm-021",level:5,provisioned:19},
  {id:"perm-029",name:"TT1",parent:"pbh1",level:4,provisioned:15},
  {id:"perm-030",name:"TT1",parent:"perm-029",level:5,provisioned:0},
  {id:"perm-031",name:"Đội chuyên trách 1 - trung tâm 1",parent:"perm-029",level:5,provisioned:4},
  {id:"perm-032",name:"Đội Chuyên Trách 2",parent:"perm-029",level:5,provisioned:0},
  {id:"pbh2",name:"PBH2",parent:"rd-corp",level:3,provisioned:155},
  {id:"perm-034",name:"CN Đà Nẵng",parent:"pbh2",level:4,provisioned:51},
  {id:"perm-035",name:"Đội Bình Định",parent:"perm-034",level:5,provisioned:6},
  {id:"perm-036",name:"Đội Đà Nẵng",parent:"perm-034",level:5,provisioned:6},
  {id:"perm-037",name:"Đội Huế",parent:"perm-034",level:5,provisioned:3},
  {id:"perm-038",name:"Đội Quảng Bình",parent:"perm-034",level:5,provisioned:5},
  {id:"perm-039",name:"Đội Quảng Nam",parent:"perm-034",level:5,provisioned:4},
  {id:"perm-040",name:"Đội Quảng Trị",parent:"perm-034",level:5,provisioned:5},
  {id:"perm-041",name:"Đội chuyên trách - CN Đà Nẵng",parent:"perm-034",level:5,provisioned:6},
  {id:"perm-042",name:"CN Nha Trang",parent:"pbh2",level:4,provisioned:41},
  {id:"perm-043",name:"Đội Khánh Hòa",parent:"perm-042",level:5,provisioned:11},
  {id:"perm-044",name:"Đội Lâm Đồng",parent:"perm-042",level:5,provisioned:7},
  {id:"perm-045",name:"Đội Ninh Thuận",parent:"perm-042",level:5,provisioned:4},
  {id:"perm-046",name:"Đội Phú Yên",parent:"perm-042",level:5,provisioned:3},
  {id:"perm-047",name:"Đội chuyên trách - CN Nha Trang",parent:"perm-042",level:5,provisioned:4},
  {id:"perm-048",name:"Tây Nguyên",parent:"pbh2",level:4,provisioned:39},
  {id:"perm-049",name:"Đội Đắk Lắk",parent:"perm-048",level:5,provisioned:8},
  {id:"perm-050",name:"Đội Đắk Nông",parent:"perm-048",level:5,provisioned:4},
  {id:"perm-051",name:"Đội Gia Lai",parent:"perm-048",level:5,provisioned:9},
  {id:"perm-052",name:"Đội Kon Tum",parent:"perm-048",level:5,provisioned:4},
  {id:"perm-053",name:"Đội chuyên trách - Tây Nguyên",parent:"perm-048",level:5,provisioned:0},
  {id:"perm-054",name:"TT2",parent:"pbh2",level:4,provisioned:12},
  {id:"perm-055",name:"TT2",parent:"perm-054",level:5,provisioned:0},
  {id:"perm-056",name:"Đội 1 - TT2",parent:"perm-054",level:5,provisioned:2},
  {id:"perm-057",name:"Đội 2 - TT2",parent:"perm-054",level:5,provisioned:2},
  {id:"perm-058",name:"Đội 3 - TT2",parent:"perm-054",level:5,provisioned:1},
  {id:"perm-059",name:"Đội 4 - TT2",parent:"perm-054",level:5,provisioned:2},
  {id:"perm-060",name:"Đội 5 - TT2",parent:"perm-054",level:5,provisioned:1},
  {id:"perm-061",name:"Đội 6 - TT2",parent:"perm-054",level:5,provisioned:1},
  {id:"pbh3",name:"PBH3",parent:"rd-corp",level:3,provisioned:257},
  {id:"perm-063",name:"CN Hồ Chí Minh",parent:"pbh3",level:4,provisioned:74},
  {id:"perm-064",name:"Đội 1",parent:"perm-063",level:5,provisioned:9},
  {id:"perm-065",name:"Đội 2",parent:"perm-063",level:5,provisioned:7},
  {id:"perm-066",name:"Đội 3",parent:"perm-063",level:5,provisioned:8},
  {id:"perm-067",name:"Đội 4",parent:"perm-063",level:5,provisioned:8},
  {id:"perm-068",name:"Đội 5",parent:"perm-063",level:5,provisioned:11},
  {id:"perm-069",name:"Đội Siêu Thị",parent:"perm-063",level:5,provisioned:2},
  {id:"perm-070",name:"Đội chuyên trách - CN Hồ Chí Minh",parent:"perm-063",level:5,provisioned:10},
  {id:"perm-071",name:"CN Biên Hòa",parent:"pbh3",level:4,provisioned:54},
  {id:"perm-072",name:"Đội Bình Dương",parent:"perm-071",level:5,provisioned:6},
  {id:"perm-073",name:"Đội Bình Phước",parent:"perm-071",level:5,provisioned:8},
  {id:"perm-074",name:"Đội Bình Thuận",parent:"perm-071",level:5,provisioned:6},
  {id:"perm-075",name:"Đội Đồng Nai",parent:"perm-071",level:5,provisioned:9},
  {id:"perm-076",name:"Đội Vũng Tàu",parent:"perm-071",level:5,provisioned:9},
  {id:"perm-077",name:"Đội chuyên trách - CN Biên Hòa",parent:"perm-071",level:5,provisioned:4},
  {id:"perm-078",name:"CN Cần Thơ",parent:"pbh3",level:4,provisioned:67},
  {id:"perm-079",name:"Đội An Giang",parent:"perm-078",level:5,provisioned:5},
  {id:"perm-080",name:"Đội Kiên Giang",parent:"perm-078",level:5,provisioned:13},
  {id:"perm-081",name:"Đội Cần Thơ",parent:"perm-078",level:5,provisioned:11},
  {id:"perm-082",name:"Đội Sóc Trăng",parent:"perm-078",level:5,provisioned:7},
  {id:"perm-083",name:"Đội Cà Mau",parent:"perm-078",level:5,provisioned:7},
  {id:"perm-084",name:"Đội Bạc Liêu",parent:"perm-078",level:5,provisioned:6},
  {id:"perm-085",name:"Đội Campuchia",parent:"perm-078",level:5,provisioned:0},
  {id:"perm-086",name:"Đội chuyên trách - CN Cần Thơ",parent:"perm-078",level:5,provisioned:7},
  {id:"perm-087",name:"CN Tiền Giang",parent:"pbh3",level:4,provisioned:39},
  {id:"perm-088",name:"Đội Vĩnh Long",parent:"perm-087",level:5,provisioned:11},
  {id:"perm-089",name:"Đội Đồng Tháp",parent:"perm-087",level:5,provisioned:8},
  {id:"perm-090",name:"Đội Long An",parent:"perm-087",level:5,provisioned:5},
  {id:"perm-091",name:"Đội chuyên trách - CN Tiền Giang",parent:"perm-087",level:5,provisioned:4},
  {id:"perm-092",name:"TT3",parent:"pbh3",level:4,provisioned:14},
  {id:"perm-093",name:"TT4",parent:"pbh3",level:4,provisioned:5},
  {id:"pxk",name:"Xuất khẩu",parent:"rd-corp",level:3,provisioned:25},
  {id:"truyenthong",name:"Truyền thông",parent:"rd-corp",level:3,provisioned:7},
  {id:"ketoan",name:"Kế toán",parent:"rd-corp",level:3,provisioned:1},
  {id:"ecom",name:"TMĐT",parent:"rd-corp",level:3,provisioned:27},
  {id:"c4led",name:"C4LED",parent:"company",level:2,provisioned:13},
  {id:"nctt2",name:"Nghiên cứu thị trường",parent:"company",level:2,provisioned:12},
  {id:"kehoach",name:"Kế hoạch",parent:"company",level:2,provisioned:7},
  {id:"rnd",name:"Trung tâm R&D",parent:"company",level:2,provisioned:20},
  {id:"qths",name:"Quản trị hệ thống",parent:"company",level:2,provisioned:18},
  /* Đơn vị của các agent khác không nằm trong workbook phân quyền Ralli. */
  {id:"aemkt",name:"Anh Em tiếp thị",parent:null,level:1,provisioned:40},
  {id:"cskh",name:"Chăm sóc khách hàng",parent:null,level:1,provisioned:28},
  {id:"nctt",name:"P.NCTT",parent:null,level:1,provisioned:30},
  {id:"cpbd",name:"Công ty CPBĐ PN Rạng Đông",parent:null,level:1,provisioned:18},
  {id:"ttdl",name:"TTDL&ĐHS",parent:null,level:1,provisioned:6},
  {id:"tttmdt",name:"TT&TMĐT",parent:null,level:1,provisioned:3}
];
var UNIT_ALIASES = {
  "Toàn công ty":"company", "Tổng công ty Rạng Đông":"rd-corp",
  "PBH1":"pbh1", "Phòng Bán hàng 1":"pbh1",              // danh mục chuẩn: BH1
  "PBH2":"pbh2", "Phòng Bán hàng 2":"pbh2",              // danh mục chuẩn: BH2
  "PBH3":"pbh3", "Phòng Bán hàng 3":"pbh3",
  "TMĐT":"ecom", "Thương mại điện tử":"ecom",            // danh mục chuẩn: TMDT
  "TT C4LED":"c4led", "C4LED":"c4led",
  "Cty CPBĐ PN Rạng Đông":"cpbd", "Công ty CPBĐ PN Rạng Đông":"cpbd",
  "P.NCTT":"nctt",
  "P.NCTT , TTDL&ĐHS":"nctt", "P.NCTT, TTDL&ĐHS":"nctt", // fallback cho dữ liệu cũ trước khi tách
  "Anh Em tiếp thị":"aemkt", "Chăm sóc khách hàng":"cskh",
  "TTDL&DHS":"ttdl", "TTDL&ĐHS":"ttdl", "TT&TMĐT":"tttmdt", "Xuất khẩu":"pxk",
  "Truyền thông":"truyenthong", "Kế toán":"ketoan", "Kế hoạch":"kehoach",
  "Nghiên cứu thị trường":"nctt2", "Trung tâm R&D":"rnd", "Quản trị hệ thống":"qths"
};
/* Số tài khoản được cấp sẽ được dựng lại từ danh sách user Ralli đã làm sạch.
   Không dùng số demo hoặc số của agent khác cho các KPI/bảng người dùng. */
var DEPT_PROVISIONED = {};
var MODALITY = [["TEXT",86,"#667eea"],["IMAGE",9,"#10b981"],["AUDIO",4,"#f59e0b"],["VIDEO",1,"#8b5cf6"]];
var USER_HEAT = {
  cols: ["Sale Agent","Chatbot CC","CRM","Phản Hồi TT","Ralli","Hợp Đồng"],
  rows: ["Nhóm Sales","Nhóm CSKH","Nhóm Data","Nhóm Vận hành"],
  matrix: [[480,40,10,20,110,60],[30,400,5,8,0,4],[12,6,300,85,2,0],[88,13,4,0,8,24]]
};
var palette = ["#667eea","#3b82f6","#f59e0b","#10b981","#8b5cf6","#06b6d4","#ef4444","#64748b","#ec4899","#14b8a6"];

/* ═══════════════ DANH MỤC TÀI KHOẢN RALLI ═══════════════
   Nguồn usage KHÔNG có userId (mỗi dòng là tổng theo agent × phòng ban), nên không thể
   quy số liệu về từng tài khoản thật. Danh tính, tên và phòng ban lấy từ TLA Ralli;
   request/token chỉ được PHÂN BỔ từ tổng thật của phòng để các cấp drilldown cộng khớp.

   Vì vậy: số của từng tài khoản là SỐ PHÂN BỔ, không phải số đo. Mọi khối UI hiển thị
   số ở cấp tài khoản phải mang nhãn ALLOCATED_DATA_LABEL.

   Tách hai phần để tổng luôn khớp ở MỌI kỳ:
     buildAccountCatalogue()      → danh tính, tĩnh (không chứa số liệu)
     applyAccountAllocation(rows) → phân bổ theo kỳ + bộ lọc đang xem, chạy mỗi lượt render
   ═════════════════════════════════════════════════════════ */
var ALLOCATED_DATA_LABEL = "Số liệu phân bổ theo phòng ban";
var ALLOCATED_DATA_HINT = "Nguồn usage hiện tại không có định danh user. Số theo tài khoản là "
  + "số phân bổ từ tổng thật của phòng ban, không phải số đo theo từng tài khoản.";
var USER_ACCOUNTS = [];

/* Băm tiền định: cùng chuỗi luôn cho cùng số. Không dùng Math.random để mọi lần
   render và mọi lần tải trang đều cho cùng kết quả. */
function stableHash(str){
  var h=2166136261, s=String(str);
  for(var i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); }
  return (h>>>0);
}
/* Các agent/model/nhóm thực tế phục vụ từng đơn vị, đọc từ dữ liệu usage seed. */
function unitAgentProfiles(){
  // Ưu tiên dữ liệu đang nạp trong state; khi chưa có state thì dựng từ nguồn seed.
  var byUnit={}, sources=[];
  // Khi chưa có state, dựng danh mục từ hai bộ dữ liệu Excel tháng 6 và tháng 7.
  if(typeof state!=="undefined" && state && state.days) sources.push(state.days);
  else sources.push(buildJuneExcelWeeks(), SEED_DAYS);
  sources.forEach(function(src){
    if(!src) return;
    Object.keys(src).forEach(function(day){
      (src[day]||[]).forEach(function(r){
        var unit=unitOf(r.d);
        if(!unit||isExcludedUnit(unit)||!r.a) return;
        var list=byUnit[unit.id]=byUnit[unit.id]||[];
        if(!list.some(function(p){return p.a===r.a&&p.m===r.m;})) list.push({a:r.a,m:r.m,ug:r.ug});
      });
    });
  });
  return byUnit;
}
/* Tỷ lệ tài khoản có khả năng hoạt động của một đơn vị — cố định theo unitId. */
function adoptionRatio(unitId){ return 0.55 + (stableHash("adopt:"+unitId)%36)/100; }
function buildAccountCatalogue(){
  var out=[], byUnit={};
  (window.RALLI_USERS||[]).forEach(function(entry){
    var unit=unitOf(entry.department);
    if(!unit||isExcludedUnit(unit)) return;
    (byUnit[unit.id]=byUnit[unit.id]||[]).push({entry:entry,unit:unit});
  });
  Object.keys(byUnit).sort().forEach(function(unitId){
    var group=byUnit[unitId].sort(function(x,y){return x.entry.login.localeCompare(y.entry.login);});
    var eligible=Math.max(1,Math.round(group.length*adoptionRatio(unitId)));
    group.forEach(function(item,i){
      var entry=item.entry, unit=item.unit, h=stableHash(entry.login);
      var sourceActive=String(entry.status||"").trim().toLowerCase()==="hoạt động";
      out.push({
        user:entry.email||entry.login,
        login:entry.login, email:entry.email, n:entry.name,
        unitId:unit.id, d:entry.department,
        a:"Trợ lý ảo Ralli", m:"Gemini 2.5 Flash", ug:"Người dùng Ralli",
        // weight > 0 ⇒ tài khoản có thể nhận phân bổ; = 0 ⇒ luôn là tài khoản chưa dùng.
        weight: sourceActive&&i<eligible ? 1+(h%9) : 0,
        role:entry.accountType==="service"?"Tài khoản chức năng":(entry.role||"Nhân viên"),
        accountType:entry.accountType||"person", sourceStatus:entry.status||"",
        // File TLA Ralli.xlsx hiện chỉ có STT, Phòng ban, Họ tên, Tài khoản đăng nhập,
        // Tên đầy đủ, Tài khoản, Vai trò, trạng thái — chưa có cột ngày cấp. Khi nguồn
        // bổ sung, chỉ cần map vào đây là cột "Thời gian được cấp" và thẻ "Cấp mới
        // trong kỳ" cùng hoạt động, không phải sửa gì thêm.
        created:entry.created||"",
        disabled:!sourceActive,
        req:0, ti:0, to:0, last:"", active:false, quotaPct:0
      });
    });
  });
  return out;
}
/* Phân bổ số liệu THẬT xuống tài khoản, khoá theo CẶP (đơn vị, agent).
   Phải theo cặp, không chỉ theo đơn vị: nếu phân bổ tổng của phòng cho mọi tài khoản
   bất kể agent, thì một agent có 0 request trong kỳ vẫn nhận số khi drilldown, và
   ma trận cấp 1 (0 request) sẽ nói ngược với ma trận cấp 2. Khoá theo cặp giữ đồng
   thời hai bất biến: tổng theo phòng khớp, và tổng theo phòng × agent cũng khớp. */
function applyAccountAllocation(rows){
  var totals={};
  (rows||[]).forEach(function(r){
    var unit=unitOf(r.d);
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
   Mọi đơn giá dưới đây suy từ HOÁ ĐƠN Google: lấy số tiền thật chia cho số token
   thật trong data/billing/. Không chép từ trang giá.
   Hai giá đã sửa so với bản cũ:
     Gemini 2.5 Pro   giá ra  3.75 -> 10.00   (hoá đơn: $10.0000/1tr)
     Gemini 3.5 Flash 0/0     -> 1.50 / 9.00  (trước ghi là "chưa dùng", thực tế có dùng)
   Bốn model bổ sung vì có phát sinh thật nhưng chưa được khai báo. ─── */
var basePricing = {
  "Gemini 2.5 Flash":       {i:0.30, o:2.50},
  "Gemini 2.5 Flash Lite":  {i:0.10, o:0.40},
  "Gemini 2.5 Pro":         {i:1.25, o:10.00},
  "Gemini 2.0 Flash":       {i:0.10, o:0.40},
  "Gemini 3.0 Flash":       {i:0.50, o:3.00},
  "Gemini 3.1 Flash Lite":  {i:0.25, o:1.50},
  "Gemini 3.5 Flash":       {i:1.50, o:9.00},
  "Gemini 3 Pro":           {i:2.00, o:12.00},
  "Gemini Embedding 001":   {i:0.1510, o:0},
  "GPT-4o mini":            {i:0.15, o:0.60},   // OpenAI — giữ sẵn cho nhập thủ công
  "GPT-4o":                 {i:2.50, o:10.00}   // OpenAI — đã khai báo, chưa dùng
};

/* ═══════════════════════════════════════════════════════════════════
   SEED_DAYS — sinh tự động từ dữ liệu THẬT đã thu thập.
   Sinh bởi test/sinh_du_lieu_dashboard.py. KHÔNG sửa tay file này.

   Nguồn từng cột:
     ti / to / cached   Google Billing   (số tiền thật đã bị thu)
     r / er / lat       Google Monitoring (lọc generativelanguage,
                        chỉ GenerateContent + StreamGenerateContent)
     Ralli toàn bộ      bảng thô token_usage — Ralli không qua GCP
     u                  số tài khoản được cấp, gắn vào MỘT ngày duy nhất

   ⚠ Đơn vị của Trợ Lý Ảo Hợp Đồng là SỐ PHÂN BỔ: billing cho tổng theo
     ngày nhưng không có phòng ban, app cho phòng ban nhưng không có ngày.
   ═══════════════════════════════════════════════════════════════════ */
var SEED_DAYS = {
  "2026-01-01": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:887473,to:62972,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:98487,to:28858,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-02": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:211874,to:17884,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:43263,to:9993,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-03": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:319226,to:23882,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:51564,to:11203,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-04": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:276937,to:18948,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38006,to:11877,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-05": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:413048,to:29083,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:59535,to:12397,r:0,er:0.0,lat:0.0,cached:1650,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-06": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:416039,to:33011,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:81634,to:29608,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-07": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:831050,to:49242,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:120502,to:44197,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-08": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:362242,to:24171,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:52712,to:11132,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-09": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:264018,to:25136,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:77183,to:25352,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-10": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:197936,to:9334,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:22031,to:4304,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-11": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:268749,to:20381,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:41429,to:9452,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-12": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:216950,to:15854,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:61008,to:8296,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-13": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:142049,to:15056,r:0,er:0.0,lat:0.0,cached:7256,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:408839,to:31061,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:81953,to:10692,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-14": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15593,to:2915,r:0,er:0.0,lat:0.0,cached:617,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2009113,to:29877,r:0,er:0.0,lat:0.0,cached:367795,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1737432,to:91340,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:721598,to:48296,r:0,er:0.0,lat:0.0,cached:3318,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-15": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2315118,to:20246,r:0,er:0.0,lat:0.0,cached:796689,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1466845,to:105993,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:389140,to:61084,r:0,er:0.0,lat:0.0,cached:5799,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-16": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6222562,to:24400,r:0,er:0.0,lat:0.0,cached:2954848,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:651380,to:70527,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:141873,to:48547,r:0,er:0.0,lat:0.0,cached:842,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-17": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:63134,to:6993,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8996,to:1374,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-18": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:477819,to:6755,r:0,er:0.0,lat:0.0,cached:8053,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:553006,to:33828,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:59999,to:14876,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-19": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:53972,to:327,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:359596,to:22568,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:49034,to:10955,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-20": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2614015,to:24214,r:0,er:0.0,lat:0.0,cached:488437,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1722642,to:166385,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:388199,to:53113,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-21": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3 Pro",ug:"Nhóm CSKH",u:0,c:0,ti:11473,to:391,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:816181,to:6506,r:0,er:0.0,lat:0.0,cached:357772,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1005049,to:74006,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:175290,to:38860,r:0,er:0.0,lat:0.0,cached:1660,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-22": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:3724,to:394,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3 Pro",ug:"Nhóm CSKH",u:0,c:0,ti:161266,to:2703,r:41,er:0.0,lat:0.0,cached:97552,think:0,e4:0,e5:0,e429:0,eKnown:41,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:36598,to:1767,r:10,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:433610,to:34832,r:1,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:77187,to:9361,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-23": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3266756,to:29261,r:134,er:0.0,lat:0.0,cached:1371128,think:0,e4:0,e5:0,e429:0,eKnown:134,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:486758,to:32782,r:17,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:17,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:50493,to:11045,r:2,er:0.0,lat:0.0,cached:830,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:0.0}
  ],
  "2026-01-24": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:11037,to:174,r:84,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:84,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:226257,to:24095,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:46115,to:8910,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-25": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:34696,to:2544,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15168,to:422,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:225149,to:20705,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:43097,to:10344,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-26": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1572147,to:24019,r:7,er:0.0,lat:0.0,cached:119891,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:330465,to:28002,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:89239,to:21668,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:0.0}
  ],
  "2026-01-27": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7148784,to:82982,r:274,er:0.0,lat:0.0,cached:1906417,think:0,e4:0,e5:0,e429:0,eKnown:274,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1126810,to:66397,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:663916,to:60017,r:0,er:0.0,lat:0.0,cached:1660,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-28": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:963869,to:8659,r:274,er:0.0,lat:0.0,cached:274924,think:0,e4:0,e5:0,e429:0,eKnown:274,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:305790,to:0,r:86,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:86,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:100739,to:10093,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:17815,to:3319,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-29": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2581,to:209,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4719445,to:29476,r:0,er:0.0,lat:0.0,cached:2251614,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:946296,to:80017,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:246416,to:37064,r:0,er:0.0,lat:0.0,cached:1661,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-30": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1524518,to:17780,r:0,er:0.0,lat:0.0,cached:206936,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:117963,to:11385,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21629,to:3386,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-01-31": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:316109,to:29780,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:69906,to:17611,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-01": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:241849,to:7067,r:0,er:0.0,lat:0.0,cached:14076,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1042149,to:83776,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:220898,to:44508,r:0,er:0.0,lat:0.0,cached:1656,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-02": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:44222,to:37100,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15249,to:989,r:0,er:0.0,lat:0.0,cached:4079,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:66257,to:2066,r:0,er:0.0,lat:0.0,cached:3999,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:939849,to:82757,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:25104,to:16614,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:247465,to:54589,r:0,er:0.0,lat:0.0,cached:1658,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-03": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:867571,to:4944,r:0,er:0.0,lat:0.0,cached:56482,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:623765,to:44439,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:98325,to:102285,r:0,er:0.0,lat:0.0,cached:1657,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-04": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2581,to:210,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:472346,to:4949,r:0,er:0.0,lat:0.0,cached:269006,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:517377,to:35746,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:84123,to:30683,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-05": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2581,to:426,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:235883,to:7740,r:0,er:0.0,lat:0.0,cached:58318,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:712736,to:51542,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:97656,to:34629,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-06": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1248297,to:6376,r:0,er:0.0,lat:0.0,cached:754657,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:1273635,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:182258,to:21803,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:42587,to:12457,r:0,er:0.0,lat:0.0,cached:840,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-07": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:16232,to:2781,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:50354,to:838,r:0,er:0.0,lat:0.0,cached:16024,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:21910750,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:119657,to:13547,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:39052,to:10764,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-08": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1764387,to:12754,r:0,er:0.0,lat:0.0,cached:833271,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:1701390,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:201999,to:17794,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:60383,to:10363,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-09": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:10020,to:1027,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1141026,to:11169,r:0,er:0.0,lat:0.0,cached:468179,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:1439902,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:76579,to:5776,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:28422,to:10625,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-10": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4985,to:312,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4191566,to:33062,r:0,er:0.0,lat:0.0,cached:1615456,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:4082032,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:504379,to:46458,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:103386,to:30568,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-11": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:85835,to:10190,r:0,er:0.0,lat:0.0,cached:33647,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:204738,to:3315,r:0,er:0.0,lat:0.0,cached:28522,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:1438219,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:859647,to:70277,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:142858,to:47211,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-12": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:3388733,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:245900,to:22318,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:42461,to:15622,r:0,er:0.0,lat:0.0,cached:1680,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-13": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:682196,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:321822,to:15408,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:49738,to:20378,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-14": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:172683,to:11606,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:10924,to:4016,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-15": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:300794,to:12378,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:23427,to:11242,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-17": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:65652,to:5940,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:12361,to:3791,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-18": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:37296,to:3420,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8210,to:1870,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-19": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:480714,to:11640,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:32756,to:15956,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-20": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:8556,to:404,r:0,er:0.0,lat:0.0,cached:4017,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:323939,to:9027,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:24585,to:13900,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-21": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4989,to:208,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2804457,to:15624,r:0,er:0.0,lat:0.0,cached:1162731,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:2325689,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1131286,to:23461,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:65691,to:30488,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-22": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:19866,to:16424,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:5024,to:612,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:434562,to:6173,r:0,er:0.0,lat:0.0,cached:154647,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:198726,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1610086,to:60916,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:141750,to:61216,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-23": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:45115,to:4688,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:359726,to:5687,r:0,er:0.0,lat:0.0,cached:83199,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:243,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1060220,to:43589,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:125666,to:52807,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-24": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:719445,to:124967,r:0,er:0.0,lat:0.0,cached:170259,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:72854,to:2687,r:0,er:0.0,lat:0.0,cached:14124,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:87536,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:521604,to:32149,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:98039,to:97208,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-25": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:18265,to:3808,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:220125,to:40273,r:0,er:0.0,lat:0.0,cached:39763,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:86907,to:3150,r:0,er:0.0,lat:0.0,cached:12088,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:55564,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:666843,to:19100,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:67804,to:25722,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-26": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:575231,to:11767,r:0,er:0.0,lat:0.0,cached:208987,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:122,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1134557,to:42180,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:127492,to:40416,r:0,er:0.0,lat:0.0,cached:1682,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-27": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:9300,to:10570,r:0,er:0.0,lat:0.0,cached:1206,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:45052,to:45064,r:0,er:0.0,lat:0.0,cached:1018,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2218947,to:6247,r:0,er:0.0,lat:0.0,cached:751377,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:5,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1355704,to:43671,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:139085,to:53859,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-02-28": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:156807,to:3549,r:0,er:0.0,lat:0.0,cached:30284,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:46,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:203255,to:19985,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:48914,to:16965,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-01": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:15525,to:20412,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:262138,to:2381,r:0,er:0.0,lat:0.0,cached:107618,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:65,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:37374,to:4217,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:31530,to:8321,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-02": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7254,to:5389,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:25986,to:20618,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:468,to:1399,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:682579,to:6306,r:0,er:0.0,lat:0.0,cached:304158,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:44,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:575670,to:29331,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:88060,to:30022,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-03": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1833697,to:9338,r:0,er:0.0,lat:0.0,cached:899320,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:184717,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:680826,to:36259,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:80462,to:30319,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-04": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:75867,to:3531,r:0,er:0.0,lat:0.0,cached:4038,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:22,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:210428,to:15921,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:92888,to:15351,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-05": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:265175,to:5109,r:0,er:0.0,lat:0.0,cached:52746,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:1065346,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:160245,to:7589,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:51132,to:11898,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-06": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15354,to:751,r:0,er:0.0,lat:0.0,cached:8057,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:246947,to:7308,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:26003,to:6555,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-07": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:263670,to:6470,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:26314,to:12157,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-08": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:59590,to:2272,r:0,er:0.0,lat:0.0,cached:24249,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:28,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:468237,to:17328,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:54131,to:21059,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-09": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4534221,to:4993,r:0,er:0.0,lat:0.0,cached:3758174,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:40,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:526077,to:11385,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:54593,to:85861,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-10": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:531773,to:9308,r:0,er:0.0,lat:0.0,cached:95315,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:139,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:161646,to:12223,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:47214,to:14160,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-11": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:904005,to:8335,r:0,er:0.0,lat:0.0,cached:359301,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:154062,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5553186,to:261760,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3572394,to:377425,r:0,er:0.0,lat:0.0,cached:70943,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-12": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:774,to:646,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1592123,to:5733,r:0,er:0.0,lat:0.0,cached:1084360,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:115,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6732525,to:202603,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:833265,to:190401,r:0,er:0.0,lat:0.0,cached:254494,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-13": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:703203,to:8192,r:0,er:0.0,lat:0.0,cached:329368,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:326,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:263259,to:6785,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:40231,to:16130,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-14": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:322954,to:22680,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:94439,to:37372,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8711,to:22213,r:13,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-15": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:204394,to:2203,r:0,er:0.0,lat:0.0,cached:67106,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:53,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:341656,to:23183,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:116083,to:36783,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:591,to:5581,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-16": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:10324,to:634,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:5301,to:390,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1054196,to:19558,r:0,er:0.0,lat:0.0,cached:648886,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:59,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1835501,to:41973,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:155507,to:58611,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-17": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:61944,to:5983,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:19079,to:7368,r:0,er:0.0,lat:0.0,cached:603,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:70944,to:2123,r:0,er:0.0,lat:0.0,cached:4024,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:416703,to:27503,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:89652,to:22583,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1694,to:6772,r:3,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-18": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:725667,to:11628,r:0,er:0.0,lat:0.0,cached:526234,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:74,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:516193,to:34238,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:106097,to:29472,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:828,to:3200,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-19": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:42854,to:6912,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2129881,to:13848,r:0,er:0.0,lat:0.0,cached:1683581,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:83,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8702124,to:660124,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2869350,to:373539,r:0,er:0.0,lat:0.0,cached:390457,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-20": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2079686,to:29213,r:0,er:0.0,lat:0.0,cached:1195433,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:96,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:602144,to:28502,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:148055,to:38686,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-21": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1585403,to:21153,r:0,er:0.0,lat:0.0,cached:981802,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:99,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:173816,to:7848,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:64601,to:19970,r:0,er:0.0,lat:0.0,cached:859,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-22": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:430824,to:10286,r:0,er:0.0,lat:0.0,cached:244522,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:54,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:587914,to:51756,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:264897,to:39766,r:0,er:0.0,lat:0.0,cached:22521,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-23": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:730308,to:31849,r:0,er:0.0,lat:0.0,cached:313653,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:141,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:174067,to:7909,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:40304,to:14338,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2211,to:71,r:1,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-24": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:566968,to:163440,r:0,er:0.0,lat:0.0,cached:35219,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:9546526,to:29728,r:0,er:0.0,lat:0.0,cached:7222649,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:200,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:413438,to:21320,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:57722,to:20416,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-25": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:139046,to:7614,r:0,er:0.0,lat:0.0,cached:28465,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:9,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:316204,to:20293,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:37328,to:13327,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19630,to:4823,r:10,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-26": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:21231,to:1957,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:244060,to:7197,r:0,er:0.0,lat:0.0,cached:107692,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:21,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:659463,to:43872,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:109839,to:35421,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-27": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:84924,to:9502,r:0,er:0.0,lat:0.0,cached:5030,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3352681,to:16822,r:0,er:0.0,lat:0.0,cached:2158756,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:63,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:409658,to:29698,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:51731,to:20080,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-28": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:55347,to:3774,r:0,er:0.0,lat:0.0,cached:26359,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:44,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:93723,to:3294,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:18807,to:4343,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:806122,to:272432,r:171,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-29": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:433194,to:5949,r:0,er:0.0,lat:0.0,cached:305435,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:35,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:251902,to:8206,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:32461,to:13581,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:80935,to:12915,r:25,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-30": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:48431,to:5047,r:0,er:0.0,lat:0.0,cached:8066,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:36,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:417371,to:20657,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:54831,to:83143,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:107954,to:10577,r:36,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-03-31": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:398251,to:10846,r:0,er:0.0,lat:0.0,cached:160970,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:45,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:570700,to:30649,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:89853,to:32499,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:96298,to:33305,r:1,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-01": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:291836,to:11510,r:0,er:0.0,lat:0.0,cached:56924,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:34,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:231008,to:13874,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:37885,to:12103,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:11215,to:4877,r:3,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-02": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:332591,to:13640,r:0,er:0.0,lat:0.0,cached:173399,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:28,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:883540,to:39142,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:122364,to:47249,r:0,er:0.0,lat:0.0,cached:5073,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3201,to:94,r:1,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-03": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:300240,to:13045,r:0,er:0.0,lat:0.0,cached:121816,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:101,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:407814,to:13520,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:65921,to:27337,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-04": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2711509,to:31486,r:0,er:0.0,lat:0.0,cached:1716783,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:232,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4211996,to:112960,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:738612,to:297206,r:0,er:0.0,lat:0.0,cached:41397,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-05": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:25564,to:1180,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:450466,to:23507,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:87944,to:31697,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-06": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:22451,to:1512,r:0,er:0.0,lat:0.0,cached:2000,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:503770,to:21653,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:93482,to:26848,r:0,er:0.0,lat:0.0,cached:1695,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-07": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2273926,to:31536,r:0,er:0.0,lat:0.0,cached:1340150,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:33732,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:672840,to:26119,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:150774,to:19012,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:91548,to:26401,r:21,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-08": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:2428,to:2032,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:991439,to:21777,r:0,er:0.0,lat:0.0,cached:537811,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:151,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:352450,to:31907,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3280,to:2736,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:60876,to:36459,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:496092,to:133765,r:50,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-09": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:118948,to:37251,r:0,er:0.0,lat:0.0,cached:5033,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:23146,to:71624,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:244756,to:8720,r:0,er:0.0,lat:0.0,cached:89544,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:32,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:507591,to:15611,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:67450,to:95068,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-10": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:63647,to:5891,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:143549,to:464100,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:130908,to:5282,r:0,er:0.0,lat:0.0,cached:20350,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:45,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:530218,to:26883,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:84109,to:33394,r:0,er:0.0,lat:0.0,cached:2535,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-11": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:292570,to:11520,r:0,er:0.0,lat:0.0,cached:93454,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:85,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:364511,to:16071,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:44680,to:15332,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-12": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:59940,to:184753,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:607834,to:15484,r:0,er:0.0,lat:0.0,cached:151797,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:53,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:142665,to:11018,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:46282,to:22510,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6038,to:1548,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-13": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:20105,to:61437,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:359176,to:14873,r:0,er:0.0,lat:0.0,cached:83328,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:36,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:122418,to:4052,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:16861,to:8189,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5918,to:605,r:3,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-14": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:83927,to:7956,r:0,er:0.0,lat:0.0,cached:16131,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:93,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:293890,to:12683,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:51761,to:21209,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-15": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:129480,to:31915,r:0,er:0.0,lat:0.0,cached:5032,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:9714,to:32860,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:143707,to:8326,r:0,er:0.0,lat:0.0,cached:59109,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:22,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1043195,to:23871,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:101602,to:46520,r:0,er:0.0,lat:0.0,cached:2537,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:721672,to:188155,r:202,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-16": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:60231,to:17479,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2309797,to:16942,r:0,er:0.0,lat:0.0,cached:1697224,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:108,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:516831,to:20790,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:55892,to:23818,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:216415,to:142467,r:30,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-17": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2581,to:426,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:298703,to:103792,r:0,er:0.0,lat:0.0,cached:1012,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:5852699,to:22466,r:0,er:0.0,lat:0.0,cached:4647059,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:72,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:101673,to:5366,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:34737,to:11260,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:206902,to:87878,r:20,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-18": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:44893,to:20585,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:892000,to:17034,r:0,er:0.0,lat:0.0,cached:498688,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:107,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:198409,to:8289,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:35080,to:11308,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21353,to:1602,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-19": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:83509,to:24417,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1087924,to:16695,r:0,er:0.0,lat:0.0,cached:706928,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:9,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:292236,to:17782,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:58226,to:20589,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21579,to:1629,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-20": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:78563,to:23839,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:887400,to:18516,r:0,er:0.0,lat:0.0,cached:375523,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:277,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:248540,to:7987,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:62909,to:21784,r:0,er:0.0,lat:0.0,cached:3376,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:55147,to:3606,r:10,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-21": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.0 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:4645,to:380,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:72809,to:26516,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:822297,to:25050,r:0,er:0.0,lat:0.0,cached:363727,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:138,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:77121,to:6023,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:65163,to:15764,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:637536,to:196411,r:206,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-22": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:15260,to:6186,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:258102,to:11626,r:0,er:0.0,lat:0.0,cached:111571,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:57,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:9489,to:1170,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:674245,to:173142,r:0,er:0.0,lat:0.0,cached:10018,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:199255,to:37358,r:74,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-23": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:49248,to:22176,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:74222,to:4383,r:0,er:0.0,lat:0.0,cached:14133,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:35,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:487314,to:124732,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13147,to:406,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-24": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:538557,to:12549,r:0,er:0.0,lat:0.0,cached:369379,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:81,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2238818,to:613804,r:0,er:0.0,lat:0.0,cached:592325,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:31244,to:5071,r:12,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-25": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:115792,to:4107,r:0,er:0.0,lat:0.0,cached:52855,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:31,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2743246,to:942182,r:0,er:0.0,lat:0.0,cached:119636,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:352190,to:78635,r:126,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-26": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:208302,to:5979,r:0,er:0.0,lat:0.0,cached:128525,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:29,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:51539,to:19097,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:201306,to:22330,r:52,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-27": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:3844,to:4785,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15885,to:1557,r:0,er:0.0,lat:0.0,cached:2022,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:27,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:120041,to:43031,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:453467,to:50837,r:101,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-28": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:21221,to:5094,r:0,er:0.0,lat:0.0,cached:1429,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:597883,to:15391,r:0,er:0.0,lat:0.0,cached:272725,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:89,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:118616,to:47597,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1205192,to:141275,r:248,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-29": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:232470,to:1808,r:0,er:0.0,lat:0.0,cached:75866,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:24095318,to:1366481,r:0,er:0.0,lat:0.0,cached:9669291,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:669383,to:30325,r:99,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-04-30": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:145366,to:1842,r:0,er:0.0,lat:0.0,cached:12644,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:109926,to:17028,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:17144,to:396,r:3,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-01": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:250786,to:3000,r:14,er:0.0,lat:3.93,cached:113797,think:0,e4:0,e5:0,e429:0,eKnown:14,lat99:4.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:57724,to:25559,r:8,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:8.3}
  ],
  "2026-05-02": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:41864,to:719,r:15,er:0.0,lat:2.86,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:3.09},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:159543,to:39545,r:32,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:32,lat99:8.35}
  ],
  "2026-05-03": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:178619,to:5829,r:1,er:0.0,lat:2.04,cached:87569,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:2.09},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:49,to:0,r:0,er:0.0,lat:2.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:2.09},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:181030,to:57565,r:55,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:55,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:59847,to:2389,r:19,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-04": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:252550,to:3443,r:5,er:0.0,lat:4.09,cached:52007,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:9920,to:435,r:0,er:0.0,lat:0.51,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.52},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1702447,to:28770,r:11,er:0.0,lat:0.51,cached:931293,think:0,e4:0,e5:0,e429:0,eKnown:11,lat99:0.52},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:1333254,to:0,r:8,er:0.0,lat:0.51,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:0.52},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:486606,to:150312,r:134,er:0.0,lat:8.07,cached:13270,think:0,e4:0,e5:0,e429:0,eKnown:134,lat99:8.33},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:146454,to:13544,r:28,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-05": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:188310,to:8627,r:92,er:4.3478,lat:1.02,cached:32534,think:0,e4:4,e5:0,e429:0,eKnown:92,lat99:1.04},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:75,to:0,r:0,er:4.3478,lat:1.02,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:1.04},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:254343,to:103358,r:106,er:0.9434,lat:8.18,cached:3059,think:0,e4:0,e5:1,e429:0,eKnown:106,lat99:8.35},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:20,er:0.0,lat:3.93,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:20,lat99:4.14},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:25599,to:500,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-06": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:448742,to:5420,r:0,er:0.0,lat:0.0,cached:101153,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:72938,to:233840,r:38,er:0.0,lat:7.65,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:38,lat99:8.24},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:467230,to:22827,r:61,er:0.0,lat:7.65,cached:107415,think:0,e4:0,e5:0,e429:0,eKnown:61,lat99:8.24},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:272,to:0,r:0,er:0.0,lat:7.65,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.24},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:846102,to:158528,r:94,er:1.0638,lat:8.18,cached:7151,think:0,e4:0,e5:1,e429:0,eKnown:94,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:103478,to:4973,r:18,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-07": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:744,to:562,r:44,er:0.0,lat:3.77,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:44,lat99:4.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:51419,to:122131,r:42,er:0.0,lat:7.13,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:42,lat99:8.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:910645,to:25472,r:227,er:0.0,lat:7.13,cached:331291,think:0,e4:0,e5:0,e429:0,eKnown:227,lat99:8.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:475,to:0,r:0,er:0.0,lat:7.13,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:232247,to:87712,r:170,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:170,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:17158,to:377,r:3,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-08": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:210960,to:2576,r:5,er:0.0,lat:2.91,cached:25288,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:3.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:25008,to:65970,r:89,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:89,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:204802,to:15287,r:216,er:0.0,lat:3.98,cached:38428,think:0,e4:0,e5:0,e429:0,eKnown:216,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:221,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:48129,to:101515,r:47,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:47,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:91052,to:3168,r:19,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-09": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:92150,to:296775,r:144,er:0.0,lat:11.43,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:144,lat99:12.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:161291,to:4398,r:61,er:0.0,lat:11.43,cached:79568,think:0,e4:0,e5:0,e429:0,eKnown:61,lat99:12.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:20,to:0,r:0,er:0.0,lat:11.43,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:12.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:301344,to:422196,r:355,er:0.0,lat:15.94,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:355,lat99:16.61},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:15,er:0.0,lat:2.91,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:3.1},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:34261,to:726,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-10": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:6999569,to:51924,r:4,er:0.0,lat:3.01,cached:6591449,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:3.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:37938,to:118610,r:12,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:12,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:631098,to:18577,r:49,er:0.0,lat:16.36,cached:269939,think:0,e4:0,e5:0,e429:0,eKnown:49,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:9781,to:0,r:1,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:230106,to:67103,r:60,er:1.6667,lat:8.18,cached:0,think:0,e4:1,e5:0,e429:0,eKnown:60,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:25553,to:473,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-11": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:215025,to:5479,r:114,er:0.0,lat:5.4,cached:124341,think:0,e4:0,e5:0,e429:0,eKnown:114,lat99:6.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:47,to:0,r:0,er:0.0,lat:5.4,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:6.11},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:533949,to:210153,r:100,er:0.0,lat:15.1,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:100,lat99:16.44},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:551,er:0.0,lat:2.08,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:551,lat99:3.43},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:314960,to:16500,r:58,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-12": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:465616,to:76525,r:5,er:0.0,lat:6.13,cached:281027,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:6.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1432,to:7479,r:0,er:0.0,lat:3.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:3.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:327440,to:8650,r:14,er:0.0,lat:3.03,cached:173416,think:0,e4:0,e5:0,e429:0,eKnown:14,lat99:3.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:44,to:0,r:0,er:0.0,lat:3.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:3.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:735110,to:195477,r:147,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:147,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38514,to:1273,r:10,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-13": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:222803,to:8090,r:72,er:0.0,lat:4.09,cached:37932,think:0,e4:0,e5:0,e429:0,eKnown:72,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:53471,to:159170,r:24,er:0.0,lat:7.55,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:24,lat99:8.22},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:447111,to:17467,r:52,er:0.0,lat:7.55,cached:85277,think:0,e4:0,e5:0,e429:0,eKnown:52,lat99:8.22},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:287,to:0,r:0,er:0.0,lat:7.55,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.22},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:155049,to:56874,r:128,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:128,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:141079,to:4787,r:30,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-14": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:138621,to:330612,r:99,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:99,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:271440,to:12274,r:60,er:0.0,lat:16.36,cached:62740,think:0,e4:0,e5:0,e429:0,eKnown:60,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:107,to:0,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:224651,to:101342,r:74,er:0.0,lat:8.18,cached:1021,think:0,e4:0,e5:0,e429:0,eKnown:74,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:18410,to:493,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-15": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:10116,to:30382,r:6,er:0.0,lat:12.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:12.49},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:120534,to:6524,r:19,er:0.0,lat:12.09,cached:26455,think:0,e4:0,e5:0,e429:0,eKnown:19,lat99:12.49},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:52,to:0,r:0,er:0.0,lat:12.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:12.49},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:428689,to:61026,r:90,er:0.0,lat:8.18,cached:30328,think:0,e4:0,e5:0,e429:0,eKnown:90,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:345618,to:78238,r:79,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-16": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:21531,to:1698,r:19,er:0.0,lat:7.97,cached:10056,think:0,e4:0,e5:0,e429:0,eKnown:19,lat99:8.3},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:415406,to:80018,r:88,er:0.0,lat:8.1,cached:35449,think:0,e4:0,e5:0,e429:0,eKnown:88,lat99:8.33},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:928448,to:169739,r:197,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-17": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3257,to:11282,r:0,er:0.0,lat:3.01,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:3.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:244664,to:3036,r:8,er:0.0,lat:3.01,cached:100095,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:3.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:95594,to:33677,r:62,er:0.0,lat:8.07,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:62,lat99:8.33},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:30104,to:753,r:7,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-18": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:21640,to:67653,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:11950273,to:42717,r:67,er:0.0,lat:8.18,cached:9912030,think:0,e4:0,e5:0,e429:0,eKnown:67,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:87806,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:35700,to:8867,r:27,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:27,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:185020,to:10513,r:50,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-19": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:405844,to:4395,r:37,er:0.0,lat:4.09,cached:282931,think:0,e4:0,e5:0,e429:0,eKnown:37,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:49483,to:145760,r:50,er:0.0,lat:3.9,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:50,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:240771,to:15085,r:66,er:0.0,lat:3.9,cached:40429,think:0,e4:0,e5:0,e429:0,eKnown:66,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:67,to:0,r:0,er:0.0,lat:3.9,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:514567,to:108401,r:76,er:0.0,lat:8.13,cached:90980,think:0,e4:0,e5:0,e429:0,eKnown:76,lat99:8.34},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:284741,to:14185,r:54,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-20": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:120783,to:374232,r:46,er:0.0,lat:15.52,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:46,lat99:16.53},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:889660,to:14201,r:85,er:0.0,lat:15.52,cached:424358,think:0,e4:0,e5:0,e429:0,eKnown:85,lat99:16.53},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:227,to:0,r:0,er:0.0,lat:15.52,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.53},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:162878,to:29926,r:70,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:70,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:636794,to:26524,r:111,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-21": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:22366,to:51450,r:14,er:0.0,lat:11.43,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:14,lat99:12.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:554025,to:20380,r:109,er:0.0,lat:11.43,cached:195188,think:0,e4:0,e5:0,e429:0,eKnown:109,lat99:12.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:43210,to:0,r:8,er:0.0,lat:11.43,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:12.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:551377,to:156952,r:92,er:0.0,lat:8.18,cached:5104,think:0,e4:0,e5:0,e429:0,eKnown:92,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:20704,to:1138,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-22": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1501026,to:46320,r:58,er:0.0,lat:7.86,cached:768364,think:0,e4:0,e5:0,e429:0,eKnown:58,lat99:8.28},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:93,to:0,r:0,er:0.0,lat:7.86,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.28},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:339599,to:102204,r:148,er:0.6757,lat:8.18,cached:6127,think:0,e4:0,e5:1,e429:0,eKnown:148,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:104301,to:4690,r:22,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-23": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6418,to:18146,r:7,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:8.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:257732,to:12460,r:81,er:0.0,lat:7.03,cached:99455,think:0,e4:0,e5:0,e429:0,eKnown:81,lat99:8.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:53,to:0,r:0,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:523482,to:68589,r:55,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:55,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:188249,to:6681,r:31,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-24": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:50179,to:1977,r:11,er:0.0,lat:3.98,cached:20288,think:0,e4:0,e5:0,e429:0,eKnown:11,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:11,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:281207,to:49868,r:63,er:0.0,lat:13.84,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:63,lat99:16.19},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1119284,to:33201,r:173,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-25": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:29737,to:102904,r:3,er:0.0,lat:4.59,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:5.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:282864,to:11124,r:8,er:0.0,lat:4.59,cached:99073,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:5.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:64,to:0,r:0,er:0.0,lat:4.59,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:5.11},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3383467,to:1448992,r:128,er:0.0,lat:8.18,cached:144739,think:0,e4:0,e5:0,e429:0,eKnown:128,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:112619,to:8146,r:26,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-26": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:58753,to:202447,r:54,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:54,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:150269,to:7463,r:33,er:0.0,lat:16.36,cached:46829,think:0,e4:0,e5:0,e429:0,eKnown:33,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:112,to:0,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4195885,to:2029142,r:2469,er:0.0,lat:8.18,cached:68663,think:0,e4:0,e5:0,e429:0,eKnown:2469,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:422966,to:32590,r:80,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-27": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:282439,to:12118,r:37,er:0.0,lat:14.68,cached:97779,think:0,e4:0,e5:0,e429:0,eKnown:37,lat99:16.36},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:29908,to:0,r:4,er:0.0,lat:14.68,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:16.36},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:144748,to:8631,r:88,er:0.0,lat:15.31,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:88,lat99:16.48},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:520699,to:142314,r:380,er:0.0,lat:15.31,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:380,lat99:16.48},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:702439,to:62806,r:112,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-28": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2921772,to:35728,r:0,er:0.0,lat:0.0,cached:1839723,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6552,to:16532,r:1,er:0.0,lat:4.05,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1689547,to:29120,r:64,er:0.0,lat:4.05,cached:965209,think:0,e4:0,e5:0,e429:0,eKnown:64,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:280,to:0,r:0,er:0.0,lat:4.05,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:322,to:49,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:244421,to:88328,r:164,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:164,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2435797,to:434963,r:448,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-29": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:239554,to:6753,r:299,er:0.0,lat:4.09,cached:15503,think:0,e4:0,e5:0,e429:0,eKnown:299,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:43849,to:143407,r:20,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:20,lat99:8.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:187372,to:8483,r:21,er:0.0,lat:7.76,cached:65051,think:0,e4:0,e5:0,e429:0,eKnown:21,lat99:8.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:107,to:0,r:0,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.26},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:476031,to:9163,r:125,er:2.2222,lat:2.7,cached:0,think:0,e4:3,e5:0,e429:0,eKnown:125,lat99:3.06},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:182241,to:34031,r:55,er:2.2222,lat:2.7,cached:0,think:0,e4:1,e5:0,e429:0,eKnown:55,lat99:3.06},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:303478,to:18434,r:60,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-30": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:52740,to:655,r:6,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:10083,to:30777,r:32,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:32,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:64768,to:3861,r:53,er:0.0,lat:8.18,cached:20250,think:0,e4:0,e5:0,e429:0,eKnown:53,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:51,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.0 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:203911,to:6096,r:43,er:0.0,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:43,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:158723,to:46751,r:42,er:0.0,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:42,lat99:4.16},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38868,to:1970,r:9,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-05-31": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:266992,to:3955,r:32,er:0.0,lat:3.93,cached:25288,think:0,e4:0,e5:0,e429:0,eKnown:32,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:115441,to:10118,r:6,er:0.0,lat:3.93,cached:28301,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:20,to:0,r:0,er:0.0,lat:3.93,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:44811,to:19147,r:47,er:0.0,lat:8.07,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:47,lat99:8.33},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:28866,to:4081,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-01": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:524085,to:5809,r:5,er:0.0,lat:2.91,cached:227597,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:3.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:18635,to:61903,r:2,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1154757,to:41794,r:37,er:0.0,lat:8.18,cached:290713,think:0,e4:0,e5:0,e429:0,eKnown:37,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:109,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:665446,to:138165,r:53,er:0.0,lat:8.18,cached:20097,think:0,e4:0,e5:0,e429:0,eKnown:53,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 3.1 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:9882,to:927,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 3.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3294,to:2969,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:84242,to:8586,r:18,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-02": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:559287,to:7097,r:43,er:0.0,lat:2.04,cached:164378,think:0,e4:0,e5:0,e429:0,eKnown:43,lat99:2.09},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:23555,to:73490,r:1,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7925211,to:77054,r:116,er:0.0,lat:7.97,cached:5677536,think:0,e4:0,e5:0,e429:0,eKnown:116,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:310,to:0,r:0,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.3},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:273012,to:55260,r:183,er:1.6393,lat:4.09,cached:20032,think:0,e4:3,e5:0,e429:0,eKnown:183,lat99:4.17},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:28650,to:4442,r:7,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-03": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1157732,to:13187,r:94,er:0.0,lat:3.77,cached:392929,think:0,e4:0,e5:0,e429:0,eKnown:94,lat99:4.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:5837,to:17403,r:1,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3195058,to:96154,r:183,er:0.0,lat:7.97,cached:1452015,think:0,e4:0,e5:0,e429:0,eKnown:183,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:175,to:0,r:0,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.3},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:893206,to:282602,r:95,er:0.0,lat:8.18,cached:33209,think:0,e4:0,e5:0,e429:0,eKnown:95,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:639926,to:77047,r:138,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-04": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:78316,to:855,r:70,er:0.0,lat:3.88,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:70,lat99:4.13},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:11483609,to:107839,r:246,er:0.0,lat:8.02,cached:7751675,think:0,e4:0,e5:0,e429:0,eKnown:246,lat99:8.32},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:357,to:0,r:0,er:0.0,lat:8.02,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.32},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:335341,to:45515,r:248,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:248,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:477046,to:39020,r:90,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-05": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:117128,to:3259,r:24,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:24,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3716,to:11831,r:1,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3616056,to:73488,r:153,er:0.0,lat:7.76,cached:1414070,think:0,e4:0,e5:0,e429:0,eKnown:153,lat99:8.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:101,to:0,r:0,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.26},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:259073,to:74122,r:64,er:0.0,lat:8.18,cached:1006,think:0,e4:0,e5:0,e429:0,eKnown:64,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:348595,to:13584,r:68,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-06": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:108828,to:1746,r:12,er:0.0,lat:4.04,cached:12644,think:0,e4:0,e5:0,e429:0,eKnown:12,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:13094,to:40008,r:17,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:17,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:485029,to:16876,r:160,er:0.0,lat:4.09,cached:55781,think:0,e4:0,e5:0,e429:0,eKnown:160,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:6,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:78965,to:40784,r:75,er:1.3333,lat:8.18,cached:0,think:0,e4:1,e5:0,e429:0,eKnown:75,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3312479,to:158765,r:615,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-07": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:474786,to:5495,r:35,er:0.0,lat:3.88,cached:75865,think:0,e4:0,e5:0,e429:0,eKnown:35,lat99:4.13},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:12272,to:39775,r:0,er:0.0,lat:7.55,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.22},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1976553,to:55054,r:16,er:0.0,lat:7.55,cached:1068418,think:0,e4:0,e5:0,e429:0,eKnown:16,lat99:8.22},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:290,to:0,r:0,er:0.0,lat:7.55,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.22},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:166666,to:43718,r:15,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2420684,to:118211,r:440,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-08": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2023333,to:23642,r:130,er:0.0,lat:3.77,cached:742806,think:0,e4:0,e5:0,e429:0,eKnown:130,lat99:4.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:10759,to:38835,r:5,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2109322,to:61065,r:223,er:0.0,lat:7.97,cached:531927,think:0,e4:0,e5:0,e429:0,eKnown:223,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:194,to:0,r:0,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.3},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:578972,to:114925,r:116,er:1.7241,lat:8.18,cached:0,think:0,e4:0,e5:2,e429:0,eKnown:116,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1126716,to:43148,r:203,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-09": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7103,to:23200,r:2,er:0.0,lat:7.34,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.18},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1519854,to:34232,r:112,er:0.0,lat:7.34,cached:674488,think:0,e4:0,e5:0,e429:0,eKnown:112,lat99:8.18},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:211,to:0,r:0,er:0.0,lat:7.34,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.18},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:271693,to:61395,r:83,er:1.2048,lat:8.18,cached:13291,think:0,e4:0,e5:1,e429:0,eKnown:83,lat99:8.35},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:68,er:0.0,lat:3.77,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:68,lat99:4.11},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19835,to:1415,r:5,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-10": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6102,to:20136,r:2,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1635779,to:27089,r:109,er:0.0,lat:4.09,cached:995587,think:0,e4:0,e5:0,e429:0,eKnown:109,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:169,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:718880,to:166891,r:145,er:0.0,lat:8.18,cached:30326,think:0,e4:0,e5:0,e429:0,eKnown:145,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:228122,to:6463,r:49,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-11": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:11804,to:40414,r:5,er:0.0,lat:14.68,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:16.36},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:338216,to:17207,r:31,er:0.0,lat:14.68,cached:97270,think:0,e4:0,e5:0,e429:0,eKnown:31,lat99:16.36},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:70,to:0,r:0,er:0.0,lat:14.68,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.36},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5947955,to:266715,r:304,er:0.0,lat:8.18,cached:345155,think:0,e4:0,e5:0,e429:0,eKnown:304,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:63993,to:1897,r:14,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-12": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:26388,to:88300,r:2,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6416528,to:34144,r:123,er:0.0,lat:4.09,cached:4770529,think:0,e4:0,e5:0,e429:0,eKnown:123,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:514,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1380409,to:165058,r:149,er:0.0,lat:7.97,cached:296032,think:0,e4:0,e5:0,e429:0,eKnown:149,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:170874,to:10673,r:37,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-13": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:105508,to:1197,r:0,er:0.0,lat:0.0,cached:12645,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7272872,to:65491,r:264,er:0.0,lat:4.02,cached:4507074,think:0,e4:0,e5:0,e429:0,eKnown:264,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:696,to:0,r:0,er:0.0,lat:4.02,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:498617,to:126510,r:126,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:126,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:48215,to:2165,r:11,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-14": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:52754,to:592,r:15,er:0.0,lat:3.07,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:3.13},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2547307,to:38944,r:12,er:0.0,lat:2.27,cached:1511372,think:0,e4:0,e5:0,e429:0,eKnown:12,lat99:2.34},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:226,to:0,r:0,er:0.0,lat:2.27,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:2.34},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:209743,to:37546,r:47,er:0.0,lat:7.76,cached:7151,think:0,e4:0,e5:0,e429:0,eKnown:47,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:269196,to:10132,r:49,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-15": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1660,to:265,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:877529,to:7829,r:94,er:0.0,lat:4.04,cached:515066,think:0,e4:0,e5:0,e429:0,eKnown:94,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:54,to:0,r:0,er:0.0,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:552219,to:116060,r:75,er:1.3333,lat:8.18,cached:0,think:0,e4:0,e5:1,e429:0,eKnown:75,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:259182,to:7697,r:54,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-16": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:8300,to:1527,r:1,er:0.0,lat:4.09,cached:1436,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:5971,to:18492,r:2,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:639543,to:11836,r:42,er:0.0,lat:4.09,cached:144539,think:0,e4:0,e5:0,e429:0,eKnown:42,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:63,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:888042,to:199435,r:194,er:0.0,lat:8.18,cached:10221,think:0,e4:0,e5:0,e429:0,eKnown:194,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:56197,to:2542,r:14,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-17": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:684142,to:7627,r:34,er:0.0,lat:3.98,cached:101155,think:0,e4:0,e5:0,e429:0,eKnown:34,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:41687,to:146141,r:24,er:0.0,lat:23.17,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:24,lat99:24.77},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:62786,to:2360,r:8,er:0.0,lat:23.17,cached:34369,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:24.77},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:567841,to:101319,r:153,er:0.6536,lat:8.18,cached:30338,think:0,e4:0,e5:1,e429:0,eKnown:153,lat99:8.35},
    {a:"Tools Quizzer",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Nội bộ",u:0,c:0,ti:0,to:0,r:1,er:100.0,lat:0.26,cached:0,think:0,e4:1,e5:0,e429:0,eKnown:1,lat99:0.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:66718,to:2769,r:15,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-18": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:386975,to:6405,r:46,er:2.1739,lat:3.93,cached:179240,think:0,e4:0,e5:1,e429:0,eKnown:46,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:5019,to:16382,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:532643,to:19318,r:35,er:0.0,lat:8.18,cached:195162,think:0,e4:0,e5:0,e429:0,eKnown:35,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:191,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1114657,to:200514,r:130,er:0.0,lat:8.13,cached:90338,think:0,e4:0,e5:0,e429:0,eKnown:130,lat99:8.34},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:57882,to:10799,r:16,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-19": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:580235,to:6506,r:39,er:0.0,lat:6.29,cached:63220,think:0,e4:0,e5:0,e429:0,eKnown:39,lat99:7.97},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:309471,to:5212,r:50,er:0.0,lat:3.98,cached:147066,think:0,e4:0,e5:0,e429:0,eKnown:50,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:5,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:24990490,to:10057724,r:386,er:0.7772,lat:15.1,cached:0,think:0,e4:0,e5:3,e429:0,eKnown:386,lat99:16.44},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:74694,to:2772,r:15,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-20": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2360,to:7663,r:1,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:163275,to:5308,r:13,er:0.0,lat:7.97,cached:40629,think:0,e4:0,e5:0,e429:0,eKnown:13,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:24,to:0,r:0,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.3},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:45,er:0.0,lat:3.67,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:45,lat99:4.09},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:5795,er:0.0863,lat:15.31,cached:0,think:0,e4:4,e5:1,e429:0,eKnown:5795,lat99:16.48},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1996244,to:206647,r:407,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-21": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:220165,to:6735,r:0,er:0.0,lat:0.0,cached:40806,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:26,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:412037,to:93081,r:28,er:35.7143,lat:0.26,cached:44638,think:0,e4:10,e5:0,e429:0,eKnown:28,lat99:0.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:266576,to:12947,r:51,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-22": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:158262,to:1764,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2176093,to:29523,r:18,er:0.0,lat:7.55,cached:1038926,think:0,e4:0,e5:0,e429:0,eKnown:18,lat99:8.22},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:42,to:0,r:0,er:0.0,lat:7.55,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.22},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:583117,to:127122,r:161,er:0.0,lat:8.0,cached:1705,think:0,e4:0,e5:0,e429:0,eKnown:161,lat99:8.31},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:158307,to:6070,r:37,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-23": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:318184,to:3891,r:25,er:0.0,lat:2.91,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:25,lat99:3.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6044178,to:42992,r:173,er:0.0,lat:4.09,cached:4451812,think:0,e4:0,e5:0,e429:0,eKnown:173,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:173,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:279304,to:63012,r:121,er:0.0,lat:8.07,cached:30328,think:0,e4:0,e5:0,e429:0,eKnown:121,lat99:8.33},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:343677,to:26246,r:66,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-24": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:132316,to:1425,r:33,er:0.0,lat:3.88,cached:50576,think:0,e4:0,e5:0,e429:0,eKnown:33,lat99:4.13},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2056662,to:26713,r:57,er:0.0,lat:4.05,cached:1396635,think:0,e4:0,e5:0,e429:0,eKnown:57,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:82,to:0,r:0,er:0.0,lat:4.05,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Tools Quizzer",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Nội bộ",u:0,c:0,ti:7957,to:4464,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:314812,to:68287,r:33,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:33,lat99:4.17},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:168536,to:12057,r:40,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-25": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:233267,to:2270,r:0,er:0.0,lat:0.0,cached:63222,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:10116,to:34226,r:5,er:0.0,lat:4.56,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:5.95},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1101729,to:24795,r:115,er:0.0,lat:4.56,cached:508630,think:0,e4:0,e5:0,e429:0,eKnown:115,lat99:5.95},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:145,to:0,r:0,er:0.0,lat:4.56,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:5.95},
    {a:"Tools Quizzer",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Nội bộ",u:0,c:0,ti:5118,to:7580,r:9,er:44.4444,lat:0.64,cached:0,think:0,e4:4,e5:0,e429:0,eKnown:9,lat99:0.65},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:704111,to:146091,r:111,er:0.0,lat:8.18,cached:151660,think:0,e4:0,e5:0,e429:0,eKnown:111,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:27265,to:676,r:5,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-26": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:137375,to:7449,r:25,er:0.0,lat:4.09,cached:42540,think:0,e4:0,e5:0,e429:0,eKnown:25,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:27,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:552679,to:111975,r:193,er:0.5181,lat:8.18,cached:863,think:0,e4:0,e5:1,e429:0,eKnown:193,lat99:8.35},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:21,er:4.7619,lat:2.04,cached:0,think:0,e4:0,e5:1,e429:0,eKnown:21,lat99:2.09},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:230928,to:4496,r:35,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-27": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:10116,to:33280,r:10,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:18038,to:1744,r:5,er:0.0,lat:3.98,cached:2023,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.1 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:9059,to:131,r:2,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:507540,to:103247,r:71,er:0.0,lat:8.18,cached:47701,think:0,e4:0,e5:0,e429:0,eKnown:71,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:92279,to:2428,r:19,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-28": [
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:498523,to:13347,r:34,er:0.0,lat:2.04,cached:212006,think:0,e4:0,e5:0,e429:0,eKnown:34,lat99:2.09},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:84,to:0,r:0,er:0.0,lat:2.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:2.09},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:400343,to:112427,r:122,er:0.8197,lat:8.18,cached:0,think:0,e4:0,e5:1,e429:0,eKnown:122,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:37618,to:1275,r:8,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-29": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1660,to:265,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:945834,to:20828,r:27,er:0.0,lat:4.09,cached:519949,think:0,e4:0,e5:0,e429:0,eKnown:27,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:179,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Tools Quizzer",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Nội bộ",u:0,c:0,ti:23626,to:599,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:369247,to:113316,r:124,er:2.4194,lat:7.97,cached:1013,think:0,e4:3,e5:0,e429:0,eKnown:124,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:74202,to:2270,r:15,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-06-30": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:119924,to:1498,r:3,er:0.0,lat:4.09,cached:37933,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:794099,to:23587,r:61,er:0.0,lat:4.06,cached:436492,think:0,e4:0,e5:0,e429:0,eKnown:61,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:85,to:0,r:0,er:0.0,lat:4.06,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Tools Quizzer",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Nội bộ",u:0,c:0,ti:1193,to:543,r:6,er:0.0,lat:3.07,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:3.13},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:354460,to:121518,r:102,er:0.0,lat:8.18,cached:1014,think:0,e4:0,e5:0,e429:0,eKnown:102,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:27277,to:644,r:5,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-01": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:345402,to:4426,r:9,er:0.0,lat:5.91,cached:63221,think:0,e4:0,e5:0,e429:0,eKnown:9,lat99:6.22},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4320,to:13191,r:0,er:0.0,lat:5.82,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:6.2},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3062786,to:53915,r:57,er:0.0,lat:5.82,cached:1965107,think:0,e4:0,e5:0,e429:0,eKnown:57,lat99:6.2},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:219,to:0,r:0,er:0.0,lat:5.82,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:6.2},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:959019,to:241264,r:203,er:0.0,lat:8.07,cached:20290,think:0,e4:0,e5:0,e429:0,eKnown:203,lat99:8.33},
    {a:"Tools Quizzer",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Nội bộ",u:0,c:0,ti:0,to:0,r:3,er:0.0,lat:1.02,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:1.04},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:125118,to:2755,r:20,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-02": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2634,to:615,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:664,to:155,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:509,to:119,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:288,to:67,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:276,to:64,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:271,to:63,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:160,to:37,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:110,to:26,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:23303,to:8157,r:4,er:0.0,lat:16.36,cached:2181,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5876,to:2057,r:1,er:0.0,lat:16.36,cached:550,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4504,to:1577,r:1,er:0.0,lat:16.36,cached:422,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2552,to:893,r:0,er:0.0,lat:16.36,cached:239,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2438,to:853,r:0,er:0.0,lat:16.36,cached:228,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2401,to:841,r:0,er:0.0,lat:16.36,cached:225,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1415,to:495,r:0,er:0.0,lat:16.36,cached:132,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:977,to:342,r:0,er:0.0,lat:16.36,cached:91,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:105508,to:1213,r:34,er:0.0,lat:4.04,cached:25288,think:0,e4:0,e5:0,e429:0,eKnown:34,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1248767,to:100585,r:235,er:0.0,lat:5.77,cached:537323,think:0,e4:0,e5:0,e429:0,eKnown:235,lat99:7.86},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:97,to:0,r:0,er:0.0,lat:5.77,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:7.86},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:408005,to:124460,r:138,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:138,lat99:8.35}
  ],
  "2026-07-03": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:212676,to:2728,r:31,er:0.0,lat:3.77,cached:37932,think:0,e4:0,e5:0,e429:0,eKnown:31,lat99:4.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1036386,to:18177,r:66,er:0.0,lat:6.92,cached:644963,think:0,e4:0,e5:0,e429:0,eKnown:66,lat99:8.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:65,to:0,r:0,er:0.0,lat:6.92,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.1},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:201065,to:63199,r:85,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:85,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:83529,to:2449,r:17,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-04": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:126672,to:1837,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:585388,to:11296,r:5,er:0.0,lat:10.2,cached:183764,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:10.43},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:58856,to:25758,r:46,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:46,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:257239,to:21090,r:58,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-05": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:224153,to:2386,r:36,er:0.0,lat:3.88,cached:75865,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:4.13},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:351111,to:83045,r:66,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:66,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:0,to:0,r:31,er:0.0,lat:6.71,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:31,lat99:8.05},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36917,to:1210,r:7,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-06": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1650824,to:1693669,r:0,er:0.0,lat:0.0,cached:241362,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:10,to:134,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:301490,to:64423,r:0,er:0.0,lat:0.0,cached:42712,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1959950,to:26597,r:21,er:0.0,lat:4.06,cached:1154890,think:0,e4:0,e5:0,e429:0,eKnown:21,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:54,to:0,r:0,er:0.0,lat:4.06,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:234218,to:57198,r:57,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:57,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:789688,to:18176,r:120,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-07": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:481747,to:522956,r:251,er:0.0,lat:32.72,cached:30288,think:0,e4:0,e5:0,e429:0,eKnown:251,lat99:33.39},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:29046,to:27136,r:11,er:0.0,lat:16.15,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:11,lat99:16.65},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:8120035,to:130168,r:47,er:0.0,lat:3.98,cached:6082675,think:0,e4:0,e5:0,e429:0,eKnown:47,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:84040,to:2708,r:45,er:0.0,lat:7.97,cached:40705,think:0,e4:0,e5:0,e429:0,eKnown:45,lat99:8.3},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:230527,to:79134,r:78,er:1.2821,lat:7.97,cached:0,think:0,e4:0,e5:1,e429:0,eKnown:78,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1434436,to:33139,r:201,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-08": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:28986,to:33665,r:72,er:0.0,lat:60.4,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:72,lat99:65.77},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:187229,to:193094,r:0,er:0.0,lat:0.0,cached:26374,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:23435731,to:857657,r:2739,er:0.2921,lat:4.09,cached:17463654,think:0,e4:0,e5:8,e429:0,eKnown:2739,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:569199,to:19010,r:27,er:0.0,lat:7.97,cached:261119,think:0,e4:0,e5:0,e429:0,eKnown:27,lat99:8.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:14,to:0,r:0,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.3},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:679147,to:183673,r:96,er:0.0,lat:11.01,cached:1023,think:0,e4:0,e5:0,e429:0,eKnown:96,lat99:12.27},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1108965,to:44289,r:141,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-09": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:31488,to:33712,r:5,er:0.0,lat:32.3,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:33.3},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:3682316,to:309913,r:605,er:0.0,lat:6.19,cached:2579654,think:0,e4:0,e5:0,e429:0,eKnown:605,lat99:7.95},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1875191,to:27139,r:82,er:0.0,lat:4.08,cached:1162721,think:0,e4:0,e5:0,e429:0,eKnown:82,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:149,to:0,r:0,er:0.0,lat:4.08,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:607374,to:96009,r:154,er:0.0,lat:8.02,cached:130663,think:0,e4:0,e5:0,e429:0,eKnown:154,lat99:8.32},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:39,er:0.0,lat:62.08,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:39,lat99:66.1},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:27214,to:638,r:5,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-10": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:98274,to:119235,r:5,er:0.0,lat:64.17,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:66.52},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:103860,to:138047,r:0,er:0.0,lat:0.0,cached:32462,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1829160,to:20104,r:340,er:0.0,lat:4.04,cached:1204063,think:0,e4:0,e5:0,e429:0,eKnown:340,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1340165,to:26035,r:30,er:0.0,lat:7.76,cached:411973,think:0,e4:0,e5:0,e429:0,eKnown:30,lat99:8.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:34,to:0,r:0,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.26},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:277371,to:64292,r:131,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:131,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:564497,to:64764,r:107,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-11": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:35932,to:45934,r:15,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:33.39},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:95008,to:79512,r:43,er:0.0,lat:63.75,cached:21289,think:0,e4:0,e5:0,e429:0,eKnown:43,lat99:66.44},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:79981,to:1084,r:8,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1279397,to:22100,r:94,er:0.0,lat:4.09,cached:744026,think:0,e4:0,e5:0,e429:0,eKnown:94,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:111,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:171700,to:62992,r:41,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:41,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:590005,to:89734,r:131,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-12": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:65259,to:80209,r:6,er:0.0,lat:62.08,cached:3015,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:66.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:53450,to:172809,r:11,er:1.6667,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:11,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:971943,to:22876,r:49,er:1.6667,lat:4.04,cached:553449,think:0,e4:0,e5:1,e429:0,eKnown:49,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:79,to:0,r:0,er:1.6667,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:309212,to:49587,r:65,er:0.0,lat:7.97,cached:30332,think:0,e4:0,e5:0,e429:0,eKnown:65,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:206661,to:13659,r:41,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-13": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:150704,to:180619,r:10,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:33.39},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2991611,to:41022,r:5,er:0.0,lat:3.06,cached:2101093,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:3.13},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3298,to:14589,r:2,er:0.0,lat:15.94,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:16.61},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1314533,to:23001,r:137,er:0.0,lat:15.94,cached:697041,think:0,e4:0,e5:0,e429:0,eKnown:137,lat99:16.61},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:91,to:0,r:0,er:0.0,lat:15.94,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.61},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:100574,to:30834,r:21,er:0.0,lat:11.22,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:21,lat99:12.31},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:370932,to:28491,r:75,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-14": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:65639,to:31659,r:0,er:0.0,lat:0.0,cached:15207,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:16552,to:7984,r:0,er:0.0,lat:0.0,cached:3835,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:12686,to:6119,r:0,er:0.0,lat:0.0,cached:2939,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7187,to:3467,r:0,er:0.0,lat:0.0,cached:1665,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6868,to:3312,r:0,er:0.0,lat:0.0,cached:1591,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6764,to:3262,r:0,er:0.0,lat:0.0,cached:1567,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3987,to:1923,r:0,er:0.0,lat:0.0,cached:924,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2753,to:1328,r:0,er:0.0,lat:0.0,cached:638,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:121157,to:156787,r:23,er:0.0,lat:59.56,cached:3025,think:0,e4:0,e5:0,e429:0,eKnown:23,lat99:65.6},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:4478498,to:54884,r:328,er:0.0,lat:4.09,cached:3600602,think:0,e4:0,e5:0,e429:0,eKnown:328,lat99:7.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:6372275,to:23059,r:63,er:1.5873,lat:7.86,cached:4648283,think:0,e4:1,e5:0,e429:0,eKnown:63,lat99:8.28},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:104,to:0,r:0,er:1.5873,lat:7.86,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.28},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126206,to:50669,r:32,er:6.25,lat:7.76,cached:0,think:0,e4:2,e5:0,e429:0,eKnown:32,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:663815,to:79592,r:146,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-15": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:22679,to:27182,r:22,er:0.0,lat:57.88,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:22,lat99:65.26},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:289490,to:382131,r:57,er:0.0,lat:63.75,cached:194812,think:0,e4:0,e5:0,e429:0,eKnown:57,lat99:66.44},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:7613992,to:100450,r:801,er:0.0,lat:5.98,cached:6134299,think:0,e4:0,e5:0,e429:0,eKnown:801,lat99:7.94},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:8344,to:25417,r:2,er:0.0,lat:7.44,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.2},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2247381,to:37785,r:117,er:0.0,lat:7.44,cached:1221376,think:0,e4:0,e5:0,e429:0,eKnown:117,lat99:8.2},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:164,to:0,r:0,er:0.0,lat:7.44,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.2},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4049337,to:774314,r:72,er:5.5556,lat:8.18,cached:94162,think:0,e4:4,e5:0,e429:0,eKnown:72,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:10,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:3,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:2,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:33.39},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:345096,to:18184,r:77,er:0.0,lat:0.0,cached:59608,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-16": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:52747,to:61061,r:4,er:0.0,lat:63.75,cached:6016,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:66.44},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:2296800,to:298276,r:567,er:0.0,lat:4.09,cached:1840550,think:0,e4:0,e5:0,e429:0,eKnown:567,lat99:7.84},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7070,to:22648,r:2,er:0.0,lat:6.92,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1580786,to:20187,r:83,er:0.0,lat:6.92,cached:1150860,think:0,e4:0,e5:0,e429:0,eKnown:83,lat99:8.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:109,to:0,r:0,er:0.0,lat:6.92,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.1},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:821826,to:270140,r:807,er:0.0,lat:13.0,cached:2696,think:0,e4:0,e5:0,e429:0,eKnown:807,lat99:16.02},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:258843,to:26284,r:56,er:0.0,lat:0.0,cached:50468,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-17": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:83112,to:110057,r:10,er:0.0,lat:46.56,cached:6025,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:49.58},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:206977,to:259051,r:0,er:0.0,lat:0.0,cached:74070,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:970571,to:13191,r:6,er:0.0,lat:4.09,cached:594937,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1724814,to:19404,r:48,er:0.0,lat:7.13,cached:1356391,think:0,e4:0,e5:0,e429:0,eKnown:48,lat99:8.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:219,to:0,r:0,er:0.0,lat:7.13,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:281062,to:75765,r:62,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:62,lat99:8.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:393323,to:31629,r:82,er:0.0,lat:0.0,cached:226218,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-18": [
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:132704,to:1461,r:94,er:0.0,lat:3.83,cached:12644,think:0,e4:0,e5:0,e429:0,eKnown:94,lat99:4.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:580098,to:12498,r:21,er:0.0,lat:5.56,cached:220782,think:0,e4:0,e5:0,e429:0,eKnown:21,lat99:6.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:13,to:0,r:0,er:0.0,lat:5.56,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:6.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:84661,to:31219,r:59,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:59,lat99:8.3},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:15,er:0.0,lat:57.88,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:65.26},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:40,er:0.0,lat:63.75,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:40,lat99:66.44},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:286644,to:10665,r:51,er:0.0,lat:0.0,cached:149395,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-19": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:374274,to:48541,r:0,er:0.0,lat:0.0,cached:89757,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:94382,to:12241,r:0,er:0.0,lat:0.0,cached:22634,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:72338,to:9382,r:0,er:0.0,lat:0.0,cached:17348,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:40983,to:5315,r:0,er:0.0,lat:0.0,cached:9828,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:39160,to:5079,r:0,er:0.0,lat:0.0,cached:9391,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38568,to:5002,r:0,er:0.0,lat:0.0,cached:9249,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:22733,to:2948,r:0,er:0.0,lat:0.0,cached:5452,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:15698,to:2036,r:0,er:0.0,lat:0.0,cached:3765,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:28056,to:35549,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:157244,to:194726,r:0,er:0.0,lat:0.0,cached:64947,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:239852,to:3304,r:13,er:0.0,lat:2.04,cached:89944,think:0,e4:0,e5:0,e429:0,eKnown:13,lat99:2.09},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:474888,to:14558,r:47,er:0.0,lat:4.04,cached:191506,think:0,e4:0,e5:0,e429:0,eKnown:47,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:133,to:0,r:0,er:0.0,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:161877,to:42645,r:10,er:0.0,lat:9.8,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:10.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13258,to:2075,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-20": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126585,to:42121,r:13,er:0.0,lat:55.36,cached:30520,think:0,e4:0,e5:0,e429:0,eKnown:13,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:31921,to:10622,r:3,er:0.0,lat:55.36,cached:7696,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:24466,to:8141,r:3,er:0.0,lat:55.36,cached:5899,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13861,to:4612,r:1,er:0.0,lat:55.36,cached:3342,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13244,to:4407,r:1,er:0.0,lat:55.36,cached:3193,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13044,to:4341,r:1,er:0.0,lat:55.36,cached:3145,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7689,to:2558,r:1,er:0.0,lat:55.36,cached:1854,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5309,to:1767,r:1,er:0.0,lat:55.36,cached:1280,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:3714,to:2059,r:5,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:33.39},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:10060,to:8060,r:33,er:0.0,lat:63.75,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:33,lat99:66.44},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:171043,to:1930,r:35,er:0.0,lat:3.77,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:35,lat99:4.11},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1165411,to:28326,r:49,er:0.0,lat:7.76,cached:494630,think:0,e4:0,e5:0,e429:0,eKnown:49,lat99:8.26},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:105,to:0,r:0,er:0.0,lat:7.76,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.26},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:234389,to:24699,r:49,er:0.0,lat:8.07,cached:22291,think:0,e4:0,e5:0,e429:0,eKnown:49,lat99:8.33},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:84498,to:2405,r:16,er:0.0,lat:0.0,cached:40392,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-21": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:3694,to:2681,r:1,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:87879,to:58811,r:18,er:0.0,lat:32.3,cached:43607,think:0,e4:0,e5:0,e429:0,eKnown:18,lat99:33.3},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:52754,to:605,r:5,er:0.0,lat:3.01,cached:12644,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:3.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:8671080,to:57831,r:115,er:0.0,lat:6.08,cached:6336660,think:0,e4:0,e5:0,e429:0,eKnown:115,lat99:7.93},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:244,to:0,r:0,er:0.0,lat:6.08,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:7.93},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:314999,to:41452,r:86,er:0.0,lat:5.66,cached:34416,think:0,e4:0,e5:0,e429:0,eKnown:86,lat99:6.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:12,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:12,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:3,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:2,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:46093,to:1527,r:8,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-22": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:10871,to:14395,r:1,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:947200,to:13372,r:5,er:0.0,lat:2.91,cached:491044,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:3.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:475808,to:11384,r:114,er:0.0,lat:7.13,cached:222244,think:0,e4:0,e5:0,e429:0,eKnown:114,lat99:8.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:41,to:0,r:0,er:0.0,lat:7.13,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.14},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:199511,to:48618,r:112,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:112,lat99:4.17},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:609093,to:43066,r:117,er:0.0,lat:0.0,cached:349427,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-23": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19170,to:8393,r:0,er:0.0,lat:0.0,cached:6551,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4834,to:2117,r:0,er:0.0,lat:0.0,cached:1652,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3705,to:1622,r:0,er:0.0,lat:0.0,cached:1266,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2099,to:919,r:0,er:0.0,lat:0.0,cached:717,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2006,to:878,r:0,er:0.0,lat:0.0,cached:685,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1975,to:865,r:0,er:0.0,lat:0.0,cached:675,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1164,to:510,r:0,er:0.0,lat:0.0,cached:398,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:804,to:352,r:0,er:0.0,lat:0.0,cached:275,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:62159,to:80723,r:2,er:0.0,lat:49.07,cached:3022,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:50.08},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1744093,to:23447,r:204,er:0.0,lat:3.93,cached:1097600,think:0,e4:0,e5:0,e429:0,eKnown:204,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2855745,to:70310,r:167,er:0.0,lat:7.71,cached:1566028,think:0,e4:0,e5:0,e429:0,eKnown:167,lat99:8.25},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:177,to:0,r:0,er:0.0,lat:7.71,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.25},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:861226,to:124891,r:62,er:0.0,lat:7.76,cached:45032,think:0,e4:0,e5:0,e429:0,eKnown:62,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:144973,to:19796,r:32,er:0.0,lat:0.0,cached:26276,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-24": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:353322,to:111855,r:40,er:0.0,lat:32.72,cached:96139,think:0,e4:0,e5:0,e429:0,eKnown:40,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:89099,to:28207,r:10,er:0.0,lat:32.72,cached:24244,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:68288,to:21619,r:8,er:0.0,lat:32.72,cached:18581,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38689,to:12248,r:4,er:0.0,lat:32.72,cached:10527,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36967,to:11703,r:4,er:0.0,lat:32.72,cached:10059,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36409,to:11526,r:4,er:0.0,lat:32.72,cached:9907,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21460,to:6794,r:2,er:0.0,lat:32.72,cached:5839,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:14819,to:4691,r:2,er:0.0,lat:32.72,cached:4032,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:110775,to:139769,r:11,er:0.0,lat:32.72,cached:6003,think:0,e4:0,e5:0,e429:0,eKnown:11,lat99:33.39},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:52754,to:608,r:81,er:0.0,lat:3.89,cached:25289,think:0,e4:0,e5:0,e429:0,eKnown:81,lat99:4.13},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:44993,to:133567,r:7,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:923209,to:10392,r:36,er:0.0,lat:16.36,cached:396073,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:16.69},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:32,to:0,r:0,er:0.0,lat:16.36,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:118775,to:55147,r:162,er:0.6173,lat:4.09,cached:855,think:0,e4:0,e5:1,e429:0,eKnown:162,lat99:4.17},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126537,to:3346,r:23,er:0.0,lat:0.0,cached:64818,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-25": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:113678,to:150422,r:20,er:0.0,lat:32.49,cached:12094,think:0,e4:0,e5:0,e429:0,eKnown:20,lat99:33.34},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:629600,to:8108,r:58,er:0.0,lat:4.8,cached:469881,think:0,e4:0,e5:0,e429:0,eKnown:58,lat99:5.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1079683,to:8833,r:42,er:0.0,lat:3.98,cached:656610,think:0,e4:0,e5:0,e429:0,eKnown:42,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:39,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:141517,to:49018,r:60,er:0.0,lat:14.68,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:60,lat99:16.36},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:224913,to:4789,r:38,er:0.0,lat:0.0,cached:107281,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-26": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:39649,to:49169,r:21,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:21,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1370098,to:36394,r:28,er:0.0,lat:8.18,cached:599487,think:0,e4:0,e5:0,e429:0,eKnown:28,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:48,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:290264,to:101719,r:100,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:100,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:241444,to:7602,r:49,er:0.0,lat:0.0,cached:145766,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-27": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:125635,to:165780,r:7,er:0.0,lat:32.51,cached:6031,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.34},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2581322,to:43873,r:136,er:0.0,lat:4.01,cached:1228559,think:0,e4:0,e5:0,e429:0,eKnown:136,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:269725,to:0,r:14,er:0.0,lat:4.01,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:14,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:221282,to:77963,r:60,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:60,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:158674,to:8924,r:30,er:0.0,lat:0.0,cached:56690,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-28": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:90505,to:114436,r:22,er:0.0,lat:32.72,cached:3016,think:0,e4:0,e5:0,e429:0,eKnown:22,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4707867,to:51880,r:147,er:0.0,lat:3.83,cached:2908994,think:0,e4:0,e5:0,e429:0,eKnown:147,lat99:4.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:184900,to:0,r:6,er:0.0,lat:3.83,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:4.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2474003,to:139722,r:114,er:0.0,lat:7.65,cached:319223,think:0,e4:0,e5:0,e429:0,eKnown:114,lat99:8.24},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:79296,to:2629,r:16,er:0.0,lat:0.0,cached:8101,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-29": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:50486,to:59837,r:16,er:0.0,lat:32.61,cached:3024,think:0,e4:0,e5:0,e429:0,eKnown:16,lat99:33.37},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:196313,to:6359,r:38,er:0.0,lat:3.95,cached:4041,think:0,e4:0,e5:0,e429:0,eKnown:38,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5318852,to:234386,r:992,er:0.3024,lat:3.67,cached:674288,think:0,e4:0,e5:3,e429:0,eKnown:992,lat99:4.09},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:430787,to:51484,r:89,er:0.0,lat:0.0,cached:222055,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:9402,to:267,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:56618,to:2543,r:17,er:0.0,lat:0.0,cached:24305,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 2 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5724,to:221,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Biên Hòa",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:14307,to:533,r:5,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:26108,to:396,r:3,er:0.0,lat:0.0,cached:8106,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-30": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:109968,to:141821,r:9,er:0.0,lat:32.72,cached:3025,think:0,e4:0,e5:0,e429:0,eKnown:9,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3167,to:16282,r:2,er:0.0,lat:3.01,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:3.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:28294,to:1000,r:4,er:0.0,lat:3.01,cached:8149,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:3.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3541807,to:280671,r:1205,er:0.0,lat:3.72,cached:332236,think:0,e4:0,e5:0,e429:0,eKnown:1205,lat99:4.1},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:318344,to:24651,r:56,er:0.0,lat:0.0,cached:145886,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:120052,to:18121,r:25,er:0.0,lat:0.0,cached:95451,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:144784,to:4578,r:26,er:0.0,lat:0.0,cached:48609,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:59514,to:2541,r:11,er:0.0,lat:0.0,cached:48611,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:45039,to:4283,r:12,er:0.0,lat:0.0,cached:24304,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19391,to:864,r:4,er:0.0,lat:0.0,cached:16205,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-31": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:246023,to:306639,r:19,er:0.0,lat:62.08,cached:21133,think:0,e4:0,e5:0,e429:0,eKnown:19,lat99:66.1},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:776379,to:977484,r:0,er:0.0,lat:0.0,cached:365368,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:328991,to:9379,r:22,er:0.0,lat:3.98,cached:134774,think:0,e4:0,e5:0,e429:0,eKnown:22,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:5,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5043129,to:225843,r:1249,er:0.0801,lat:3.88,cached:854050,think:0,e4:0,e5:1,e429:0,eKnown:1249,lat99:4.13},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:137743,to:8654,r:25,er:0.0,lat:0.0,cached:89126,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:161548,to:4365,r:31,er:0.0,lat:0.0,cached:81040,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:73546,to:1716,r:13,er:0.0,lat:0.0,cached:56713,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-01": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1242647,to:241084,r:0,er:0.0,lat:0.0,cached:594550,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:313363,to:60795,r:0,er:0.0,lat:0.0,cached:149930,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:240172,to:46595,r:0,er:0.0,lat:0.0,cached:114911,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:136071,to:26399,r:0,er:0.0,lat:0.0,cached:65104,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:130016,to:25224,r:0,er:0.0,lat:0.0,cached:62207,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:128052,to:24843,r:0,er:0.0,lat:0.0,cached:61267,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:75477,to:14643,r:0,er:0.0,lat:0.0,cached:36112,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:52119,to:10111,r:0,er:0.0,lat:0.0,cached:24936,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:52318,to:68345,r:44,er:0.0,lat:32.38,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:44,lat99:33.32},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:408631,to:13253,r:40,er:0.0,lat:4.01,cached:89724,think:0,e4:0,e5:0,e429:0,eKnown:40,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:77,to:0,r:0,er:0.0,lat:4.01,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:74619,to:13903,r:60,er:0.0,lat:3.88,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:60,lat99:4.13},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:146,er:0.0,lat:63.75,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:146,lat99:66.44},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:187086,to:5428,r:37,er:0.0,lat:0.0,cached:105329,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:45592,to:3809,r:7,er:0.0,lat:0.0,cached:16202,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:66408,to:1317,r:12,er:0.0,lat:0.0,cached:42555,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-02": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:4597,to:6442,r:9,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:9,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:42986,to:146988,r:2,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2283995,to:55647,r:18,er:0.0,lat:3.98,cached:1575349,think:0,e4:0,e5:0,e429:0,eKnown:18,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:281,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:385809,to:54424,r:58,er:1.7241,lat:7.13,cached:19979,think:0,e4:0,e5:1,e429:0,eKnown:58,lat99:8.14},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:66,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:66,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:17,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:17,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:13,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:13,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:7,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:7,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:7,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:4,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:3,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:33.39},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:56031,to:1754,r:11,er:0.0,lat:0.0,cached:16204,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-03": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:476470,to:51418,r:0,er:0.0,lat:0.0,cached:105132,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:120153,to:12966,r:0,er:0.0,lat:0.0,cached:26512,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:92090,to:9938,r:0,er:0.0,lat:0.0,cached:20319,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:52174,to:5630,r:0,er:0.0,lat:0.0,cached:11512,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:49852,to:5380,r:0,er:0.0,lat:0.0,cached:11000,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:49099,to:5299,r:0,er:0.0,lat:0.0,cached:10834,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:28940,to:3123,r:0,er:0.0,lat:0.0,cached:6386,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19984,to:2157,r:0,er:0.0,lat:0.0,cached:4409,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:55843,to:70767,r:1,er:0.0,lat:32.72,cached:3026,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:9590,to:32788,r:10,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:530749,to:17427,r:123,er:0.0,lat:8.18,cached:113940,think:0,e4:0,e5:0,e429:0,eKnown:123,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:41,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1110902,to:66474,r:112,er:0.0,lat:7.76,cached:189332,think:0,e4:0,e5:0,e429:0,eKnown:112,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126903,to:6509,r:22,er:0.0,lat:0.0,cached:64816,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-04": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:201409,to:57711,r:36,er:0.0,lat:32.72,cached:45826,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:50790,to:14553,r:9,er:0.0,lat:32.72,cached:11556,think:0,e4:0,e5:0,e429:0,eKnown:9,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38927,to:11154,r:7,er:0.0,lat:32.72,cached:8857,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:22054,to:6319,r:4,er:0.0,lat:32.72,cached:5018,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21073,to:6038,r:4,er:0.0,lat:32.72,cached:4795,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:20755,to:5947,r:4,er:0.0,lat:32.72,cached:4722,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:12233,to:3505,r:2,er:0.0,lat:32.72,cached:2783,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8447,to:2420,r:2,er:0.0,lat:32.72,cached:1922,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:37402,to:49255,r:10,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7211,to:21235,r:0,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4253440,to:38141,r:38,er:0.0,lat:7.03,cached:2646520,think:0,e4:0,e5:0,e429:0,eKnown:38,lat99:8.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:317,to:0,r:0,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1459674,to:97784,r:253,er:0.0,lat:2.04,cached:69236,think:0,e4:0,e5:0,e429:0,eKnown:253,lat99:2.09},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36206,to:835,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-05": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:24547,to:29496,r:7,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:508428,to:14465,r:138,er:0.0,lat:3.96,cached:138861,think:0,e4:0,e5:0,e429:0,eKnown:138,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:37,to:0,r:0,er:0.0,lat:3.96,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:562165,to:65906,r:217,er:0.0,lat:7.03,cached:142189,think:0,e4:0,e5:0,e429:0,eKnown:217,lat99:8.12},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:182688,to:6900,r:34,er:0.0,lat:0.0,cached:64822,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:154803,to:4814,r:32,er:0.0,lat:0.0,cached:85018,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:75019,to:1473,r:13,er:0.0,lat:0.0,cached:48643,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-06": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:61532,to:78459,r:5,er:0.0,lat:32.3,cached:3021,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:33.3},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:148806,to:123339,r:30,er:0.0,lat:32.3,cached:40577,think:0,e4:0,e5:0,e429:0,eKnown:30,lat99:33.3},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:27203,to:273,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1984131,to:28447,r:36,er:0.0,lat:3.98,cached:880661,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:4.15},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:110,to:0,r:0,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1088483,to:144796,r:168,er:0.0,lat:7.97,cached:108017,think:0,e4:0,e5:0,e429:0,eKnown:168,lat99:8.3},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36190,to:824,r:6,er:0.0,lat:0.0,cached:8102,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38007,to:1067,r:9,er:0.0,lat:0.0,cached:8103,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:28703,to:2828,r:4,er:0.0,lat:0.0,cached:8102,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-07": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:156995,to:198145,r:11,er:0.0,lat:60.4,cached:6046,think:0,e4:0,e5:0,e429:0,eKnown:11,lat99:65.77},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:254228,to:291055,r:48,er:0.0,lat:62.91,cached:123809,think:0,e4:0,e5:0,e429:0,eKnown:48,lat99:66.27},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:145223,to:7599,r:37,er:0.0,lat:7.86,cached:16258,think:0,e4:0,e5:0,e429:0,eKnown:37,lat99:8.28},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:60,to:0,r:0,er:0.0,lat:7.86,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.28},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:976357,to:82602,r:319,er:0.3135,lat:3.67,cached:85882,think:0,e4:0,e5:1,e429:0,eKnown:319,lat99:4.09},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:3,er:0.0,lat:2.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:2.09},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126399,to:5005,r:18,er:0.0,lat:0.0,cached:81021,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:149756,to:5277,r:30,er:0.0,lat:0.0,cached:81013,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:18911,to:502,r:4,er:0.0,lat:0.0,cached:8101,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-08": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:75792,to:14367,r:0,er:0.0,lat:0.0,cached:12712,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19113,to:3623,r:0,er:0.0,lat:0.0,cached:3206,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:14649,to:2777,r:0,er:0.0,lat:0.0,cached:2457,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8299,to:1573,r:0,er:0.0,lat:0.0,cached:1392,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7930,to:1503,r:0,er:0.0,lat:0.0,cached:1330,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7810,to:1480,r:0,er:0.0,lat:0.0,cached:1310,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4604,to:873,r:0,er:0.0,lat:0.0,cached:772,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3179,to:603,r:0,er:0.0,lat:0.0,cached:533,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:32419,to:41790,r:28,er:0.0,lat:44.88,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:28,lat99:49.24},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:25906,to:92064,r:39,er:0.0,lat:7.86,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:39,lat99:8.28},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:103038,to:46923,r:79,er:0.0,lat:15.1,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:79,lat99:16.44},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:67163,to:1905,r:13,er:0.0,lat:0.0,cached:40512,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:39858,to:10557,r:10,er:0.0,lat:0.0,cached:7904,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Nghiên cứu thị trường",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:42942,to:7932,r:8,er:0.0,lat:0.0,cached:7904,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19127,to:357,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-09": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:609416,to:73803,r:60,er:0.9009,lat:8.07,cached:81092,think:0,e4:1,e5:0,e429:0,eKnown:60,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:153679,to:18611,r:15,er:0.9009,lat:8.07,cached:20449,think:0,e4:0,e5:0,e429:0,eKnown:15,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:117785,to:14264,r:12,er:0.9009,lat:8.07,cached:15673,think:0,e4:0,e5:0,e429:0,eKnown:12,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:66731,to:8081,r:7,er:0.9009,lat:8.07,cached:8880,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:63762,to:7722,r:6,er:0.9009,lat:8.07,cached:8484,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:62799,to:7605,r:6,er:0.9009,lat:8.07,cached:8356,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:37015,to:4483,r:4,er:0.9009,lat:8.07,cached:4925,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:8.33},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:25560,to:3095,r:2,er:0.9009,lat:8.07,cached:3401,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.33},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:11445,to:13695,r:6,er:0.0,lat:32.51,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:33.34},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:129471,to:142461,r:0,er:0.0,lat:0.0,cached:56837,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:175319,to:6062,r:5,er:0.0,lat:5.87,cached:40818,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:6.21},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:957253,to:72146,r:40,er:0.0,lat:4.04,cached:56285,think:0,e4:0,e5:0,e429:0,eKnown:40,lat99:4.16},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:632418,to:40841,r:44,er:0.0,lat:0.0,cached:74018,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Nghiên cứu thị trường",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:407878,to:67172,r:41,er:0.0,lat:0.0,cached:45620,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:26789,to:9379,r:7,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-10": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:39782,to:5750,r:12,er:0.0,lat:43.62,cached:8476,think:0,e4:0,e5:0,e429:0,eKnown:12,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:10032,to:1450,r:3,er:0.0,lat:43.62,cached:2138,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7689,to:1111,r:2,er:0.0,lat:43.62,cached:1638,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4356,to:630,r:1,er:0.0,lat:43.62,cached:928,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4162,to:602,r:1,er:0.0,lat:43.62,cached:887,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4099,to:593,r:1,er:0.0,lat:43.62,cached:873,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2416,to:349,r:1,er:0.0,lat:43.62,cached:515,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:62.41},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1669,to:241,r:1,er:0.0,lat:43.62,cached:356,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:62.41},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:274390,to:329717,r:36,er:0.0,lat:63.75,cached:146137,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:66.44},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:13709,to:46731,r:1,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1169042,to:26865,r:23,er:0.0,lat:4.09,cached:431872,think:0,e4:0,e5:0,e429:0,eKnown:23,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:77,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:681020,to:72560,r:182,er:0.5495,lat:4.09,cached:45954,think:0,e4:0,e5:1,e429:0,eKnown:182,lat99:4.17},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:2,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:128239,to:28582,r:23,er:0.0,lat:0.0,cached:39527,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-11": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:110723,to:56410,r:9,er:0.0,lat:4.09,cached:29665,think:0,e4:0,e5:0,e429:0,eKnown:9,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:27922,to:14225,r:2,er:0.0,lat:4.09,cached:7481,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21400,to:10903,r:2,er:0.0,lat:4.09,cached:5734,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:12124,to:6177,r:1,er:0.0,lat:4.09,cached:3248,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:11585,to:5902,r:1,er:0.0,lat:4.09,cached:3104,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:11410,to:5813,r:1,er:0.0,lat:4.09,cached:3057,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6725,to:3426,r:1,er:0.0,lat:4.09,cached:1802,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:4.17},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4644,to:2366,r:0,er:0.0,lat:4.09,cached:1244,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:123918,to:149869,r:0,er:0.0,lat:0.0,cached:18095,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:129502,to:144011,r:64,er:0.0,lat:63.75,cached:56847,think:0,e4:0,e5:0,e429:0,eKnown:64,lat99:66.44},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15469,to:50361,r:6,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1050522,to:45964,r:102,er:0.0,lat:4.09,cached:320159,think:0,e4:0,e5:0,e429:0,eKnown:102,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:135,to:0,r:0,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.17},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2739807,to:279251,r:393,er:0.2545,lat:7.76,cached:240138,think:0,e4:0,e5:1,e429:0,eKnown:393,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36206,to:5124,r:6,er:0.0,lat:0.0,cached:7907,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5748,to:903,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:32252,to:4699,r:8,er:0.0,lat:0.0,cached:7904,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-12": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:18136,to:2786,r:18,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:18,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4574,to:702,r:5,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3505,to:538,r:3,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1986,to:305,r:2,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1898,to:291,r:2,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1869,to:287,r:2,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1102,to:169,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:761,to:117,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3579,to:1644,r:4,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:902,to:414,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:692,to:318,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:392,to:180,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:374,to:172,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:369,to:169,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:217,to:100,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:150,to:69,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:44818,to:54837,r:22,er:0.0,lat:57.04,cached:3022,think:0,e4:0,e5:0,e429:0,eKnown:22,lat99:65.1},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:53261,to:173983,r:18,er:0.0,lat:15.94,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:18,lat99:16.61},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:1272464,to:9383,r:100,er:0.0,lat:15.94,cached:761092,think:0,e4:0,e5:0,e429:0,eKnown:100,lat99:16.61},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:25,to:0,r:0,er:0.0,lat:15.94,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.61},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:407294,to:47462,r:329,er:0.0,lat:3.72,cached:5029,think:0,e4:0,e5:0,e429:0,eKnown:329,lat99:4.1},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:152533,to:88226,r:24,er:0.0,lat:0.0,cached:39525,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:30398,to:9038,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:48048,to:11451,r:9,er:0.0,lat:0.0,cached:15810,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Tổng công ty Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:9384,to:1702,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-13": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:8,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:2,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:1,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:8,er:0.0,lat:60.4,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:65.77},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:6,er:0.0,lat:4.09,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:6,lat99:4.17},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:0,to:0,r:46,er:0.0,lat:16.22,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:46,lat99:16.67},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:115,er:0.0,lat:5.61,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:115,lat99:6.16},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:47993,to:8641,r:9,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:10355,to:4190,r:2,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:10570,to:4084,r:3,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"C4LED",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:13,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"CN Biên Hòa",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:12,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"CN Cần Thơ",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"CN Hồ Chí Minh",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:19,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"CN Nha Trang",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:12,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"CN Tiền Giang",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"CN Đà Nẵng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:16,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Kế hoạch",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Kế toán",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:1,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Nghiên cứu thị trường",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:12,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:30,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:12,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"PBH3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:18,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TMĐT",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:27,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:14,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT4",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Trung tâm R&D",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:20,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Truyền thông",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Tây Nguyên",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:14,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Tổng công ty Rạng Đông",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:74,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Vùng 1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Vùng 2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:13,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Vùng 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Xuất khẩu",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:25,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:9,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 1 - HN2 - Sơn La - Điện Biên",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:18,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 1 - Hà Nội",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 1 - Nam Định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 1 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 2 - HN2 - Hoà Bình",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 2 - Hà Nội",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 2 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 2 - Thái Bình",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 3 - Hà Nam - Ninh Bình",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 3 - Hà Nội",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 3 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:1,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 3 - Vĩnh Phúc",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 4",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 4 - Bắc Ninh",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 4 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 4 - Thanh Hoá",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:13,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 4 - Thái Nguyên - Cao Bằng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 5",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 5 - Bắc Giang - Lạng Sơn",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 5 - Nghệ An - Hà Tĩnh",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 5 - Phú Thọ",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 5 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:1,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 6 - Hưng Yên",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 6 - TT2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:1,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 6 - Yên Bái - Tuyên Quang - Hà Giang - Lào Cai - Lai Châu",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:19,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 7 - Hải Dương - Hải Phòng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:12,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội 8 - Quảng Ninh",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội An Giang",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Bình Dương",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Bình Phước",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Bình Thuận",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Bình Định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Bạc Liêu",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Cà Mau",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Cần Thơ",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Gia Lai",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:9,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Huế",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Khánh Hòa",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Kiên Giang",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:13,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Kon Tum",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Long An",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Lâm Đồng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Ninh Thuận",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Phú Yên",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Quảng Bình",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Quảng Nam",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Quảng Trị",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:5,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Siêu Thị",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Sóc Trăng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Vĩnh Long",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Vũng Tàu",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:9,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Biên Hòa",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Cần Thơ",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Hồ Chí Minh",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Nha Trang",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Tiền Giang",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - CN Đà Nẵng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:7,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 2",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách - Vùng 3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội chuyên trách 1 - trung tâm 1",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Đà Nẵng",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Đắk Lắk",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Đắk Nông",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:4,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Đồng Nai",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:9,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Đội Đồng Tháp",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"CN Tiền Giang",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:1,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:1,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:9,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ]
};

function juneExcelRow(a,d,m,ug,ti,to,r,er,lat,u){
  return {a:a,d:d,m:m,ug:ug,u:u||0,c:0,ti:ti||0,to:to||0,r:r||0,er:er||0,lat:lat||0,cached:0,think:0};
}
function buildJuneExcelWeeks(){
  // Đọc và chuẩn hóa từ “Bảng tổng hợp chi phí token AI agent tháng 6 (3).xlsx”.
  // Các dòng tuần 1 bị lệch cột và ô 967.585 được chuẩn hóa theo ngữ nghĩa token.
  var k="Nhóm Kinh doanh", cs="Nhóm CSKH", data="Nhóm Dữ liệu", internal="Nhóm Nội bộ";
  var days={
    "2026-06-01":[
      juneExcelRow("Sale Agent","Anh Em tiếp thị","Gemini 3.1 Flash Lite",k,0,927,1),
      juneExcelRow("Sale Agent","Anh Em tiếp thị","Gemini 3.5 Flash",k,0,2969,1),
      juneExcelRow("Sale Agent","Anh Em tiếp thị","Gemini 2.5 Flash",k,0,681499,136),
      juneExcelRow("Chatbot Contact Center","Chăm sóc khách hàng","Gemini 3.1 Flash Lite",cs,0,0,0),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 3.0 Flash",cs,30500000,420712,973),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 2.5 Flash",cs,77130,204635,86),
      juneExcelRow("Phân Loại Phản Hồi Tiếp Thị","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,2559100,1206600,188,0,4.5,3),
      juneExcelRow("Phân Loại Dữ Liệu CRM","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,1735334,1209481,147,0,4.5,3)
    ],
    "2026-06-08":[
      juneExcelRow("Sale Agent","Anh Em tiếp thị","Gemini 2.5 Flash",k,0,922587,185),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 3.0 Flash",cs,21680000,297545,761),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 2.5 Flash",cs,62270,250660,72),
      juneExcelRow("Phân Loại Phản Hồi Tiếp Thị","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,1559100,1066000,104,0,4.5),
      juneExcelRow("Phân Loại Dữ Liệu CRM","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,1388267,967585,186,0,4.5)
    ],
    "2026-06-15":[
      juneExcelRow("Sale Agent","Anh Em tiếp thị","Gemini 2.5 Flash",k,0,10737006,2147),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 3.0 Flash",cs,2750000,91908,145),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 2.5 Flash",cs,55140,188678,49),
      juneExcelRow("Phân Loại Phản Hồi Tiếp Thị","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,1339100,1006600,97,0,4.5),
      juneExcelRow("Phân Loại Dữ Liệu CRM","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,2776534,1935170,248,0,4.5)
    ],
    "2026-06-22":[
      juneExcelRow("Sale Agent","Anh Em tiếp thị","Gemini 2.5 Flash",k,0,685476,137),
      juneExcelRow("Chatbot Contact Center","Chăm sóc khách hàng","Gemini 3.1 Flash Lite",cs,9060,131,2),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 3.0 Flash",cs,13060000,188678,481),
      juneExcelRow("Chatbot Contact Center","Thương mại điện tử","Gemini 2.5 Flash",cs,20240,34226,12),
      juneExcelRow("Phân Loại Phản Hồi Tiếp Thị","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,2059133,1306621,155,0,4.5),
      juneExcelRow("Phân Loại Dữ Liệu CRM","P.NCTT , TTDL&ĐHS","Gemini 2.5 Flash",data,1653300,1109400,188,0,4.5)
    ]
  };
  var contractUnits=[["Công ty CPBĐ PN Rạng Đông",5],["Phòng Bán hàng 1",19],["Phòng Bán hàng 2",10],["Phòng Bán hàng 3",10],["TT C4LED",2],["TT&TMĐT",3],["TTDL&DHS",6]];
  var ralliUnits=[["PBH1",257],["PBH2",155],["PBH3",247],["Xuất khẩu",25],["Truyền thông",7],["Kế toán",1],["TMĐT",27],["C4LED",15],["Nghiên cứu thị trường",11],["Kế hoạch",8],["Trung tâm R&D",20],["Quản trị hệ thống",18]];
  contractUnits.forEach(function(x){days["2026-06-01"].push(juneExcelRow("Trợ Lý Ảo Hợp Đồng",x[0],"Gemini 2.5 Flash",k,0,0,0,0,0,x[1]));});
  ralliUnits.forEach(function(x){days["2026-06-01"].push(juneExcelRow("Trợ lý ảo Ralli",x[0],"Gemini 2.5 Flash",k,0,0,0,0,0,x[1]));});
  return days;
}

/* ─── Tiện ích ─── */
function num(v){ var n = Number(v); return isNaN(n) ? 0 : n; }
function rid(){ return "r" + Math.random().toString(36).slice(2,8); }
function clone(o){ var n={}; Object.keys(o).forEach(function(k){ n[k]={i:num(o[k].i), o:num(o[k].o)}; }); return n; }
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
// Ngày theo định dạng mm/dd/YYYY dùng cho tiêu đề và dòng "Kỳ dữ liệu".
function fmtDateUS(iso){
  var p=String(iso==null?"":iso).split("-");
  return p.length===3 ? (p[1]+"/"+p[2]+"/"+p[0]) : String(iso);
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
function moneyCell(usdValue, cls){
  return "<td class='"+(cls||"num cost")+"' title='"+esc(usdReference(usdValue))+"'>"+money(usdValue)+"</td>";
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
function cost(r){ var p = state.pricing[r.m]; if(!p) return 0; return num(r.ti)/1e6*num(p.i) + num(r.to)/1e6*num(p.o); }
function isExcludedDepartment(name){ return !!EXCLUDED_DEPARTMENTS[String(name||"").trim()]; }
function isExcludedAgent(name){ return !!EXCLUDED_AGENTS[String(name||"").trim().toLowerCase()]; }
/* File nguồn đang gộp P.NCTT và TTDL&ĐHS trong một nhãn. Tách theo đúng agent nghiệp vụ
   để không nhân đôi request/token: phản hồi tiếp thị thuộc P.NCTT, dữ liệu CRM thuộc TTDL&ĐHS. */
function splitCombinedDepartment(row){
  var dept=String(row&&row.d||"").trim().replace(/\s*,\s*/g,",").toLowerCase();
  if(dept!=="p.nctt,ttdl&đhs") return row.d;
  if(row.a==="Phân Loại Phản Hồi Tiếp Thị") return "P.NCTT";
  if(row.a==="Phân Loại Dữ Liệu CRM") return "TTDL&ĐHS";
  return row.d;
}
function sanitizeUsageRows(rows){
  return (rows||[]).filter(function(r){return !isExcludedDepartment(r.d)&&!isExcludedAgent(r.a);})
    .map(function(r){
      var dept=splitCombinedDepartment(r);
      return dept===r.d?r:Object.assign({},r,{d:dept});
    });
}

/* ═══════════════ TRUY VẤN CÂY ĐƠN VỊ ═══════════════ */
var unitIndex = {}, unitChildIndex = {}, autoUnitSeq = 0;
(function buildUnitIndex(){
  unitIndex = {}; unitChildIndex = {};
  ORG_UNITS.forEach(function(u){
    unitIndex[u.id] = u;
    var p = u.parent || "";
    (unitChildIndex[p] = unitChildIndex[p] || []).push(u);
  });
})();
/* Phân giải chuỗi phòng ban tự do về một đơn vị. Chuỗi lạ KHÔNG bị loại: tự sinh một
   đơn vị cấp 1 để không mất số liệu và không gom sai vào đơn vị khác. */
function unitOf(deptString){
  var key = String(deptString==null?"":deptString).trim();
  if(!key || key==="—") return null;
  var id = UNIT_ALIASES[key];
  if(id && unitIndex[id]) return unitIndex[id];
  // Khớp lỏng: bỏ khoảng trắng thừa quanh dấu phẩy để chịu được lệch dấu cách.
  var loose = key.replace(/\s*,\s*/g, ",").toLowerCase();
  for(var alias in UNIT_ALIASES){
    if(alias.replace(/\s*,\s*/g, ",").toLowerCase() === loose){
      var hit = unitIndex[UNIT_ALIASES[alias]];
      if(hit) return hit;
    }
  }
  // Danh sách Ralli dùng tên đầy đủ của 86 phòng/đội trong ORG_UNITS. Khớp trực tiếp
  // trước khi tạo auto-unit để tài khoản luôn nằm đúng nhánh vùng/chi nhánh.
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
function reportingRoots(){
  var companyChildren=unitChildren("company"), corpChildren=unitChildren("rd-corp");
  var companyDirect=companyChildren.filter(function(u){return u.id!=="rd-corp";});
  var outsideCompany=unitRoots().filter(function(u){return u.id!=="company";});
  return corpChildren.concat(companyDirect,outsideCompany);
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
function rebuildRalliProvisioned(){
  DEPT_PROVISIONED={};
  (window.RALLI_USERS||[]).forEach(function(entry){
    var unit=unitOf(entry.department);
    if(!unit||isExcludedUnit(unit)) return;
    unitPath(unit.id).forEach(function(node){
      DEPT_PROVISIONED[node.id]=(DEPT_PROVISIONED[node.id]||0)+1;
    });
  });
}
rebuildRalliProvisioned();
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
function defaultState(){
  // Seed dữ liệu Excel thật tháng 6 làm kỳ so sánh và tháng 7 làm kỳ hiện tại.
  var sourceDays=Object.assign({},buildJuneExcelWeeks(),SEED_DAYS), days={}, order=Object.keys(sourceDays).sort();
  order.forEach(function(d){ days[d] = sanitizeUsageRows(sourceDays[d]).map(function(r){ return Object.assign({}, r, { id:rid() }); }); });
  return { days:days, dayOrder:order, activeDay:order[order.length-1],
    range:{start:"2026-08-01",end:"2026-08-13"},
    filters:{dept:"",user:"",provider:"",model:"",agent:""},
    deptExpanded:defaultDeptExpanded(), deptExpandedInit:1, deptSearch:"",
    matrixExpanded:{}, matrixSearch:"", pmCollapsed:{}, pricing:clone(basePricing) };
}
/* Cấp 1 của cây giờ đã là phòng ban thật (xem buildDeptRows dùng reportingRoots),
   nên mở dashboard là thấy ngay danh sách phòng ban mà không cần bung sẵn cấp nào —
   giống hệt ma trận tab Agents. */
function defaultDeptExpanded(){ return {}; }
function loadState(){
  try{ var raw = localStorage.getItem(STORE); if(!raw) return defaultState();
    var s = JSON.parse(raw);
    if(!s || !s.days || !s.dayOrder || !s.pricing) return defaultState();
    if(!s.filters) s.filters = {dept:"",user:"",provider:"",model:"",agent:""};
    // State mới: bỏ qua an toàn khi đọc localStorage của phiên bản cũ.
    if(!s.deptExpanded||typeof s.deptExpanded!=="object") s.deptExpanded={};
    if(!s.matrixExpanded||typeof s.matrixExpanded!=="object") s.matrixExpanded={};
    if(typeof s.matrixSearch!=="string") s.matrixSearch="";
    if(typeof s.deptSearch!=="string") s.deptSearch="";
    // Cây nhà cung cấp → model mặc định MỞ, nên chỉ lưu những nhánh bị thu lại.
    if(!s.pmCollapsed||typeof s.pmCollapsed!=="object") s.pmCollapsed={};
    // Chỉ seed trạng thái mở mặc định MỘT lần. Không có cờ này thì người dùng thu gọn
    // hết rồi tải lại trang sẽ bị bung ra lần nữa.
    if(!s.deptExpandedInit){ s.deptExpanded=defaultDeptExpanded(); s.deptExpandedInit=1; }
    // Bản cũ dùng breadcrumb theo cột; ma trận giờ là cây accordion nên bỏ hai khoá này.
    delete s.matrixPath; delete s.matrixUser;
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
    s.dayOrder.forEach(function(d){if(s.days[d]) s.days[d]=sanitizeUsageRows(s.days[d]);});
    s.dayOrder = s.dayOrder.filter(function(d){ return s.days[d]&&s.days[d].length; }).sort();
    if(isExcludedDepartment(s.filters.dept)) s.filters.dept="";
    if(!s.activeDay) s.activeDay = s.dayOrder[s.dayOrder.length-1] || SEED_DAY;
    if(!s.range || !s.range.start || !s.range.end){ s.range = {start:"2026-08-01",end:"2026-08-13"}; }
    return s;
  }catch(e){ return defaultState(); }
}
function saveState(){ try{ localStorage.setItem(STORE, JSON.stringify(state)); }catch(e){} }

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
    if(wantIds){ var u=unitOf(r.d); if(!u||!wantIds[u.id]) return false; }
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
function minDataDate(){ return state.dayOrder.length ? parseISO(state.dayOrder[0]) : parseISO(SEED_DAY); }
function maxDataDate(){ return state.dayOrder.length ? parseISO(state.dayOrder[state.dayOrder.length-1]) : parseISO(SEED_DAY); }
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
function aggregate(rows){
  var a = {u:0,c:0,ti:0,to:0,r:0,cached:0,think:0,cost:0,erW:0,latW:0,latR:0,
           e4:0,e5:0,e429:0,eKnown:0,lat99W:0,lat99R:0};
  rows.forEach(function(row){
    a.u+=num(row.u); a.c+=num(row.c); a.ti+=num(row.ti); a.to+=num(row.to);
    a.r+=num(row.r); a.cached+=num(row.cached); a.think+=num(row.think);
    a.cost+=cost(row); a.erW+=num(row.er)*num(row.r);
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
  a.tokens = a.ti + a.to;
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
  setWithTitle("m-ov-cost",usageCompact(A.cost),money(A.cost)+" · "+usdReference(A.cost));
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
  set("i-ov-error",topError&&topError.er>0?esc(topError.key)+" cao nhất: "+topError.er.toFixed(1)+"%.":"Không ghi nhận lỗi.");

  set("ov-cost-total",moneyCompact(A.cost));
  set("ov-token-total",fmtTok(A.tokens));
  set("ov-request-total",fmtCompactNum(A.r)+" request");
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
function renderOverviewDetail(rows,active){
  var agents=active.slice().sort(function(a,b){return b.cost-a.cost;});
  var html="", totals={u:0,r:0,tokens:0,cost:0,erW:0};
  agents.forEach(function(g){
    var agentRows=rows.filter(function(r){return r.a===g.key;});
    var byDept=groupAgg(agentRows,function(r){return deptDisplayName(r.d);})
      .sort(function(a,b){return (b.cost-a.cost)||(b.r-a.r)||a.key.localeCompare(b.key,"vi");});
    if(!byDept.length) return;
    totals.u+=g.u; totals.r+=g.r; totals.tokens+=g.tokens; totals.cost+=g.cost; totals.erW+=g.er*g.r;
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
        "<td class='num cost' title='"+esc(usdReference(d.cost))+"'>"+moneyCompact(d.cost)+"</td>"+
        "<td class='num"+(d.er>=2?" text-red":"")+"'>"+d.er.toFixed(1)+"%</td>"+
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
      "<td class='num cost'>"+moneyCompact(totals.cost)+"</td><td class='num'>"+totalEr.toFixed(1)+"%</td>"+
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
  mkDonut("c-ov-success",["Trả kết quả tốt","Lỗi"],[Math.max(0,100-A.er),Math.max(0,A.er)],null,function(v){return v.toFixed(1)+"%";},["#22c55e","#ef4444"]);
  var byAgent=groupAgg(rows,function(r){return r.a;}).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;}).slice(0,8);
  mkDonut("c-ov-agent-share",byAgent.map(function(g){return g.key;}),byAgent.map(function(g){return g.cost;}),"lg-ov-agent-share",moneyCompact);
  var byUnit=groupAgg(rows.filter(function(r){return r.d&&r.d!=="—";}),function(r){return r.d;}).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;}).slice(0,8);
  mkBar("c-ov-unit-cost",byUnit.map(function(g){return g.key;}),byUnit.map(function(g){return g.cost;}),{horizontal:true,money:true,colors:"#22c55e"});
  buildOverviewWeekHeatmap();
}
function mkOverviewLine(id,labels,data,kind,color){
  var tick=kind==="money"?function(v){return moneyCompact(v);}:kind==="tokens"?function(v){return fmtTokShort(v);}:function(v){return fmt(v);};
  chart(id,{
    type:"line",
    data:{labels:labels,datasets:[{data:data,borderColor:color,backgroundColor:color+"22",fill:true,tension:.34,borderWidth:2,pointRadius:data.length<=8?3:1.5,pointBackgroundColor:color}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){
      return kind==="money"?money(c.parsed.y):kind==="tokens"?fmtTokFull(c.parsed.y):fmt(c.parsed.y)+" request";
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
    requests:aggs.map(function(a){return a.r;})
  };
}

/* ═══════════════ RENDER: PHÒNG BAN & USER ═══════════════ */
/* Gom usage row theo đơn vị đã chuẩn hoá (không theo chuỗi r.d thô nữa). */
function groupRowsByUnit(rows){
  var map={};
  (rows||[]).forEach(function(r){
    var unit=unitOf(r.d);
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
function adoptionCell(activeCount, provisioned){
  if(provisioned==null||provisioned<=0) return "<td class='num'><span class='metric-na'>—</span></td>";
  var rate=activeCount/provisioned*100;
  var cls=rate<INSIGHT_THRESHOLDS.adoptionCritical?"text-red":
    (rate<INSIGHT_THRESHOLDS.adoptionWarning?"text-orange":"text-green");
  return "<td class='num "+cls+"' title='"+esc(fmt(activeCount)+" tài khoản có request / "+fmt(provisioned)+" tài khoản được cấp")+"'>"+
    fmt(activeCount)+"/"+fmt(provisioned)+" · "+rate.toFixed(0)+"%</td>";
}
function naCell(){ return "<td class='num'><span class='metric-na'>—</span></td>"; }
function sortAccounts(list){
  return list.slice().sort(function(a,b){ return num(b.req)-num(a.req)||a.user.localeCompare(b.user); });
}
function usageUnderUnit(unitId, rows){
  var ids={};
  [unitId].concat(unitDescendants(unitId).map(function(u){return u.id;})).forEach(function(id){ids[id]=true;});
  var scoped=(rows||[]).filter(function(r){var u=unitOf(r.d);return u&&ids[u.id];});
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
/* Đơn vị nào có usage thật trong kỳ (cộng dồn lên mọi cấp cha). */
function deptUsageUnitIds(rows){
  var ids={};
  (rows||[]).forEach(function(r){
    var u=unitOf(r.d);
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
    var u=unitOf(r.d);
    if(!u||isExcludedUnit(u)) return;
    var rq=num(r.r), c=cost(r), ti=num(r.ti), to=num(r.to), erW=num(r.er)*rq;
    unitPath(u.id).forEach(function(n){
      var m=map[n.id]||(map[n.id]={r:0,ti:0,to:0,tokens:0,cost:0,erW:0,rowCount:0,agentSet:{}});
      m.r+=rq; m.ti+=ti; m.to+=to; m.cost+=c; m.erW+=erW; m.rowCount++;
      if(r.a) m.agentSet[r.a]=1;
    });
  });
  Object.keys(map).forEach(function(id){
    var m=map[id];
    m.tokens=m.ti+m.to; m.er=m.r?m.erW/m.r:0; m.agents=Object.keys(m.agentSet).length;
  });
  return map;
}
/* Chỉ số của MỘT hàng đơn vị. Ưu tiên usage thật; đơn vị không có dòng usage riêng
   (vùng/đội) thì lấy phần đã phân bổ xuống tài khoản, để tổng cấp con khớp cấp cha. */
function deptUnitMetrics(unit, usageIndex, accounts){
  var hit=usageIndex&&usageIndex[unit.id];
  if(hit&&hit.rowCount>0) return {agg:hit, agents:hit.agents};
  var a={r:0,ti:0,to:0,tokens:0,cost:0,er:0}, agentMap={};
  (accounts||[]).forEach(function(u){
    a.r+=num(u.req); a.ti+=num(u.ti); a.to+=num(u.to); a.cost+=accountCost(u);
    if(u.a&&u.a!=="—") agentMap[u.a]=1;
  });
  a.tokens=a.ti+a.to;
  return {agg:a, agents:Object.keys(agentMap).length};
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
  var m=deptUnitMetrics(row.unit,usageIndex,row.accounts), g=m.agg;
  var activeCount=row.accounts.filter(function(u){return u.active&&!u.disabled;}).length;
  // Cấp "Trực thuộc" chỉ gom tài khoản gắn thẳng vào đơn vị nên mẫu số là chính nó,
  // không phải số cấp phát của cả đơn vị cha.
  var prov=row.tier==="direct"?row.accounts.length:provisionedOf(row.unit.id);
  html+="<td class='num'>"+fmt(m.agents)+"</td>"+
    adoptionCell(activeCount,prov)+
    "<td class='num'>"+fmt(g.r)+"</td>"+
    "<td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtCompactNum(g.tokens)+"</td>"+
    "<td class='num cost' title='"+esc(usdReference(g.cost))+"'>"+moneyCompact(g.cost)+"</td>"+
    "<td class='num"+(g.er>2?" text-red":"")+"'>"+num(g.er).toFixed(1)+"%</td>"+
    naCell()+"</tr>";
  return html;
}
function buildDeptRows(rows){
  // Dùng CHUNG gốc với ma trận tab Agents: bỏ qua hai hàng tổng hợp "Toàn công ty" và
  // "Tổng công ty Rạng Đông" để cấp 1 là phòng ban thật, không tốn hai cấp bung vô ích.
  var byUnit=accountsByUnitIndex(deptPool()), usageIds=deptUsageUnitIds(rows), out=[];
  reportingRoots().forEach(function(root,i){
    var node=deptTreeNode(root,byUnit,usageIds);
    if(node) flattenMatrixTree(node,1,[],true,i,null,out,deptIsOpen);
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
  var byUnitId=groupRowsByUnit(rows);
  var pool=filterAccounts();
  var groups=Object.keys(byUnitId).map(function(id){
    var g=byUnitId[id];
    return {unit:g.unit, agents:Object.keys(g.agents), agg:aggregate(g.rows)};
  });
  var totalReq=aggregate(rows).r;
  // "Năng suất nhất" = phòng tạo ra nhiều lượt dùng nhất, không xếp theo tiền.
  var byReq=groups.slice().sort(function(a,b){ return b.agg.r-a.agg.r; });

  set("m-dep-count", groups.filter(function(g){return g.agg.r>0;}).length);
  if(byReq.length&&byReq[0].agg.r>0){
    set("m-dep-top", esc(byReq[0].unit.name));
    set("m-dep-top-def", "<b>"+fmt(byReq[0].agg.r)+" request · "+pct(byReq[0].agg.r,totalReq).toFixed(0)+
      "%</b> tổng lượt dùng kỳ này.");
  } else { set("m-dep-top","—"); set("m-dep-top-def","Chưa phòng ban nào phát sinh lượt dùng."); }
  set("m-dep-users",fmtCompactNum(pool.length));

  renderDeptTree(rows);
  bindDeptToolbar();
  set("dep-alloc-note","<span title='"+esc(ALLOCATED_DATA_HINT)+"'>· "+ALLOCATED_DATA_LABEL+"</span>");
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

  // Tỷ lệ tài khoản được sử dụng = tài khoản có request / tài khoản được cấp, khoá theo
  // unitId. Đây là tỷ lệ NỘI BỘ từng phòng, các phòng KHÔNG cộng lại thành 100% — nên vẽ
  // bằng thanh ngang thang 0–100%, không dùng biểu đồ chia phần (tròn/polar).
  // Đơn vị chưa khai báo số cấp không được suy ra thành 100%: tách ra ghi chú bên dưới.
  var pool=filterAccounts(), missing=[];
  var adoption=units.map(function(g){
    var prov=provisionedOf(g.unit.id);
    if(prov==null||prov<=0){ missing.push(g.unit.name); return null; }
    var active=accountsUnderUnit(g.unit.id,pool).filter(function(u){return u.active;}).length;
    return {key:g.unit.name, active:active, prov:prov,
            value:Math.min(100,Math.round(active/prov*100))};
  }).filter(Boolean).sort(function(a,b){return a.value-b.value;}).slice(0,8);
  var missingNote=missing.length
    ? "Chưa tính được "+missing.length+" phòng do nguồn TLA Ralli chưa có số tài khoản được cấp: "+missing.join(", ")+"."
    : "";
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
    var u=unitOf(r.d);
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
  reportingRoots().forEach(function(root,i){
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
    var u=unitOf(r.d);
    if(u&&!isExcludedUnit(u)&&r.a) real+=num(r.r);
  });
  var accounts=0, blind=0;
  rows.forEach(function(r){
    if(r.depth!==1) return;
    accounts+=r.accounts.length;
    if(r.noAccounts) blind++;
  });
  // Dưới cấp mà file usage ghi nhận, phần chia cho từng đơn vị/tài khoản là số PHÂN BỔ.
  var allocated=" · <span title='"+esc(ALLOCATED_DATA_HINT)+"'>ⓘ "+ALLOCATED_DATA_LABEL+"</span>";
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
  set("m-us-adoption",activePctRounded+"%");
  set("m-us-adoption-def","<b>"+fmt(active.length)+"/"+fmt(accounts.length)+"</b> tài khoản đã dùng.");
  set("m-us-inactive",(accounts.length?100-activePctRounded:0)+"%");
  set("m-us-inactive-def","<b>"+fmt(inactive.length)+"/"+fmt(accounts.length)+"</b> tài khoản · chưa từng dùng: "+
    fmt(neverUsed)+" · ngừng >30 ngày: "+fmt(dormant)+".");
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
    if(f.user && u.ug!==f.user) return false;
    if(f.agent && u.a!==f.agent) return false;
    if(f.provider && modelProvider(u.m)!==f.provider) return false;
    if(f.model && u.m!==f.model) return false;
    return true;
  });
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
/* Ước lượng người dùng hoạt động theo ngày. Nguồn usage chưa có userId nên DAU là số
   suy ra từ lưu lượng ngày đó — dùng để nhìn xu hướng, không phải số đo tuyệt đối. */
function dauSeries(){
  var accounts=filterAccounts(), total=accounts.length;
  var dates=state.dayOrder.filter(function(d){return d>=state.range.start&&d<=state.range.end;}).slice(-30);
  var requests=dates.map(function(d){return aggregate(applyFilters(state.days[d]||[])).r;});
  var maxReq=Math.max.apply(null,requests.concat([1]));
  var dau=requests.map(function(r){return Math.min(total,Math.round(total*(0.10+0.16*r/maxReq)));});
  return {dates:dates, total:total, dau:dau};
}
function chartsUsers(rows){
  var s=dauSeries(), labels=s.dates.map(dayLabel);
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
    set("nt-us-adopt-all","Mẫu số là "+fmt(accounts.length)+" tài khoản đã cấp"+
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
    return "<tr><td>"+esc(g.key)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td><td class='num'>"+fmt(g.r)+"</td>"+(g.tokens?moneyCell(g.cost/(g.tokens/1e6),"num"):"<td class='num'>—</td>")+moneyCell(g.cost)+"<td><div class='progress-bar'><div class='progress-fill' style='width:"+pct(g.cost,total).toFixed(0)+"%'></div><span class='progress-text'>"+pct(g.cost,total).toFixed(0)+"%</span></div></td></tr>";
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
      var u=unitOf(r.d);
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
  set("m-pf-4xx", A.codeAvailable?fmtDecimal(pct(A.e4,A.eKnown),1)+"%":chuaCo);
  set("m-pf-5xx", A.codeAvailable?fmtDecimal(pct(A.e5,A.eKnown),1)+"%":chuaCo);
  set("m-pf-429", A.codeAvailable?fmtDecimal(pct(A.e429,A.eKnown),1)+"%":chuaCo);
  // Mẫu số là eKnown chứ không phải tổng lượt gọi. Ralli không đi qua Google
  // nên không ai biết nó lỗi bao nhiêu; đưa nó vào mẫu số là ngầm khai rằng
  // 7.924 lượt đó đều thành công.
  set("m-pf-success", A.codeAvailable
    ? fmtDecimal(pct(A.eKnown-A.e4-A.e5-A.e429, A.eKnown),1)+"%" : chuaCo);
  set("m-pf-p95", A.latAvailable?fmtDecimal(A.lat,1):chuaCo);
  set("m-pf-p99", A.lat99Available?fmtDecimal(A.lat99,1):chuaCo);
  setWithTitle("m-pf-req", fmtCompactNum(A.r), fmt(A.r)+" lượt gọi");
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.cost-a.cost;});
  set("pf-tbody", byAgent.map(function(g){
    var model = agentModelListHtml(g.models);
    // Agent không có nguồn đo mã trả về thì để gạch ngang. "100% thành công"
    // và "chưa đo được" là hai điều khác hẳn nhau.
    var thanhCong = g.codeAvailable ? fmtDecimal(pct(g.eKnown-g.e4-g.e5-g.e429, g.eKnown),1)+"%" : "—";
    var tyLeLoi   = g.codeAvailable ? fmtDecimal(pct(g.e4+g.e5+g.e429, g.eKnown),1)+"%" : "—";
    return "<tr><td>"+esc(g.key)+"</td><td class='agent-model-cell'>"+model+"</td><td class='num'>"+fmt(g.r)+"</td>"+
      "<td class='num'>"+thanhCong+"</td>"+
      "<td class='num"+(g.codeAvailable&&g.er>2?" text-red":"")+"'>"+tyLeLoi+"</td>"+
      "<td class='num'>"+(g.latAvailable?fmtDecimal(g.lat,1)+"s":"—")+"</td>"+
      "<td class='num'>"+(g.lat99Available?fmtDecimal(g.lat99,1)+"s":"—")+"</td></tr>";
  }).join("") || emptyRow(7));
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
   Ô text nhận mm/dd/yyyy (kiểu hiển thị chung của dashboard) và cũng chấp nhận
   yyyy-mm-dd cho ai quen ISO. Nhập sai thì giữ nguyên khoảng đang xem và báo lỗi
   ngay tại chỗ, không âm thầm nhảy về một ngày bất kỳ. */
function parseTypedDate(text){
  var t=String(text==null?"":text).trim();
  if(!t) return null;
  var m=t.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);      // mm/dd/yyyy
  var y,mo,d;
  if(m){ mo=+m[1]; d=+m[2]; y=+m[3]; }
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
    else { rangeHint("Ngày không hợp lệ — nhập theo mm/dd/yyyy."); renderRange(); }
  };
  text.onkeydown=function(ev){ if(ev.key==="Enter"){ ev.preventDefault(); this.blur(); } };
}
function renderRange(){
  var s=document.getElementById("range-start"), e=document.getElementById("range-end");
  if(s) s.value = state.range.start;
  if(e) e.value = state.range.end;
  var st=document.getElementById("range-start-text"), et=document.getElementById("range-end-text");
  if(st) st.value = fmtDateUS(state.range.start);
  if(et) et.value = fmtDateUS(state.range.end);
  var host=document.getElementById("range-presets"); if(!host) return;
  host.innerHTML="";
  RANGE_PRESETS.forEach(function(p){
    var r=presetRange(p[1]);
    var active = r.start===state.range.start && r.end===state.range.end;
    var b=document.createElement("button"); b.className="time-btn"+(active?" active":""); b.textContent=p[0];
    b.onclick=function(){ state.range={start:r.start,end:r.end}; renderAll(); };
    host.appendChild(b);
  });
  var q=prevQuarterRange();
  [
    ["Quý trước ("+q.label+")",q.start,q.end],
    ["Tháng 6","2026-06-01","2026-06-30"],
    ["Tháng 7","2026-07-01","2026-07-31"]
  ].forEach(function(p){
    var active=p[1]===state.range.start&&p[2]===state.range.end;
    var b=document.createElement("button"); b.className="time-btn month-preset"+(active?" active":""); b.textContent=p[0];
    b.onclick=function(){state.range={start:p[1],end:p[2]};renderAll();};
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
  set("status-period", esc(fmtDateUS(state.range.start)+" → "+fmtDateUS(state.range.end)));
  set("header-data-date", esc(fmtDateUS(toISO(maxDataDate()))));
}

/* ═══════════════ NHẬP LIỆU THEO NGÀY ═══════════════ */
function insertDayOrdered(iso){
  var at=state.dayOrder.length;
  for(var i=0;i<state.dayOrder.length;i++){ if(iso < state.dayOrder[i]){ at=i; break; } }
  state.dayOrder.splice(at,0,iso);
}
function renderDataDay(){
  var d=document.getElementById("data-date");
  if(d){
    d.value=state.activeDay;
    d.onchange=function(){ if(this.value){ state.activeDay=this.value; dayRows(state.activeDay); renderDataPanel(); renderDataDayHint(); } };
  }
  var del=document.getElementById("del-day-btn"); if(del) del.disabled = state.dayOrder.indexOf(state.activeDay)<0;
  renderDataDayHint();
}
function renderDataDayHint(){
  var h=document.getElementById("data-days-hint"); if(!h) return;
  var saved = state.dayOrder.indexOf(state.activeDay)>=0;
  var base = state.dayOrder.length ? ("Đã lưu "+state.dayOrder.length+" ngày. ") : "Chưa có ngày nào được lưu. ";
  h.textContent = base + (saved ? "Ngày này đã có dữ liệu — đang sửa." : "Ngày mới — nhập xong bấm 💾 Lưu.");
}
function dataMsg(t, err){ var e=document.getElementById("data-msg"); if(!e) return; e.textContent=t; e.className="config-msg"+(err?" error":""); setTimeout(function(){ if(e.textContent===t) e.textContent=""; },4000); }
function saveDay(){
  var iso=state.activeDay;
  var rows=sanitizeUsageRows(state.days[iso]||[]);
  state.days[iso]=rows;
  var idx=state.dayOrder.indexOf(iso);
  if(rows.length>0){ if(idx<0) insertDayOrdered(iso); }
  else { if(idx>=0) state.dayOrder.splice(idx,1); delete state.days[iso]; }
  saveState(); renderAll();
  dataMsg(rows.length>0 ? ("✅ Đã lưu ngày "+iso+" — dashboard đã cập nhật.") : ("Ngày "+iso+" trống nên không được lưu."), rows.length===0);
}
function delDay(){
  var iso=state.activeDay, idx=state.dayOrder.indexOf(iso);
  if(idx<0){ dataMsg("Ngày "+iso+" chưa được lưu nên không có gì để xoá.", true); return; }
  if(!confirm("Xoá toàn bộ dữ liệu ngày "+iso+"? Hành động này không thể hoàn tác.")) return;
  state.dayOrder.splice(idx,1); delete state.days[iso];
  state.activeDay = state.dayOrder.length ? state.dayOrder[Math.max(0,idx-1)] : iso;
  saveState(); renderAll();
  dataMsg("🗑 Đã xoá ngày "+iso, false);
}

/* ═══════════════ BỘ LỌC ═══════════════ */
function fillSelect(id, opts, val, allLabel){
  var el=document.getElementById(id); if(!el) return;
  el.innerHTML = "<option value=''>"+allLabel+"</option>" + opts.map(function(o){ return "<option"+(o===val?" selected":"")+">"+esc(o)+"</option>"; }).join("");
  el.onchange = function(){
    var key=id.split("-")[1];
    state.filters[key] = this.value;
    // Đổi phòng ban ⇒ đường đi drilldown của ma trận không còn hợp lệ, đưa về cấp gốc.
    // Đổi phòng ban lọc thì cây ma trận đang bung không còn nghĩa gì, thu về gốc.
    if(key==="dept") state.matrixExpanded={};
    renderAll();
  };
}
function renderFilters(){
  var rows=allDayRows();
  // Dropdown hiển thị TÊN ĐƠN VỊ chuẩn hoá, mỗi phòng chỉ một lựa chọn.
  var deptNames=[], seenDept={};
  rows.forEach(function(r){
    var u=unitOf(r.d);
    if(!u||isExcludedUnit(u)) return;
    var root=reportingRootOf(u.id)||u;
    if(!seenDept[root.name]){ seenDept[root.name]=true; deptNames.push(root.name); }
  });
  fillSelect("f-dept", deptNames.sort(), state.filters.dept, "Tất cả phòng ban");
  fillSelect("f-user", distinct(rows.map(function(r){return r.ug;}).filter(Boolean)), state.filters.user, "Tất cả user");
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
    var i=priceInput(p.i, function(v){ state.pricing[m].i=v; renderDataPanel(); });
    var o=priceInput(p.o, function(v){ state.pricing[m].o=v; renderDataPanel(); });
    var x=document.createElement("button"); x.className="icon-x"; x.innerHTML="&times;"; x.title="Xoá model";
    x.onclick=function(){ if(Object.keys(state.pricing).length<=1){ configMsg("Cần giữ ít nhất 1 model.",true); return; } delete state.pricing[m]; renderPricing(); renderDataPanel(); };
    el.appendChild(name); el.appendChild(i); el.appendChild(o); el.appendChild(x);
  });
}
function priceInput(val, on){ var i=document.createElement("input"); i.type="number"; i.step="0.01"; i.value=val; i.onchange=function(){ on(num(this.value)); }; return i; }

/* ═══════════════ BẢNG DỮ LIỆU NGUỒN (editable, theo ngày) ═══════════════ */
function td(child){ var t=document.createElement("td"); t.appendChild(child); return t; }
function tdNum(child){ var t=document.createElement("td"); t.className="num"; t.appendChild(child); return t; }
function textInput(v, on){ var i=document.createElement("input"); i.type="text"; i.className="text-input"; i.value=v; i.onchange=function(){ on(this.value); renderDataPanel(); }; return i; }
function numInput(v, on){ var i=document.createElement("input"); i.type="number"; i.className="cell-input"; i.value=v; i.onchange=function(){ on(num(this.value)); renderDataPanel(); }; return i; }
function modelSelect(v, on){
  var s=document.createElement("select"); s.className="cell-select";
  Object.keys(state.pricing).forEach(function(m){ var o=document.createElement("option"); o.value=m; o.textContent=m; if(m===v) o.selected=true; s.appendChild(o); });
  s.onchange=function(){ on(this.value); renderDataPanel(); }; return s;
}
function renderDataPanel(){
  var tb=document.getElementById("data-tbody"); if(!tb) return;
  var rows=dayRows(state.activeDay); tb.innerHTML="";
  rows.forEach(function(row){
    var tr=document.createElement("tr");
    tr.appendChild(td(textInput(row.a, function(v){ row.a=v; })));
    tr.appendChild(td(textInput(row.d, function(v){ row.d=v; })));
    tr.appendChild(td(modelSelect(row.m, function(v){ row.m=v; })));
    tr.appendChild(tdNum(numInput(row.u, function(v){ row.u=v; })));
    tr.appendChild(tdNum(numInput(row.c, function(v){ row.c=v; })));
    tr.appendChild(tdNum(numInput(row.ti, function(v){ row.ti=v; })));
    tr.appendChild(tdNum(numInput(row.to, function(v){ row.to=v; })));
    tr.appendChild(tdNum(numInput(row.r, function(v){ row.r=v; })));
    tr.appendChild(tdNum(numInput(row.er, function(v){ row.er=v; })));
    var rowCost=cost(row);
    var c=document.createElement("td"); c.className="num cost"; c.textContent=money(rowCost); c.title=usdReference(rowCost); tr.appendChild(c);
    var xtd=document.createElement("td"); var xb=document.createElement("button"); xb.className="icon-x"; xb.innerHTML="&times;"; xb.title="Xoá dòng";
    xb.onclick=function(){ var idx=rows.indexOf(row); if(idx>=0){ rows.splice(idx,1); renderDataPanel(); } };
    xtd.appendChild(xb); tr.appendChild(xtd);
    tb.appendChild(tr);
  });
  // Dòng Tổng (giống bảng gốc): cộng dồn u/c/token/request + tổng chi phí
  var t = rows.reduce(function(a,r){
    a.u+=num(r.u); a.c+=num(r.c); a.ti+=num(r.ti); a.to+=num(r.to); a.r+=num(r.r); a.cost+=cost(r); return a;
  }, {u:0,c:0,ti:0,to:0,r:0,cost:0});
  var trt=document.createElement("tr"); trt.className="data-total-row";
  trt.innerHTML =
    "<td colspan='3'>Tổng</td>"+
    "<td class='num'>"+fmt(t.u)+"</td>"+
    "<td class='num'>"+fmt(t.c)+"</td>"+
    "<td class='num'>"+fmt(t.ti)+"</td>"+
    "<td class='num'>"+fmt(t.to)+"</td>"+
    "<td class='num'>"+fmt(t.r)+"</td>"+
    "<td class='num'></td>"+
    "<td class='num' title='"+esc(usdReference(t.cost))+"'>"+money(t.cost)+"</td>"+
    "<td></td>";
  tb.appendChild(trt);
}

/* ═══════════════ CSV ═══════════════ */
function csv(v){ v=v==null?"":String(v); return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v; }
function exportCSV(){
  var rows=scopedRows();
  var period = state.range.start+" → "+state.range.end;
  var lines=["Kỳ,Agent,Phòng ban,Model,Provider,Users,Chat,Token in,Token out,Request,Lỗi %,Chi phí USD,Chi phí VNĐ,Tỷ giá cấu hình"];
  rows.forEach(function(r){
    lines.push([period,r.a,r.d,r.m,modelProvider(r.m),r.u,r.c,r.ti,r.to,r.r,num(r.er).toFixed(2),cost(r).toFixed(2),toVnd(cost(r)),VND_RATE].map(csv).join(","));
  });
  var blob=new Blob([lines.join("\n")],{type:"text/csv;charset=utf-8;"});
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
  renderDataDay();
  renderStatus();
  renderFilters();
  renderPricing();
  renderDataPanel();
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
  document.getElementById("btn-data").onclick=function(){ document.getElementById("data-panel").classList.toggle("open"); };
  document.getElementById("btn-export").onclick=exportCSV;
  var themeBtn=document.getElementById("btn-theme");
  if(themeBtn) themeBtn.onclick=function(){ applyTheme(currentTheme()==="light"?"dark":"light"); renderAll(); };

  // dữ liệu nguồn theo ngày
  document.getElementById("add-row-btn").onclick=function(){
    dayRows(state.activeDay).push({ id:rid(), a:"Agent mới", d:"—", m:Object.keys(state.pricing)[0], u:0,c:0,ti:0,to:0,r:0,er:0,lat:2.0,cached:0,think:0 });
    renderDataPanel();
  };
  var saveDayBtn=document.getElementById("save-day-btn"); if(saveDayBtn) saveDayBtn.onclick=saveDay;
  var delDayBtn=document.getElementById("del-day-btn"); if(delDayBtn) delDayBtn.onclick=delDay;

  document.getElementById("f-reset").onclick=function(){ state.filters={dept:"",user:"",provider:"",model:"",agent:""}; renderAll(); };

  // global time range — mỗi mốc có 1 ô gõ tay (mm/dd/yyyy) + 1 ô lịch, luôn đồng bộ.
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
    renderPricing(); renderDataPanel();
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

  renderAll();
}

if(document.readyState==="loading") document.addEventListener("DOMContentLoaded", init);
else init();
})();
