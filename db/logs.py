"""Logger dung chung cho moi tien trinh chay trong container.

VI SAO TEN FILE LA `logs.py`, KHONG PHAI `logging.py`
----------------------------------------------------
`db/` KHONG phai mot package - khong co `__init__.py`. Cac script noi vao no
bang cach chen thang duong dan len DAU sys.path:

    sys.path.insert(0, str(ROOT / "db"))     # scripts/rebuild_db.py:81
    import connect                            # scripts/rebuild_db.py:83

`insert(0, ...)` dat `db/` TRUOC thu vien chuan. Nen mot file ten
`db/logging.py` se CHE KHUAT module `logging` cua Python trong moi tien trinh
noi vao `db/` - va hong theo kieu kho lan nhat: `import logging` van thanh cong,
chi la nhap nham file. Ten `logs.py` khong dung ten nao trong thu vien chuan.

VI SAO GHI RA STDOUT CHU KHONG PHAI STDERR
------------------------------------------
`logging` mac dinh ghi ra stderr, con `print()` ghi ra stdout. Pipeline nay long
ba tang bang `subprocess`, va cac tien trinh con dang ghi stdout. De mac dinh
thi hai luong tron nhau va THU TU DONG SAI - dung cai bay ma
scripts/update_dashboard.py:61 da ghi lai:

    "Tien trinh con ghi thang ra terminal, con print() o day di qua bo dem.
     Khong flush thi thong bao loi cua con HIEN TRUOC tieu de buoc, va nguoi
     doc khong biet loi thuoc ve buoc nao."

Te hon nua: `flush()` cua luong nay khong giup gi cho luong kia. Nen MOI THU ra
mot luong duy nhat, va la stdout - doi cha theo con re hon doi 238 cho theo cha.

NGOAI LE CO CHU Y: hai thong bao chan khoi dong o backend/main.py va
docker/gateway/entrypoint.sh giu nguyen stderr. Chung la loi chan khoi dong,
stderr la cho dung cho chung.

MUC LAY TU BIEN MOI TRUONG, KHONG PHAI THAM SO
----------------------------------------------
Ba tien trinh rieng biet (update_dashboard -> rebuild_db -> load_*), moi tien
trinh mot khong gian bien. Tham so ham o tang cha KHONG lam tang chau im bot.

`subprocess.run()` ke thua `os.environ`, nen LOG_LEVEL dat mot lan se tu chay
xuong ca ba tang. Cung co che `PYTHONUNBUFFERED=1` dang dung o tools.Dockerfile.

NHUNG ke thua chi dung BEN TRONG container. Compose noi suy `.env` cho chinh
file compose, KHONG bom bien vao container - phai khai tuong minh trong khoi
`environment:`. Xem docker-compose.yml, dich vu `tools` va `api`.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import timedelta, timezone

# Gio Viet Nam. Cung hang so voi db/load_gateway.py va db/load_ralli.py, cung ly
# do: moi cot ngay trong du an nay la gio VN, khong phai UTC.
VN = timezone(timedelta(hours=7))

# Muc mac dinh. INFO giu lai tien do tung buoc, canh bao, loi va MOI DONG SO DO.
# Chi tiet nam o DEBUG.
MUC_MAC_DINH = "INFO"

_FORMAT = "%(asctime)s  %(levelname)-5s  %(message)s"
_NGAY_GIO = "%Y-%m-%d %H:%M:%S"


class _GioVN(logging.Formatter):
    """Nhan thoi gian theo gio VN.

    `logging` mac dinh dung gio cuc bo cua may. Container chay UTC, may dev chay
    gio VN - nen cung mot pipeline se ghi hai moc gio khac nhau tuy chay o dau,
    va khong ai doi chieu duoc. Ep ve VN o ca hai noi.
    """

    def formatTime(self, record, datefmt=None):  # noqa: N802 (ten cua thu vien)
        from datetime import datetime
        t = datetime.fromtimestamp(record.created, VN)
        return t.strftime(datefmt or _NGAY_GIO)


def muc_tu_moi_truong() -> int:
    """Doc LOG_LEVEL. Gia tri la thi ve INFO, KHONG duoc sap.

    Mot bien moi truong go sai khong duoc lam hong ca lan chay pipeline - no chi
    la muc chi tiet cua log. Nhung cung KHONG duoc im lang: canh bao mot dong roi
    di tiep, de nguoi dat sai con biet duong sua.
    """
    tho = (os.environ.get("LOG_LEVEL") or MUC_MAC_DINH).strip().upper()
    muc = logging.getLevelName(tho)
    if isinstance(muc, int):
        return muc
    print(f"LOG_LEVEL={tho!r} is not valid, falling back to {MUC_MAC_DINH}", file=sys.stderr)
    return logging.getLevelName(MUC_MAC_DINH)


def get_logger(ten: str | None = None) -> logging.Logger:
    """Logger da cau hinh. Goi bao nhieu lan cung duoc.

    BAY KINH DIEN cua `logging`: goi basicConfig/addHandler hai lan thi moi dong
    log in RA HAI LAN. Day khong phai gia thuyet - no xay ra ngay khi mot script
    import hai module ma ca hai cung dung logger. Chan bang cach kiem `.handlers`
    truoc khi them.
    """
    root = logging.getLogger()
    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)     # KHONG de mac dinh (stderr)
        h.setFormatter(_GioVN(_FORMAT, _NGAY_GIO))
        root.addHandler(h)
    root.setLevel(muc_tu_moi_truong())
    return logging.getLogger(ten) if ten else root
