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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:23300,to:8156,r:4,er:0.0,lat:16.36,cached:2181,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5877,to:2057,r:1,er:0.0,lat:16.36,cached:550,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4505,to:1577,r:1,er:0.0,lat:16.36,cached:422,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2552,to:893,r:0,er:0.0,lat:16.36,cached:239,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2439,to:854,r:0,er:0.0,lat:16.36,cached:228,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2402,to:841,r:0,er:0.0,lat:16.36,cached:225,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1416,to:496,r:0,er:0.0,lat:16.36,cached:133,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:978,to:342,r:0,er:0.0,lat:16.36,cached:92,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:16.69},
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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:65630,to:31655,r:0,er:0.0,lat:0.0,cached:15205,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:16555,to:7985,r:0,er:0.0,lat:0.0,cached:3835,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:12688,to:6120,r:0,er:0.0,lat:0.0,cached:2940,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7189,to:3467,r:0,er:0.0,lat:0.0,cached:1665,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6869,to:3313,r:0,er:0.0,lat:0.0,cached:1591,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:6765,to:3263,r:0,er:0.0,lat:0.0,cached:1567,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:374224,to:48534,r:0,er:0.0,lat:0.0,cached:89745,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:94397,to:12243,r:0,er:0.0,lat:0.0,cached:22638,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:72349,to:9383,r:0,er:0.0,lat:0.0,cached:17350,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:40990,to:5316,r:0,er:0.0,lat:0.0,cached:9830,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:39166,to:5079,r:0,er:0.0,lat:0.0,cached:9393,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38574,to:5003,r:0,er:0.0,lat:0.0,cached:9251,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:22737,to:2949,r:0,er:0.0,lat:0.0,cached:5453,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:15700,to:2036,r:0,er:0.0,lat:0.0,cached:3765,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:28056,to:35549,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:157244,to:194726,r:0,er:0.0,lat:0.0,cached:64947,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:239852,to:3304,r:13,er:0.0,lat:2.04,cached:89944,think:0,e4:0,e5:0,e429:0,eKnown:13,lat99:2.09},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:474888,to:14558,r:47,er:0.0,lat:4.04,cached:191506,think:0,e4:0,e5:0,e429:0,eKnown:47,lat99:4.16},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:133,to:0,r:0,er:0.0,lat:4.04,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:4.16},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:161877,to:42645,r:10,er:0.0,lat:9.8,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:10.35},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13258,to:2075,r:4,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-20": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126568,to:42116,r:13,er:0.0,lat:55.36,cached:30516,think:0,e4:0,e5:0,e429:0,eKnown:13,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:31926,to:10624,r:3,er:0.0,lat:55.36,cached:7698,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:24469,to:8142,r:3,er:0.0,lat:55.36,cached:5900,think:0,e4:0,e5:0,e429:0,eKnown:3,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13863,to:4613,r:1,er:0.0,lat:55.36,cached:3342,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13246,to:4408,r:1,er:0.0,lat:55.36,cached:3194,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:13046,to:4341,r:1,er:0.0,lat:55.36,cached:3146,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:7690,to:2559,r:1,er:0.0,lat:55.36,cached:1854,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:5310,to:1767,r:1,er:0.0,lat:55.36,cached:1280,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:64.76},
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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19167,to:8392,r:0,er:0.0,lat:0.0,cached:6550,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:4835,to:2117,r:0,er:0.0,lat:0.0,cached:1652,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:3706,to:1622,r:0,er:0.0,lat:0.0,cached:1266,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2099,to:919,r:0,er:0.0,lat:0.0,cached:717,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:2006,to:878,r:0,er:0.0,lat:0.0,cached:685,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1976,to:865,r:0,er:0.0,lat:0.0,cached:675,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1165,to:510,r:0,er:0.0,lat:0.0,cached:398,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:804,to:352,r:0,er:0.0,lat:0.0,cached:275,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:62159,to:80723,r:2,er:0.0,lat:49.07,cached:3022,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:50.08},
    {a:"Multi modal AI Invoice",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:1744093,to:23447,r:204,er:0.0,lat:3.93,cached:1097600,think:0,e4:0,e5:0,e429:0,eKnown:204,lat99:4.14},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:2855745,to:70310,r:167,er:0.0,lat:7.71,cached:1566028,think:0,e4:0,e5:0,e429:0,eKnown:167,lat99:8.25},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:177,to:0,r:0,er:0.0,lat:7.71,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.25},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:861226,to:124891,r:62,er:0.0,lat:7.76,cached:45032,think:0,e4:0,e5:0,e429:0,eKnown:62,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:144973,to:19796,r:32,er:0.0,lat:0.0,cached:26276,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-07-24": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:353275,to:111840,r:40,er:0.0,lat:32.72,cached:96126,think:0,e4:0,e5:0,e429:0,eKnown:40,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:89113,to:28211,r:10,er:0.0,lat:32.72,cached:24247,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:68299,to:21622,r:8,er:0.0,lat:32.72,cached:18584,think:0,e4:0,e5:0,e429:0,eKnown:8,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38695,to:12250,r:4,er:0.0,lat:32.72,cached:10529,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36973,to:11705,r:4,er:0.0,lat:32.72,cached:10060,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36415,to:11528,r:4,er:0.0,lat:32.72,cached:9908,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21464,to:6795,r:2,er:0.0,lat:32.72,cached:5840,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:14821,to:4692,r:2,er:0.0,lat:32.72,cached:4033,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1242479,to:241052,r:0,er:0.0,lat:0.0,cached:594470,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:313412,to:60805,r:0,er:0.0,lat:0.0,cached:149953,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:240210,to:46603,r:0,er:0.0,lat:0.0,cached:114929,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:136092,to:26403,r:0,er:0.0,lat:0.0,cached:65114,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:130036,to:25228,r:0,er:0.0,lat:0.0,cached:62216,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:128072,to:24847,r:0,er:0.0,lat:0.0,cached:61277,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:75489,to:14646,r:0,er:0.0,lat:0.0,cached:36118,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:52127,to:10113,r:0,er:0.0,lat:0.0,cached:24940,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:476406,to:51411,r:0,er:0.0,lat:0.0,cached:105118,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:120172,to:12968,r:0,er:0.0,lat:0.0,cached:26516,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:92104,to:9939,r:0,er:0.0,lat:0.0,cached:20323,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:52182,to:5631,r:0,er:0.0,lat:0.0,cached:11514,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:49860,to:5381,r:0,er:0.0,lat:0.0,cached:11001,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:49107,to:5299,r:0,er:0.0,lat:0.0,cached:10835,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:28945,to:3124,r:0,er:0.0,lat:0.0,cached:6387,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:19987,to:2157,r:0,er:0.0,lat:0.0,cached:4410,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:55843,to:70767,r:1,er:0.0,lat:32.72,cached:3026,think:0,e4:0,e5:0,e429:0,eKnown:1,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:9590,to:32788,r:10,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:530749,to:17427,r:123,er:0.0,lat:8.18,cached:113940,think:0,e4:0,e5:0,e429:0,eKnown:123,lat99:8.35},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:41,to:0,r:0,er:0.0,lat:8.18,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.35},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:1110902,to:66474,r:112,er:0.0,lat:7.76,cached:189332,think:0,e4:0,e5:0,e429:0,eKnown:112,lat99:8.26},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:126903,to:6509,r:22,er:0.0,lat:0.0,cached:64816,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-04": [
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Chưa xác định",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:201382,to:57703,r:36,er:0.0,lat:32.72,cached:45820,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:50798,to:14555,r:9,er:0.0,lat:32.72,cached:11558,think:0,e4:0,e5:0,e429:0,eKnown:9,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:38933,to:11156,r:7,er:0.0,lat:32.72,cached:8858,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:22058,to:6320,r:4,er:0.0,lat:32.72,cached:5019,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:21076,to:6039,r:4,er:0.0,lat:32.72,cached:4795,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:20758,to:5948,r:4,er:0.0,lat:32.72,cached:4723,think:0,e4:0,e5:0,e429:0,eKnown:4,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:12235,to:3506,r:2,er:0.0,lat:32.72,cached:2784,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:0,c:0,ti:8449,to:2421,r:2,er:0.0,lat:32.72,cached:1922,think:0,e4:0,e5:0,e429:0,eKnown:2,lat99:33.39},
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:37402,to:49255,r:10,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 2.5 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:7211,to:21235,r:10,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:10,lat99:8.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:78155,to:3176,r:28,er:0.0,lat:7.03,cached:22326,think:0,e4:0,e5:0,e429:0,eKnown:28,lat99:8.12},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini Embedding 001",ug:"Nhóm CSKH",u:0,c:0,ti:31,to:0,r:0,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:8.12},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:764226,to:52161,r:253,er:0.0,lat:2.04,cached:41972,think:0,e4:0,e5:0,e429:0,eKnown:253,lat99:2.09},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:36206,to:835,r:6,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-05": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:7,er:0.0,lat:32.72,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:7,lat99:33.39},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:0,to:0,r:138,er:0.0,lat:3.96,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:138,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:217,er:0.0,lat:7.03,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:217,lat99:8.12},
    {a:"Trợ lý ảo Ralli",d:"Chưa xác định",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:182688,to:6900,r:34,er:0.0,lat:0.0,cached:64822,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"TT3",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:154803,to:4814,r:32,er:0.0,lat:0.0,cached:85018,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ lý ảo Ralli",d:"Toàn công ty",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:0,c:0,ti:75019,to:1473,r:13,er:0.0,lat:0.0,cached:48643,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ],
  "2026-08-06": [
    {a:"Phân Loại Dữ Liệu CRM",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:5,er:0.0,lat:32.3,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:5,lat99:33.3},
    {a:"Phân Loại Phản Hồi Tiếp Thị",d:"P.NCTT , TTDL&ĐHS",m:"Gemini 2.5 Flash",ug:"Nhóm Dữ liệu",u:0,c:0,ti:0,to:0,r:30,er:0.0,lat:32.3,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:30,lat99:33.3},
    {a:"Chatbot Contact Center",d:"Chăm sóc khách hàng",m:"Gemini 3.0 Flash",ug:"Nhóm CSKH",u:0,c:0,ti:0,to:0,r:36,er:0.0,lat:3.98,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:36,lat99:4.15},
    {a:"Sale Agent",d:"Anh Em tiếp thị",m:"Gemini 2.5 Flash",ug:"Nhóm Kinh doanh",u:0,c:0,ti:0,to:0,r:133,er:0.0,lat:7.97,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:133,lat99:8.3},
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
    {a:"Trợ lý ảo Ralli",d:"Tổng công ty Rạng Đông",m:"Gemini 2.5 Flash Lite",ug:"Nhóm Kinh doanh",u:73,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
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
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Công ty CPBĐ PN Rạng Đông",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:2,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH1",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:8,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH2",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:9,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"Phòng BH3",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:11,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT C4LED",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TT&TMĐT",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:3,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0},
    {a:"Trợ Lý Ảo Hợp Đồng",d:"TTDL&DHS",m:"Gemini 2.5 Pro",ug:"Nhóm Kinh doanh",u:6,c:0,ti:0,to:0,r:0,er:0.0,lat:0.0,cached:0,think:0,e4:0,e5:0,e429:0,eKnown:0,lat99:0.0}
  ]
};
