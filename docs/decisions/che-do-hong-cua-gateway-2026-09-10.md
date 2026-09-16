# Gateway hỏng thì nên chết hay nên đi tiếp — chốt 10/09/2026

## Quyết định

**Giai đoạn dev: giữ cửa chặn cứng.** `docker/gateway/entrypoint.sh` thiếu khoá thì dừng hẳn,
không cho LiteLLM khởi động.

**Khi triển khai lên server: phải sửa thành fall back.** Chốt bởi lead, anh Tuấn chuyển lại
ngày 10/09.

Nguyên văn ý của lead:

> ko , phải fall back
>
> nếu mà báo lỗi hệ thống bị gián đoạn
>
> cái việc mình track không được ưu tiên trước hệ thống ổn định

## Vì sao hai giai đoạn lại ngược nhau

Không phải ai đó sai. Hai giai đoạn tối ưu cho hai thứ khác nhau.

| | dev | production |
|---|---|---|
| Sợ nhất điều gì | Lỗi **ẩn**, không ai thấy | Hệ thống **đứng**, người dùng chịu |
| Nên hỏng kiểu gì | Dừng ngay, ồn ào | Đi tiếp, có ghi lại |
| Cái giá chấp nhận được | Mất thời gian của người dev | Mất một phần số liệu theo dõi |

Lý lẽ của lead đứng vững: **đo đạc là việc phụ, chạy được mới là việc chính.** Một dashboard
thiếu vài dòng thì vẫn dùng được. Một hệ thống không khởi động được thì không.

## Nhưng có một điều phải giữ khi sửa

Hôm 10/09 đã tìm ra một lỗi thật, và nó sinh ra **chính vì** hệ thống đã "đi tiếp" khi thiếu
khoá: `docker-compose.yml` viết `${KEY_BENCH_CRM_TEST:-}`, dấu `:-` biến khoá thiếu thành chuỗi
rỗng, container lên bình thường, cửa kiểm sức khoẻ trả `200`, và **tuyến CRM chết im lặng**
suốt từ lúc `.env` đổi tên biến cho tới khi có người gọi thật.

Nên "fall back" và "hỏng im lặng" **không được là một**. Ba điều phải có khi sửa cho server:

1. **Vẫn khởi động** — đúng ý lead, không chặn hệ thống
2. **Nhưng phải kêu to** — ghi log mức `ERROR` lúc khởi động, không phải `WARNING` lẫn giữa
   trăm dòng khác
3. **Và cửa kiểm sức khoẻ phải nói thật** — `/health/liveliness` trả `200` trong khi tuyến đã
   chết là điều đã xảy ra hôm nay. Cần một cửa kiểm phân biệt "tiến trình còn sống" với
   "tuyến gọi được"

Điều 3 là điều đáng làm nhất, và nó đúng tinh thần của lead hơn cả cửa chặn cứng: hệ thống
vẫn chạy, mà người vận hành vẫn biết có thứ đang hỏng.

## Việc phải làm trước khi lên server

- [ ] Đổi cửa chặn cứng trong `entrypoint.sh` thành cảnh báo, giữ lại phần chặn cho
      `LITELLM_MASTER_KEY` — khoá đó rỗng thì cổng `4000` mở cho bất kỳ ai, đó là lỗ hổng bảo
      mật chứ không phải mất số liệu
- [ ] Thêm một cửa kiểm sức khoẻ soi được từng tuyến, không chỉ soi tiến trình
- [ ] Bỏ `:-` ở những biến mà rỗng đồng nghĩa với hỏng, hoặc giữ `:-` nhưng bắt buộc phải có
      cảnh báo đi kèm
