"""Quy tắc dùng chung cho mọi script nạp - một bản duy nhất.

Vì sao tách file: quy tắc phân loại SKU được dùng ở CẢ HAI chỗ - lúc sinh bảng
danh mục và lúc nạp hoá đơn. Nếu mỗi chỗ một bản thì đến lúc sửa sẽ chỉ sửa một
bên, và không có gì báo lỗi: tổng tiền vẫn đúng, chỉ tỷ lệ giữa các model sai.

Nguồn: docs/plan-xay-dung-database-2026-08-07.md mục 4.6 (quy tắc 1-9)
"""

from __future__ import annotations

import re

# Tên CHUẨN. Mỗi nguồn gọi một kiểu, đây là kiểu ta chọn.
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
    (11, "gemini-3.6-flash", "gemini-3"),
    # Them 31/08/2026: tuyen `gemini-flash-lite` cua Gateway dinh tuyen toi day.
    (12, "gemini-3.5-flash-lite", "gemini-3"),
    (13, "gemini-3.8-flash", "gemini-3"),
]
MODEL_ID = {name: i for i, name, _ in MODELS}

# Tên model mà API Gateway (LiteLLM) ghi vào cột `model` của LiteLLM_SpendLogs.
# KHÁC bí danh: agent xin `gemini-flash-lite`, Gateway ghi lại tên upstream có
# tiền tố nhà cung cấp. Đo 31/08: 34/34 dòng thành công đều mang dạng có tiền tố.
#
# CỐ Ý KHÔNG khai `gemini/gemini-3-flash-preview`. `guess_model` sẽ suy nó thành
# `gemini-3-flash` - gộp bản preview vào bản chính thức, mà đơn giá hai bản thì
# chưa ai kiểm. Thà để lưu lượng của nó rơi vào mục "không nối được model" của bộ
# nạp - ở đó nó được ĐẾM và IN RA - còn hơn khớp nhầm trong im lặng.
# TRI THUC CUU TU MOT FILE SINH RA (09/09/2026). `db/02_catalog.sql` la file do
# `gen_catalog.py` SINH, nhung ngay 04/09 co nguoi go tay bon dong chu thich vao
# no; chay lai gen_catalog la mat sach. Chuyen no ve day -- nguon su that -- de
# lan sau sinh lai khong xoa mat:
#
#     Monitoring cua project ma Gateway goi toi bao TEN TRAN
#     ('gemini-3.5-flash-lite'), trong khi nguon 'gateway' bao ten CO TIEN TO nha
#     cung cap ('gemini/gemini-3.5-flash-lite'). Cung mot model, hai khong gian
#     ten -- dung cai ma bang bi danh sinh ra de xu ly.
#
# Bai hoc kem theo: dung go tay vao `db/02_catalog.sql`. Muon ghi chu gi thi ghi
# vao day hoac vao chinh gen_catalog.py.
GATEWAY_MODELS = [
    "gemini/gemini-3.6-flash",
    "gemini/gemini-3.5-flash-lite",
    # Them 09/09/2026, khi dua agent `crm-feedback` qua Gateway. Tuyen cua no khai
    # `model: gemini/gemini-2.5-flash` (Vertex express mode) vi do la model
    # production CRM dang dung -- 1.888 luot / 22,6 trieu token, 06/07 -> 29/08.
    #
    # THIEU DONG NAY THI HONG NHU SAU, da do truoc khi them: luot goi 200, dong vao
    # `fact_call` binh thuong, nhung `model_id` la NULL nen `fact_usage_daily` KHONG
    # co dong nao, va dashboard hien 0 cho CRM. `audit_db.py` nhom J van DAT vi no
    # kiem "moi dong nguon co vao so hay bi bo co ly do", ma dong nay DA vao so.
    #
    # Bo nap CO dem va CO in: `model not declared 3`. Nhung dich vu `ledger-refresh`
    # chay bo nap voi `capture_output=True` o che do vong lap, nen dong do bi NUOT
    # khi luot chay thanh cong -- xem ghi chu o scripts/refresh_gateway.py.
    "gemini/gemini-2.5-flash",
]

# Thứ tự QUAN TRỌNG: mẫu dài hơn phải đứng trước. '2.5 flash lite' phải được thử
# trước '2.5 flash', nếu không Flash Lite bị gán nhầm thành Flash.
MODEL_PATTERNS = [
    ("embedding 001", "gemini-embedding-1.0"),
    ("embedding 1.0", "gemini-embedding-1.0"),
    ("embedding 2", "gemini-embedding-2"),
    ("3.1 flash lite", "gemini-3.1-flash-lite"),
    # PHAI dung TRUOC "3.5 flash": chuoi ngan nam tron trong chuoi dai.
    # Do 31/08: thieu dong nay thi guess_model("gemini/gemini-3.5-flash-lite")
    # tra ve "gemini-3.5-flash" -- khop nham sang model khac gia, IM LANG.
    ("3.5 flash lite", "gemini-3.5-flash-lite"),
    ("3.5 flash", "gemini-3.5-flash"),
    ("3.8 flash", "gemini-3.8-flash"),
    ("3.6 flash", "gemini-3.6-flash"),
    ("3 pro", "gemini-3-pro"),
    ("3 flash", "gemini-3-flash"),
    ("2.5 flash lite", "gemini-2.5-flash-lite"),
    ("2.5 pro", "gemini-2.5-pro"),
    ("2.5 flash", "gemini-2.5-flash"),
    ("2.0 flash", "gemini-2.0-flash"),
]


def guess_model(sku_name: str) -> str | None:
    t = " " + re.sub(r"[^a-z0-9.]+", " ", sku_name.lower()) + " "
    for pattern, model in MODEL_PATTERNS:
        if pattern in t:
            return model
    return None


def guess_kind(sku_name: str) -> str | None:
    """QUY TẮC 8. Thứ tự BẮT BUỘC: cached -> output -> input.

    SKU 911A-8880-A243 tên đầy đủ là:
        "Generate content OUTPUT token count gemini 2.5 flash short INPUT text"

    Kiểm 'input' trước 'output' thì 346 dòng / $105,42 = 38,9% chi phí nhảy sai
    cột. Tổng vẫn đúng $270,9517 nên mọi phép nghiệm thu tổng VẪN XANH - chỉ có
    tỷ lệ input/output là sai hết.

    'cached' phải trước 'input' vì "cached input token" chứa cả "input token".
    """
    t = sku_name.lower()
    if "cached" in t:
        return "cached"
    if "output" in t:
        return "output"
    if "input" in t:
        return "input"
    return None


def guess_service(res_service: str, metric_type: str) -> str:
    """QUY TẮC 9. res_service, rỗng thì lấy tiền tố của metric_type.

    Đúng các dòng TOKEN của generativelanguage lại có res_service RỖNG - dịch vụ
    của chúng nằm ở tiền tố metric_type. Gán thẳng service = res_service rồi lọc
    `WHERE service='generativelanguage...'` sẽ trả về 0 DÒNG TOKEN, không báo lỗi.
    """
    return res_service or metric_type.split("/")[0]


def is_quota_limit(metric_nickname: str) -> bool:
    """*_limit là ALIGN_MAX - hạn mức quota, KHÔNG phải số đếm. Không được SUM."""
    return metric_nickname.endswith("_limit")
