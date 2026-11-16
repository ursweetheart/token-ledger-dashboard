"""Hàm thuần đọc/dựng hạn mức trên dữ liệu virtual key. KHÔNG giữ master key.

VÌ SAO FILE NÀY KHÔNG CÒN GỌI GATEWAY
-------------------------------------
Trước đây file này giữ master key và gọi thẳng `/key/list`, `/key/update`. Ngày
03/11/2026 đã chứng minh trên máy dev: code chạy trong container `api` dùng chính
master key đó tạo một đường chuyển tiếp (`/config/pass_through_endpoint`) rò khoá
Google ra ngoài. Nên mọi thao tác cần master key đã chuyển sang worker trên host
(`backend/connection_worker.py`); container `api` không còn giữ master key.

Còn lại ở đây là các hàm THUẦN: đọc hạn mức / tag / số đã tiêu từ dict khoá mà
worker trả về, kiểm giá trị tiền, và dựng metadata mới. Worker dùng lại
`merge_quota`, `parse_amount`, `quota_of` cho đường ghi; `api` dùng phần đọc để
dựng dòng cho tab Setting. Không hàm nào ở đây mở kết nối mạng.

GHI METADATA LÀ THAY THẾ, KHÔNG PHẢI GỘP
----------------------------------------
`key_management_endpoints.py` của LiteLLM chỉ giữ metadata cũ khi yêu cầu KHÔNG
mang `metadata`. Gửi `{"metadata": {"quota_usd": 50}}` sẽ XOÁ `tags` của khoá,
làm request lạc tuyến và tiền ghi sai project trong khi vẫn trả 200. Vì vậy
`merge_quota` luôn bắt đầu từ bản metadata hiện có, chỉ đổi `quota_usd` và thêm
một dòng vào `quota_log`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Hai khoá metadata duy nhất đường ghi được phép đụng tới.
QUOTA_FIELD = "quota_usd"
LOG_FIELD = "quota_log"
WRITABLE_FIELDS = frozenset({QUOTA_FIELD, LOG_FIELD})

# Tiền tố tên mọi khoá do worker của tab Kết nối agent cấp
# (`connection_worker.py`, `connection-<mã thao tác>`). Không ai nhập tay.
# Khoá như vậy chỉ được sửa hạn mức ở tab Kết nối (khoá quản trị, có audit); đường
# hạn mức của dashboard từ chối chúng bằng 409. Nhận diện bằng tiền tố vì đọc bảng
# thì phải cấp thêm GRANT cho vai chỉ-đọc.
MANAGED_KEY_PREFIX = "connection-"


def is_managed_alias(key_alias: str) -> bool:
    """True nếu khoá do tab Kết nối agent quản lý."""
    return key_alias.startswith(MANAGED_KEY_PREFIX)


def quota_of(key: dict[str, Any]) -> float | None:
    """Hạn mức ghi trong metadata, hoặc None nếu chưa đặt / ghi sai kiểu.

    Ghi sai kiểu được coi như CHƯA ĐẶT, không phải lỗi: hạn mức hỏng mà chặn hết
    lưu lượng thì một lỗi gõ tay thành một sự cố toàn hệ thống.
    """
    raw = (key.get("metadata") or {}).get(QUOTA_FIELD)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    return float(raw) if raw >= 0 else None


def log_of(key: dict[str, Any]) -> list[dict[str, Any]]:
    raw = (key.get("metadata") or {}).get(LOG_FIELD)
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


def tag_of(key: dict[str, Any]) -> str | None:
    """Tag định danh của khoá, hoặc None nếu khoá không mang tag nào.

    Đây mới là thứ quyết định project, KHÔNG PHẢI TÊN KHOÁ. Tên khoá chỉ là nhãn
    người đặt: `dms-feedback` và `dms-feedback-tagged` trông như cùng một project
    nhưng cái trước không mang tag nào, còn `crm-feedback-12-09` trông như một
    project riêng mà thật ra cùng tag với `crm-feedback-tagged`.

    Bỏ qua tag do LiteLLM tự thêm (`User-Agent: ...`) - cùng luật với hook chặn
    trong docker/gateway/quota_hook.py, để hai nơi không bao giờ hiểu khác nhau
    về việc một request thuộc agent nào.
    """
    tags = (key.get("metadata") or {}).get("tags")
    if not isinstance(tags, list):
        return None
    for tag in tags:
        if isinstance(tag, str) and tag and not tag.startswith("User-Agent:"):
            return tag
    return None


def spend_of(key: dict[str, Any]) -> float:
    raw = key.get("spend")
    return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else 0.0


def merge_quota(existing_metadata: dict[str, Any], new_quota: float,
                actor: str) -> dict[str, Any]:
    """Dựng metadata MỚI từ bản hiện có. Chỗ duy nhất dựng metadata cho đường ghi.

    Bắt đầu bằng `dict(existing)` chứ không bằng `{}`: xem ghi chú đầu file về việc
    LiteLLM thay thế cả cục metadata. Bắt đầu từ rỗng là xoá `tags`.
    """
    merged = dict(existing_metadata)
    before = merged.get(QUOTA_FIELD)
    merged[QUOTA_FIELD] = new_quota
    entry = {"at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
             "from": before if isinstance(before, (int, float))
                     and not isinstance(before, bool) else None,
             "to": new_quota,
             "by": actor}
    merged[LOG_FIELD] = [*(x for x in (merged.get(LOG_FIELD) or []) if isinstance(x, dict)),
                         entry]
    return merged


def parse_amount(raw: Any) -> float:
    """Số tiền hợp lệ, hoặc `ValueError` kèm lý do đọc được.

    Đặt ở đây (hàm thuần, không kéo FastAPI) để chạy được trên máy sạch: `api` bọc
    `ValueError` thành HTTP 400 trước khi gọi worker, và worker cũng gọi lại hàm
    này để tự bảo vệ (một đường ghi, hai lần kiểm).

    `bool` bị loại tường minh: trong Python `True` là số nguyên hợp lệ, nên
    `quota_usd: true` sẽ lặng lẽ thành hạn mức 1 đô.

    Chuỗi số ĐƯỢC chấp nhận: ô nhập trên web gửi chuỗi, từ chối "50" là từ chối
    chính đường dùng thật.
    """
    if isinstance(raw, bool) or raw is None or raw == "":
        raise ValueError(f"Missing {QUOTA_FIELD!r} in the request body")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{QUOTA_FIELD!r} must be a number, got {raw!r}") from None
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{QUOTA_FIELD!r} must be a finite number")
    if value < 0:
        raise ValueError(f"{QUOTA_FIELD!r} must not be negative, got {value}")
    return value


def sanitize_incoming(fields: dict[str, Any] | None) -> dict[str, Any]:
    """Bỏ mọi khoá metadata mà người gọi không được phép đụng tới.

    Người gọi chỉ được gửi hạn mức. Mọi khoá khác - kể cả `tags` - bị bỏ ở đây,
    trước khi có gì chạm tới worker.
    """
    return {k: v for k, v in (fields or {}).items() if k in WRITABLE_FIELDS}
