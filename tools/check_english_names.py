"""Chặn tiếng Việt quay lại tên tệp, cờ dòng lệnh, định danh và chuỗi trong code.

Vì sao tồn tại file này
-----------------------
Quy ước từ 14/08/2026: định danh tiếng Anh, ghi chú tiếng Việt. Đo ngày 15/09/2026 thì code chỉ theo
được một nửa: khoảng 40 cờ tiếng Việt, 20 tên tệp tiếng Việt, hàng trăm chuỗi in ra có dấu. Cờ `--goc`
không đoán được nghĩa. Sửa tay một lần mà không có gì canh thì sẽ trôi lại.
Xem openspec/changes/name-the-code-in-english/design.md, mục D5.

Năm phép, chỉ dùng thư viện chuẩn:
  1. tên tệp          tách theo _ - . ; có mảnh trong danh sách từ tiếng Việt -> hỏng
  2. cờ dòng lệnh     chuỗi bắt đầu bằng "-" trong add_argument(...)
  3. định danh        hàm, lớp, tham số, biến gán, thuộc tính gán, tên tham số khi gọi
  4. chuỗi            có chữ có dấu -> hỏng; không dấu mà có >= 2 từ tiếng Việt -> hỏng
                      không xét docstring và chuỗi đứng một mình thành câu lệnh;
                      chuỗi SQL thì bỏ comment `--` trước khi xét
  5. viết tắt cờ      mọi ArgumentParser(...) phải có allow_abbrev=False

Được giữ tiếng Việt: comment, docstring, và dòng có `# vi-ok: <lý do>`. Chuỗi nhiều dòng thì dấu nằm ở
dòng nào trong chuỗi cũng được. Dấu không có lý do thì chính nó hỏng. KHÔNG có danh sách tệp miễn trừ.

Giới hạn đã biết: chuỗi không dấu được bắt theo danh sách từ, nên câu toàn từ không có trong danh sách sẽ
lọt. Thấy lọt thật thì thêm từ vào VN_WORDS.

Chạy:
    python tools/check_english_names.py                  # quét backend db scripts tools tests
    python tools/check_english_names.py tools/x.py db/   # chỉ quét những đường dẫn này

Mã thoát:  0 = sạch   1 = có vi phạm   2 = lỗi khi chạy (tệp không parse được, đường dẫn sai)
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("backend", "db", "scripts", "tools", "tests")
SKIP_PREFIXES = ("db/migrations/",)  # mã phiên bản nằm trong tên tệp và đã ghi vào alembic_version
SKIP_PARTS = {"__pycache__", ".venv", "node_modules"}

VN_CHARS = re.compile(
    "[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",  # vi-ok: defines a Vietnamese letter
    re.IGNORECASE,
)

# Âm tiết tiếng Việt viết không dấu mà KHÔNG trùng từ tiếng Anh thông dụng hay viết tắt hay gặp.
# Cố ý bỏ: do to ban loc den dot ket don dung hong dat qua tho thu tim lan doc that can van thi sau.
VN_WORDS = frozenset("""
    khong chua kiem soat doi chieu lech gop nap keo ngay nguon thieu dong loi luot canh bao ra tra
    lieu muc tep hoa nhanh chay xong luan dich nguoi nhap nhiet giay nghi cau duong khoa bien mong
    phan moi trich yeu doan tien suy dien goi tuyen dinh sach cuoi giu xoa sua ghi viet tieng gia
    gio phut thang tuan mau tach gom tinh hien phai duoc nhung neu khi cua voi nhu trong ngoai truoc
    tren duoi mot hai sai truc tiep chi bo dau vao lay luu tang giam tong kho tuy chon theo tat cac
    tiet trung
""".split())  # vi-ok: the word list itself

SQL_HINT = re.compile(r"\b(SELECT|FROM|WITH|INSERT|UPDATE|CREATE|DELETE|ALTER)\b")
SQL_COMMENT = re.compile(r"--[^\n]*")
MARKER = re.compile(r"#\s*vi-ok:(.*)$")
IDENT_PIECES = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
WORD_PIECES = re.compile(r"[A-Za-z]+")


def vn_pieces(pieces) -> list[str]:
    return [p for p in (x.lower() for x in pieces) if p in VN_WORDS]


def ident_hits(name: str) -> list[str]:
    return vn_pieces(IDENT_PIECES.findall(name.strip("_")))


def read_markers(source: str) -> tuple[dict[int, str], list[int]]:
    """Trả về {dòng: lý do} và danh sách dòng có dấu vi-ok mà không nêu lý do."""
    reasons, empty = {}, []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            m = MARKER.search(tok.string)
            if m:
                if m.group(1).strip():
                    reasons[tok.start[0]] = m.group(1).strip()
                else:
                    empty.append(tok.start[0])
    return reasons, empty


def check_source(rel: str, source: str) -> list[tuple[str, int, str, str]]:
    """Kiểm một tệp. Trả về [(đường dẫn, dòng, loại, thứ bắt được)]."""
    out: list[tuple[str, int, str, str]] = []
    tree = ast.parse(source, filename=rel)
    reasons, empty = read_markers(source)
    for line in empty:
        out.append((rel, line, "vi-ok without reason", "# vi-ok:"))

    def report(node: ast.AST, kind: str, detail: str) -> None:
        first = node.lineno
        last = getattr(node, "end_lineno", None) or first
        if any(line in reasons for line in range(first, last + 1)):
            return
        out.append((rel, first, kind, detail))

    # Tên tệp: không có dấu vi-ok nào gỡ được, vì không có "dòng" để đánh dấu.
    stem_hits = vn_pieces(re.split(r"[_\-.]", Path(rel).stem))
    if stem_hits:
        out.append((rel, 1, "file name", " ".join(stem_hits)))

    # Chuỗi dùng như comment (docstring, chuỗi đứng một mình) và chữ cờ trong add_argument: không xét
    # như chuỗi thường. ast.walk đi theo chiều rộng, nên nút cha luôn được thăm trước nút con.
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, (ast.Constant, ast.JoinedStr)):
            for sub in ast.walk(node.value):
                skip.add(id(sub))
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_argument":
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("-"):
                    skip.add(id(a))
                    if vn_pieces(re.split(r"[-_]", a.value.lstrip("-"))):
                        report(a, "cli flag", a.value)

    def check_text(node: ast.AST, text: str) -> None:
        if SQL_HINT.search(text):
            text = SQL_COMMENT.sub("", text)
        m = VN_CHARS.search(text)
        if m:
            report(node, "string (accents)", snippet(text, m.start()))
            return
        hits = vn_pieces(WORD_PIECES.findall(text))
        if len(hits) >= 2:
            report(node, "string (words)", " ".join(hits[:4]))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if ident_hits(node.name):
                report(node, "identifier", node.name)
        elif isinstance(node, ast.arg):
            if ident_hits(node.arg):
                report(node, "identifier", node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if ident_hits(node.id):
                report(node, "identifier", node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            if ident_hits(node.attr):
                report(node, "identifier", node.attr)
        elif isinstance(node, ast.keyword) and node.arg:
            if ident_hits(node.arg):
                report(node, "identifier", node.arg + "=")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "ArgumentParser":
                ok = any(k.arg == "allow_abbrev" and isinstance(k.value, ast.Constant)
                         and k.value.value is False for k in node.keywords)
                if not ok:
                    report(node, "parser allows abbreviations", "ArgumentParser(...)")
        elif isinstance(node, ast.JoinedStr) and id(node) not in skip:
            # f-string xét như MỘT câu: tách theo {x} thì mỗi mảnh có thể dưới 2 từ và lọt.
            parts = [v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            for sub in ast.walk(node):
                skip.add(id(sub))
            check_text(node, " ".join(parts))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            check_text(node, node.value)
    return out


def snippet(text: str, at: int) -> str:
    start = max(0, at - 15)
    return text[start:at + 25].replace("\n", " ").strip()


def iter_files(root: Path, targets: list[str]):
    bases = [root / t for t in targets] if targets else [root / d for d in SCAN_DIRS]
    for base in bases:
        if not base.exists():
            raise FileNotFoundError(base)
        files = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for path in files:
            rel = path.relative_to(root).as_posix()
            if rel.startswith(SKIP_PREFIXES) or SKIP_PARTS.intersection(path.parts):
                continue
            yield rel, path


def scan(root: Path, targets: list[str] | None = None) -> list[tuple[str, int, str, str]]:
    found = []
    for rel, path in iter_files(root, targets or []):
        found.extend(check_source(rel, path.read_text(encoding="utf-8")))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Block Vietnamese file names, CLI flags, identifiers and strings from the code.",
        allow_abbrev=False,
    )
    parser.add_argument("paths", nargs="*", help="files or folders relative to --root (default: all scan folders)")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        found = scan(root, args.paths)
    except (SyntaxError, FileNotFoundError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for rel, line, kind, detail in found:
        print(f"{rel}:{line}  [{kind}]  {detail}")
    by_kind = Counter(kind for _, _, kind, _ in found)
    by_dir = Counter(rel.split("/", 1)[0] for rel, _, _, _ in found)
    print(f"\n{len(found)} violations in {len({r for r, _, _, _ in found})} files")
    for kind, n in by_kind.most_common():
        print(f"  {n:>5}  {kind}")
    for folder, n in by_dir.most_common():
        print(f"  {n:>5}  {folder}/")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
