"""Canh hạn mức của từng project và gửi thư khi sắp hết.

CÙNG KHUÔN VỚI `watch_gateway.py`, và dùng lại chính nó: `send_mail`, `env`,
`load_state`, `save_state` đều lấy từ đó. Thứ duy nhất khác là cái đem ra so -
ở kia là "Gateway sống hay chết", ở đây là "đang ở bậc nào".

BA BẬC, VÀ VÌ SAO BẬC THỨ BA Ở 110% CHỨ KHÔNG PHẢI 100,01%
-----------------------------------------------------------
    b90     >= 90%    sắp hết, còn kịp nạp
    b100    >= 100%   đã chạm hạn mức, Gateway bắt đầu chặn
    over    >= 110%   VƯỢT ĐÁNG KỂ

Bậc `over` không phải để nhắc lại rằng đã hết. Nó trả lời một câu khác hẳn:
*việc chặn có đang hoạt động không?* Gateway chặn ngay khi chạm 100%, nên tiêu
thêm được hơn 10% nữa nghĩa là lưu lượng đang đi đường khác - agent còn khoá
nhà cung cấp riêng, hoặc hook không được nạp. Đó là thứ đáng gọi người dậy, còn
"đã hết tiền" thì bậc b100 đã nói rồi.

MỘT THƯ MỖI LẦN ĐỔI BẬC, KHÔNG PHẢI MỖI NHỊP KIỂM
--------------------------------------------------
Trạng thái lưu ra file JSON nên khởi động lại không gửi lại thư của bậc đang ở.
Nhảy nhiều bậc giữa hai nhịp thì gửi MỘT thư của bậc cao nhất. Nạp thêm làm tỉ
lệ tụt xuống thì đặt lại bậc trong im lặng - lần vượt sau lại báo.

GỬI THƯ HỎNG KHÔNG ĐƯỢC ẢNH HƯỞNG TỚI VIỆC CHẶN
-----------------------------------------------
Không có gì để ảnh hưởng: việc chặn nằm ở hook trong Gateway, tiến trình này chỉ
đọc và gửi thư. Tách bạch đó là chủ ý - cảnh báo là thứ giúp người biết, chặn là
thứ giữ tiền, buộc hai thứ vào nhau thì một máy chủ thư hỏng sẽ lặng lẽ mở cửa
cho chi tiêu.

    python scripts/watch_quota.py --once --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend import gateway  # noqa: E402
from watch_gateway import env, load_state, save_state, send_mail  # noqa: E402

LOG = logging.getLogger("watch_quota")

OK = "ok"
B90 = "b90"
B100 = "b100"
OVER = "over"

# Thứ tự tăng dần. Dùng chỉ số để biết bậc có ĐI LÊN hay không - chỉ đi lên mới
# gửi thư.
LADDER = (OK, B90, B100, OVER)

SUBJECT = {
    B90: "sap het han muc (>=90%)",      # vi-ok: email subject
    B100: "DA HET han muc - Gateway dang chan",
    OVER: "VUOT HAN MUC >10% - viec chan co the khong hoat dong",
}


def level_of(ratio: float | None) -> str:
    """Bậc của một tỉ lệ. `None` (chưa đặt hạn mức) cũng là `ok`."""
    if ratio is None:
        return OK
    if ratio >= 1.10:
        return OVER
    if ratio >= 1.0:
        return B100
    if ratio >= 0.90:
        return B90
    return OK


def rose(old: str, new: str) -> bool:
    """Bậc có đi lên không. Đi xuống (vì vừa nạp thêm) thì im lặng đặt lại."""
    known = {name: i for i, name in enumerate(LADDER)}
    return known.get(new, 0) > known.get(old, 0)


def rows_from_gateway() -> list[dict]:
    """Một dòng cho mỗi virtual key: bí danh, hạn mức, đã tiêu, tỉ lệ."""
    out = []
    for key in gateway.list_keys():
        alias = key.get("key_alias")
        if not alias:
            continue
        quota = gateway.quota_of(key)
        spent = gateway.spend_of(key)
        out.append({"alias": alias, "quota": quota, "spent": spent,
                    "ratio": (spent / quota) if quota else None})
    return out


def body_for(row: dict, level: str, enforceable: bool) -> str:
    """Thư phải đủ để người nhận biết làm gì tiếp, không chỉ biết là có chuyện."""
    quota = row["quota"]
    lines = [
        f"Khoa:      {row['alias']}",                                # vi-ok: email text
        f"Han muc:   {quota:.2f} USD" if quota is not None else "Han muc:   chua dat",
        f"Da tieu:   {row['spent']:.4f} USD",
        f"Ty le:     {row['ratio'] * 100:.1f}%" if row["ratio"] is not None else "",
        "",
    ]
    if level == B90:
        lines.append("Chua bi chan. Con kip nap them o tab Setting cua dashboard.")
    elif level == B100:
        lines.append("Gateway DANG CHAN luu luong cua khoa nay.")
        lines.append("Mo lai bang cach nap them han muc o tab Setting cua dashboard.")
    elif level == OVER:
        lines.append("Da tieu qua han muc hon 10%, tuc la luu luong VAN DI duoc.")
        lines.append("Kiem ba thu, theo thu tu:")
        lines.append("  1. hook quota co duoc nap khong (tim dong `quota_block` trong log)")
        lines.append("  2. QUOTA_DRY_RUN con bang 1 khong")
        lines.append("  3. agent co duong di thang toi nha cung cap khong")
    if not enforceable:
        lines += ["", "LUU Y: khoa nay khong chan duoc - day chi la canh bao suong."]
    # Thư MUST NOT chứa nội dung câu hỏi hay câu trả lời. Ở đây không có đường nào
    # để nội dung lọt vào: chỉ có bí danh khoá và ba con số.
    return "\n".join(lines)


def tick(state: dict, args) -> dict:
    levels = state.setdefault("levels", {})
    try:
        rows = rows_from_gateway()
    except gateway.GatewayError as exc:
        # Không đọc được thì KHÔNG đoán và KHÔNG gửi thư. Giữ nguyên bậc cũ.
        LOG.error("Khong doc duoc Gateway (%s); giu nguyen bac cu", type(exc).__name__)
        return state

    for row in rows:
        alias = row["alias"]
        old = levels.get(alias, OK)
        new = level_of(row["ratio"])
        if new == old:
            continue
        if rose(old, new):
            send_mail(f"[quota] {alias} - {SUBJECT.get(new, new)}",
                      body_for(row, new, enforceable=True), args.dry_run)
            LOG.warning("%s: %s -> %s", alias, old, new)
        else:
            # Tụt bậc = vừa có người nạp thêm. Đặt lại trong im lặng.
            LOG.info("%s: %s -> %s (da nap them)", alias, old, new)
        levels[alias] = new
    return state


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--every", type=int, default=0,
                   help="Lap lai moi N giay. Bo qua thi chay mot lan roi thoat.")
    p.add_argument("--once", action="store_true", help="Chay dung mot nhip.")
    p.add_argument("--dry-run", action="store_true",
                   help="In thu ra man hinh thay vi gui.")
    p.add_argument("--state", default=str(ROOT / "var" / "watch_quota.json"))
    args = p.parse_args()

    logging.basicConfig(level=env("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(message)s")
    # THANG vao litellm: nginx o gateway-lb chan moi duong /key/*.
    gateway.configure(env("GATEWAY_BASE_URL", "http://litellm-1:4000"),
                      env("LITELLM_MASTER_KEY"))
    if not gateway.configured():
        raise SystemExit("Thieu LITELLM_MASTER_KEY - khong doc duoc han muc.")

    path = Path(args.state)
    while True:
        state = tick(load_state(path), args)
        save_state(path, state)
        if args.once or not args.every:
            return
        time.sleep(args.every)


if __name__ == "__main__":
    main()
