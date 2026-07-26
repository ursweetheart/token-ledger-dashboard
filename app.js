/* ═══════════════════════════════════════════════════════════════════════
   Agent Analytics · Token Ledger — engine data-driven
   Mô hình dữ liệu: state → days (nhập theo NGÀY) → rows + pricing.
   Mọi chỉ số/biểu đồ/bảng được TÍNH từ rows. Sửa dữ liệu/giá rồi bấm
   "💾 Lưu" ⇒ dashboard tính lại. (v5: chuyển từ nhập theo tháng → theo ngày.)
   ═══════════════════════════════════════════════════════════════════════ */
(function(){
"use strict";

/* ─── Hằng số ─── */
var STORE = "agent-dash-state-v12-ralli-permissions"; // v12: Excel tháng 6/7 + cây phân quyền Ralli
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
  {id:"nctt",name:"P.NCTT , TTDL&ĐHS",parent:null,level:1,provisioned:30},
  {id:"cpbd",name:"Công ty CPBĐ PN Rạng Đông",parent:null,level:1,provisioned:18},
  {id:"ttdl",name:"TTDL&DHS",parent:null,level:1,provisioned:6},
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
  "P.NCTT , TTDL&ĐHS":"nctt", "P.NCTT, TTDL&ĐHS":"nctt", // chỉ khác dấu cách
  "Anh Em tiếp thị":"aemkt", "Chăm sóc khách hàng":"cskh",
  "TTDL&DHS":"ttdl", "TT&TMĐT":"tttmdt", "Xuất khẩu":"pxk",
  "Truyền thông":"truyenthong", "Kế toán":"ketoan", "Kế hoạch":"kehoach",
  "Nghiên cứu thị trường":"nctt2", "Trung tâm R&D":"rnd", "Quản trị hệ thống":"qths"
};
/* Snapshot phân quyền Ralli đọc từ data/phong_ban_phan_quyen.xlsx.
   Mỗi cấp giữ số Excel khai báo trực tiếp; không tự cộng lại từ cấp con vì số cấp cha
   gồm cả user chưa được gán xuống đội/vùng. */
var DEPT_PROVISIONED = {};
ORG_UNITS.forEach(function(unit){ DEPT_PROVISIONED[unit.id]=unit.provisioned; });
var MODALITY = [["TEXT",86,"#667eea"],["IMAGE",9,"#10b981"],["AUDIO",4,"#f59e0b"],["VIDEO",1,"#8b5cf6"]];
var USER_HEAT = {
  cols: ["Sale Agent","Chatbot CC","CRM","Phản Hồi TT","Ralli","Hợp Đồng"],
  rows: ["Nhóm Sales","Nhóm CSKH","Nhóm Data","Nhóm Vận hành"],
  matrix: [[480,40,10,20,110,60],[30,400,5,8,0,4],[12,6,300,85,2,0],[88,13,4,0,8,24]]
};
var palette = ["#667eea","#3b82f6","#f59e0b","#10b981","#8b5cf6","#06b6d4","#ef4444","#64748b","#ec4899","#14b8a6"];

/* ═══════════════ DANH MỤC TÀI KHOẢN (DEMO) ═══════════════
   Nguồn usage KHÔNG có userId (mỗi dòng là tổng theo agent × phòng ban), nên không thể
   quy số liệu về từng tài khoản thật. Tầng này sinh danh tính tài khoản rồi PHÂN BỔ số
   liệu thật của phòng xuống các tài khoản đó, để mọi cấp drilldown cộng khớp cấp cha.

   Vì vậy: số của từng tài khoản là SỐ PHÂN BỔ, không phải số đo. Mọi khối UI hiển thị
   số ở cấp tài khoản phải mang nhãn ALLOCATED_DATA_LABEL.

   Tách hai phần để tổng luôn khớp ở MỌI kỳ:
     buildAccountCatalogue()      → danh tính, tĩnh (không chứa số liệu)
     applyAccountAllocation(rows) → phân bổ theo kỳ + bộ lọc đang xem, chạy mỗi lượt render
   ═════════════════════════════════════════════════════════ */
var ALLOCATED_DATA_LABEL = "Dữ liệu phân bổ (demo)";
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
var FAMILY_NAMES=["Nguyễn","Trần","Lê","Phạm","Hoàng","Vũ","Đặng","Đỗ","Bùi","Ngô"];
var GIVEN_NAMES=["An","Bình","Chi","Dũng","Giang","Hà","Hải","Hương","Khánh","Linh",
  "Minh","Nam","Oanh","Phương","Quân","Sơn","Trang","Tuấn","Vy","Yến"];
/* Tỷ lệ tài khoản có khả năng hoạt động của một đơn vị — cố định theo unitId. */
function adoptionRatio(unitId){ return 0.55 + (stableHash("adopt:"+unitId)%36)/100; }
function buildAccountCatalogue(){
  var profiles=unitAgentProfiles(), out=[], seq=0;
  ORG_UNITS.forEach(function(unit){
    if(isExcludedUnit(unit)) return;
    // Chỉ sinh phần user thuộc trực tiếp đơn vị này. Phần đã phân xuống cấp con
    // được sinh tại chính cấp con, nhờ đó tổng của mọi nút khớp workbook.
    var total=directProvisionedOf(unit.id);
    if(total==null||total<=0) return;
    var path=unitPath(unit.id), root=path[0]||unit, prof=null;
    // Toàn bộ cây từ workbook phong_ban_phan_quyen.xlsx là quyền của Ralli.
    if(root.id==="company") prof=[{a:"Trợ lý ảo Ralli",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh"}];
    else {
      for(var k=path.length-1;k>=0&&!prof;k--) if(profiles[path[k].id]) prof=profiles[path[k].id];
    }
    if(!prof||!prof.length) prof=[{a:"—",m:"—",ug:"—"}];
    var eligible=Math.max(1, Math.round(total*adoptionRatio(unit.id)));
    for(var i=0;i<total;i++){
      seq++;
      var p=prof[i%prof.length], h=stableHash(unit.id+":"+i);
      out.push({
        user:"user."+("0000"+seq).slice(-4)+"@corp.vn",
        // Dùng >>> để giữ số không dấu: h>>3 có thể âm khi h > 2^31 ⇒ index âm ⇒ undefined.
        n:FAMILY_NAMES[h%FAMILY_NAMES.length]+" "+GIVEN_NAMES[(h>>>3)%GIVEN_NAMES.length],
        unitId:unit.id, d:unit.name,
        a:p.a, m:p.m, ug:p.ug,
        // weight > 0 ⇒ tài khoản có thể nhận phân bổ; = 0 ⇒ luôn là tài khoản chưa dùng.
        weight: i<eligible ? 1+(h%9) : 0,
        role: seq%31===0 ? "Admin" : "User",
        created: (h%9===0) ? "2026-07-"+("0"+(1+h%27)).slice(-2) : "2026-03-"+("0"+(1+h%27)).slice(-2),
        disabled: (h%97===0),
        req:0, ti:0, to:0, last:"", active:false, quotaPct:0
      });
    }
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
    (byUnit[u.unitId]=byUnit[u.unitId]||[]).push(u);
  });
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
      pool.forEach(function(u){ var share=Math.floor(target*u.weight/W); u[acctKey]+=share; used+=share; });
      pool[0][acctKey]+=target-used;      // dồn phần dư ⇒ tổng khớp chính xác
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

/* ─── Bảng giá gốc (USD / 1M token) — gồm Google Gemini + OpenAI ─── */
var basePricing = {
  "Gemini 2.5 Flash": {i:0.30, o:2.50},
  "Gemini 3.0 Flash": {i:0.50, o:3.00},
  "Gemini 2.5 Pro":   {i:1.25, o:3.75},
  "Gemini 3.1 Flash Lite": {i:0.25, o:1.50},
  "Gemini 3.5 Flash": {i:0, o:0},          // đã khai báo, chưa dùng
  "GPT-4o mini":      {i:0.15, o:0.60},    // OpenAI — giữ sẵn cho nhập thủ công
  "GPT-4o":           {i:2.50, o:10.00}    // OpenAI — đã khai báo, chưa dùng
};

/* ─── Dữ liệu THẬT tháng 7/2026 — nạp từ
       data/Bảng tổng hợp chi phí AI Agent tháng 7.xlsx.
       Bốn sheet tuần được gắn lần lượt vào 01, 08, 15 và 22/07.
       Số người dùng (u) là số ĐÃ CẤP theo phòng (snapshot) ⇒ chỉ gắn vào Tuần 1 để tránh
       cộng trùng khi time-range trải nhiều tuần. Chi phí do dashboard tự tính theo bảng giá.
       Phòng ban "Đang trong quá trình thử nghiệm" bị loại theo cấu hình EXCLUDED_DEPARTMENTS. ─── */
var SEED_DAYS = {
  "2026-07-01": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:5,c:0,ti:4910,to:1147,r:9,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng Bán hàng 1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:19,c:0,ti:43470,to:15220,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng Bán hàng 2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng Bán hàng 3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:10,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2214480,to:612620,r:610,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:0,to:0,r:459,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7980000,to:213290,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:4350,to:13190,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:3,c:0,ti:60523,to:578430,r:93,er:0.0,lat:0,cached:0,think:0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:3,c:0,ti:85641,to:2135755,r:324,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:887,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:2838200,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"PBH2",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"PBH3",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Xuất khẩu",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Truyền thông",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Kế toán",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"TMĐT",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"C4LED",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Nghiên cứu thị trường",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Kế hoạch",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Trung tâm R&D",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"Quản trị hệ thống",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:0,er:0.0,lat:0,cached:0,think:0}
  ],
  "2026-07-08": [
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2053010,to:454260,r:450,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.1 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:0,to:0,r:312,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:5540000,to:108600,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:530,to:1150,r:0,er:1.0,lat:0,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:3030700,r:0,er:0.0,lat:0,cached:0,think:0}
  ],
  "2026-07-15": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:934255,to:169112,r:48,er:0.0,lat:0,cached:0,think:0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5948151,to:1260234,r:1182,er:0.0034,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:15414,to:48065,r:17,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:16444458,to:190589,r:520,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 3.1 Flash Lite",ug:"Nhóm CSKH",u:0,c:0,ti:987,to:0,r:515,er:0.0,lat:0,cached:0,think:0},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:751650,to:902779,r:148,er:0.0,lat:4.5,cached:0,think:0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:194002,to:238589,r:36,er:0.0,lat:4.5,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1427755,to:92769,r:294,er:0.0,lat:0,cached:0,think:0}
  ],
  "2026-07-22": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:694811,to:224300,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1076850,to:181373,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:44993,to:133567,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Chatbot Contact Center",d:"Thương mại điện tử",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:3788140,to:84372,r:0,er:0.0,lat:0,cached:0,think:0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:183805,to:234887,r:0,er:0.0,lat:4.5,cached:0,think:0},
    {a:"Trợ lý ảo Ralli",d:"PBH1",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1096933,to:70685,r:207,er:0.0,lat:0,cached:0,think:0}
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
function sanitizeUsageRows(rows){
  return (rows||[]).filter(function(r){return !isExcludedDepartment(r.d)&&!isExcludedAgent(r.a);});
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
    range:{ start:"2026-07-01", end:"2026-07-31" },
    filters:{dept:"",user:"",provider:"",model:"",agent:""}, matrixUser:"",
    deptExpanded:{}, matrixPath:[], pricing:clone(basePricing) };
}
function loadState(){
  try{ var raw = localStorage.getItem(STORE); if(!raw) return defaultState();
    var s = JSON.parse(raw);
    if(!s || !s.days || !s.dayOrder || !s.pricing) return defaultState();
    if(!s.filters) s.filters = {dept:"",user:"",provider:"",model:"",agent:""};
    if(!s.matrixUser) s.matrixUser="";
    // State mới: bỏ qua an toàn khi đọc localStorage của phiên bản cũ.
    if(!s.deptExpanded||typeof s.deptExpanded!=="object") s.deptExpanded={};
    if(!Array.isArray(s.matrixPath)) s.matrixPath=[];
    // Đường đi/khoá đơn vị không còn hợp lệ sau khi chuẩn hoá cây thì loại bỏ.
    Object.keys(s.deptExpanded).forEach(function(id){ if(!unitById(id)) delete s.deptExpanded[id]; });
    s.matrixPath=s.matrixPath.filter(function(id){ return !!unitById(id); });
    s.dayOrder.forEach(function(d){if(s.days[d]) s.days[d]=sanitizeUsageRows(s.days[d]);});
    s.dayOrder = s.dayOrder.filter(function(d){ return s.days[d]&&s.days[d].length; }).sort();
    if(isExcludedDepartment(s.filters.dept)) s.filters.dept="";
    if(!s.activeDay) s.activeDay = s.dayOrder[s.dayOrder.length-1] || SEED_DAY;
    if(!s.range || !s.range.start || !s.range.end){ s.range = {start:"2026-07-01",end:"2026-07-31"}; }
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
   Scorecard luôn viết đầy đủ chiều biến động, tên kỳ, giá trị gốc → giá trị hiện tại
   và phần trăm thay đổi để người xem không phải giải mã KT/CK. ─── */
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
    return "<div class='delta-line d-dim' title='"+esc(tip+": chưa có dữ liệu")+"'>So với "+
      basis.full+": chưa có dữ liệu</div>";
  }
  var diff=cur-b.v, p=diff/b.v*100, flat=Math.abs(p)<0.5, up=diff>0;
  // Màu biểu thị trực tiếp hướng biến động theo quy ước dashboard:
  // tăng = xanh, giảm = đỏ, gần như không đổi = trung tính.
  // betterUp chỉ còn được giữ trong chữ ký hàm để tương thích với các lời gọi hiện tại.
  var cls = flat ? "d-neutral" : (up ? "d-green" : "d-red");
  var arrow = flat ? "→" : (up ? "▲" : "▼");
  var percent = flat ? "0%" : ((up?"+":"−")+Math.abs(p).toFixed(0)+"%");
  return "<div class='delta-line "+cls+"' title='"+esc(tip+": "+fmtFn(b.v))+"'>"+arrow+" "+
    percent+" so với "+basis.full+": <span class='delta-abs'>"+
    (b.mock?"≈":"")+fmtFn(b.v)+" → "+fmtFn(cur)+"</span></div>";
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
  var a = {u:0,c:0,ti:0,to:0,r:0,cached:0,think:0,cost:0,erW:0,latW:0,latR:0};
  rows.forEach(function(row){
    a.u+=num(row.u); a.c+=num(row.c); a.ti+=num(row.ti); a.to+=num(row.to);
    a.r+=num(row.r); a.cached+=num(row.cached); a.think+=num(row.think);
    a.cost+=cost(row); a.erW+=num(row.er)*num(row.r);
    if(num(row.lat)>0&&num(row.r)>0){a.latW+=num(row.lat)*num(row.r);a.latR+=num(row.r);}
  });
  a.tokens = a.ti + a.to;
  a.er = a.r ? a.erW/a.r : 0;
  a.latAvailable = a.latR>0;
  a.lat = a.latAvailable ? a.latW/a.latR : 0;
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
function configuredBudgetSummary(rows){
  var costs={}, matchedRows=[];
  (rows||[]).forEach(function(row){
    var config=agentBudgetConfig(row.a);
    if(!config) return;
    costs[config.agent]=(costs[config.agent]||0)+cost(row);
    matchedRows.push(row);
  });
  var agents=AGENT_MONTHLY_BUDGETS.map(function(config){
    var spend=costs[config.agent]||0;
    return {agent:config.agent,cost:spend,budget:config.usd,rate:pct(spend,config.usd)};
  });
  return {
    cost:agents.reduce(function(sum,item){return sum+item.cost;},0),
    budget:MONTHLY_BUDGET,
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
  var configured=configuredBudgetSummary(rows), spend=configured.cost;
  if(!elapsed || !totalDays || spend<=0) return insight("budget-pace","unavailable");
  var budgetPct=pct(spend,MONTHLY_BUDGET), timePct=pct(elapsed,totalDays);
  var forecast=spend/elapsed*totalDays, forecastPct=pct(forecast,MONTHLY_BUDGET);
  var top=topGroup(configured.rows,function(r){return r.a;},"cost");
  var driver=top?(top.key+" đóng góp "+top.share.toFixed(0)+"% chi phí."):"";
  var evidence="Dự kiến cuối kỳ "+money(forecast)+" / ngân sách "+money(MONTHLY_BUDGET)+" ("+forecastPct.toFixed(0)+"%).";
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
  var chosen=candidates[0], label=chosen.severity==="critical"?"CẢNH BÁO":chosen.severity==="warning"?"CẦN CHÚ Ý":"BÌNH THƯỜNG";
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
function mkBar(id, labels, data, o){
  o = o || {};
  var numericTick=o.money?function(v){return moneyCompact(v);}:o.tokens?function(v){return fmtTokShort(v);}:undefined;
  var categoryTick=function(v){return wrapAxisLabel(this.getLabelForValue(v),26);};
  chart(id, {
    type:"bar",
    data:{ labels:labels, datasets:[{ data:data, backgroundColor:o.colors||"#667eea", borderRadius:4, maxBarThickness:o.horizontal?22:44 }] },
    options:{ indexAxis:o.horizontal?"y":"x",
      plugins:{ legend:{display:false}, tooltip:{ callbacks:{ label:function(c){ var v=o.horizontal?c.parsed.x:c.parsed.y; return o.money?[money(v),usd(v)+" · "+EXCHANGE_RATE_META.source]:(o.tokens?fmtTokFull(v):fmt(v)); } } } },
      scales:{
        x:{ grid:{ color:gridColor(), display:!o.horizontal }, ticks:{ callback:o.horizontal?numericTick:categoryTick } },
        y:{ grid:{ color:gridColor(), display:!!o.horizontal }, ticks:{ callback:o.horizontal?categoryTick:numericTick, autoSkip:false } }
      } }
  });
}
function mkDonut(id, labels, data, legendId, fmtVal, colors){
  colors = colors || palette;
  chart(id, {
    type:"doughnut",
    data:{ labels:labels, datasets:[{ data:data, backgroundColor:colors, borderWidth:0 }] },
    options:{ cutout:"62%", plugins:{ legend:{display:false},
      tooltip:{ callbacks:{ label:function(c){ return c.label+": "+(fmtVal?fmtVal(c.parsed):fmt(c.parsed)); } } } } }
  });
  if(legendId){
    var tot = data.reduce(function(s,x){ return s+num(x); },0);
    set(legendId, labels.map(function(l,i){
      return "<span class='li'><span class='dot' style='background:"+colors[i%colors.length]+"'></span>"+esc(l)+" · "+pct(data[i],tot).toFixed(0)+"%</span>";
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

  set("m-ov-agents",active.length+"/"+created);
  set("m-ov-units",fmt(byUnit.length));
  set("m-ov-users",fmt(activeUsers));
  set("m-ov-requests",fmt(A.r));
  set("m-ov-tokens",fmtTokShort(A.tokens));
  var tokenMetric=document.getElementById("m-ov-tokens");
  if(tokenMetric) tokenMetric.title=fmtTokFull(A.tokens);
  setMoney("m-ov-cost",A.cost);
  setMoney("m-ov-costuser",costPerUser);
  set("m-ov-error",A.er.toFixed(1)+"%");

  renderSingleDelta("d-ov-agents",active.length,prevActive.length,fmt);
  renderSingleDelta("d-ov-units",byUnit.length,prevUnits.length,fmt);
  renderSingleDelta("d-ov-users",activeUsers,0,fmt);
  renderSingleDelta("d-ov-requests",A.r,prevA.r,fmt);
  renderSingleDelta("d-ov-tokens",A.tokens,prevA.tokens,fmtTok);
  renderSingleDelta("d-ov-cost",A.cost,prevA.cost,money);
  renderSingleDelta("d-ov-costuser",costPerUser,0,money);
  renderSingleDelta("d-ov-error",A.er,prevA.er,function(v){return v.toFixed(1)+"%";});

  set("i-ov-agents",Math.max(0,created-active.length)+" agent chưa hoạt động trong kỳ.");
  set("i-ov-units",topUnit?esc(topUnit.key)+" dẫn đầu, chiếm "+pct(topUnit.cost,A.cost).toFixed(0)+"% chi phí.":"Chưa có đơn vị phát sinh sử dụng.");
  set("i-ov-users",fmt(activeUsers)+" đang dùng · "+fmt(inactiveUsers)+" tài khoản không hoạt động.");
  set("i-ov-requests",topRequest?esc(topRequest.key)+" chiếm "+pct(topRequest.r,A.r).toFixed(0)+"% request.":"Chưa có request trong kỳ.");
  set("i-ov-tokens",topAgent?esc(topAgent.key)+" chiếm "+pct(topAgent.tokens,A.tokens).toFixed(0)+"% token.":"Chưa có token trong kỳ.");
  set("i-ov-cost",topAgent?esc(topAgent.key)+" chiếm "+pct(topAgent.cost,A.cost).toFixed(0)+"% tổng chi phí.":"Chưa phát sinh chi phí.");
  set("i-ov-costuser","Bình quân trên "+fmt(activeUsers)+" user hoạt động.");
  set("i-ov-error",topError&&topError.er>0?esc(topError.key)+" cao nhất: "+topError.er.toFixed(1)+"%.":"Không ghi nhận lỗi.");

  set("ov-cost-total",money(A.cost));
  set("ov-token-total",fmtTok(A.tokens));
  set("ov-request-total",fmt(A.r));
  set("ov-success-value",(100-A.er).toFixed(1)+"%");

  var detail=active.slice().sort(function(a,b){return b.cost-a.cost;}).slice(0,8);
  set("ov-detail-tbody",detail.map(function(g){
    var success=Math.max(0,100-g.er), dept=g.depts.length>1?g.depts[0]+" +"+(g.depts.length-1):g.depts[0]||"—";
    return "<tr><td><b>"+esc(g.key)+"</b></td><td class='subtle'>"+esc(dept)+"</td><td class='num'>"+fmt(g.u)+"</td>"+
      "<td class='num'>"+fmt(g.r)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTokShort(g.tokens)+"</td>"+
      moneyCell(g.cost)+"<td class='num"+(g.er>=2?" text-red":"")+"'>"+g.er.toFixed(1)+"%</td>"+
      "<td><div class='overview-success-cell'><span><i style='width:"+success.toFixed(1)+"%'></i></span><b>"+success.toFixed(1)+"%</b></div></td></tr>";
  }).join("")||emptyRow(8));
  renderOverviewAlerts(A,rows,active,topAgent,inactiveUsers);
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
    text:errTop&&errTop.er>0?errTop.key+" đang ở mức "+errTop.er.toFixed(1)+"%.":"Tỷ lệ thành công toàn hệ thống đạt "+(100-A.er).toFixed(1)+"%."
  });
  alerts.push({
    cls:topAgent&&pct(topAgent.cost,A.cost)>=40?"warning":"info",icon:"●",title:"Mức tập trung chi phí",
    text:topAgent?topAgent.key+" chiếm "+pct(topAgent.cost,A.cost).toFixed(0)+"% tổng chi phí.":"Chưa có dữ liệu chi phí."
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
  mkDonut("c-ov-success",["Thành công","Lỗi"],[Math.max(0,100-A.er),Math.max(0,A.er)],null,function(v){return v.toFixed(1)+"%";},["#22c55e","#ef4444"]);
  var byAgent=groupAgg(rows,function(r){return r.a;}).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;}).slice(0,8);
  mkBar("c-ov-agent-cost",byAgent.map(function(g){return g.key;}),byAgent.map(function(g){return g.cost;}),{horizontal:true,money:true,colors:"#3b82f6"});
  mkDonut("c-ov-agent-share",byAgent.map(function(g){return g.key;}),byAgent.map(function(g){return g.cost;}),"lg-ov-agent-share",money);
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
function deptToggleCell(label, level, expandable, expanded){
  var caret=expandable?"<span class='drill-caret'>"+(expanded?"▼":"▶")+"</span>"
                      :"<span class='drill-caret drill-leaf'>·</span>";
  return "<td class='drill-name drill-l"+level+"'>"+caret+"<span>"+esc(label)+"</span></td>";
}
function deptAccountRow(u, level){
  var tokens=num(u.ti)+num(u.to);
  var status=u.disabled?"user-status-disabled":(u.active?"user-status-active":"user-status-inactive");
  var label=u.disabled?"Vô hiệu hóa":(u.active?"Hoạt động":"Chưa dùng");
  return "<tr class='drill-row drill-account'>"+
    "<td class='drill-name drill-l"+level+"'><span class='drill-caret drill-leaf'>·</span>"+
      "<span class='user-id'>"+esc(u.user)+"</span> <span class='subtle'>"+esc(u.n)+"</span>"+
      " <span class='user-status "+status+"'>"+label+"</span></td>"+
    "<td class='num'>"+(u.a&&u.a!=="—"?1:0)+"</td>"+
    naCell()+naCell()+naCell()+
    "<td class='num' title='"+esc(fmtTokFull(tokens))+"'>"+fmtTok(tokens)+"</td>"+
    "<td class='num'>"+fmt(u.req)+"</td>"+
    naCell()+
    "</tr>";
}
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
function renderDepartmentBranch(unit, level, rows, pool, expanded){
  var usage=usageUnderUnit(unit.id,rows), accounts=accountsUnderUnit(unit.id,pool);
  var directAccounts=(pool||[]).filter(function(u){return u.unitId===unit.id;});
  var kids=unitChildren(unit.id).filter(function(k){return !isExcludedUnit(k);});
  var isOpen=!!expanded[unit.id], canOpen=kids.length>0||directAccounts.length>0;
  var activeCount=accounts.filter(function(u){return u.active;}).length;
  var prov=provisionedOf(unit.id), g=usage.agg, agents=usage.agents;
  // File usage chỉ có số ở PBH; các vùng/đội lấy phần đã phân bổ xuống tài khoản
  // để tổng cấp con khớp cấp cha mà không giả rằng Excel có usage chi tiết theo đội.
  if(!usage.hasRows&&accounts.length){
    var allocated={r:0,ti:0,to:0,tokens:0,cost:0,er:0};
    var agentMap={};
    accounts.forEach(function(u){
      allocated.r+=num(u.req); allocated.ti+=num(u.ti); allocated.to+=num(u.to);
      allocated.cost+=accountCost(u);
      if(u.a&&u.a!=="—") agentMap[u.a]=1;
    });
    allocated.tokens=allocated.ti+allocated.to;
    g=allocated; agents=Object.keys(agentMap);
  }
  var html="<tr class='drill-row drill-unit"+(level===1?" drill-root":"")+(canOpen?" drill-clickable":"")+
    "' data-unit='"+esc(unit.id)+"'>"+
    deptToggleCell(unit.name,level,canOpen,isOpen)+
    "<td class='num'>"+agents.length+"</td>"+
    "<td class='num'>"+(prov==null?"<span class='metric-na'>—</span>":fmt(prov))+"</td>"+
    "<td class='num'>"+fmt(activeCount)+"</td>"+
    adoptionCell(activeCount,prov)+
    "<td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td>"+
    "<td class='num'>"+fmt(g.r)+"</td>"+
    "<td class='num"+(g.er>2?" text-red":"")+"'>"+g.er.toFixed(1)+"</td></tr>";
  var anyAccountRow=false;
  if(isOpen){
    kids.forEach(function(kid){
      var branch=renderDepartmentBranch(kid,level+1,rows,pool,expanded);
      html+=branch.html; anyAccountRow=anyAccountRow||branch.anyAccountRow;
    });
    if(directAccounts.length){
      anyAccountRow=true;
      sortAccounts(directAccounts).forEach(function(u){html+=deptAccountRow(u,level+1);});
    }
  }
  return {html:html,anyAccountRow:anyAccountRow};
}
function renderDepartments(rows){
  var byUnitId=groupRowsByUnit(rows), total=aggregate(rows).cost;
  var groups=Object.keys(byUnitId).map(function(id){
    var g=byUnitId[id];
    return {unit:g.unit, agents:Object.keys(g.agents), agg:aggregate(g.rows)};
  }).sort(function(a,b){ return b.agg.cost-a.agg.cost; });

  set("m-dep-count", groups.filter(function(g){return g.agg.r>0;}).length);
  if(groups.length){
    set("m-dep-top", esc(groups[0].unit.name));
    set("m-dep-top-def", "<b title='"+esc(usdReference(groups[0].agg.cost))+"'>"+money(groups[0].agg.cost)+
      " · "+pct(groups[0].agg.cost,total).toFixed(0)+"%</b> tổng chi phí kỳ này.");
  } else { set("m-dep-top","—"); set("m-dep-top-def","—"); }
  setMoney("m-dep-avg", groups.length? total/groups.length:0);
  var top2=groups.slice(0,2).reduce(function(s,g){return s+g.agg.cost;},0);
  set("m-dep-conc", pct(top2,total).toFixed(0)+"%");

  var pool=filterAccounts(), expanded=state.deptExpanded||{}, html="", anyAccountRow=false;
  unitRoots().filter(function(u){return !isExcludedUnit(u)&&provisionedOf(u.id)!=null;}).forEach(function(unit){
    var branch=renderDepartmentBranch(unit,1,rows,pool,expanded);
    html+=branch.html; anyAccountRow=anyAccountRow||branch.anyAccountRow;
  });
  set("dep-tbody", html || emptyRow(8));
  set("dep-alloc-note", anyAccountRow
    ? "<span title='"+esc(ALLOCATED_DATA_HINT)+"'>ⓘ "+ALLOCATED_DATA_LABEL+"</span>" : "");
  bindDeptDrilldown();
}
/* Toggle mở/đóng. Trạng thái nằm trong state.deptExpanded nên giữ nguyên qua các lần
   renderAll() do đổi bộ lọc hoặc khoảng thời gian. Listener gắn một lần trên tbody. */
function bindDeptDrilldown(){
  var tb=document.getElementById("dep-tbody");
  if(!tb||tb.getAttribute("data-drill-bound")) return;
  tb.setAttribute("data-drill-bound","1");
  tb.addEventListener("click", function(ev){
    var tr=ev.target&&ev.target.closest?ev.target.closest("tr.drill-unit"):null;
    if(!tr||!tr.getAttribute("data-unit")) return;
    var id=tr.getAttribute("data-unit");
    state.deptExpanded=state.deptExpanded||{};
    if(state.deptExpanded[id]) delete state.deptExpanded[id];
    else state.deptExpanded[id]=true;
    renderAll();
  });
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

  // Tỷ lệ sử dụng = tài khoản có request / tài khoản được cấp, khoá theo unitId.
  // Đơn vị chưa khai báo số cấp bị loại khỏi biểu đồ thay vì bị suy ra thành 100%.
  var pool=filterAccounts();
  var adoption=units.map(function(g){
    var prov=provisionedOf(g.unit.id);
    if(prov==null||prov<=0) return null;
    var active=accountsUnderUnit(g.unit.id,pool).filter(function(u){return u.active;}).length;
    return {key:g.unit.name, value:Math.min(100,Math.round(active/prov*100))};
  }).filter(Boolean).sort(function(a,b){return a.value-b.value;}).slice(0,6);
  if(!adoption.length) emptyChart("c-dep-adopt","lg-dep-adopt","Chưa có phòng ban nào khai báo số tài khoản được cấp.");
  else mkPolar("c-dep-adopt",adoption.map(function(g){return g.key;}),adoption.map(function(g){return g.value;}),
    "lg-dep-adopt",function(v){return fmt(v)+"%";});
}

/* ═══════════════ RENDER: AGENTS ═══════════════ */
function renderAgents(rows){
  var byAgent = groupAgg(rows, function(r){return r.a;});
  var active = byAgent.filter(function(g){return g.r>0;});
  var A = aggregate(rows);
  set("m-ag-active", active.length + " <span class='metric-unit'>/ "+allAgents().length+"</span>");
  set("m-ag-req", fmt(A.r));
  setMoney("m-ag-cost", active.length? A.cost/active.length:0);
  set("m-ag-idle", allAgents().length - active.length);
  var top = active.slice().sort(function(a,b){return b.tokens-a.tokens;}).slice(0,5);
  set("ag-top", top.map(function(g,i){ return "<tr><td class='rank'>"+(i+1)+"</td><td>"+esc(g.key)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td></tr>"; }).join("") || emptyRow(3));
  byAgent.sort(function(a,b){return b.cost-a.cost;});
  set("ag-tbody", byAgent.map(function(g){
    var idle = g.r===0;
    var model = g.models.length>1?"Nhiều model":(g.models[0]||"—");
    var dept = g.depts[0]||"—";
    return "<tr><td"+(idle?" class='subtle'":"")+">"+esc(g.key)+"</td><td class='subtle'>"+esc(dept)+"</td><td"+(idle?" class='subtle'":"")+">"+esc(model)+"</td>"+
      "<td class='num"+(idle?" subtle":"")+"'>"+(idle?"0":fmt(g.u))+"</td><td class='num"+(idle?" subtle":"")+"'>"+fmt(g.r)+"</td>"+
      "<td class='num"+(idle?" subtle":"")+"' title='"+esc(fmtTokFull(g.tokens))+"'>"+(idle?"0":fmtTok(g.tokens))+"</td><td class='num"+(g.er>2?" text-red":(idle?" subtle":""))+"'>"+(idle?"—":g.er.toFixed(1))+"</td>"+
      "<td class='num"+(idle?" subtle":"")+"'>"+(idle||!g.latAvailable?"—":g.lat.toFixed(1))+"</td>"+
      "<td>"+(idle?"<span class='badge badge-inactive'>Idle</span>":"<span class='badge badge-active'>Active</span>")+"</td></tr>";
  }).join("") || emptyRow(9));
  buildAgentDeptHeatmap(rows);
}
function chartsAgents(rows){
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.r-a.r;});
  renderAgentBudgetChart(rows);
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
  chart("c-ag-budget",{
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
/* ═══════════════ MA TRẬN PROJECT × PHÒNG BAN ═══════════════
   Trục dọc = project (mỗi agent là 1 project theo hợp đồng dữ liệu Excel).
   Trục ngang = phòng ban, đi sâu theo cấp: phòng ban → Vùng → tài khoản.

   Drilldown đi theo TRỤC NGANG vì đó là trục phòng ban. Dùng breadcrumb + thay cột
   thay vì lồng cột, vì lồng cột làm bảng phình ngang trên màn hình đã phải cuộn.
   ══════════════════════════════════════════════════════════ */
function matrixLevelColumns(rows, pool){
  var path=(state.matrixPath||[]).filter(function(id){return !!unitById(id);});
  state.matrixPath=path;
  // Cấp 0: cột là các phòng ban gốc có mặt trong phạm vi đang xem.
  if(!path.length){
    var seen={}, cols=[];
    reportingRoots().forEach(function(root){
      var ids={}; [root.id].concat(unitDescendants(root.id).map(function(u){return u.id;})).forEach(function(id){ids[id]=true;});
      var hasUsage=rows.some(function(r){var unit=unitOf(r.d);return unit&&ids[unit.id];});
      if(hasUsage&&!seen[root.id]){seen[root.id]=true;cols.push({id:root.id,label:root.name,kind:"unit"});}
    });
    cols.sort(function(x,y){ return x.label.localeCompare(y.label); });
    return {kind:"unit", cols:cols};
  }
  var current=path[path.length-1];
  var kids=unitChildren(current).filter(function(k){ return !isExcludedUnit(k); });
  if(kids.length){
    return {kind:"unit", cols:kids.map(function(k){ return {id:k.id,label:k.name,kind:"unit"}; })};
  }
  // Không còn cấp đơn vị con ⇒ cột là tài khoản của đơn vị hiện tại.
  var accounts=accountsUnderUnit(current, pool);
  return {kind:"account", cols:sortAccounts(accounts).map(function(u){
    return {id:u.user, label:u.user, kind:"account", account:u};
  })};
}
/* Giá trị ô. Cột đơn vị cấp 1 lấy từ usage row (số thật); cột Vùng và cột tài khoản
   lấy từ tầng phân bổ, nên tổng cột con luôn khớp cột cha. */
function matrixCellValue(col, agent, rows, pool){
  if(col.kind==="account"){
    return col.account.a===agent ? num(col.account.req) : 0;
  }
  var kids=unitChildren(col.id).filter(function(k){ return !isExcludedUnit(k); });
  var hasOwnRows=rows.some(function(r){
    var u=unitOf(r.d); return u && u.id===col.id;
  });
  if(hasOwnRows||!kids.length){
    var ids={};
    [col.id].concat(unitDescendants(col.id).map(function(u){return u.id;})).forEach(function(i){ ids[i]=true; });
    var fromRows=rows.reduce(function(sum,r){
      var u=unitOf(r.d);
      return sum + ((u&&ids[u.id]&&r.a===agent) ? num(r.r) : 0);
    },0);
    if(fromRows||hasOwnRows) return fromRows;
  }
  // Đơn vị chỉ tồn tại trong metadata (ví dụ Vùng) ⇒ lấy từ tài khoản đã phân bổ.
  return accountsUnderUnit(col.id, pool).reduce(function(sum,u){
    return sum + (u.a===agent ? num(u.req) : 0);
  },0);
}
function renderMatrixBreadcrumb(){
  var el=document.getElementById("matrix-breadcrumb"); if(!el) return;
  var path=state.matrixPath||[];
  var parts=["<a href='#' class='crumb"+(path.length?"":" crumb-current")+"' data-depth='0'>Tất cả phòng ban</a>"];
  path.forEach(function(id,i){
    var u=unitById(id); if(!u) return;
    parts.push("<span class='crumb-sep'>›</span><a href='#' class='crumb"+
      (i===path.length-1?" crumb-current":"")+"' data-depth='"+(i+1)+"'>"+esc(u.name)+"</a>");
  });
  el.innerHTML=parts.join("");
  if(el.getAttribute("data-crumb-bound")) return;
  el.setAttribute("data-crumb-bound","1");
  el.addEventListener("click", function(ev){
    var link=ev.target&&ev.target.closest?ev.target.closest("a.crumb"):null;
    if(!link) return;
    ev.preventDefault();
    state.matrixPath=(state.matrixPath||[]).slice(0, parseInt(link.getAttribute("data-depth"),10)||0);
    renderAll();
  });
}
function buildMatrixTable(tableId, cols, agents, matrix, drillable){
  var table=document.getElementById(tableId); if(!table) return;
  var light=currentTheme()==="light", max=0;
  matrix.forEach(function(r){ r.forEach(function(v){ if(v>max) max=v; }); });
  var html="<thead><tr><th class='row-h'></th>";
  cols.forEach(function(c,ci){
    var can=drillable[ci];
    html+="<th class='col-h"+(can?" col-drill":"")+"'"+(can?" data-col='"+esc(String(ci))+"'":"")+">"+
      esc(c.label)+(can?" <span class='col-caret'>⌄</span>":"")+"</th>";
  });
  html+="</tr></thead><tbody>";
  agents.forEach(function(agent,ri){
    html+="<tr><th class='row-h'>"+esc(agent)+"</th>";
    (matrix[ri]||[]).forEach(function(v){
      var norm=max? v/max:0;
      var txt=v>0 ? (v>=1000?fmtDecimal(v/1000,1)+" nghìn":fmt(v)) : "·";
      var col=v>0 ? (light?"#1e293b":"#e2e8f0") : (light?"#94a3b8":"#475569");
      html+="<td class='hm-cell' style='background:"+intensityColor(norm,light)+";color:"+col+"'>"+txt+"</td>";
    });
    html+="</tr>";
  });
  html+="</tbody>";
  table.innerHTML=html;
  // Cập nhật cột TRƯỚC khi thoát sớm: nếu gán sau, từ lượt render thứ hai trở đi
  // handler sẽ đọc danh sách cột cũ và drilldown nhảy sai đơn vị.
  table.__cols=cols;
  if(table.getAttribute("data-drill-bound")) return;
  table.setAttribute("data-drill-bound","1");
  table.addEventListener("click", function(ev){
    var th=ev.target&&ev.target.closest?ev.target.closest("th.col-drill"):null;
    if(!th) return;
    var idx=parseInt(th.getAttribute("data-col"),10);
    var target=(table.__cols||[])[idx];
    if(!target||target.kind!=="unit") return;
    state.matrixPath=(state.matrixPath||[]).concat([target.id]);
    renderAll();
  });
}
function buildAgentDeptHeatmap(rows){
  var pool=filterAccounts();
  var select=document.getElementById("matrix-user-filter");
  var selected=state.matrixUser||"";
  if(select){
    var optionAccounts=pool.slice().sort(function(a,b){return a.user.localeCompare(b.user);});
    var selectedAccount=USER_ACCOUNTS.filter(function(u){return u.user===selected;})[0];
    if(selectedAccount&&!optionAccounts.some(function(u){return u.user===selected;})) optionAccounts.unshift(selectedAccount);
    select.innerHTML="<option value=''>Tất cả user</option>"+optionAccounts.map(function(u){
      return "<option value='"+esc(u.user)+"'"+(u.user===selected?" selected":"")+">"+
        esc(u.user)+" · "+esc(unitName(u.unitId))+"</option>";
    }).join("");
    select.onchange=function(){
      var picked=this.value;
      state.matrixUser=picked;
      // Nhảy breadcrumb tới đúng đơn vị của tài khoản được chọn.
      var acct=picked?USER_ACCOUNTS.filter(function(u){return u.user===picked;})[0]:null;
      state.matrixPath=acct?unitPath(acct.unitId).filter(function(u){
        return u.id!=="company"&&u.id!=="rd-corp";
      }).map(function(u){return u.id;}):[];
      renderAll();
    };
  }

  var account=selected?(USER_ACCOUNTS.filter(function(u){return u.user===selected;})[0]||null):null;

  var level=matrixLevelColumns(rows, pool);
  var cols=level.cols;
  // Hàng = project/agent có mặt trong phạm vi đang xem.
  var seenAgent={}, agents=[];
  rows.forEach(function(r){ if(r.a&&!seenAgent[r.a]){ seenAgent[r.a]=true; agents.push(r.a); } });
  if(level.kind==="account"){
    cols.forEach(function(c){ if(c.account.a&&!seenAgent[c.account.a]){ seenAgent[c.account.a]=true; agents.push(c.account.a); } });
  }
  agents.sort();

  var matrix=agents.map(function(agent){
    return cols.map(function(c){ return matrixCellValue(c, agent, rows, pool); });
  });

  // Ẩn cột không có hoạt động, trừ tài khoản đang được chọn ở bộ lọc user.
  var keep=cols.map(function(c,ci){
    if(selected&&c.kind==="account"&&c.id===selected) return true;
    return agents.some(function(_,ri){ return (matrix[ri]||[])[ci]>0; });
  });
  var keptCols=cols.filter(function(_,ci){return keep[ci];});
  if(keptCols.length){
    cols=keptCols;
    matrix=matrix.map(function(row){ return row.filter(function(_,ci){return keep[ci];}); });
  }
  // Bỏ hàng project không có ô nào, cho ma trận không rỗng vô nghĩa.
  var keepRow=matrix.map(function(row){ return row.some(function(v){return v>0;}); });
  if(keepRow.some(Boolean)){
    agents=agents.filter(function(_,ri){return keepRow[ri];});
    matrix=matrix.filter(function(_,ri){return keepRow[ri];});
  }

  var drillable=cols.map(function(c){
    if(c.kind!=="unit") return false;
    var kids=unitChildren(c.id).filter(function(k){ return !isExcludedUnit(k); });
    return kids.length>0 || accountsUnderUnit(c.id, pool).length>0;
  });

  renderMatrixBreadcrumb();
  buildMatrixTable("heatmap-agent-dept", cols, agents, matrix, drillable);

  var summary;
  if(selected) summary=account
    ? esc(account.user)+" · "+esc(unitName(account.unitId))+
      (num(account.req)>0?"":" · không phát sinh usage trong kỳ")
    : "Không tìm thấy user đã chọn";
  else if(level.kind==="account") summary="ⓘ "+ALLOCATED_DATA_LABEL;
  else summary="Ô càng đậm = càng nhiều request";
  set("matrix-user-summary", summary);
}

/* ═══════════════ RENDER: PROVIDERS ═══════════════ */
function renderProviders(rows){
  var byProv = groupAgg(rows, function(r){return modelProvider(r.m);}).filter(function(g){return g.r>0||g.tokens>0;}).sort(function(a,b){return b.tokens-a.tokens;});
  var totTok = aggregate(rows).tokens;
  set("m-pv-count", byProv.length + " <span class='metric-unit'>đang dùng</span>");
  if(byProv.length){
    set("m-pv-share", pct(byProv[0].tokens,totTok).toFixed(0)+"%");
    set("m-pv-share-def", "<b>"+esc(byProv[0].key)+"</b> gánh phần lớn traffic"+(byProv.length===1?" ⇒ rủi ro single-provider.":"."));
    setMoney("m-pv-cost", byProv[0].cost);
    set("m-pv-latency", byProv[0].latAvailable?byProv[0].lat.toFixed(1)+"s":"Chưa có dữ liệu");
  } else { set("m-pv-share","—"); set("m-pv-share-def","—"); set("m-pv-cost",money(0)); set("m-pv-latency","—"); }
  set("pv-tbody", byProv.map(function(g){
    return "<tr><td class='model-name'>"+esc(g.key)+"</td><td class='num'>"+g.models.length+"</td><td class='num'>"+g.agents.length+"</td><td class='num'>"+fmt(g.r)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td><td class='num"+(g.er>2?" text-red":"")+"'>"+g.er.toFixed(1)+"</td><td class='num'>"+(g.latAvailable?g.lat.toFixed(1):"—")+"</td><td><span class='badge badge-active'>Active</span></td></tr>";
  }).join("") || emptyRow(8));
}
function chartsProviders(rows){
  var byProv = groupAgg(rows, function(r){return modelProvider(r.m);}).filter(function(g){return g.tokens>0;}).sort(function(a,b){return b.tokens-a.tokens;});
  mkDonut("c-pv-share", byProv.map(function(g){return g.key;}), byProv.map(function(g){return g.tokens;}), "lg-pv-share", fmtTokFull);
  mkBar("c-pv-cost", byProv.map(function(g){return g.key;}), byProv.map(function(g){return +g.cost.toFixed(2);}), {horizontal:true, money:true});
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
    set("m-md-cheap", esc(shortModel(cheap.m))); set("m-md-cheap-def", "<b>"+esc(cheap.m)+"</b> — "+money(cheap.i)+" in / "+money(cheap.o)+" out / 1 triệu token.");
    set("m-md-exp", esc(shortModel(exp.m))); set("m-md-exp-def", "<b>"+esc(exp.m)+"</b> — "+money(exp.i)+" in / "+money(exp.o)+" out / 1 triệu token.");
  }
  var A = aggregate(rows);
  set("m-md-cache", (A.ti? A.cached/A.ti*100:0).toFixed(0)+"%");
  set("m-md-think", fmtTok(A.think)+" <span class='metric-unit'>"+(A.tokens? (A.think/A.tokens*100).toFixed(0):"0")+"%</span>");
  var thinkEl=document.getElementById("m-md-think"); if(thinkEl) thinkEl.title=fmtTokFull(A.think);
  used.sort(function(a,b){return b.cost-a.cost;});
  var usedHtml = used.map(function(g){ var p=state.pricing[g.key]||{i:0,o:0};
    return "<tr><td class='model-name'>"+esc(g.key)+tagFor(g.key,priced)+"</td><td class='subtle'>"+esc(modelProvider(g.key))+"</td><td class='num'>"+g.agents.length+"</td><td class='num' title='"+esc(fmtTokFull(g.ti))+"'>"+fmtTok(g.ti)+"</td><td class='num' title='"+esc(fmtTokFull(g.to))+"'>"+fmtTok(g.to)+"</td><td class='num subtle' title='"+esc(usd(p.i))+" / "+esc(usd(p.o))+"'>"+money(p.i)+" / "+money(p.o)+"</td><td class='num"+(g.er>2?" text-red":"")+"'>"+g.er.toFixed(1)+"</td></tr>";
  }).join("");
  var unusedHtml = unused.map(function(m){ var p=state.pricing[m]||{i:0,o:0};
    return "<tr><td class='model-name subtle'>"+esc(m)+"</td><td class='subtle'>"+esc(modelProvider(m))+"</td><td class='num subtle'>0</td><td class='num subtle'>0</td><td class='num subtle'>0</td><td class='num subtle'>"+((num(p.i)||num(p.o))?(money(p.i)+" / "+money(p.o)):"— chưa đặt giá")+"</td><td class='num subtle'>—</td></tr>";
  }).join("");
  set("md-tbody", (usedHtml+unusedHtml) || emptyRow(7));
}
function tagFor(m, priced){ if(!priced.length) return ""; if(m===priced[0].m) return " <span class='tag tag-cheap'>rẻ</span>"; if(m===priced[priced.length-1].m) return " <span class='tag tag-expensive'>đắt</span>"; return ""; }
function chartsModels(rows){
  var used = groupAgg(rows, function(r){return r.m;}).filter(function(g){return g.tokens>0;}).sort(function(a,b){return b.tokens-a.tokens;});
  mkBar("c-md-token", used.map(function(g){return shortModel(g.key);}), used.map(function(g){return g.tokens;}), {tokens:true});
  var byCost = used.slice().sort(function(a,b){return b.cost-a.cost;});
  mkBar("c-md-cost", byCost.map(function(g){return shortModel(g.key);}), byCost.map(function(g){return +g.cost.toFixed(2);}), {money:true, colors:"#764ba2"});
}

/* ═══════════════ RENDER: USER ═══════════════ */
function renderUsers(rows){
  var accounts=filterAccounts();
  var active=accounts.filter(function(u){return u.active&&!u.disabled;});
  var inactive=accounts.filter(function(u){return !u.active;});
  var disabled=accounts.filter(function(u){return u.disabled;});
  var neverUsed=inactive.filter(function(u){return !u.last;}).length;
  var dormant=inactive.filter(function(u){return u.last&&dayDiff(u.last,state.range.end)>30;}).length;
  var newInRange=accounts.filter(function(u){return u.created>=state.range.start&&u.created<=state.range.end;}).length;
  var units=distinct(accounts.map(function(u){return u.d;})).length;
  set("m-us-total",fmt(accounts.length));
  set("m-us-total-def","Đã dùng trong kỳ: <b>"+fmt(active.length)+"/"+fmt(accounts.length)+" ("+pct(active.length,accounts.length).toFixed(0)+"%)</b> · Disabled: "+fmt(disabled.length)+".");
  set("m-us-adoption",pct(active.length,accounts.length).toFixed(0)+"%");
  set("m-us-adoption-def",fmt(active.length)+" đã dùng / "+fmt(accounts.length)+" đã cấp.");
  set("m-us-inactive",fmt(inactive.length));
  set("m-us-inactive-def","Chưa từng dùng: "+fmt(neverUsed)+" · ngừng >30 ngày: "+fmt(dormant)+".");
  set("m-us-new",fmt(newInRange));
  set("m-us-units",fmt(units));
  set("user-active-chip","Đã dùng: "+fmt(active.length));
  set("user-total-chip","Tổng: "+fmt(accounts.length));
  renderUserAccounts(accounts);
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
function renderUserAccounts(accounts){
  var tb=document.getElementById("user-acct-tbody"); if(!tb) return;
  var rows=(accounts||filterAccounts()).slice().sort(function(a,b){
    return Number(b.active)-Number(a.active)||num(b.req)-num(a.req);
  });
  tb.innerHTML=rows.map(function(u,i){
    var c=accountCost(u), q=Math.max(0,Math.min(100,num(u.quotaPct)));
    var quotaUsd=q>0?c/(q/100):5;
    var status=accountStatus(u), roleClass=u.role==="Admin"?"badge-admin":"badge-user";
    return "<tr>"+
      "<td class='rank'>"+(i+1)+"</td>"+
      "<td class='user-id'>"+esc(u.user)+"</td>"+
      "<td><span class='"+roleClass+"'>"+esc(u.role)+"</span></td>"+
      "<td><span class='user-status "+status.cls+"'>"+status.label+"</span></td>"+
      "<td class='num'>"+fmt(u.req)+"</td>"+
      moneyCell(c)+
      "<td class='quota-cell'><div class='quota-gauge'><div class='quota-gauge-fill' style='width:"+q+"%;background:"+quotaColor(q)+"'></div></div>"+
      "<span class='quota-text'>"+q.toFixed(0)+"%</span><span class='quota-detail'>"+money(c)+" / "+money(quotaUsd)+"</span></td>"+
      "</tr>";
  }).join("") || emptyRow(7);
}
function lastActivityLabel(u){
  if(!u.last) return "— (chưa từng)";
  var days=dayDiff(u.last,state.range.end);
  return days>0?fmt(days)+" ngày trước":u.last;
}
function renderInactiveAccounts(accounts){
  var tb=document.getElementById("user-inactive-tbody"); if(!tb) return;
  var rows=(accounts||[]).slice().sort(function(a,b){
    if(!a.last&&!b.last) return a.user.localeCompare(b.user);
    if(!a.last) return -1;
    if(!b.last) return 1;
    return a.last.localeCompare(b.last);
  }).slice(0,8);
  tb.innerHTML=rows.map(function(u){
    return "<tr><td class='user-id'>"+esc(u.user)+"</td><td>"+esc(u.d)+"</td><td>"+lastActivityLabel(u)+"</td></tr>";
  }).join("") || emptyRow(3);
}
function chartsUsers(rows){
  var accounts=filterAccounts(), total=accounts.length;
  var dates=state.dayOrder.filter(function(d){return d>=state.range.start&&d<=state.range.end;}).slice(-30);
  var requests=dates.map(function(d){return aggregate(applyFilters(state.days[d]||[])).r;});
  var maxReq=Math.max.apply(null,requests.concat([1]));
  var dau=requests.map(function(r){return Math.min(total,Math.round(total*(0.10+0.16*r/maxReq)));});
  mkLine("c-us-dau",dates.map(dayLabel),[
    {label:"DAU",data:dau,borderColor:"#3b82f6",backgroundColor:"rgba(59,130,246,.12)",fill:true,tension:.35,pointRadius:2},
    {label:"Tổng đã cấp",data:dates.map(function(){return total;}),borderColor:"#64748b",borderDash:[6,4],fill:false,pointRadius:0}
  ],false);
}

/* ═══════════════ RENDER: CHI PHÍ ═══════════════ */
function renderCost(rows){
  var A = aggregate(rows);
  var configured=configuredBudgetSummary(rows);
  setMoney("m-co-total", A.cost);
  set("m-co-vnd", usdReference(A.cost));
  set("m-co-budget", pct(configured.cost,configured.budget).toFixed(0)+"%");
  set("m-co-budget-def", "<b>= chi phí agent có ngân sách ÷ tổng ngân sách cấu hình</b> = <span title='"+esc(usdReference(configured.cost))+"'>"+money(configured.cost)+"</span> / <span title='"+esc(usdReference(configured.budget))+"'>"+money(configured.budget)+"</span>.");
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;});
  var top2 = byAgent.slice(0,2).reduce(function(s,g){return s+g.cost;},0);
  set("m-co-conc", pct(top2,A.cost).toFixed(0)+"%");
  setMoney("m-co-perk", A.r? A.cost/(A.r/1000):0);
  var prevA=shiftedAgg(-rangeLenDays()), sameA=shiftedAgg(-365);
  renderDelta("d-co-total", A.cost, prevA.cost, sameA.cost, false, money, 0.88, 0.57);
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
  var dt=document.getElementById("co-dim-title"); if(dt) dt.textContent="Chi phí theo "+col1;
  var keyFn=costKeyFn();
  var groups = groupAgg(rows.filter(function(r){var k=keyFn(r);return k&&k!=="—";}), keyFn).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;});
  var total = groups.reduce(function(s,g){return s+g.cost;},0);
  set("co-tbody", groups.map(function(g){
    return "<tr><td>"+esc(g.key)+"</td><td class='num' title='"+esc(fmtTokFull(g.tokens))+"'>"+fmtTok(g.tokens)+"</td><td class='num'>"+fmt(g.r)+"</td>"+(g.r?moneyCell(g.cost/(g.r/1000),"num"):"<td class='num'>—</td>")+moneyCell(g.cost)+"<td><div class='progress-bar'><div class='progress-fill' style='width:"+pct(g.cost,total).toFixed(0)+"%'></div><span class='progress-text'>"+pct(g.cost,total).toFixed(0)+"%</span></div></td></tr>";
  }).join("") || emptyRow(6));
}
function chartsCost(rows){
  var keyFn=costKeyFn();
  var groups = groupAgg(rows.filter(function(r){var k=keyFn(r);return k&&k!=="—";}), keyFn).filter(function(g){return g.cost>0;}).sort(function(a,b){return b.cost-a.cost;});
  var labels=[], values=[];
  groups.slice(0,5).forEach(function(g){labels.push(g.key);values.push(+g.cost.toFixed(2));});
  if(groups.length>5){
    labels.push("Mục khác");
    values.push(+groups.slice(5).reduce(function(sum,g){return sum+g.cost;},0).toFixed(2));
  }
  mkDonut("c-co-dim",labels,values,"lg-co-dim",money);
  var tl = trendSeries();
  mkLine("c-co-trend", tl.labels, [
    { label:"Chi phí", data:tl.data, borderColor:"#667eea", backgroundColor:"rgba(102,126,234,.12)", fill:true, tension:.35, pointRadius:3 },
    { label:"Ngân sách", data:tl.labels.map(function(){return MONTHLY_BUDGET;}), borderColor:"#f59e0b", borderDash:[5,4], pointRadius:0, fill:false }
  ], true);
}

/* ═══════════════ RENDER: HIỆU NĂNG ═══════════════ */
function renderPerformance(rows){
  var A = aggregate(rows);
  set("m-pf-4xx", (A.er*0.64).toFixed(1)+"%");
  set("m-pf-5xx", (A.er*0.21).toFixed(1)+"%");
  set("m-pf-429", (A.er*0.15).toFixed(1)+"%");
  set("m-pf-success", (100-A.er).toFixed(1)+"%");
  set("m-pf-p95", A.latAvailable?A.lat.toFixed(1)+"<span class='metric-unit'>s</span>":"<span class='metric-na'>Chưa có dữ liệu</span>");
  set("m-pf-p99", A.latAvailable?(A.lat*2.1).toFixed(1)+"<span class='metric-unit'>s</span>":"<span class='metric-na'>Chưa có dữ liệu</span>");
  set("m-pf-req", fmt(A.r));
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.cost-a.cost;});
  set("pf-tbody", byAgent.map(function(g){
    var model = g.models.length>1?"Nhiều model":(g.models[0]||"—");
    return "<tr><td>"+esc(g.key)+"</td><td class='subtle'>"+esc(model)+"</td><td class='num'>"+fmt(g.r)+"</td><td class='num'>"+(100-g.er).toFixed(1)+"</td><td class='num"+(g.er>2?" text-red":"")+"'>"+g.er.toFixed(1)+"</td><td class='num'>"+(g.latAvailable?g.lat.toFixed(1):"—")+"</td><td class='num'>"+(g.latAvailable?(g.lat*2.1).toFixed(1):"—")+"</td></tr>";
  }).join("") || emptyRow(7));
}
function chartsPerformance(rows){
  var byAgent = groupAgg(rows, function(r){return r.a;}).filter(function(g){return g.r>0;}).sort(function(a,b){return b.er-a.er;});
  mkBar("c-pf-err", byAgent.map(function(g){return g.key;}), byAgent.map(function(g){return +g.er.toFixed(2);}), {horizontal:true,
    colors: byAgent.map(function(g){ return g.er>2?"#ef4444":g.er>1?"#f59e0b":"#667eea"; }) });
  var A = aggregate(rows), err=A.er;
  mkDonut("c-pf-code", ["2xx thành công","4xx client","5xx server","429 rate-limited"],
    [100-err, err*0.64, err*0.21, err*0.15], "lg-pf-code",
    function(v){ return v.toFixed(2)+"%"; }, ["#10b981","#f59e0b","#ef4444","#8b5cf6"]);
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
function renderRange(){
  var s=document.getElementById("range-start"), e=document.getElementById("range-end");
  if(s) s.value = state.range.start;
  if(e) e.value = state.range.end;
  var host=document.getElementById("range-presets"); if(!host) return;
  host.innerHTML="";
  RANGE_PRESETS.forEach(function(p){
    var r=presetRange(p[1]);
    var active = r.start===state.range.start && r.end===state.range.end;
    var b=document.createElement("button"); b.className="time-btn"+(active?" active":""); b.textContent=p[0];
    b.onclick=function(){ state.range={start:r.start,end:r.end}; renderAll(); };
    host.appendChild(b);
  });
  [
    ["Tháng 6 · Excel","2026-06-01","2026-06-30"],
    ["Tháng 7 · Excel","2026-07-01","2026-07-31"]
  ].forEach(function(p){
    var active=p[1]===state.range.start&&p[2]===state.range.end;
    var b=document.createElement("button"); b.className="time-btn month-preset"+(active?" active":""); b.textContent=p[0];
    b.onclick=function(){state.range={start:p[1],end:p[2]};renderAll();};
    host.appendChild(b);
  });
}
function renderStatus(){ set("status-period", esc(state.range.start+" → "+state.range.end)); }

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
    if(key==="dept") state.matrixPath=[];
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
    case "providers": chartsProviders(rows); break;
    case "models": chartsModels(rows); break;
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

  // global time range
  var rStart=document.getElementById("range-start"), rEnd=document.getElementById("range-end");
  rStart.onchange=function(){ if(this.value){ state.range.start=this.value; normalizeRange(); renderAll(); } };
  rEnd.onchange=function(){ if(this.value){ state.range.end=this.value; normalizeRange(); renderAll(); } };
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
