-- =====================================================================
-- Token Ledger - lớp CORE
-- Nguồn: docs/plan-xay-dung-database-2026-08-07.md mục 4.2 / 4.3 / 4.5
--        docs/mui-gio-2026-08-08.md (quyết định M-A .. M-H)
--
-- 17 bảng + 3 view: 7 dim_ + 6 fact_ + 3 ref_ + account
--   Kế hoạch gốc ghi 12 (5+4+3). Thay đổi so với kế hoạch:
--     + dim_model_alias    ba nguồn gọi tên model theo ba kiểu
--     + fact_perf_daily    hai công tơ của Google không giao nhau
--     + dim_metric_alias   (14/08) ba nguồn gọi TÊN ĐO ĐẠC theo ba kiểu
--     + account            (14/08) ba nguồn ghi "AI DÙNG" theo ba kiểu
--     + fact_latency_daily (14/08) tách khỏi fact_perf_daily: hai chỉ tiêu
--                          đo ở hai độ mịn khác nhau
--
-- BA VIEW, VÀ THỨ TỰ ĐỌC CHÚNG
--   usage_resolved     <- đọc cái này trước. Đã chọn sẵn nguồn, một câu hỏi
--                         một con số. Tên nói rõ điều làm nó khác
--                         fact_usage_daily: nguồn đã được GIẢI QUYẾT.
--   usage_by_account   <- cùng số liệu, nhìn theo tài khoản
--   monitoring_ai      <- fact_monitoring đã lọc, dùng khi cần số liệu thô
--
-- QUY ƯỚC NGÀY: MỌI cột ngày là GIỜ VIỆT NAM (chốt 14/08). Không quy đổi múi
-- giờ ở bất kỳ đâu. Chi tiết ở ghi chú trên fact_billing_daily.
--
-- NGÔN NGỮ: tên bảng / cột / view đều là TIẾNG ANH; ghi chú bằng tiếng Việt.
--
-- LƯU Ý KHI VIẾT SCRIPT ĐỌC BẢNG NÀY: tên agent có dấu tiếng Việt. Console
-- Windows mặc định cp1252 sẽ ném UnicodeEncodeError khi in ra. Gọi
-- sys.stdout.reconfigure(encoding="utf-8") trước khi in.
--
-- CHẠY ĐƯỢC CẢ PostgreSQL LẪN SQLite.
--   Không dùng SERIAL - mọi khoá đều gán tường minh. Lý do không phải để
--   tương thích: dim_agent 8 dòng và dim_model 10 dòng vốn đã gõ tay, nên
--   khoá tự sinh không mang lại gì ngoài việc số ID đổi mỗi lần nạp lại.
--   Nhờ vậy kiểm được toàn bộ khâu nạp bằng SQLite khi Docker chưa chạy.
-- =====================================================================


-- =====================================================================
-- 1. BẢNG DANH MỤC
-- =====================================================================

CREATE TABLE dim_agent (
    agent_id           INT PRIMARY KEY,
    code               TEXT UNIQUE NOT NULL,
    name               TEXT NOT NULL,
    gcp_project_id     TEXT,              -- NULL nếu agent không đi qua GCP
    has_org_tree       BOOLEAN NOT NULL,  -- chỉ TLA HĐ và Ralli (quyết định A1)
    project_created_at DATE,
    data_from          DATE NOT NULL,
    data_to            DATE,              -- NULL = còn chạy
    is_running         BOOLEAN NOT NULL,
    -- Quyết định M-D: Ralli không có billing lẫn monitoring. Cột này tồn tại
    -- để mọi view biết lúc nào phải trả về '-' thay vì '0%'. Không có nó thì
    -- "không đo được" sẽ hiện ra màn hình y hệt "không có lỗi nào".
    --
    -- TÁCH RIÊNG khỏi gcp_project_id (14/08): project `tla-ralli` CÓ tồn tại
    -- trên GCP nhưng CHƯA nối Google Billing. Trước đây cột này được suy ra
    -- bằng `gcp_project_id IS NOT NULL` - gộp hai chuyện vào một phép suy
    -- chính là chỗ từng sai.
    has_google_source  BOOLEAN NOT NULL
);

CREATE TABLE dim_unit (
    unit_id    TEXT PRIMARY KEY,
    agent_id   INT NOT NULL REFERENCES dim_agent,
    name       TEXT NOT NULL,
    parent_id  TEXT REFERENCES dim_unit,
    level      INT,
    path       TEXT,
    -- TRUE với 6 dòng 'Đơn vị sử dụng <agent>' và dòng 'Chưa quy được'.
    -- Thiếu cột này thì COUNT(*) đếm cả dòng kỹ thuật thành phòng ban thật.
    is_technical BOOLEAN NOT NULL
);

-- MỘT DÒNG = MỘT TÀI KHOẢN, không phải một con người ngoài đời.
--
-- VÌ SAO BẢNG NÀY TỒN TẠI (mục 6 của bản rà soát 14/08)
--   Trước đây mỗi nguồn ghi "ai dùng" theo kiểu riêng: Ralli ghi ObjectId của
--   Ralli, TLA HĐ ghi id của TLA HĐ, còn Google thì KHÔNG ghi người nào cả -
--   hoá đơn chỉ biết "cả project này tiêu ngần này". Ba quyển sổ, không có mã
--   chung, nên câu hỏi "tài khoản này tiêu bao nhiêu" phải dò tên bằng tay.
--   Từ đây mọi nơi đều trỏ về account_id.
--
-- KHÔNG dùng tên đăng nhập làm khoá ngoại. Tên đăng nhập là CHUỖI, và đã thấy
-- ba dạng khác nhau cho cùng một tài khoản (hoa/thường, khoảng trắng thừa, và
-- Ralli đôi khi ghi username vào chỗ ObjectId). `username` ở đây đã LOWER+TRIM,
-- giữ lại để tra cứu, nhưng khoá là số.
--
-- BA LOẠI:
--   'real'         tài khoản người thật, từ danh bạ hoặc nhật ký của app
--   'whole_agent'  Google chỉ báo được mức project -> không quy được về ai.
--                  Một dòng cho mỗi agent. KHÔNG phải dữ liệu thiếu: Google
--                  vốn không biết.
--   'unattributed' có lượt gọi nhưng bản ghi không kèm người dùng
-- Thiếu hai loại sau thì khoá của fact_usage_daily phải nhận NULL, mà SQLite
-- coi NULL != NULL nên sẽ âm thầm nhận hai dòng giống hệt nhau.
--
-- ĐƠN VỊ NẰM Ở ĐÂY, KHÔNG ở dim_user (sửa 14/08, đợt rà soát thứ hai)
--   Trước đây account không có cột `unit_id`, nên câu hỏi "người này thuộc
--   đơn vị nào" phải vòng qua dim_user. Mà dim_user có NHIỀU dòng cho cùng
--   một tài khoản, mỗi dòng một đơn vị:
--       longnt        TLA HĐ nói 'Phòng BH1'   Ralli nói 'PBH1'
--       tg.namnh      TLA HĐ nói 'CN Tiền Giang'
--                     Ralli nói 'Đội chuyên trách - CN Tiền Giang'
--       quy.tv@...    TLA HĐ biết đơn vị, Ralli ghi 'Chưa quy được'
--   Đó là cùng một tổ chức được mô hình hoá HAI LẦN, hai cây khác gốc khác độ
--   sâu. 5/932 tài khoản có mặt ở cả hai app và đều vấp phải chuyện này.
--
-- QUY TẮC CHỌN, tất định (xem load_org.py mục 3b):
--   1. bỏ các dòng trỏ vào đơn vị 'Chưa quy được' - trừ khi không còn dòng nào
--   2. còn lại thì lấy đơn vị SÂU NHẤT (`level` lớn nhất). Sâu hơn = cụ thể
--      hơn, và cuộn ngược lên luôn làm được qua parent_id; cuộn xuống thì không
--   3. hoà thì lấy agent_id nhỏ nhất, rồi unit_id theo thứ tự chữ cái
-- `unit_conflict` GIỮ LẠI dấu vết: 1 = các nguồn đã KHÔNG đồng ý, ta vừa chọn
-- hộ. Không có cột này thì việc chọn diễn ra âm thầm.
CREATE TABLE account (
    account_id     INT PRIMARY KEY,
    username       TEXT UNIQUE NOT NULL,   -- đã LOWER(TRIM())
    full_name      TEXT,
    email          TEXT,
    kind           TEXT NOT NULL,          -- 'real' | 'whole_agent' | 'unattributed'
    unit_id        TEXT NOT NULL REFERENCES dim_unit,
    -- Tài khoản DÙNG CHUNG, không đại diện cho một người: 'admin', các tài
    -- khoản thử. Vẫn tính đủ vào token và tiền - lưu lượng của chúng là lưu
    -- lượng thật. Nhưng phải loại khỏi chỉ tiêu TỶ LỆ ÁP DỤNG, vì ở đó mỗi
    -- dòng phải là một người có thể chọn dùng hay không dùng.
    -- Thực tế 14/08: 'admin' một mình tạo 46,4% lưu lượng TLA Hợp Đồng. Tính
    -- nó vào là đẩy tỷ lệ áp dụng lên bằng một tài khoản quản trị.
    -- KHÔNG dùng lại dim_user.is_technical cho việc này: cờ đó khiến dòng
    -- KHÔNG sinh ra account, tức sẽ vứt luôn 33 triệu token đang quy đúng.
    is_shared      INT NOT NULL,                     -- 0 | 1
    -- Ba cột dưới đây gộp từ các dòng dim_user của cùng tài khoản, để giao diện
    -- đọc được BẢNG NGƯỜI DÙNG thẳng từ database. Trước 15/08 chúng chỉ có
    -- trong ralli-users.js - một bản Excel 622 dòng, trong khi database có 937
    -- tài khoản thật, nên 8/15 người có phát sinh request không hiện lên nổi.
    role           TEXT,                  -- vai trò cao nhất trong các app
    is_enabled     BOOLEAN,               -- NULL = app không khai
    created_at     TIMESTAMP,             -- ngày được cấp, NULL = app không khai
    unit_agent_id  INT NOT NULL REFERENCES dim_agent,  -- cây tổ chức của app nào
    unit_conflict  INT NOT NULL            -- 0 | 1
);

CREATE TABLE dim_user (
    user_id      TEXT NOT NULL,
    agent_id     INT NOT NULL REFERENCES dim_agent,
    -- Tài khoản mà dòng này thuộc về. Nhiều dòng dim_user có thể trỏ vào CÙNG
    -- một account: 13 dòng do Ralli ghi hai dạng khoá, 5 dòng do cùng một tên
    -- đăng nhập tồn tại ở cả hai app, 1 dòng do hai tài khoản dùng chung email.
    account_id   INT REFERENCES account,
    username     TEXT NOT NULL,
    full_name    TEXT,
    email        TEXT,
    unit_id      TEXT REFERENCES dim_unit,
    is_enabled   BOOLEAN,
    created_at   TIMESTAMP,
    is_technical BOOLEAN NOT NULL,
    -- 'directory' | 'log' | 'technical'.
    -- Ralli có user_id CHỈ xuất hiện trong nhật ký chứ KHÔNG có trong danh bạ
    -- 890 người: 'system' (6.986 lượt), 'admin' (2 khoá khác nhau, 480 lượt),
    -- 'guest'. Không thể nạp dim_user thuần từ danh bạ được.
    -- 'technical' = 6 dòng sinh ra cho 6 agent một-người-dùng (quyết định A1).
    found_in     TEXT NOT NULL,
    -- Vai trò do CHÍNH APP khai: MEMBER | UNIT_LEAD | COMPANY_ADMIN | ADMIN |
    -- DT | PKH. NULL ở dòng chỉ thấy trong nhật ký và ở 6 dòng kỹ thuật.
    -- Trước 15/08 trường này bị bỏ đi lúc nạp, nên giao diện phải lấy vai trò
    -- từ ralli-users.js - một bản Excel 622 dòng gõ tay. Giữ lại thì bảng người
    -- dùng đọc thẳng được từ database.
    role         TEXT,
    PRIMARY KEY (agent_id, user_id)
);

CREATE TABLE dim_model (
    model_id  INT PRIMARY KEY,
    name      TEXT UNIQUE NOT NULL,   -- tên CHUẨN, dạng gạch ngang
    family    TEXT,
    provider  TEXT NOT NULL
);

-- Ba nguồn gọi tên model theo ba kiểu. Không có bảng này thì phải đoán bằng
-- chuỗi, và 'gemini-embedding-001' với 'gemini-embedding-1.0' không có quy tắc
-- chuẩn hoá nào nói được với nhau.
CREATE TABLE dim_model_alias (
    source    TEXT NOT NULL,          -- 'billing_sku' | 'monitoring' | 'app'
    raw_name  TEXT NOT NULL,
    model_id  INT NOT NULL REFERENCES dim_model,
    PRIMARY KEY (source, raw_name)
);

CREATE TABLE dim_function (
    agent_id       INT NOT NULL REFERENCES dim_agent,
    code           TEXT NOT NULL,
    label          TEXT,
    is_user_facing BOOLEAN,           -- NULL = chưa biết, KHÔNG mặc định true
    PRIMARY KEY (agent_id, code)
);

-- Google đặt tên đo đạc theo kiểu của Google. Bảng này dịch sang từ vựng của
-- ta. Cùng khuôn với dim_model_alias, và sinh ra để chữa cùng một bệnh.
--
-- TRƯỚC KHI CÓ BẢNG NÀY, phân loại là ĐOÁN TÊN ở hai chỗ khác nhau:
--     rules.guess_kind()        regex trên sku_name
--     LIKE '%token_count'       trong build_usage_daily.py
-- Google đổi cách đặt tên thì cả hai đều trả về RỖNG chứ không báo lỗi. Đổi
-- thành bảng tra cứu thì tên lạ sẽ làm khâu nạp DỪNG HẲN - hỏng ồn ào, không
-- hỏng im lặng.
--
-- PHẦN NÀO LẤY TỪ METADATA, PHẦN NÀO VẪN PHẢI ĐỌC TÊN (đo 14/08, xem docs)
--   measures='quota_limit' <- metricKind = GAUGE          metadata quyết định
--   measures='latency'     <- valueType = DISTRIBUTION    metadata quyết định
--   measures='token' hay 'calls'                          metadata KHÔNG phân
--       biệt: cả hai đều DELTA/INT64/unit='1'. Vẫn phải đọc tên - nhưng đọc từ
--       `raw_name` (metric_type, mã API chính thức của Google) chứ KHÔNG phải
--       từ biệt danh do script tự chế.
--   kind='input'/'output'/'cached' cho SKU                catalog KHÔNG có
--       trường nào: cả 597 SKU đều resourceGroup='Gemini', usageType='OnDemand'.
--       Regex trên mô tả là không tránh được, nhưng chạy trên `label`
--       (description chính chủ từ catalog) thay vì trên sku_name trong CSV.
CREATE TABLE dim_metric_alias (
    source       TEXT NOT NULL,   -- 'billing_sku' | 'monitoring'
    raw_name     TEXT NOT NULL,   -- sku_id, hoặc metric_type đầy đủ
    label        TEXT,            -- mô tả chính chủ của Google
    measures     TEXT NOT NULL,   -- 'token' | 'calls' | 'latency' | 'quota_limit'
    kind         TEXT,            -- 'input'|'output'|'cached'; NULL khi không phải token
    metric_kind  TEXT,            -- DELTA | GAUGE          (chỉ nguồn monitoring)
    value_type   TEXT,            -- INT64 | DISTRIBUTION   (chỉ nguồn monitoring)
    PRIMARY KEY (source, raw_name)
);


-- =====================================================================
-- 2. BẢNG SỰ KIỆN
-- Nguyên tắc số một: mỗi nguồn một bảng riêng, không trộn.
-- =====================================================================

-- MỘT dòng = MỘT lượt gọi API. Chỉ Ralli có mức này.
CREATE TABLE fact_call (
    call_id           TEXT PRIMARY KEY,
    agent_id          INT NOT NULL REFERENCES dim_agent,
    ts_raw            TIMESTAMP NOT NULL,   -- chép nguyên, chưa quy đổi
    tz_confirmed      BOOLEAN NOT NULL,     -- TRUE từ 08/08: đã chứng minh là UTC (M2)
    ts_local          TIMESTAMP,            -- giờ Việt Nam
    user_id           TEXT,                 -- khoá GỐC của app, giữ để truy vết
    account_id        INT REFERENCES account,  -- khoá CHUNG, dùng để tính toán
    unit_id           TEXT REFERENCES dim_unit,
    model_id          INT REFERENCES dim_model,
    function_code     TEXT,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT,
    total_tokens      BIGINT NOT NULL,   -- cột chuẩn, KHÔNG tự cộng hai cột trên (quy tắc 6)
    cached_tokens     BIGINT,            -- NULL ở 6.871 dòng cũ, KHÔNG phải 0 (quy tắc 5)
    record_format     SMALLINT           -- 1 / 2 / 3
);

-- Chiều người dùng của app KHÔNG phơi log từng lượt gọi.
--
-- Ralli phơi `db-token_usage-raw.json` - từng lượt một - nên vào fact_call, gộp
-- ra ngày nào cũng được. TLA Hợp Đồng chỉ phơi API đã tổng hợp sẵn, mức mịn
-- nhất lấy được là (ngày x người x model). Không có bảng này thì hoặc phải bịa
-- ra những lượt gọi giả để nhét vào fact_call, hoặc phải bỏ hẳn chiều người
-- dùng của TLA HĐ - trước 14/08 là phương án thứ hai, và hậu quả là biểu đồ tỷ
-- lệ áp dụng báo 0/39 trong khi sự thật là "có người dùng, không nhìn thấy ai".
--
-- Hai đường cùng đổ về fact_usage_daily source='app'. Xem build_usage_daily.py.
--
-- model_id để NULL ĐƯỢC, giống fact_call: app đôi khi không nói model (2 lượt
-- tên 'none', 2 lượt của một tài khoản đã xoá nên không lọc riêng được). Vì
-- vậy khoá chính là số thứ tự gán tường minh chứ không phải bộ khoá tự nhiên -
-- PostgreSQL cấm NULL trong khoá chính, SQLite thì cho, và đó đúng là kiểu
-- khác biệt chỉ lộ ra lúc đổi hệ.
CREATE TABLE fact_app_daily (
    row_id            INT PRIMARY KEY,
    day               DATE NOT NULL,
    agent_id          INT NOT NULL REFERENCES dim_agent,
    account_id        INT NOT NULL REFERENCES account,
    model_id          INT REFERENCES dim_model,   -- NULL = app không nói model
    raw_model         TEXT,                       -- tên gốc, giữ để truy vết
    calls             INT NOT NULL,
    total_tokens      BIGINT NOT NULL,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT
);

-- QUY ƯỚC NGÀY (chốt 14/08): MỌI cột ngày trong database này là GIỜ VIỆT NAM.
-- Google cắt ngày hoá đơn theo giờ Thái Bình Dương; ta coi luôn là giờ VN,
-- không quy đổi. Tổng cả kỳ vẫn tuyệt đối đúng. Cái phải biết: ngày CUỐI CÙNG
-- luôn hụt, và mỗi ngày lẫn khoảng 15 giờ của ngày kề bên. Đủ để theo xu
-- hướng, không đủ để đối chiếu một ngày lẻ với nguồn khác.
CREATE TABLE fact_billing_daily (
    day        DATE NOT NULL,
    -- agent_id là khoá CHUẨN. `project` giữ lại để truy vết về GCP.
    -- Trước đây chỉ có `project`, nên mọi truy vấn phải nhớ viết
    -- `JOIN dim_agent ON gcp_project_id = project`; quên là mất dòng mà không
    -- có lỗi nào báo. Ánh xạ vốn đã đầy đủ (2.377/2.377), chỉ là chưa ai áp vào.
    agent_id   INT NOT NULL REFERENCES dim_agent,
    project    TEXT NOT NULL,
    sku_id     TEXT NOT NULL,
    sku_name   TEXT NOT NULL,
    model_id   INT REFERENCES dim_model,
    kind       TEXT NOT NULL,        -- 'input' | 'output' | 'cached'
    quantity   BIGINT NOT NULL,      -- số token
    cost_usd   NUMERIC(14,6) NOT NULL,
    PRIMARY KEY (day, project, sku_id)
);

CREATE TABLE fact_monitoring (
    ts_utc          TIMESTAMP NOT NULL,
    ts_local        TIMESTAMP NOT NULL,   -- giờ Việt Nam
    agent_id        INT NOT NULL REFERENCES dim_agent,   -- khoá CHUẨN
    project         TEXT NOT NULL,                       -- giữ để truy vết
    metric_nickname TEXT NOT NULL,        -- biệt danh do pull_monitoring tự đặt
    -- Mã CHÍNH CHỦ của Google, ví dụ
    --   generativelanguage.googleapis.com/quota/generate_content_paid_tier_3_input_token_count/usage
    -- Cột này CÓ trong file cào nhưng trước đây bị vứt lúc nạp, chỉ giữ lại
    -- biệt danh. Nghĩa là thứ duy nhất có cam kết ổn định thì bỏ, còn thứ do
    -- mình tự chế thì giữ. Nối vào dim_metric_alias bằng chính cột này.
    metric_type     TEXT,
    -- NULL vì phép đo dạng request không có nhãn `model`. Tỷ lệ PHỤ THUỘC TẬP:
    -- 85,6% trên bảng thô (450.138/525.639, phần lớn là Drive), 39,6% trong
    -- view monitoring_ai (33.734/85.166). Con số hay được trích dẫn là 39,6%.
    model_id        INT REFERENCES dim_model,
    response_code   TEXT,
    service         TEXT NOT NULL,        -- quy tắc 9: res_service, rỗng thì lấy tiền tố metric_type
    method          TEXT,
    credential_id   TEXT,                 -- cùng phút cùng method vẫn có nhiều chuỗi nếu nhiều API key
    -- TRUE với hạn mức quota: ALIGN_MAX, KHÔNG được SUM.
    -- Trước suy từ hậu tố '_limit' của tên; giờ đối chiếu được với metadata:
    -- mọi phép đo hạn mức đều metricKind=GAUGE, mọi công tơ đều DELTA (5/5, 9/9).
    is_quota_limit  BOOLEAN NOT NULL,
    -- Ba nhãn nữa có trong file cào mà trước đây bị bỏ. `thinking_enabled`
    -- đáng kể nhất: dashboard có cột "think" mà database không có nguồn nào -
    -- nguồn chính là đây.
    thinking_enabled TEXT,
    output_modality  TEXT,
    limit_name       TEXT,
    value           DOUBLE PRECISION NOT NULL,
    unit            TEXT
);

-- BẢNG ĐỐI CHỨNG. Đọc để SO SÁNH ba nguồn với nhau, KHÔNG phải để hỏi một con
-- số. Muốn một con số thì đọc view `usage_resolved` ở cuối file.
--
-- Cột `source` cho phép cùng một ngày có nhiều con số từ nhiều nguồn mà không
-- đè lên nhau - chính là cách phát hiện ra app ghi thiếu 17%. Nhưng vì `source`
-- nằm trong KHOÁ CHÍNH, ai hỏi bảng này cũng phải tự chọn nguồn trước. Đó là
-- việc của view chứ không phải của người hỏi.
--
-- MỌI CỘT KHOÁ ĐỀU NOT NULL. Ban đầu để unit_id/user_id/model_id nhận NULL, và
-- đó là một cái bẫy im lặng:
--   PostgreSQL  PRIMARY KEY => NOT NULL, sẽ TỪ CHỐI dòng billing đầu tiên
--   SQLite      cho phép NULL trong khoá chính, và coi NULL != NULL, nên NHẬN
--               CẢ HAI DÒNG GIỐNG HỆT NHAU. Đã thử, nó nhận thật.
-- Cách chữa: dùng dòng kỹ thuật ở dim_unit/account thay cho NULL.
--   model_id KHÔNG cần dòng kỹ thuật - đã kiểm, cả 3 phép đo token đều có nhãn
--   model. Phép đo thiếu model (api/request_count, latencies) thuộc về
--   fact_perf_daily chứ không vào đây.
--
-- KHÔNG CÓ CỘT `unit_id` - và đó là cố ý (sửa 14/08).
--   Đơn vị là thuộc tính CỦA TÀI KHOẢN, suy ra được bằng JOIN account. Chép
--   thêm một bản sao vào đây thì hai bản có thể lệch nhau, và đúng cái lệch đó
--   là thứ vừa phải đi dọn ở trên. Bỏ hẳn cột thì không còn chỗ để lệch.
--   Đã kiểm trước khi bỏ: 1.715 dòng, bỏ unit_id khỏi khoá chính vẫn ra đúng
--   1.715 tổ hợp - không dòng nào bị gộp mất.
--   Muốn đơn vị thì: JOIN account a ON a.account_id = f.account_id -> a.unit_id
CREATE TABLE fact_usage_daily (
    day           DATE NOT NULL,      -- giờ Việt Nam, như mọi cột ngày khác
    agent_id      INT NOT NULL REFERENCES dim_agent,
    model_id      INT NOT NULL REFERENCES dim_model,
    -- Trước đây là `user_id TEXT` - khoá RIÊNG của từng app, mỗi app một kiểu.
    -- Giờ là khoá CHUNG. Đổi kéo theo một việc đúng: 19 dòng dim_user vốn là
    -- cùng một tài khoản ghi hai lần giờ gộp lại thật, nên khâu nạp phải
    -- GROUP BY account_id chứ không chèn thẳng, nếu không sẽ đụng khoá chính.
    account_id    INT NOT NULL REFERENCES account,
    calls         INT,
    total_tokens  BIGINT,
    -- TÁCH VÀO / RA / CACHE (thêm 14/08, vì màn hình cần nó để vẽ)
    --
    -- CÁI BẪY: 'cached' KHÔNG cùng nghĩa ở ba nguồn. Đã đo, không phải suy:
    --   billing     cached là SKU RIÊNG, nằm NGOÀI input. Cộng cả ba mới ra
    --               total: 413.450.261 + 57.923.992 + 224.609.584 = 695.983.837
    --   app         cached là một phần CỦA prompt_tokens (Gemini trả về
    --               cachedContentTokenCount như tập con của promptTokenCount).
    --               Cộng vào là đếm hai lần.
    --   monitoring  KHÔNG có phép đo cached nào -> luôn NULL
    -- Vì vậy total_tokens giữ nguyên theo QUY ƯỚC CỦA NGUỒN, và cột `source`
    -- cho biết đang đọc quy ước nào. Ép ba nguồn về một định nghĩa sẽ làm sai
    -- một trong hai đầu, mà không đầu nào kêu.
    input_tokens  BIGINT,
    output_tokens BIGINT,
    cached_tokens BIGINT,
    cost_usd      NUMERIC(14,6),
    source        TEXT NOT NULL,      -- 'app' | 'billing' | 'monitoring'
    PRIMARY KEY (day, agent_id, model_id, account_id, source)
);

-- TÁCH LÀM HAI BẢNG (14/08). Bản trước gộp số lượt và độ trễ vào một bảng với
-- khoá (ngày, agent, method, response_code) - và đó là lý do nó nằm rỗng từ
-- đầu đến giờ: KHÔNG CÓ dữ liệu nào đúng độ mịn ấy.
--   số lượt   có response_code, có method  -> 578 dòng
--   độ trễ    KHÔNG có response_code. Và con số độ trễ ĐÚNG chỉ tồn tại ở mức
--             (ngày, agent): phân vị không cộng được, phải gộp histogram rồi
--             mới đọc mốc - xem scripts/merge_latency_daily.py.
-- Nhét cả hai vào một khoá thì hoặc phải bịa response_code cho độ trễ, hoặc
-- phải lấy trung bình các p95 từng phút. Cách thứ hai đã đo thử: lệch trên 19%.
CREATE TABLE fact_perf_daily (
    day           DATE NOT NULL,      -- giờ Việt Nam
    agent_id      INT NOT NULL REFERENCES dim_agent,
    method        TEXT NOT NULL,
    response_code TEXT NOT NULL,      -- '200' | '429' | '503' ...
    calls         INT NOT NULL,
    PRIMARY KEY (day, agent_id, method, response_code)
);

-- Độ trễ ở ĐÚNG độ mịn mà Google cho: một con số cho mỗi (ngày, agent).
--
-- Hai cột `p95_bucket_*` là bề rộng ô chứa phân vị: histogram gộp lại thì
-- chính xác, nhưng đọc một phân vị ra vẫn phải nội suy trong ô, mà ô rộng gấp
-- đôi sau mỗi bậc. Trung vị bề rộng = 57% của chính giá trị p95. Dashboard
-- phải hiện KHOẢNG, không phải số lẻ.
CREATE TABLE fact_latency_daily (
    day             DATE NOT NULL,    -- giờ Việt Nam
    agent_id        INT NOT NULL REFERENCES dim_agent,
    samples         INT NOT NULL,     -- số mẫu vào histogram của ngày đó
    p50_seconds     DOUBLE PRECISION,
    p95_seconds     DOUBLE PRECISION,
    p95_bucket_from DOUBLE PRECISION,
    p95_bucket_to   DOUBLE PRECISION,
    p99_seconds     DOUBLE PRECISION,
    enough_samples  BOOLEAN NOT NULL, -- FALSE khi samples < 10: phân vị vô nghĩa
    PRIMARY KEY (day, agent_id)
);


-- =====================================================================
-- 3. BẢNG THAM CHIẾU (quy ước do NGƯỜI quyết định, không phải đo được)
-- =====================================================================

CREATE TABLE ref_price (
    model_id       INT NOT NULL REFERENCES dim_model,
    effective_from DATE NOT NULL,
    price_input    NUMERIC(12,8),       -- USD / 1 triệu token
    price_output   NUMERIC(12,8),
    price_cached   NUMERIC(12,8),
    source         TEXT NOT NULL,       -- 'derived' | 'google' | 'vendor'
    PRIMARY KEY (model_id, effective_from)
);

CREATE TABLE ref_fx (
    day          DATE PRIMARY KEY,
    vnd_per_usd  NUMERIC(12,2) NOT NULL,
    source       TEXT NOT NULL        -- 'hardcoded' cho đến khi kéo API (M-F)
);

CREATE TABLE ref_budget (
    agent_id      INT NOT NULL REFERENCES dim_agent,
    month         DATE NOT NULL,
    budget_usd    NUMERIC(12,2),
    -- Ralli bị chặn theo TOKEN (50.000.000/tháng), 6 agent kia theo TIỀN.
    -- Không quy đổi: quy ra USD thì ngân sách trôi mỗi lần bảng giá đổi, trong
    -- khi Ralli đang bị chặn theo token thật.
    budget_tokens BIGINT,
    PRIMARY KEY (agent_id, month),
    CHECK (budget_usd IS NOT NULL OR budget_tokens IS NOT NULL)
);


-- =====================================================================
-- 4. VIEW
-- =====================================================================

-- Quyết định M-A: nạp ĐỦ 525.639 dòng, lọc ở tầng view.
-- Bảng thô giữ cả lưu lượng Drive/Sheets/Compute vì chính nó là bằng chứng cho
-- quy tắc 3 (pro-tuner sai 45,7 lần nếu quên lọc). View này là cửa duy nhất
-- nên đi qua khi tính toán.
CREATE VIEW monitoring_ai AS
SELECT *
FROM fact_monitoring
WHERE service = 'generativelanguage.googleapis.com'
  AND is_quota_limit = FALSE;

-- =====================================================================
-- usage_resolved - CỬA CHÍNH ĐỂ HỎI SỐ LIỆU
--
-- Đây là cái fact_usage_daily lẽ ra phải là. Bảng đó để ba nguồn cạnh nhau và
-- bắt người hỏi tự chọn; view này CHỌN SẴN, và nói rõ nó đã chọn gì. Tên
-- 'resolved' là để nói đúng điều đó: nguồn đã được giải quyết.
--
-- CHỌN THEO TỪNG CHỈ TIÊU, không phải theo từng dòng. Mỗi nguồn mạnh một thứ:
--     tiền        chỉ billing có
--     token       billing trước, thiếu thì monitoring, thiếu nữa thì app
--                 (đo 13/08: hai nguồn khớp 100,4% khi cắt cùng khoảng ngày,
--                  nên thay thế là hợp lệ. Trước đó tưởng lệch 4,2 lần - đó là
--                  do so 111 ngày monitoring với 223 ngày hoá đơn.)
--     lượt gọi    monitoring trước, thiếu thì app; billing không có
--     người dùng  chỉ app có
--
-- VÌ SAO KHÔNG CỘNG BA NGUỒN LẠI: chúng đo CÙNG một lưu lượng bằng ba cái công
-- tơ khác nhau. Cộng lại là đếm ba lần.
--
-- HAI CỘT `*_source` LÀ BẮT BUỘC, không phải trang trí. Một con số token của
-- hôm nay đến từ monitoring (ước tính, hoá đơn chưa về) trông y hệt con số của
-- tuần trước đến từ hoá đơn. Không có cột này thì không phân biệt được.
--
-- Ralli (agent_id=8) luôn rơi về 'app': project tla-ralli chưa nối billing trên
-- GCP nên không có dòng billing lẫn monitoring nào. COALESCE tự lo việc đó,
-- không cần trường hợp riêng.
-- =====================================================================
CREATE VIEW usage_resolved AS
WITH keys AS (
    SELECT DISTINCT day, agent_id, model_id FROM fact_usage_daily
),
b AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(cost_usd) AS cost, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'billing'
    GROUP BY day, agent_id, model_id
),
m AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'monitoring'
    GROUP BY day, agent_id, model_id
),
a AS (
    SELECT day, agent_id, model_id,
           SUM(total_tokens) AS tokens, SUM(calls) AS calls,
           SUM(input_tokens) AS tok_in, SUM(output_tokens) AS tok_out,
           SUM(cached_tokens) AS tok_cached
    FROM fact_usage_daily WHERE source = 'app'
    GROUP BY day, agent_id, model_id
)
SELECT k.day,
       k.agent_id,
       k.model_id,
       COALESCE(b.tokens, m.tokens, a.tokens)  AS total_tokens,
       -- Ba cột này lấy từ CÙNG nguồn với total_tokens, không COALESCE riêng
       -- từng cột: trộn input_tokens của hoá đơn với output_tokens của
       -- monitoring sẽ ra một cặp số không kỳ nguồn nào từng báo cáo.
       CASE WHEN b.tokens IS NOT NULL THEN b.tok_in
            WHEN m.tokens IS NOT NULL THEN m.tok_in
            ELSE a.tok_in     END               AS input_tokens,
       CASE WHEN b.tokens IS NOT NULL THEN b.tok_out
            WHEN m.tokens IS NOT NULL THEN m.tok_out
            ELSE a.tok_out    END               AS output_tokens,
       CASE WHEN b.tokens IS NOT NULL THEN b.tok_cached
            WHEN m.tokens IS NOT NULL THEN m.tok_cached
            ELSE a.tok_cached END               AS cached_tokens,
       b.cost                                   AS cost_usd,
       COALESCE(m.calls, a.calls)               AS calls,
       CASE WHEN b.tokens IS NOT NULL THEN 'billing'
            WHEN m.tokens IS NOT NULL THEN 'monitoring'
            WHEN a.tokens IS NOT NULL THEN 'app'   END AS token_source,
       CASE WHEN m.calls  IS NOT NULL THEN 'monitoring'
            WHEN a.calls  IS NOT NULL THEN 'app'   END AS call_source,
       -- 1 = con số này chưa được hoá đơn xác nhận
       CASE WHEN b.tokens IS NULL THEN 1 ELSE 0 END   AS token_estimated
FROM keys k
LEFT JOIN b ON b.day = k.day AND b.agent_id = k.agent_id AND b.model_id = k.model_id
LEFT JOIN m ON m.day = k.day AND m.agent_id = k.agent_id AND m.model_id = k.model_id
LEFT JOIN a ON a.day = k.day AND a.agent_id = k.agent_id AND a.model_id = k.model_id;


-- Cùng số liệu, nhìn theo người dùng. CHỈ phủ phần có nguồn 'app' - hiện là
-- 5,7% tổng token, vì Google không ghi ai gọi.
--
-- `unit_id` và `path` lấy từ account, KHÔNG từ fact - xem ghi chú ở hai bảng
-- đó. Một tài khoản một đơn vị, không còn chuyện cùng một người ra hai phòng
-- ban tuỳ dòng.
CREATE VIEW usage_by_account AS
SELECT f.day, f.agent_id, f.model_id,
       a.unit_id, u.path AS unit_path, a.unit_conflict, a.is_shared,
       f.account_id, a.username, a.full_name, a.email,
       f.calls, f.total_tokens, f.input_tokens, f.output_tokens
FROM fact_usage_daily f
JOIN account a ON a.account_id = f.account_id
JOIN dim_unit u ON u.unit_id = a.unit_id
WHERE f.source = 'app' AND a.kind = 'real';
