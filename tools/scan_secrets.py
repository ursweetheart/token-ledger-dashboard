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
    python tools/scan_secrets.py --goc D:/RangDonk/token-ledger-dashboard

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
    ("JWT (3 doan base64url)", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("Khoa Google API", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("Khoa kieu sk-", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("Google OAuth client secret", re.compile(r"GOCSPX-[A-Za-z0-9_-]{20,}")),
    ("Khoi private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Mat khau nhung trong URL", re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:([^/\s@]+)@")),
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
        return "tham chieu bien, khong phai gia tri"
    if MASKED_PLACEHOLDER.fullmatch(password) or password.upper() in {"REDACTED", "PASSWORD", "PASS"}:
        return "da che san"
    if password in LOCAL_DEFAULT_PASSWORDS:
        return "mat khau mac dinh cuc bo, da cong khai"
    if len(password) <= 3:
        return "qua ngan, la vi du trong van xuoi"
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
        return False, -1, f"khong chay duoc git: {exc}"
    if proc.returncode != 0:
        return False, -1, proc.stderr.strip()[:200]
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return len(lines) == 0, len(lines), ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goc", default=".", help="thu muc repo du an")
    parser.add_argument("--fork", default="../litellm_rang_dong", help="repo fork LiteLLM")
    args = parser.parse_args()

    root = Path(args.goc).resolve()
    if not (root / ".git").exists():
        print(f"LOI: {root} khong phai mot repo git", file=sys.stderr)
        return 2

    print(f"Quet: {root}")
    print(f"Hinh dang tim: {len(PATTERNS)} loai\n")

    # --- 1. Quét toàn bộ file văn bản trong repo ---------------------------
    findings: list[tuple[str, int, str, int, str | None]] = []
    skipped: list[tuple[str, int, str, int, str | None]] = []
    file_count = 0
    for path in iter_text_files(root):
        file_count += 1
        for result in scan_file(path, root):
            (skipped if result[4] else findings).append(result)

    print(f"== 1/3  quet hinh dang -- {file_count} file van ban")
    if findings:
        print(f"   {len(findings)} PHAT HIEN NGHIEM TRONG (khong in gia tri):")
        for rel_path, line_no, name, length, _ in findings:
            print(f"     {rel_path}:{line_no}  [{name}]  {length} ky tu")
    else:
        print("   0 phat hien nghiem trong -- dat")
    if skipped:
        print(f"   {len(skipped)} khop duoc bo qua, tung cai co ly do:")
        by_reason: dict[str, int] = {}
        for *_, reason in skipped:
            by_reason[reason or "?"] = by_reason.get(reason or "?", 0) + 1
        for reason, count in sorted(by_reason.items(), key=lambda item: -item[1]):
            print(f"     {count:>3}  {reason}")

    # --- 2. Fork phải không có file nào thêm hay sửa ------------------------
    fork = (root / args.fork).resolve()
    print(f"\n== 2/3  fork: {fork}")
    if not fork.exists():
        print("   khong tim thay fork -- BO QUA (khong tinh la dat)")
        fork_ok = False
    else:
        clean, count, error = git_is_clean(fork)
        if error:
            print(f"   khong kiem duoc: {error}")
            fork_ok = False
        else:
            print(f"   git status --porcelain = {count} dong  ->  " +
                  ("sach, khong file nao them" if clean else "CO FILE THAY DOI"))
            fork_ok = clean

    # --- 3. .env: không quét nội dung, chỉ ghi dấu vân tay ------------------
    print("\n== 3/3  .env (duoc phep chua khoa, chi ghi dau van tay)")
    env_file = root / ".env"
    if env_file.exists():
        digest = hashlib.sha256(env_file.read_bytes()).hexdigest()
        print(f"   ton tai, {env_file.stat().st_size} byte")
        print(f"   sha256 {digest}")
        print("   -> so con so nay voi lan quet truoc de biet .env co doi khong")
        is_ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", ".env"],
            capture_output=True, timeout=30,
        ).returncode == 0
        print(f"   nam trong .gitignore: {'co -- dat' if is_ignored else 'KHONG -- HONG'}")
        if not is_ignored:
            findings.append((".env", 0, "khong duoc gitignore", 0, None))
    else:
        print("   khong co .env")

    print()
    if findings or not fork_ok:
        print("KET LUAN: KHONG DAT")
        return 1
    print("KET LUAN: dat -- khong bi mat nao lot vao repo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
