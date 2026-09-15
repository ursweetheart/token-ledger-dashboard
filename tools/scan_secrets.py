"""Quét bí mật lọt vào repo — theo HÌNH DẠNG, không theo chuỗi biết trước.

Vì sao tồn tại file này
-----------------------
Ngày 26/08/2026 phép kiểm 6.7 quét đúng HAI chuỗi khoá Google đã biết, ra "0 file",
và trông y hệt một phép kiểm đạt. Nó bỏ lọt `JWT_test_for_header` — một Bearer token
thật nằm ở gốc repo, ngoài .gitignore. Bí mật đó thuộc một LOẠI khác, nên tìm theo
chuỗi không bao giờ thấy.

Quét theo hình dạng thì không cần biết trước bí mật trông như thế nào.

Không bao giờ in giá trị bắt được. Chỉ in: đường dẫn, số dòng, tên loại, độ dài.

Chạy:
    python tools/scan_secrets.py
    python tools/scan_secrets.py --root D:/RangDonk/token-ledger-dashboard

Mã thoát:  0 = sạch   1 = có phát hiện nghiêm trọng   2 = lỗi khi chạy
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# --- Hình dạng bí mật -------------------------------------------------------
# Mỗi mục: (tên để đọc, biểu thức). Thêm một loại bí mật mới = thêm một dòng.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("JWT (3 base64url segments)", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("sk- style key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("Google OAuth client secret", re.compile(r"GOCSPX-[A-Za-z0-9_-]{20,}")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Password embedded in URL", re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:([^/\s@]+)@")),
]

# Mật khẩu mặc định CỤC BỘ, đã công khai trong docker-compose.yml và .env.example.
# Bắt được thì ghi nhận là "đã biết", không tính là phát hiện nghiêm trọng.
# Danh sách này CÓ CHỦ ĐÍCH là ngắn. Dài thêm một dòng nghĩa là mở thêm một chỗ mù.
LOCAL_DEFAULT_PASSWORDS = {
    "token_local", "probe_local", "llmproxy_local", "redis_local", "admin_local",
}

# Đuôi file không phải văn bản — đọc vào chỉ ra rác.
SKIP_EXTENSIONS = {
    ".xlsx", ".xls", ".docx", ".doc", ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".ico", ".zip", ".gz", ".sqlite", ".db", ".pyc", ".woff", ".woff2", ".ttf",
}

# Thư mục không quét.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv"}

# `.env` ĐƯỢC PHÉP chứa khoá — đó là chỗ của nó. Kiểm riêng ở bước 3.
NEVER_SCAN = {".env"}

MAX_BYTES = 4 * 1024 * 1024


# Dấu đã-che phải khớp TOÀN BỘ chuỗi, không phải khớp tiền tố.
#
# Bản đầu viết `password.startswith(("*", "<", "x"))`. Ký tự `x` biến mọi mật khẩu
# thật bắt đầu bằng `x` thành "đã che" — `xK9fTq2m` lọt sạch. Khoảng 1/36 mật khẩu
# ngẫu nhiên rơi vào lỗ đó, trong đúng công cụ sinh ra để không có lỗ nào.
# Phát hiện lúc tự soát 27/08/2026.
MASKED_PLACEHOLDER = re.compile(r"\*+|x{3,}|X{3,}|\.{3,}|-{3,}|<[^>]*>|\$\{[^}]*\}", re.ASCII)


def classify_password(password: str) -> str | None:
    """Mật khẩu bắt được trong URL có phải bí mật thật không.

    Trả về None nếu là bí mật thật; trả về LÝ DO nếu được phép bỏ qua.
    Bỏ qua ở đây là bỏ qua CÓ LÝ DO GHI RA, không phải bỏ qua cả file —
    thêm một file vào danh sách trắng là mở một chỗ mù vĩnh viễn.
    """
    if "$" in password or "{" in password or "}" in password:
        return "variable reference, not a value"
    if MASKED_PLACEHOLDER.fullmatch(password) or password.upper() in {"REDACTED", "PASSWORD", "PASS"}:
        return "already masked"
    if password in LOCAL_DEFAULT_PASSWORDS:
        return "local default password, already public"
    if len(password) <= 3:
        return "too short, an example in prose"
    return None


def iter_text_files(root: Path):
    """Sinh từng file văn bản đang nằm trong repo."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if path.name in NEVER_SCAN or path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        yield path


def scan_file(path: Path, root: Path) -> list[tuple[str, int, str, int, str | None]]:
    """Trả về [(đường dẫn, số dòng, tên loại, độ dài bắt được, lý do bỏ qua)].

    `lý do bỏ qua` là None nghĩa là phát hiện NGHIÊM TRỌNG.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return []

    results = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            for match in pattern.finditer(line):
                reason = None
                if match.groups():          # chỉ hình dạng URL mới bắt nhóm mật khẩu
                    reason = classify_password(match.group(1))
                results.append(
                    (str(path.relative_to(root)).replace("\\", "/"), line_no, name,
                     len(match.group(0)), reason)
                )
    return results


def git_is_clean(repo: Path) -> tuple[bool, int, str]:
    """git status --porcelain: 0 dòng nghĩa là không file nào thêm hay sửa."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, -1, f"could not run git: {exc}"
    if proc.returncode != 0:
        return False, -1, proc.stderr.strip()[:200]
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return len(lines) == 0, len(lines), ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repo to scan")
    parser.add_argument("--fork", default="../litellm_tuan_test",
                        help="LiteLLM fork, relative to --root; only its git status is checked")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        print(f"ERROR: {root} is not a git repo", file=sys.stderr)
        return 2

    print(f"Scanning: {root}")
    print(f"Secret shapes: {len(PATTERNS)}\n")

    # --- 1. Quét toàn bộ file văn bản trong repo ---------------------------
    findings: list[tuple[str, int, str, int, str | None]] = []
    skipped: list[tuple[str, int, str, int, str | None]] = []
    file_count = 0
    for path in iter_text_files(root):
        file_count += 1
        for result in scan_file(path, root):
            (skipped if result[4] else findings).append(result)

    print(f"== 1/3  shape scan -- {file_count} text files")
    if findings:
        print(f"   {len(findings)} SERIOUS FINDINGS (values not printed):")
        for rel_path, line_no, name, length, _ in findings:
            print(f"     {rel_path}:{line_no}  [{name}]  {length} chars")
    else:
        print("   0 serious findings -- pass")
    if skipped:
        print(f"   {len(skipped)} matches skipped, each with a reason:")
        by_reason: dict[str, int] = {}
        for *_, reason in skipped:
            by_reason[reason or "?"] = by_reason.get(reason or "?", 0) + 1
        for reason, count in sorted(by_reason.items(), key=lambda item: -item[1]):
            print(f"     {count:>3}  {reason}")

    # --- 2. Fork phải không có file nào thêm hay sửa ------------------------
    fork = (root / args.fork).resolve()
    print(f"\n== 2/3  fork: {fork}")
    if not fork.exists():
        print("   fork not found -- SKIPPED (does not count as pass)")
        fork_ok = False
    else:
        clean, count, error = git_is_clean(fork)
        if error:
            print(f"   could not check: {error}")
            fork_ok = False
        else:
            print(f"   git status --porcelain = {count} lines  ->  " +
                  ("clean, no files added" if clean else "FILES CHANGED"))
            fork_ok = clean

    # --- 3. .env: không quét nội dung, chỉ ghi dấu vân tay ------------------
    print("\n== 3/3  .env (may hold keys, fingerprint only)")
    env_file = root / ".env"
    if env_file.exists():
        digest = hashlib.sha256(env_file.read_bytes()).hexdigest()
        print(f"   exists, {env_file.stat().st_size} bytes")
        print(f"   sha256 {digest}")
        print("   -> compare with the previous scan to see whether .env changed")
        is_ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", ".env"],
            capture_output=True, timeout=30,
        ).returncode == 0
        print(f"   in .gitignore: {'yes -- pass' if is_ignored else 'NO -- FAIL'}")
        if not is_ignored:
            findings.append((".env", 0, "not gitignored", 0, None))
    else:
        print("   no .env")

    print()
    if findings or not fork_ok:
        print("RESULT: FAIL")
        return 1
    print("RESULT: pass -- no secrets leaked into the repo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
