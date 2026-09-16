"""Đo một đường gọi LLM, từng lượt một, rồi ghi lại đủ để tính lại về sau.

    # xem trước, không gọi mạng, không tốn gì
    python tools/diagnostics/measure_llm_path.py --duong gateway --khoa-bien CRM_VIRTUAL_KEY --thu-kho

    # hai lượt để bắt lỗi công cụ TRƯỚC khi tin số nó in ra (ô 1.5)
    python tools/diagnostics/measure_llm_path.py --duong gateway --khoa-bien CRM_VIRTUAL_KEY \
        --model gemini-2.5-flash --so-luot 2 --agent crm-feedback

    # đường gọi thẳng nhà cung cấp, để so với đường qua Gateway
    python tools/diagnostics/measure_llm_path.py --duong truc-tiep --khoa-bien KEY_BENCH_CRM_TEST \
        --model gemini-2.5-flash --so-luot 2 --agent crm-feedback


VÌ SAO FILE NÀY TỒN TẠI
-----------------------
Change `prove-the-crm-path-survives-refusal-and-outage` phải trả lời ba câu:
Gateway từ chối thì client lùi lịch nhánh nào, mất Gateway giữa chừng thì có mất
dòng không, và Gateway làm chậm thêm bao nhiêu. Cả ba đều cần **gọi thật nhiều
lượt và đo từng lượt**.

Chạy thẳng pipeline của agent để lấy mấy con số đó là sai, và sai theo cách đắt:
pipeline của CRM **tải file từ SharePoint, ghi ngược lên SharePoint, rồi gửi
email** (`src/pipeline.py` dòng 350, 743, 849). Ba việc đó không liên quan gì tới
câu hỏi, mà đều chạm vào hệ thống thật của công ty. File này tách phần cần đo ra
khỏi phần không cần đo.

KHÔNG NHÉT MỘT AGENT NÀO VÀO CODE (ô 1.2)
------------------------------------------
Không có chữ "crm" nào trong phần logic. Agent, model, khoá, số lượt, đường đi —
tất cả là tham số. CRM chỉ là agent ĐẦU TIÊN được đo bằng nó, không phải agent
duy nhất. Đo agent khác thì đổi tham số, không đổi file.

KHOÁ TRUYỀN BẰNG TÊN BIẾN, KHÔNG TRUYỀN BẰNG GIÁ TRỊ
-----------------------------------------------------
`--khoa-bien` nhận TÊN của biến môi trường, không nhận khoá. Truyền thẳng khoá
vào dòng lệnh thì nó nằm lại ba chỗ không xoá được: lịch sử shell, danh sách tiến
trình (`ps` của mọi user trên máy), và nhật ký nếu ai đó bật log lệnh.
File này cũng KHÔNG BAO GIỜ in khoá ra, kể cả khi báo lỗi — chỉ in tên biến và độ
dài.

NHỮNG VIỆC FILE NÀY KHÔNG LÀM (ô 1.4)
--------------------------------------
Không tải và không ghi SharePoint. Không gửi email. Không ghi Excel. Không đụng
vào database. Nó chỉ gọi HTTP rồi ghi một file JSONL. Cố ý không `import` bất kỳ
module nào của agent, để một lần sửa nhầm bên đó không kéo theo tác dụng phụ ở
đây.

VÌ SAO DÙNG HTTP TRẦN, KHÔNG DÙNG SDK
--------------------------------------
Hai lý do. Một là SDK của Google **không có** trong môi trường chạy dashboard,
nên thêm nó vào chỉ để đo là thêm một thứ phải bảo trì. Hai là SDK **giấu mất**
đúng thứ cần đo: mã HTTP thật, header, và `request_id`. Gọi trần thì cái gì
Google trả về là cái đó vào sổ.

GHI RA JSONL, MỖI LƯỢT MỘT DÒNG (ô 1.3)
----------------------------------------
Mỗi dòng đủ để tính lại mọi con số sau này mà không phải gọi lại: mốc bắt đầu,
mã trả về, độ trễ, token vào/ra/suy nghĩ/tổng, `request_id`, và cả nội dung trả
về. Có nội dung mới so được kết quả hai đường trên cùng đầu vào — đó là việc 7.6
của change trước, và nếu chỉ ghi con số thì phải gọi lại lần nữa mới so được.

TOKEN SUY NGHĨ ĐƯỢC GHI RIÊNG
------------------------------
Đo 10/09: `gemini-2.5-flash` trả `vào 13 · ra 10 · tổng 53`. Chênh 30 token là
`thoughtsTokenCount`, một NGĂN THỨ BA nằm ngoài vào và ra. Cộng vào/ra rồi coi là
tổng sẽ hụt đúng phần đó. Nên ở đây bốn con số được ghi TÁCH NHAU, và phần chênh
không giải thích được cũng được ghi ra thay vì làm tròn cho khớp.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Địa chỉ Vertex express. Trùng với `api_base` của các tuyến gemini trong
# `docker/gateway/config.gateway.yaml`, nên đường "trực tiếp" và đường "gateway"
# cuối cùng gõ vào CÙNG MỘT CỬA của Google. Khác nhau chỉ ở chặng ở giữa, và đó
# đúng là thứ cần đo.
VERTEX_BASE = "https://aiplatform.googleapis.com/v1/publishers/google/models"

# Câu nhắc mặc định. Cố tình tầm thường và ngắn: file này đo ĐƯỜNG ĐI, không đo
# chất lượng phân loại. Câu càng ngắn thì token càng ít và tiền càng nhỏ.
CAU_MAC_DINH = 'Trả về đúng JSON này, không thêm gì: {"trang_thai":"ok"}'
HE_THONG_MAC_DINH = "Bạn là bộ phân loại. Chỉ trả về JSON hợp lệ."


def bay_gio() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def lay_khoa(ten_bien: str) -> str:
    """Đọc khoá từ biến môi trường. Không in giá trị ra, kể cả khi hỏng."""
    gia_tri = os.environ.get(ten_bien, "")
    if not gia_tri:
        raise SystemExit(
            "Thiếu khoá: biến môi trường `%s` rỗng hoặc chưa đặt.\n"
            "Đặt nó rồi chạy lại. KHÔNG truyền khoá thẳng vào dòng lệnh." % ten_bien
        )
    return gia_tri


def than_yeu_cau(duong: str, model: str, he_thong: str, cau: str,
                 nhiet_do: float, token_ra_toi_da: int, che_do_json: bool) -> dict:
    """Dựng thân yêu cầu cho từng đường.

    Hai đường có hình dạng khác nhau, và đó là chuyện có thật chứ không phải
    tuỳ tiện: Gateway nói tiếng OpenAI, còn Vertex nói tiếng Google. Chỗ dễ sai
    nhất là prompt hệ thống — OpenAI đặt nó thành một `message`, còn Google đặt
    nó ra NGOÀI `contents`. Nhét nhầm vào `contents` thì cấu trúc prompt khác đi
    mà kết quả vẫn ra JSON, nên nhìn không biết.
    """
    if duong == "gateway":
        than = {
            "model": model,
            "messages": [
                {"role": "system", "content": he_thong},
                {"role": "user", "content": cau},
            ],
            "temperature": nhiet_do,
            "max_tokens": token_ra_toi_da,
        }
        if che_do_json:
            than["response_format"] = {"type": "json_object"}
        return than

    than = {
        "contents": [{"role": "user", "parts": [{"text": cau}]}],
        "systemInstruction": {"parts": [{"text": he_thong}]},
        "generationConfig": {
            "temperature": nhiet_do,
            "maxOutputTokens": token_ra_toi_da,
        },
    }
    if che_do_json:
        than["generationConfig"]["responseMimeType"] = "application/json"
    return than


def doc_ket_qua(duong: str, than: dict) -> dict:
    """Bóc bốn con số token và nội dung ra khỏi hình dạng riêng của từng đường."""
    if duong == "gateway":
        dung = than.get("usage") or {}
        lua = (than.get("choices") or [{}])[0]
        noi_dung = ((lua.get("message") or {}).get("content")) or ""
        # LiteLLM chuyển tiếp token suy nghĩ trong `completion_tokens_details`
        # khi nhà cung cấp có báo. Không có thì để None, KHÔNG để 0 — "không báo"
        # khác "báo là 0".
        chi_tiet = dung.get("completion_tokens_details") or {}
        return {
            "noi_dung": noi_dung,
            "token_vao": dung.get("prompt_tokens"),
            "token_ra": dung.get("completion_tokens"),
            "token_suy_nghi": chi_tiet.get("reasoning_tokens"),
            "token_tong": dung.get("total_tokens"),
            "request_id": than.get("id"),
        }

    dung = than.get("usageMetadata") or {}
    ung_vien = (than.get("candidates") or [{}])[0]
    cac_phan = ((ung_vien.get("content") or {}).get("parts")) or []
    noi_dung = "".join(p.get("text", "") for p in cac_phan)
    return {
        "noi_dung": noi_dung,
        "token_vao": dung.get("promptTokenCount"),
        "token_ra": dung.get("candidatesTokenCount"),
        "token_suy_nghi": dung.get("thoughtsTokenCount"),
        "token_tong": dung.get("totalTokenCount"),
        "request_id": than.get("responseId"),
    }


def goi_mot_luot(duong: str, model: str, khoa: str, base_url: str, nguoi_dung: str,
                 than: dict, han_giay: float) -> dict:
    """Gọi đúng một lượt. Mọi lỗi đều thành một dòng sổ, không ném ra ngoài.

    Một lượt hỏng cũng là một phép đo — nhất là ở change này, nơi câu hỏi chính
    là "bị từ chối thì chuyện gì xảy ra". Ném ngoại lệ ra ngoài sẽ làm mất đúng
    dòng đáng giá nhất.
    """
    if duong == "gateway":
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": "Bearer " + khoa,
            "Content-Type": "application/json",
            "X-User": nguoi_dung,
        }
    else:
        # Khoá đi trong query string là do Google quy định cho express key.
        # Nó KHÔNG được ghi vào sổ đo ở dưới — xem `url_ghi_so`.
        url = "%s/%s:generateContent?key=%s" % (VERTEX_BASE, model, khoa)
        headers = {"Content-Type": "application/json"}

    url_ghi_so = url.split("?")[0] if duong != "gateway" else url

    du_lieu = json.dumps(than).encode("utf-8")
    yeu_cau = urllib.request.Request(url, data=du_lieu, headers=headers, method="POST")

    bat_dau = bay_gio()
    dong_ho = time.perf_counter()
    dong = {"bat_dau_utc": bat_dau, "duong": duong, "model": model, "url": url_ghi_so}

    try:
        with urllib.request.urlopen(yeu_cau, timeout=han_giay) as tra_ve:
            tho = tra_ve.read().decode("utf-8", "replace")
            dong["do_tre_ms"] = round((time.perf_counter() - dong_ho) * 1000, 1)
            dong["ma_tra_ve"] = tra_ve.status
            # `x-request-id` của LiteLLM và `x-guploader-uploadid` của Google đều
            # là đường lần ngược khi phải hỏi nhà cung cấp về một lượt cụ thể.
            dong["header_id"] = (tra_ve.headers.get("x-request-id")
                                 or tra_ve.headers.get("x-litellm-call-id") or None)
            try:
                dong.update(doc_ket_qua(duong, json.loads(tho)))
            except json.JSONDecodeError:
                dong["loi"] = "tra ve 200 nhung than khong phai JSON"
                dong["than_tho"] = tho[:800]
    except urllib.error.HTTPError as e:
        tho = e.read().decode("utf-8", "replace")
        dong["do_tre_ms"] = round((time.perf_counter() - dong_ho) * 1000, 1)
        dong["ma_tra_ve"] = e.code
        dong["header_id"] = e.headers.get("x-request-id") if e.headers else None
        # Giữ NGUYÊN VĂN thân lỗi. Đây là chỗ phân biệt 429 của nhà cung cấp với
        # 429 do chính Gateway sinh ra, và hai cái đó dẫn tới hai kết luận khác
        # hẳn nhau ở mục 2 của change.
        dong["than_loi"] = tho[:1200]
    except Exception as e:                                    # noqa: BLE001
        dong["do_tre_ms"] = round((time.perf_counter() - dong_ho) * 1000, 1)
        dong["ma_tra_ve"] = None
        dong["loi"] = type(e).__name__ + ": " + str(e)[:300]

    return dong


def kiem_tong_token(dong: dict) -> str | None:
    """Bốn con số token có khớp nhau không.

    vào + ra + suy nghĩ có bằng tổng không. Lệch thì GHI RA, không làm tròn cho
    khớp: phần lệch chính là ngăn token mà ta chưa biết tên.
    """
    v, r, s, t = (dong.get("token_vao"), dong.get("token_ra"),
                  dong.get("token_suy_nghi"), dong.get("token_tong"))
    if v is None or r is None or t is None:
        return None
    cong = v + r + (s or 0)
    if cong == t:
        return None
    return "lech %+d token (vao %s + ra %s + suy nghi %s = %s, nhung tong bao %s)" % (
        t - cong, v, r, s if s is not None else "khong bao", cong, t)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Đo một đường gọi LLM, từng lượt một. Không đụng SharePoint, "
                    "không gửi email, không ghi Excel, không đụng database.")
    p.add_argument("--duong", required=True, choices=["gateway", "truc-tiep"],
                   help="gateway = qua Gateway nội bộ; truc-tiep = gọi thẳng nhà cung cấp")
    p.add_argument("--khoa-bien", required=True,
                   help="TÊN biến môi trường chứa khoá. KHÔNG phải giá trị khoá")
    p.add_argument("--model", default="gemini-2.5-flash")
    p.add_argument("--agent", default="khong-ro",
                   help="Nhãn agent, chỉ để ghi vào sổ đo. Không đổi cách gọi")
    p.add_argument("--so-luot", type=int, default=2)
    p.add_argument("--base-url", default="http://127.0.0.1:4000",
                   help="Chỉ dùng cho --duong gateway")
    p.add_argument("--nguoi-dung", default="svc.do-duong-llm",
                   help="Giá trị header X-User, để sổ Gateway quy được về ai")
    p.add_argument("--cau", default=CAU_MAC_DINH)
    p.add_argument("--he-thong", default=HE_THONG_MAC_DINH)
    p.add_argument("--nhap", type=Path,
                   help="File văn bản, mỗi dòng một câu nhắc. Có thì --cau bị bỏ qua")
    p.add_argument("--nhiet-do", type=float, default=0.0)
    p.add_argument("--token-ra-toi-da", type=int, default=8192)
    p.add_argument("--tat-json", action="store_true",
                   help="Tắt chế độ JSON, để đo chênh lệch do chính tham số đó gây ra")
    p.add_argument("--nghi", type=float, default=0.0,
                   help="Số giây nghỉ giữa hai lượt")
    p.add_argument("--rung", type=float, default=0.0,
                   help="Cộng thêm ngẫu nhiên 0..RUNG giây, giống cách agent tự giãn nhịp")
    p.add_argument("--han-giay", type=float, default=300.0)
    p.add_argument("--ra", type=Path,
                   help="File JSONL để ghi. Mặc định var/do-duong-llm-<mốc>.jsonl")
    p.add_argument("--thu-kho", action="store_true",
                   help="In ra thứ SẼ gửi rồi dừng. Không gọi mạng, không tốn tiền")
    a = p.parse_args()

    if a.so_luot < 1:
        raise SystemExit("--so-luot phải ≥ 1")

    cac_cau = [a.cau]
    if a.nhap:
        cac_cau = [d.strip() for d in a.nhap.read_text(encoding="utf-8").splitlines() if d.strip()]
        if not cac_cau:
            raise SystemExit("File --nhap không có dòng nào dùng được")

    che_do_json = not a.tat_json
    mau = than_yeu_cau(a.duong, a.model, a.he_thong, cac_cau[0],
                       a.nhiet_do, a.token_ra_toi_da, che_do_json)

    print("=" * 72)
    print("ĐO ĐƯỜNG GỌI LLM")
    print("=" * 72)
    print("  đường        :", a.duong, "" if a.duong == "gateway" else "(thẳng nhà cung cấp)")
    print("  model        :", a.model)
    print("  agent (nhãn) :", a.agent)
    print("  số lượt      :", a.so_luot)
    print("  chế độ JSON  :", "BẬT" if che_do_json else "TẮT")
    print("  đích         :", a.base_url if a.duong == "gateway" else VERTEX_BASE)
    print("  khoá         : lấy từ biến `%s`, KHÔNG in ra" % a.khoa_bien)
    print("  câu nhắc     :", len(cac_cau), "câu")
    print()
    print("KHÔNG làm: SharePoint · email · Excel · database")
    print()

    if a.thu_kho:
        print("--thu-kho: đây là thân yêu cầu SẼ gửi, và KHÔNG gọi mạng.")
        print(json.dumps(mau, indent=2, ensure_ascii=False))
        return 0

    khoa = lay_khoa(a.khoa_bien)

    dich = a.ra or (ROOT / "var" /
                    ("do-duong-llm-%s.jsonl" % datetime.now().strftime("%Y%m%d-%H%M%S")))
    dich.parent.mkdir(parents=True, exist_ok=True)

    cac_dong: list[dict] = []
    with dich.open("w", encoding="utf-8") as f:
        for i in range(a.so_luot):
            cau = cac_cau[i % len(cac_cau)]
            than = than_yeu_cau(a.duong, a.model, a.he_thong, cau,
                                a.nhiet_do, a.token_ra_toi_da, che_do_json)
            dong = goi_mot_luot(a.duong, a.model, khoa, a.base_url,
                                a.nguoi_dung, than, a.han_giay)
            dong["so_thu_tu"] = i + 1
            dong["agent"] = a.agent
            dong["cau_nhac"] = cau
            lech = kiem_tong_token(dong)
            if lech:
                dong["canh_bao_token"] = lech

            f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            f.flush()          # ghi ngay từng dòng: dừng giữa chừng vẫn còn sổ
            cac_dong.append(dong)

            ma = dong.get("ma_tra_ve")
            print("  lượt %-3d %-5s %8.1f ms  vào/ra/nghĩ/tổng %s/%s/%s/%s  %s" % (
                i + 1, ma if ma is not None else "LỖI", dong.get("do_tre_ms", 0),
                dong.get("token_vao"), dong.get("token_ra"),
                dong.get("token_suy_nghi"), dong.get("token_tong"),
                (dong.get("loi") or "")[:40]))
            if lech:
                print("        ! " + lech)

            if i + 1 < a.so_luot and (a.nghi or a.rung):
                time.sleep(a.nghi + random.random() * a.rung)

    ok = [d for d in cac_dong if d.get("ma_tra_ve") == 200]
    tre = sorted(d["do_tre_ms"] for d in ok) if ok else []
    print()
    print("-" * 72)
    print("  gọi %d lượt · %d thành công · %d hỏng" % (
        len(cac_dong), len(ok), len(cac_dong) - len(ok)))
    if tre:
        print("  độ trễ trung vị : %.1f ms" % tre[len(tre) // 2])
        print("  độ trễ nhỏ/lớn  : %.1f / %.1f ms" % (tre[0], tre[-1]))
    tong = sum(d.get("token_tong") or 0 for d in ok)
    nghi = sum(d.get("token_suy_nghi") or 0 for d in ok)
    print("  token tổng      : %d (trong đó suy nghĩ %d)" % (tong, nghi))
    ma_khac = sorted({str(d.get("ma_tra_ve")) for d in cac_dong if d.get("ma_tra_ve") != 200})
    if ma_khac:
        print("  mã khác 200     :", ", ".join(ma_khac))
    print("  sổ đo           :", dich)
    print("-" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
