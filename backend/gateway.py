"""Lớp gọi sang Gateway để đọc và sửa hạn mức. KHÔNG chạm database.

VÌ SAO HẠN MỨC NẰM Ở ĐÂY CHỨ KHÔNG NẰM TRONG MỘT BẢNG
------------------------------------------------------
Hạn mức được ghi vào phần `metadata` của chính virtual key mà agent dùng. Nhờ
vậy không phải dựng bảng mới, không phải cấp vai database mới, và số đã tiêu thì
LiteLLM đã cộng sẵn vào trường `spend` của khoá. Tiến trình thi hành ở Gateway
đọc cả hai thứ đó ngay trong tham số nó nhận được, không mở kết nối nào.

Hệ quả: backend giữ master key của Gateway. Ba ràng buộc bắt buộc đi kèm, và
chúng là lý do tồn tại của file này:

  1. Đường dẫn và phương thức VIẾT CỨNG trong `_call`. Không hàm nào ở đây nhận
     đường dẫn từ người gọi, nên không có cách nào biến backend thành đường
     chuyển tiếp lệnh tuỳ ý sang Gateway.
  2. Chỉ hai khoá metadata được ghi: `quota_usd` và `quota_log`. Xem `_merge`.
  3. Master key KHÔNG được lọt vào thông báo lỗi. Xem `GatewayError`.

GHI METADATA LÀ THAY THẾ, KHÔNG PHẢI GỘP - CHỖ NGUY NHẤT CỦA CẢ FILE
---------------------------------------------------------------------
`key_management_endpoints.py:2010` của LiteLLM chỉ giữ metadata cũ khi yêu cầu
KHÔNG mang `metadata`:

    if "metadata" not in non_default_values:
        non_default_values["metadata"] = existing_metadata.copy()

Nên gửi `{"metadata": {"quota_usd": 50}}` sẽ XOÁ `tags` của khoá. Hậu quả không
phải hạn mức hỏng mà là tag định danh biến mất: request rơi sang tuyến khác và
tiền ghi sai project, trong khi mọi lượt gọi vẫn trả 200. Đo ngày 31/08 trên
khoá không mang tag: 7/8 lượt thành công, 1/8 lạc tuyến - hỏng 12,5%, im lặng.

Vì vậy mọi thao tác ghi ở đây đều là ĐỌC - GỘP - GHI LẠI CẢ CỤC. `_merge` là
chỗ duy nhất dựng metadata mới, và nó luôn bắt đầu từ bản hiện có.

Dùng `urllib` của thư viện chuẩn, không thêm phụ thuộc - cùng lựa chọn đã dùng ở
scripts/watch_gateway.py.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

# Hai khoá metadata duy nhất file này được phép ghi.
QUOTA_FIELD = "quota_usd"
LOG_FIELD = "quota_log"
WRITABLE_FIELDS = frozenset({QUOTA_FIELD, LOG_FIELD})

# Đường dẫn viết cứng. Không hàm nào nhận đường dẫn từ bên ngoài.
_PATH_LIST = "/key/list"
_PATH_UPDATE = "/key/update"

_TIMEOUT_SECONDS = 15

_base_url = ""
_master_key = ""


class GatewayError(RuntimeError):
    """Lỗi khi gọi Gateway.

    Thông báo của lớp này đi thẳng ra cho người dùng, nên nó MUST NOT chứa master
    key. Không có chỗ nào trong file này đặt khoá vào thông điệp; `_call` cũng
    không in lại thân yêu cầu, vì thân yêu cầu không mang khoá - khoá chỉ nằm
    trong header.
    """


def configure(base_url: str, master_key: str) -> None:
    """Nhận cấu hình từ `main.py`. File này KHÔNG tự đọc biến môi trường.

    Đọc biến ở một chỗ duy nhất (`main.py`) thì cửa chặn khởi động cũng nằm ở một
    chỗ duy nhất: thiếu khoá là máy chủ không lên, chứ không phải lên rồi hỏng
    lúc có người bấm Lưu.
    """
    global _base_url, _master_key
    _base_url = base_url.rstrip("/")
    _master_key = master_key


def configured() -> bool:
    return bool(_base_url and _master_key)


def _call(path: str, method: str, payload: dict[str, Any] | None = None,
          query: dict[str, Any] | None = None) -> Any:
    """Gọi Gateway. `path` chỉ nhận hằng số khai trong file này.

    `query` được mã hoá ở đây chứ không nối chuỗi ở nơi gọi: nối chuỗi là cách
    một giá trị lạ lọt vào đường dẫn.
    """
    if not configured():
        raise GatewayError("Gateway chưa được cấu hình")  # vi-ok: thông báo cho người dùng
    if path not in (_PATH_LIST, _PATH_UPDATE):
        # Không thể xảy ra từ đường gọi bình thường. Để lại vì nó là thứ biến một
        # lỗi lập trình tương lai thành lỗi dừng ngay, thay vì thành một đường
        # chuyển tiếp lệnh sang Gateway.
        raise GatewayError("Đường dẫn không nằm trong danh sách cho phép")  # vi-ok

    url = _base_url + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"Authorization": f"Bearer {_master_key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        # Đọc thân lỗi để nói được vì sao, nhưng cắt ngắn: nguyên văn lỗi của
        # LiteLLM có thể rất dài, và chỗ này đi thẳng ra giao diện.
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            detail = ""
        raise GatewayError(f"Gateway trả HTTP {exc.code}. {detail}") from None
    except urllib.error.URLError as exc:
        raise GatewayError(f"Không gọi được Gateway: {type(exc).__name__}") from None
    except (ValueError, TimeoutError) as exc:
        raise GatewayError(f"Gateway trả về thứ không đọc được: {type(exc).__name__}") from None


def list_keys() -> list[dict[str, Any]]:
    """Mọi virtual key kèm `metadata` và `spend`.

    `return_full_object=true` là thứ mang `metadata` và `spend` về; thiếu nó thì
    chỉ có chuỗi khoá và không đọc được hạn mức.
    """
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        data = _call(_PATH_LIST, "GET",
                     query={"page": page, "size": 100, "return_full_object": "true"})
        keys = (data or {}).get("keys") or []
        out.extend(k for k in keys if isinstance(k, dict))
        total_pages = (data or {}).get("total_pages") or 1
        # Chặn vòng lặp vô hạn: Gateway trả `total_pages` sai kiểu hay quá lớn thì
        # dừng ở mức đủ cho mọi số khoá thực tế, chứ không quay mãi.
        if not isinstance(total_pages, int) or page >= total_pages or page >= 50:
            return out
        page += 1


def find_key(key_alias: str) -> dict[str, Any] | None:
    """Khoá mang đúng bí danh này, hoặc None."""
    for k in list_keys():
        if k.get("key_alias") == key_alias:
            return k
    return None


def keys_by_alias() -> dict[str, dict[str, Any]]:
    return {k["key_alias"]: k for k in list_keys() if k.get("key_alias")}


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


def _merge(existing_metadata: dict[str, Any], new_quota: float,
           actor: str) -> dict[str, Any]:
    """Dựng metadata MỚI từ bản hiện có. Chỗ duy nhất trong file làm việc này.

    Bắt đầu bằng `dict(existing)` chứ không bằng `{}`: xem ghi chú đầu file về
    việc LiteLLM thay thế cả cục metadata. Bắt đầu từ rỗng là xoá `tags`.
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


def set_quota(key_alias: str, new_quota: float, actor: str) -> dict[str, Any]:
    """Đặt hạn mức cho một khoá. ĐỌC - GỘP - GHI LẠI CẢ CỤC.

    Giới hạn đã biết: hai người sửa cùng lúc thì người ghi sau đè mất thay đổi
    của người trước. Với một người quản trị thì chưa thành vấn đề; có nhiều người
    thì phải kiểm lại giá trị cũ trước khi ghi.
    """
    key = find_key(key_alias)
    if key is None:
        raise GatewayError(f"Gateway không có khoá nào tên {key_alias!r}")  # vi-ok
    metadata = _merge(key.get("metadata") or {}, new_quota, actor)
    _call(_PATH_UPDATE, "POST", {"key_alias": key_alias, "metadata": metadata})
    return metadata


def parse_amount(raw: Any) -> float:
    """Số tiền hợp lệ, hoặc `ValueError` kèm lý do đọc được.

    Đặt ở đây chứ không đặt trong `main.py` để phép kiểm chạy được trên một máy
    sạch: `main.py` kéo theo FastAPI, mà bộ kiểm của dự án phải chạy được khi
    không cài thêm gói nào. `main.py` chỉ bọc `ValueError` này thành HTTP 400.

    `bool` bị loại tường minh: trong Python `True` là một số nguyên hợp lệ, nên
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
    trước khi có gì chạm tới Gateway.
    """
    return {k: v for k, v in (fields or {}).items() if k in WRITABLE_FIELDS}
