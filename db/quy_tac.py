"""Quy tac dung chung cho moi script nap - mot ban duy nhat.

Vi sao tach file: quy tac phan loai SKU duoc dung o CA HAI cho - luc sinh bang
danh muc va luc nap hoa don. Neu moi cho mot ban thi den luc sua se chi sua mot
ben, va khong co gi bao loi: tong tien van dung, chi ty le giua cac model sai.

Nguon: docs/plan-xay-dung-database-2026-08-07.md muc 4.6 (quy tac 1-9)
"""

from __future__ import annotations

import re

# Ten CHUAN. Moi nguon goi mot kieu, day la kieu ta chon.
MODELS = [
    (1, "gemini-2.0-flash", "gemini-2.0"),
    (2, "gemini-2.5-flash", "gemini-2.5"),
    (3, "gemini-2.5-flash-lite", "gemini-2.5"),
    (4, "gemini-2.5-pro", "gemini-2.5"),
    (5, "gemini-3-flash", "gemini-3"),
    (6, "gemini-3-pro", "gemini-3"),
    (7, "gemini-3.1-flash-lite", "gemini-3"),
    (8, "gemini-3.5-flash", "gemini-3"),
    (9, "gemini-embedding-1.0", "embedding"),
    (10, "gemini-embedding-2", "embedding"),
]
MA_MODEL = {ten: i for i, ten, _ in MODELS}

# Thu tu QUAN TRONG: mau dai hon phai dung truoc. '2.5 flash lite' phai duoc thu
# truoc '2.5 flash', neu khong Flash Lite bi gan nham thanh Flash.
MAU_MODEL = [
    ("embedding 001", "gemini-embedding-1.0"),
    ("embedding 1.0", "gemini-embedding-1.0"),
    ("embedding 2", "gemini-embedding-2"),
    ("3.1 flash lite", "gemini-3.1-flash-lite"),
    ("3.5 flash", "gemini-3.5-flash"),
    ("3 pro", "gemini-3-pro"),
    ("3 flash", "gemini-3-flash"),
    ("2.5 flash lite", "gemini-2.5-flash-lite"),
    ("2.5 pro", "gemini-2.5-pro"),
    ("2.5 flash", "gemini-2.5-flash"),
    ("2.0 flash", "gemini-2.0-flash"),
]


def suy_model(ten_sku: str) -> str | None:
    t = " " + re.sub(r"[^a-z0-9.]+", " ", ten_sku.lower()) + " "
    for mau, model in MAU_MODEL:
        if mau in t:
            return model
    return None


def suy_loai(ten_sku: str) -> str | None:
    """QUY TAC 8. Thu tu BAT BUOC: cached -> output -> input.

    SKU 911A-8880-A243 ten day du la:
        "Generate content OUTPUT token count gemini 2.5 flash short INPUT text"

    Kiem 'input' truoc 'output' thi 346 dong / $105,42 = 38,9% chi phi nhay sai
    cot. Tong van dung $270,9517 nen moi phep nghiem thu tong VAN XANH - chi co
    ty le input/output la sai het.

    'cached' phai truoc 'input' vi "cached input token" chua ca "input token".
    """
    t = ten_sku.lower()
    if "cached" in t:
        return "cached"
    if "output" in t:
        return "output"
    if "input" in t:
        return "input"
    return None


def suy_dich_vu(res_service: str, metric_type: str) -> str:
    """QUY TAC 9. res_service, rong thi lay tien to cua metric_type.

    Dung cac dong TOKEN cua generativelanguage lai co res_service RONG - dich vu
    cua chung nam o tien to metric_type. Gan thang dich_vu = res_service roi loc
    `WHERE dich_vu='generativelanguage...'` se tra ve 0 DONG TOKEN, khong bao loi.
    """
    return res_service or metric_type.split("/")[0]


def la_han_muc(metric_alias: str) -> bool:
    """*_limit la ALIGN_MAX - han muc quota, KHONG phai so dem. Khong duoc SUM."""
    return metric_alias.endswith("_limit")
