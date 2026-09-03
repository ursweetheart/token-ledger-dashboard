# Ghi độ trễ và kết cục của từng lượt gọi qua Gateway

## Why

Master Plan mục **"Ghi đủ trường cần cho dashboard ngay tại thời điểm gọi"** (mốc 21/09/2026)
đòi bản ghi mỗi request gồm **12 trường**. Đếm thật trên `fact_call` ngày 31/08:

```
   CO   token vao · token ra · token cache · chi phi · model · provider
        · agent · nguoi dung · phong ban (qua account) · thoi diem      = 10
   THIEU  DO TRE          <- so DA CO san, chi thieu duong nap
          MA TRA VE       <- so DA CO san, hien chi dung de LOC roi vut
```

Hai trường thiếu **không phải vì Gateway không ghi** — nó ghi cả hai:

```
   request_duration_ms                      45/45 dong co gia tri
   metadata.error_information.error_code     5/5 dong hong co TRUONG
                                             2/5 co ma that (401, 403)
                                             3/5 mang chuoi rong
```

`db/load_gateway.py` không nạp chúng, và `fact_call` không có cột để chứa.

### Vì sao độ trễ đáng giá hơn vẻ ngoài

`db/build_performance.py` ghi lại một giới hạn **về mặt cấu trúc** của nguồn monitoring:

> *"`fact_monitoring` CÓ cột p95 nhưng đó là p95 CỦA TỪNG PHÚT. Trung bình các p95 không ra
> p95 của ngày: trung bình của p95=2,1s trên 100 lượt và p95=8,4s trên 2 lượt cho 5,25s,
> trong khi số thật khoảng 2,3s."*

Dashboard hiện phải lấy phân vị từ một file histogram gộp tay (`fact_latency_daily`), và
chính file đó mang cột `lech_phan_tram` để ghi lại sai số của cách làm đó.

Gateway **có độ trễ thô của từng lượt gọi**, nên tính được phân vị **chính xác**, không qua
bước gộp histogram nào. Đây là thứ ba nguồn cũ không làm được — không phải vì thiếu công sức
mà vì chúng chỉ phơi ra số đã tổng hợp.

Đo 31/08 trên 40 lượt thành công:

```
   nho nhat 609 ms · trung binh 1.002 ms · p95 1.805 ms · lon nhat 3.136 ms
```

### Vì sao mã trả về đáng giá

Sổ Gateway ghi rõ lý do hỏng, chứ không chỉ ghi "hỏng":

```
   error_code 403  "key not allowed to access model. This key can only access
                    models=['gemini-flash-lite']. Tried to access gemini-flash"
   error_code 401
```

Hôm nay **toàn bộ thông tin đó bị vứt**: bộ nạp lọc `status='success'` rồi bỏ phần còn lại.
Ta chỉ biết *"có 5 lượt hỏng"*, không biết vì sao — trong khi câu trả lời nằm sẵn trong sổ.

## What Changes

- **Migration 006**: `fact_call` thêm `duration_ms`, `outcome`, `error_code`.
- **`db/load_gateway.py`**: nạp cả **lượt hỏng quy được về agent** (3/5 dòng ngày 31/08), kèm
  độ trễ và mã lỗi. Hôm nay chúng bị loại hoàn toàn.
- **`db/build_usage_daily.py`**: lọc `outcome = 'success'` khi tổng hợp — nếu không, lượt hỏng
  sẽ lọt vào số token và tiền.
- **`scripts/audit_db.py`**: cập nhật các phép kiểm đối chiếu cho khớp định nghĩa mới.

Không đụng: sổ `LiteLLM_SpendLogs` (chỉ đọc), ba nguồn cũ, tầng view, tầng frontend.

## Impact

- Đóng mục Master Plan mốc **21/09** — mốc gần nhất trong các mục chưa xong.
- Cấp nguyên liệu cho mục **"Ghi log dạng time-series"** (mốc 30/09): có độ trễ thô thì mới
  tính được phân vị chính xác theo ngày và theo giờ.
- Biết được **vì sao** một lượt gọi hỏng, thay vì chỉ biết là có hỏng.
- Rủi ro chính: nạp thêm lượt hỏng làm đổi ý nghĩa của `fact_call`. Chống bằng cách bắt mọi
  chỗ tổng hợp phải lọc `outcome` tường minh, và bằng phép kiểm đối chiếu số token trước/sau.
  Đo 31/08: **14 token** sẽ rò vào số liệu sử dụng nếu quên bộ lọc — xem design ③.
