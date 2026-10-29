-- Sức khỏe agent: giờ chạy, và từng lần chạy kèm tài liệu kết quả JSON.
-- Xem openspec/changes/add-agent-health-tab/design.md D6 và D9.

-- Một dòng duy nhất. `run_at` là giờ VN, `last_run_date` là ngày lịch VN và CHỈ do lịch ghi;
-- lần "Chạy ngay" không đọc, không ghi nó.
CREATE TABLE agent_health_setting (
    id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    run_at time NOT NULL DEFAULT '08:00',
    last_run_date date,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by text
);
INSERT INTO agent_health_setting (id) VALUES (1);

-- `status` nói LẦN CHẠY đã xong chưa, không nói agent khỏe hay không: cái đó ở `result`.
-- `result` là cùng tài liệu với var/agent-checks/<id>/result.json, khuôn ở
-- docs/reference/agent-health-result.md. Service ghi lại cả tài liệu sau MỖI phép kiểm (thanh tiến
-- độ đọc nó), nên lần chạy bị ngắt vẫn giữ các phép kiểm đã xong. Không khoá ngoại tới dim_agent:
-- agent có thể được kiểm trước khi được đăng ký. `result` chứa câu trả lời của agent, có thể là dữ
-- liệu nghiệp vụ: chỉ đọc qua backend có khoá dashboard.
CREATE TABLE agent_health_run (
    id uuid PRIMARY KEY,
    trigger text NOT NULL CHECK (trigger IN ('schedule', 'manual')),
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'done', 'interrupted')),
    total int,
    done int NOT NULL DEFAULT 0,
    current_label text,
    requested_by text,
    requested_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    result jsonb
);
-- Chốt chặn bấm chồng do DATABASE giữ, không do code: tại một thời điểm chỉ có MỘT lần chạy
-- đang chờ hoặc đang chạy. Biểu thức hằng `(true)` làm mọi dòng thoả điều kiện chung một khoá.
CREATE UNIQUE INDEX agent_health_run_one_active
    ON agent_health_run ((true)) WHERE status IN ('queued', 'running');

-- Vai quản trị kết nối chỉ được đổi giờ và xếp một lần "Chạy ngay". Ghi kết quả là việc của
-- service, chạy bằng vai admin của image tools. api_readonly tự có SELECT qua default privileges.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'connection_admin') THEN
        CREATE ROLE connection_admin NOLOGIN;
    END IF;
END $$;
GRANT SELECT, UPDATE ON agent_health_setting TO connection_admin;
GRANT SELECT, INSERT ON agent_health_run TO connection_admin;
