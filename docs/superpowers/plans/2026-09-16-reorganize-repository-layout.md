# Repository Layout Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sắp xếp toàn bộ `token-ledger-dashboard` theo layout hiện có, giữ nguyên các component production và không làm đổi hành vi runtime.

**Architecture:** Giữ nguyên `backend/`, `web/`, `scripts/`, `db/`, `tests/`, `data/` và các thư mục bắt buộc của công cụ. Phân nhóm sâu các diagnostic tool, Gateway smoke harness/report/artifact, runtime snapshot và tài liệu kế hoạch; mọi di chuyển dùng Git rename và đi kèm cập nhật import/path/link.

**Tech Stack:** Git, Python, Node.js, Docker Compose, Markdown/JSON/XML/YAML.

**Spec:** `openspec/specs/project-layout/spec.md`

## Global Constraints

- Không đổi logic nghiệp vụ hoặc runtime chỉ để làm đẹp layout.
- Không di chuyển `backend/`, `web/`, `scripts/`, `db/`, `tests/`, `data/`, `openspec/`, `.agent/`, `.claude/`, `.codex/`.
- Không xóa PostgreSQL volume/database; không chạy `docker compose down -v`.
- Không xóa artifact lịch sử, plan WIP hoặc sketch đã được checkpoint.
- Không sửa nội dung `docs/archive/`; chỉ di chuyển file lịch sử vào đó và cập nhật link từ tài liệu hiện hành.
- Stage chọn lọc; secret scan và `git diff --check` trước mỗi commit.
- Chỉ commit local trên `ChiThanh`; không push nếu chưa được yêu cầu riêng.

---

### Task 1: Dọn root và phân loại planning/runtime artifacts

**Files:**
- Move: `Master Plan API Gateway.xlsx` → `planning/Master Plan API Gateway.xlsx`
- Move: `var/baseline-*.json` → `var/baselines/`
- Move: `var/moc-truoc-change-failed-is-not-free.txt` → `var/snapshots/`
- Modify: `.gitignore`, `README.md`, `docs/reference/cay-thu-muc.md`

**Interfaces:**
- Consumes: project-layout spec.
- Produces: root chỉ còn config cấp repo và component/tool directories; ignore exception theo vị trí mới.

- [ ] Di chuyển bằng `git mv`; cập nhật `.gitignore` exception từ root sang `planning/`.
- [ ] Cập nhật README/cây thư mục để mô tả đúng `planning/`, `var/baselines/`, `var/snapshots/`.
- [ ] Tìm toàn repo và sửa mọi tham chiếu đến đường dẫn cũ.
- [ ] Xác minh `git ls-files` không còn `.xlsx/.docx` ở root và các file runtime nằm đúng nhóm.

### Task 2: Phân nhóm diagnostic tools và Gateway probe

**Files:**
- Move: các file trực tiếp dưới `tools/` (trừ thư mục) → `tools/diagnostics/`
- Keep: `tools/bench/`
- Move: `tools/probe-gateway/` → `tools/probes/gateway/`
- Modify: references trong README/docs/scripts/tests nếu có.

**Interfaces:**
- Consumes: quy tắc `tools/` là diagnostic one-off.
- Produces: `tools/diagnostics/`, `tools/bench/`, `tools/probes/gateway/`, `tools/gateway-smoke/` là bốn nhóm rõ nghĩa.

- [ ] Dùng `git mv` cho toàn bộ loose diagnostic scripts và probe directory.
- [ ] Sửa path trong docs, commands và imports.
- [ ] Chạy `python -m py_compile` cho Python tools và `node --check` cho JavaScript tools.

### Task 3: Tách runtime, harness, report và artifact của Gateway smoke

**Files:**
- Keep entrypoint: `tools/gateway-smoke/run.py`, `README.md`
- Move runtime: `Dockerfile`, `compose*.yaml`, `config.yaml`, `nginx.lb.conf` → `tools/gateway-smoke/runtime/`
- Move harnesses: `*_test.py`, `law_insight_integration.py`, `identity-audit-support/` → `tools/gateway-smoke/harnesses/`
- Move reports: report `.md`, diagram `.html`, `REPORT-INDEX.md` → `tools/gateway-smoke/reports/`
- Move current artifacts: canonical JSON/XML → `tools/gateway-smoke/artifacts/current/`
- Move historical artifacts: superseded OCR/LB JSON → `tools/gateway-smoke/artifacts/history/`

**Interfaces:**
- Consumes: existing `run.py` and harness imports.
- Produces: stable root entrypoint with runtime paths resolved from `Path(__file__)`; harness imports work from repo root or external app cwd.

- [ ] Di chuyển runtime files; sửa `run.py` và Compose `-f` paths.
- [ ] Di chuyển harnesses; sửa sibling imports bằng deterministic path bootstrap tối thiểu, không tạo package abstraction mới.
- [ ] Di chuyển reports/artifacts; sửa mọi relative link theo vị trí mới.
- [ ] Cập nhật `tools/gateway-smoke/README.md` với command mới.
- [ ] Xác minh `python tools/gateway-smoke/run.py --help`, compile toàn bộ harness và `docker compose config` cho base/LB.

### Task 4: Phân tầng tài liệu theo tuổi thọ

**Files:**
- Keep current-state docs in `docs/reference/`.
- Move dated journals/rehearsal/change logs from `docs/reference/` → `docs/archive/gateway/`.
- Move `docs/reference/ban-luu/` → `docs/archive/snapshots/`.
- Remove duplicate `planning/token-ledger-billing-export-test-log.md` only if byte-identical or superseded with provenance; otherwise archive it with an explicit suffix.
- Keep active business documents in `planning/`.

**Interfaces:**
- Consumes: `docs/reference/cay-thu-muc.md` lifetime rules.
- Produces: reference docs describe current system; date-stamped history and backups live under archive.

- [ ] Classify each dated file by content/name; use `git mv`, never delete based on name alone.
- [ ] Do not edit archived document bodies.
- [ ] Update links only in current README/reference/report/index files.
- [ ] Verify every relative Markdown link resolves.

### Task 5: Preserve plans and sketches with explicit ownership

**Files:**
- Keep: `.hermes/plans/` for active/local Hermes plans.
- Keep: `docs/superpowers/plans/` for published implementation plans.
- Move: `sketches/` → `planning/sketches/`.
- Modify: READMEs and links that refer to sketches.

**Interfaces:**
- Consumes: approved decision to include WIP.
- Produces: business/design exploration under `planning/`, agent workflow plans in their tool-owned paths.

- [ ] Move sketches and update references.
- [ ] Document the difference between `.hermes/plans/`, `docs/superpowers/plans/` and `planning/` in `docs/reference/cay-thu-muc.md`.
- [ ] Verify no plan or sketch was dropped.

### Task 6: Repository-wide verification and commit

**Files:**
- Modify only failures caused by path moves.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: behavior-preserving reorganization commit.

- [ ] Run `git diff --check` and staged secret scan.
- [ ] Compile all tracked Python files outside migrations/vendor where appropriate.
- [ ] Run existing Python and Node test suites.
- [ ] Run Docker Compose config validation for root and Gateway smoke files.
- [ ] Programmatically resolve every relative Markdown link in current docs/reports.
- [ ] Check no tracked `__pycache__`/`.pyc`, no office document at root, and no loose file directly under `tools/` except documented entrypoints.
- [ ] Review rename statistics; unexpected content modifications must be explained or reverted.
- [ ] Commit with `refactor(layout): organize repository files by responsibility` and verify HEAD/worktree.
