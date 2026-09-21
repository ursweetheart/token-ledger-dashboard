"""Chặn request khi project đã hết hạn mức. Chạy BÊN TRONG container LiteLLM.

CÁCH NẠP
--------
File này KHÔNG nằm trong image: image lấy từ GHCR chỉ chứa mã của LiteLLM. Nó
được gắn vào container bằng `volumes` (xem khối `x-litellm` trong
docker-compose.yml) rồi khai trong `litellm_settings.callbacks` của
config.gateway.yaml.

KHAI SAI TÊN CALLBACK KHÔNG LÀM LITELLM DỪNG. Container vẫn lên, `/health/
liveliness` vẫn trả 200, Docker vẫn báo `healthy`, và hạn mức không chặn gì.
Nên sau khi triển khai phải gọi THẬT một lượt và xem log có dòng của file này
không - không được kết luận từ trạng thái container.

NÓ ĐỌC GÌ, VÀ VÌ SAO KHÔNG MỞ KẾT NỐI DATABASE
----------------------------------------------
LiteLLM đưa sẵn mọi thứ cần thiết vào tham số của hook:

    user_api_key_dict.metadata["quota_usd"]   hạn mức, do dashboard ghi
    user_api_key_dict.spend                   đã tiêu, LiteLLM tự cộng
    data["metadata"]["tags"]                  tag định danh của agent

nên không có câu SQL nào ở đây, không có kết nối nào phải giữ, và không có gì
phải đồng bộ.

Số đã tiêu có thể cũ tới `user_api_key_cache_ttl` (đang là 300 giây). Đó là độ
trễ đã biết và đã chấp nhận: ở mức lưu lượng hiện tại, một cửa sổ 5 phút thường
không có lượt gọi nào.
# ponytail: doc spend tu khoa da nho dem; doc thang tu database khi luu luong
# vuot ~10 luot/giay hoac khi khoan vuot vi do tre lon hon muc chap nhan duoc.

HAI KIỂU TRẢ LỜI, VÀ VÌ SAO PHẢI CÓ HAI
---------------------------------------
    agent có người chat  -> RejectedRequestError -> LiteLLM dựng một câu trả lời
                            của model, HTTP 200, chạy cả ở chế độ luồng
    agent chạy theo lô   -> lỗi mang chuỗi `429` -> app tự lùi

Hai agent phân loại đang đợi JSON. Một câu văn xuôi đi vào đó sẽ hỏng lúc phân
tích và báo thành lỗi JSON - người vận hành đi tìm bệnh ở chỗ phân tích dữ liệu
trong khi bệnh là hết tiền. Đường 429 thì đã có sẵn trong các agent đó.

PHẢI TRẢ VỀ ĐỐI TƯỢNG LỖI, KHÔNG TRẢ VỀ CHUỖI
---------------------------------------------
`proxy/utils.py:1158` chỉ đổi chuỗi thành `RejectedRequestError` khi
`call_type in ["completion", "text_completion"]`. Nhưng `/v1/chat/completions`
truyền `route_type="acompletion"` (`proxy_server.py:10086`), nên một hook trả
chuỗi sẽ cho agent HTTP 400 - đúng thứ cần tránh. Trả về đối tượng lỗi thì
LiteLLM `raise` thẳng, không xét `call_type`.

MỌI NHÁNH HỎNG ĐỀU CHO QUA
--------------------------
Hook này chạy trên MỌI request. Một lỗi ở đây là lỗi của toàn bộ Gateway, nên
không nhánh nào được ném lỗi ngoài hai nhánh chặn có chủ ý. Thiếu hạn mức, hạn
mức sai kiểu, thiếu tag - tất cả đều là "cho đi tiếp" kèm một dòng log.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

QUOTA_FIELD = "quota_usd"

# Hành động hook quyết định. Ba giá trị này là toàn bộ phần logic của file, và
# chúng KHÔNG phụ thuộc `litellm` - xem ghi chú ở `decide_action`.
PASS = "pass"
BLOCK_CHAT = "chat"
BLOCK_BATCH = "batch"

# Tag nào là agent có người chat. Tag KHÔNG khai ở đây được coi là agent chạy
# theo lô, tức nhận 429. Sai kiểu theo hướng này chỉ làm agent nghỉ; sai theo
# hướng kia làm dữ liệu rác đi vào database của một agent phân loại.
_DEFAULT_CHAT_TAGS = "contact-center,sale-agent,tla-hd,ralli"

# Câu người dùng cuối sẽ đọc. Nó phải TỰ NÓI RÕ là thông báo của hệ thống: người
# dùng không phân biệt được "model từ chối" với "hệ thống hết tiền".
_DEFAULT_MESSAGE = (
    "[Thông báo hệ thống] Hạn mức sử dụng của dịch vụ này đã hết. "
    "Đây không phải câu trả lời của mô hình. "
    "Vui lòng liên hệ quản trị viên để cấp thêm hạn mức."
)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


# PHẢI dùng `or`, không dùng tham số mặc định của `os.getenv`. Compose truyền
# `${VAR:-}` thành chuỗi RỖNG chứ không phải vắng mặt, nên `os.getenv(name,
# default)` sẽ trả "" và mặc định không bao giờ chạy. Hậu quả của bản trước:
# người dùng nhận một tin nhắn rỗng thay vì câu thông báo - không lỗi nào báo ra.
def _chat_tags() -> frozenset[str]:
    raw = os.getenv("QUOTA_CHAT_TAGS", "").strip() or _DEFAULT_CHAT_TAGS
    return frozenset(t.strip() for t in raw.split(",") if t.strip())


def _message() -> str:
    return os.getenv("QUOTA_BLOCK_MESSAGE", "").strip() or _DEFAULT_MESSAGE


def _number(raw: Any) -> float | None:
    """Số thực không âm, hoặc None. `bool` bị loại: `True` là số nguyên hợp lệ."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if value != value or value in (float("inf"), float("-inf")) or value < 0:
        return None
    return value


def _log(event: str, **fields: Any) -> None:
    """Một dòng JSON trên stdout, đọc được bằng máy.

    KHÔNG ghi nội dung câu hỏi hay câu trả lời - cùng kỷ luật với
    `turn_off_message_logging` của Gateway.
    """
    row = {"event": event,
           "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
           **fields}
    print(json.dumps(row, ensure_ascii=False), flush=True)


def _tags_of(data: dict) -> list[str]:
    meta = data.get("metadata") or data.get("litellm_metadata") or {}
    tags = meta.get("tags") if isinstance(meta, dict) else None
    return [str(t) for t in tags] if isinstance(tags, list) else []


def _identity(tags: list[str], chat_tags: frozenset[str]) -> tuple[str | None, bool]:
    """(tag định danh, có phải agent chat không).

    Tag định danh là tag khớp danh sách agent đã khai. LiteLLM tự thêm các tag
    khác (ví dụ `User-Agent: ...`), nên KHÔNG được lấy "tag đầu tiên".
    """
    for tag in tags:
        if tag in chat_tags:
            return tag, True
    for tag in tags:
        if not tag.startswith("User-Agent:"):
            return tag, False
    return None, False


def decide_action(metadata: Any, spend: Any, tags: list[str],
                  chat_tags: frozenset[str] | None = None) -> tuple[str, dict]:
    """Toàn bộ phần quyết định, KHÔNG phụ thuộc `litellm`.

    Tách ra khỏi lớp hook có chủ ý: `litellm` là một phụ thuộc nặng và không có
    trên máy phát triển nào ngoài container Gateway. Nếu logic nằm trong lớp kế
    thừa `CustomLogger` thì phép kiểm bị bỏ qua ở mọi nơi - và một phép kiểm
    không bao giờ chạy thì không bảo vệ được gì.

    Trả về `(hành động, thông tin để ghi log)`.
    """
    info: dict[str, Any] = {}
    quota = _number((metadata or {}).get(QUOTA_FIELD)
                    if isinstance(metadata, dict) else None)
    if quota is None:
        # Chưa đặt hạn mức, hoặc đặt sai kiểu. Cả hai đều là "không chặn".
        return PASS, info

    spent = _number(spend) or 0.0
    if spent < quota:
        return PASS, info

    tag, is_chat = _identity(tags, chat_tags if chat_tags is not None else _chat_tags())
    info = {"agent": tag, "quota": quota, "spent": spent,
            "reply": "message" if is_chat else "429"}
    return (BLOCK_CHAT if is_chat else BLOCK_BATCH), info


def _build_guard():
    """Dựng lớp hook. Chỉ gọi được khi `litellm` có mặt (tức trong container)."""
    import litellm
    from litellm.exceptions import RejectedRequestError
    from litellm.integrations.custom_logger import CustomLogger

    class QuotaGuard(CustomLogger):
        async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
            try:
                return self._decide(user_api_key_dict, data)
            except Exception as exc:  # noqa: BLE001 - xem ghi chú đầu file
                # Một lỗi không lường trước KHÔNG được làm hỏng Gateway. Cho qua
                # và nói ra, chứ không chặn và cũng không im.
                _log("quota_hook_error", error=type(exc).__name__)
                return None

        def _decide(self, user_api_key_dict, data: dict):
            action, info = decide_action(
                getattr(user_api_key_dict, "metadata", None),
                getattr(user_api_key_dict, "spend", None),
                _tags_of(data))
            if action == PASS:
                return None

            dry_run = _env_flag("QUOTA_DRY_RUN")
            _log("quota_block_would_have" if dry_run else "quota_block",
                 key_alias=getattr(user_api_key_dict, "key_alias", None),
                 model=data.get("model"), **info)
            if dry_run:
                return None

            message = _message()
            model = str(data.get("model") or "")
            if action == BLOCK_CHAT:
                err = RejectedRequestError(message=message, model=model,
                                           llm_provider="", request_data=data)
                # PHẢI gán lại `.message`. Lớp đó tự đặt
                #     self.message = f"litellm.RejectedRequestError: {message}"
                # (exceptions.py:556), mà `proxy_server.py` lấy ĐÚNG thuộc tính
                # này làm nội dung câu trả lời. Không gán lại thì người dùng cuối
                # đọc được tên lớp lỗi của LiteLLM trong tin nhắn.
                err.message = message
                return err

                # VÌ SAO KHÔNG DÙNG `mock_response`: đã thử ngày 20/09/2026, nó
                # chạy đúng ở cả hai chế độ NHƯNG lượt bị chặn đi vào
                # LiteLLM_SpendLogs như một lượt THÀNH CÔNG, có token và có tiền
                # (đo được: 79 token / 0,0001799 USD cho một câu thông báo, trong
                # khi không hề gọi Google). Việc đó làm hỏng đúng thứ dự án này
                # sinh ra để giữ. Đường hiện tại ghi `failure`, spend 0, token 0.
                #
                # Đổi lại, nó đòi một bản vá trong fork -- xem
                # `_REJECTED_STREAM_LOGGING_FALLBACK` trong proxy_server.py.
            # Chuỗi `429` PHẢI có trong thông điệp: agent chạy lô nhận ra đợt
            # nghỉ bằng cách tìm chuỗi đó, không bằng mã HTTP.
            return litellm.RateLimitError(message=f"429 quota exhausted. {message}",
                                          model=model, llm_provider="")

    return QuotaGuard()


# LiteLLM nạp `proxy_handler_instance` từ file này. Trên máy không có `litellm`
# (mọi máy ngoài container Gateway) thì để None - phần logic ở trên vẫn nạp và
# kiểm được.
try:
    proxy_handler_instance = _build_guard()
except ImportError:  # pragma: no cover - chỉ xảy ra ngoài container
    proxy_handler_instance = None
