## 0. Chặn — phải xong trước

- [x] 0.1 **ĐẠT TRÊN THỰC TẾ, dù change kia còn 1 ô.** `route-the-crm-agent-through-the-gateway` đang **54/55**, ô còn lại là 7.6 (so kết quả phân loại hai đường trên cùng đầu vào).
      Ô chặn này đòi "có đường thông để mà ép hỏng". Điều đó **đã chứng minh bằng đo**: 32 lượt gọi thật đi trọn đường CRM → Gateway → Vertex → Google trong ngày, và cả 32 quy đúng về `agent_id = 7` (ô 4.5). Ô 7.6 là phép **so sánh chất lượng**, không phải điều kiện để đường chạy được.
      Ghi rõ để người đọc sau không tưởng là bỏ qua khâu chặn: **cái ô này đòi đã có, cái còn thiếu là thứ khác.**
- [x] 0.2 **ĐÃ CHỐT (anh Tuấn, 10/09): khoảng 50 lượt, đủ cho mục 1 tới 3.** Mục 4 (batch cỡ production, ~502 lượt) và mục 5 (so độ trễ hai đường) **NẰM NGOÀI** trần này và phải hỏi lại trước khi chạy.
      Đã dùng tới giờ: **2 lượt · 120 token · 0 đồng đáng kể** (phép thử công cụ ở ô 1.5). Còn lại khoảng 48 lượt.
      Ghi thêm cho lần sau: chi phí thật của change này không nằm ở token mà ở **thời gian**. Đo được ở ô 1.5 là **~12 giây một lượt** cho một câu nhắc 31 token. Một batch 502 lượt chạy tuần tự sẽ mất hơn một tiếng rưỡi, chưa tính giãn nhịp — nên trần chi tiêu của mục 4 phải là trần THỜI GIAN chứ không chỉ trần tiền
- [x] 0.3 **Đã đo, 10/09. Trả lời: Gateway KHÔNG che 429 khỏi CRM — nhưng nó làm chậm mỗi lượt thêm ~123,7 giây.** Đo bằng log của `litellm-1` trong lúc chạy phép ép 429 với `rpm: 1`, không suy từ code:

      ```
      06:43:35  Router: Exception litellm.RateLimitError: No deployments available
                         rpm_limit: 1, current_rpm: 1.0
      06:44:35  Router: ... LiteLLM Retried: 3 times, LiteLLM Max Retries: 3
                         No fallback model group found for original model_group=gemini-2.5-flash
                POST /v1/chat/completions HTTP/1.1" 429 Too Many Requests
      ```

      Hai điều đọc được, cả hai đều là **đo**:
      - **`429` tới được CRM.** Dòng cuối là mã trả về thật cho người gọi. Nên phép đo của mục 2 đo đúng đường cần đo, và giả thiết xấu nhất ở ô 0.3 **không** xảy ra. Khớp với ô 0.4: không có fallback nào nhận `gemini-2.5-flash` nên router không có đường nào khác để đi
      - **Nhưng Gateway tự thử lại 3 lần trước khi chịu trả 429, và việc đó tốn ~60 giây** (`06:43:35` → `06:44:35`). Lượt sau đo lại được `06:44:56` → `06:45:59`, tức **63 giây**. `num_retries: 3` không che được lỗi, nó chỉ hoãn lỗi

      **Hai con số, đừng lẫn.** `~60`s ở trên là khoảng cách giữa hai dòng log của `litellm-1`. Con số người gọi thật sự chờ là **`~123,7` giây**, đo ở ô 2.3 từ chính phía CRM và khớp với mốc thời gian trong sổ Gateway. Lấy con số của người gọi; con số log chỉ là một phần cửa sổ.

      **Hệ quả cho ô 2.4.** Khoảng giữa hai lượt gọi của CRM không phải `10, 20, 30`, cũng không phải `13,5 / 20 / 30` như tôi mô phỏng. Đo thật ra `134,21`s và `144,14`s. Phép mô phỏng chỉ tính phần CRM ngủ nên nó thiếu hẳn số hạng lớn nhất là tầng Gateway.
      Lúc viết dòng này tôi còn kết luận thêm rằng "số khoảng (3 so với 2) là cách duy nhất còn đứng được". **Câu đó cũng sai, và ô 2.4 đã bác bỏ bằng phép đo:** cả hai nhánh đều cho đúng 2 khoảng. Thứ duy nhất phân biệt được mà không cần log là **câu lỗi cuối** (ô 2.4b).

      **Và đây là con số đáng báo lại nhóm CRM nhất trong cả change:** một lần `429` dứt điểm khiến CRM mất `3 × 123,7` giây chờ Gateway, cộng `10,2 + 20,4 + 31,4` giây tự ngủ, tức **433,99 giây — 7 phút 14 giây cho một lô rồi vẫn hỏng**. Trong đó 31,4 giây cuối là ngủ vô ích (ô 6.5)
- [x] 0.4 **Đã xác nhận bằng đo, 10/09 — tuyến CRM KHÔNG có fallback.** Lộ ra khi làm task 4.1 của change trước. Cấu hình chỉ khai đúng một dòng fallback, và nó **không** thuộc tuyến CRM:

  ```yaml
  fallbacks:
    - gemini-flash: ["gemini-flash-preview"]
  ```

  Và LiteLLM tự nói ra lúc chạy, chứ không phải tôi suy từ file: `No fallback model group found for original model_group=gemini-2.5-flash. Fallbacks=[{'gemini-flash': ['gemini-flash-preview']}]`. Nên khi hết hạn mức, tuyến CRM sẽ **trả 429** chứ không lặng lẽ đổi tuyến, và phép đo 429 của nhóm 2 đo đúng đường cần đo. Nguyên văn: Xác nhận tuyến CRM **không** khai `fallbacks`. Có fallback thì hết hạn mức sẽ đổi tuyến chứ không trả 429, và phép đo 429 đo một đường khác hẳn

## 1. Harness thành công cụ dùng lại được

- [x] 1.1 **Xong** — `tools/do_duong_llm.py`. Không nằm trong `db/` hay `scripts/`
- [x] 1.2 **Xong, và đã kiểm bằng máy chứ không bằng mắt.** Sáu thứ đều là tham số: `--agent`, `--khoa-bien`, `--model`, `--so-luot`, `--duong` (`gateway` | `truc-tiep`), `--base-url`. Không có chuỗi `crm` nào trong phần logic; nó chỉ xuất hiện ở ví dụ trong docstring.
      **Khoá nhận bằng TÊN BIẾN, không nhận giá trị** (`--khoa-bien`). Truyền khoá thẳng vào dòng lệnh sẽ để lại dấu ở ba chỗ không xoá được: lịch sử shell, danh sách tiến trình mà mọi user trên máy đọc được, và nhật ký lệnh nếu ai bật
- [x] 1.3 **Xong, ghi JSONL mỗi lượt một dòng.** Kiểm bằng máy trên sổ đo thật: đủ cả 6 trường task này đòi — `bat_dau_utc` (ISO, có múi giờ), `ma_tra_ve`, `do_tre_ms`, `token_vao`, `token_ra`, `request_id`.
      Ghi thêm 10 trường nữa để không phải gọi lại: `token_suy_nghi`, `token_tong`, `noi_dung`, `cau_nhac`, `duong`, `model`, `agent`, `so_thu_tu`, `header_id`, `url`. **`noi_dung` là trường quan trọng nhất trong nhóm thêm** — có nó mới so được kết quả hai đường trên cùng đầu vào (ô 7.6 của change trước) mà không phải trả tiền gọi lần nữa.
      **Khoá KHÔNG lọt vào sổ**: đường trực tiếp bắt buộc để khoá trong query string, nên `url` được cắt bỏ phần sau dấu `?` trước khi ghi. Đã kiểm bằng máy: không có chuỗi `key=` nào trong file
- [x] 1.4 **Xong, và bảo đảm bằng cấu trúc chứ không bằng lời hứa.** File không `import` bất kỳ module nào của agent, chỉ dùng thư viện chuẩn. Không có đường nào dẫn tới SharePoint, email, Excel hay database.
      **Đây không phải lo hão.** Trong lúc làm việc này tôi đã hai lần vô tình chạy đúng `src/pipeline.py` của CRM, vì entrypoint của image `crm-classifier:test` là `python src/pipeline.py` nên tham số truyền vào bị nối thêm vào sau chứ không thay thế. Nó chỉ dừng lại vì thiếu cấu hình SharePoint. Có `.env` đầy đủ thì nó đã tải file thật, ghi ngược lên SharePoint (`pipeline.py:743`, `:849`) và gửi email. Muốn chạy thứ gì trong image đó phải có `--entrypoint python`
- [x] 1.5 **Xong — 2 lượt, cả hai 200, và phép thử này bắt được một lỗi thật.**
      Lỗi bắt được: tên biến môi trường chứa khoá **không phải** `KEY_BENCH_CRM_TEST` như ghi trong nhật ký cũ, mà là `KEY_BENCH_CRM_TEST_GG_AIA_STU`. Chạy thẳng batch lớn sẽ hỏng toàn bộ ở lượt đầu.
      Số đo, hai lượt giống hệt nhau ở nhiệt độ 0: `31` token vào · `8` ra · `21` suy nghĩ · `60` tổng; độ trễ `11.911` và `11.971` ms.
      **Phép kiểm cộng token trong công cụ ĐẠT**: `31 + 8 + 21 = 60`, khớp đúng con số Google báo. Đây là bằng chứng thứ tư cho thấy token suy nghĩ là **ngăn thứ ba** nằm ngoài vào và ra — và ở lượt này nó chiếm **21/60, tức 35%** tổng token. Công cụ ghi bốn con số TÁCH NHAU, và sẽ kêu nếu ba số con không cộng ra số tổng

## 2. Ép 429 và xem CRM lùi lịch nhánh nào

- [x] 2.1 **Xong, và lấy được mà KHÔNG tốn lượt gọi nào** — đọc từ 12 dòng tuyến CRM đã có trong `LiteLLM_SpendLogs`, thay vì bắn thêm request. Đo lúc dựng lại stack ngày 10/09, sau `docker compose --profile gateway up -d gateway-lb`:

      | mốc | giá trị |
      |---|---|
      | tổng số dòng trong sổ | **470** |
      | số dòng tuyến CRM (`model_group='gemini-2.5-flash'`) | **12** |
      | dòng mới nhất | `2026-09-09 18:32:46` |
      | độ trễ trung vị, chỉ tính 10 lượt thành công | **1,461**s |
      | nhanh nhất / chậm nhất | `0,488`s / `38,239`s |

      **Nhịp thực đạt: không lấy được từ mốc nền, và đó là câu trả lời đúng chứ không phải thiếu sót.** 12 dòng này rải trên hai ngày, phần lớn là phép thử tay từng lượt một, nên không có đoạn nào chạy liên tục để tính lượt/phút. Nhịp thực đạt phải đo trong chính lượt chạy của mục 2.

      Hai điều phải mang sang lúc đọc kết quả mục 2:
      - **Trung vị 1,461s nhưng chậm nhất 38,239s.** Ba trong mười lượt mất `11,8` · `27,4` · `38,2` giây mà không có lý do đã biết. Đây đúng là hiện tượng ở mục 8.2 của `docs/reference/dua-crm-qua-gateway-10-09.md`, **vẫn chưa giải thích được**. Nên một lượt chậm 30 giây ở mục 2 **không** tự động là dấu của nhánh 429 — nó có thể là cái này. Phải phân biệt bằng **số khoảng** và **câu lỗi** (ô 2.4, 2.4b), không phải bằng một con số đơn lẻ
      - Hai dòng có `total_tokens = 0` và độ trễ `0,000` / `0,001`s là các lượt bị chặn ở cửa xác thực, không phải lượt gọi. Đã loại khỏi phép tính trung vị. Nếu tính cả thì trung vị tụt xuống `0,714`s, một con số sai
- [x] 2.2 **Xong.** Hạ `rpm: 15` → `rpm: 1` ở **dòng 103** của `docker/gateway/config.gateway.yaml`, là dòng của tuyến `gemini-2.5-flash`. Sửa theo **số dòng**, không theo khớp chuỗi, vì file có ba chỗ ghi `rpm: 15` (dòng 40 `gemini-flash-preview`, dòng 49 `gemini-flash-lite`, dòng 103 tuyến CRM). Xác nhận bằng `git diff`: đúng một dòng đổi. Rồi `docker compose --profile gateway restart litellm-1 litellm-2` để nạp lại file.
      Ép đúng ở **cửa Gateway từ chối** như task yêu cầu: không bắn dồn, chỉ một lượt hâm nóng rồi để CRM tự gọi
- [x] 2.3 **Xong — đo bằng `scratchpad/do_lui_lich.py`, chạy trong container `crm-classifier:test` với `--entrypoint python`.** Script bọc lại `client.models.generate_content` để bấm giờ **từng lượt bên trong** `call_llm_batch`, nên nó đo chính vòng thử lại của CRM chứ không đo một vòng tự viết.

      Số đo, một lượt chạy, `rpm: 1`:

      | | |
      |---|---|
      | số lượt gọi bên trong `call_llm_batch` | **3** |
      | mã trả về từng lượt | `429` · `429` · `429` |
      | CRM tự báo đã ngủ | `10,2`s · `20,4`s · `31,4`s |
      | khoảng giữa hai lượt gọi | `134,21`s · `144,14`s |
      | tổng thời gian một lô | **433,99 giây**, tức 7 phút 14 giây |
      | câu lỗi cuối | `Failed calling Gemini API due to exhausted retries.` |
      | token tiêu tốn | **0** |
      | tiền | **0** |

      Sổ Gateway xác nhận độc lập: 4 dòng mới (1 hâm nóng + 3 lượt), **cả 4 đều `total_tokens = 0` và `spend = 0`**. Không lượt nào chạm tới Google, nên phép đo này **không tiêu một lượt nào** trong trần 48 lượt ở ô 0.2.

      Mốc thời gian trong sổ: `06:40:17` · `06:42:21` · `06:44:35` · `06:46:59`. Trừ ra phần CRM ngủ thì **Gateway mất ~123,7 giây để chịu trả `429`**, ba lần đo gần như bằng nhau (`124` · `123,8` · `123,6`). Con số này lớn hơn hẳn `~60`s tôi đọc từ log ở ô 0.3 — `60`s chỉ là một phần cửa sổ log của `litellm-1`, còn `123,7`s là thời gian người gọi thật sự chờ. **Lấy con số của người gọi.**

      Phép cộng khớp: `3 × 123,7 + (10,2 + 20,4 + 31,4) = 371 + 62 = 433`s, so với `433,99`s đo được.

      **Ghi chú phương pháp: KHÔNG chạy `tools/do_duong_llm.py` cho ô này.** Harness không có vòng thử lại — nó gọi một lượt rồi ghi sổ, nên nó **không có khoảng nào để đo**. Thứ cần đo là vòng thử lại **của chính CRM** (`src/llm.py:265-292`), nên phải gọi qua `call_llm_batch` của CRM trong container, bằng `--entrypoint python` (xem ô 1.4). Harness chỉ dùng ở ô 2.1 và 2.6, nơi cần một lượt gọi trơn để lấy mốc
- [x] 2.4 **Đã đo, và phép đo BÁC BỎ chính cách phân loại mà ô này đề ra.** Ghi lại nguyên văn ý cũ để thấy nó sai ở đâu: *"Lùi lịch sự: 3 khoảng. Lùi chung: 2 khoảng. Số khoảng phân biệt mạnh hơn độ dài, và phân biệt được mà không cần đọc log của CRM."*

      **Cả hai nhánh đều cho ĐÚNG 2 khoảng giữa các lượt gọi.** Lý do là thứ đã ghi ở ô 6.5: nhánh 429 ngủ **3 lần** nhưng lần ngủ thứ ba không có lượt gọi nào đi sau, nên nó **không sinh ra khoảng nào đo được**. Vòng lặp chỉ có 3 lượt gọi, và 3 lượt gọi thì tối đa là 2 khoảng, ở cả hai nhánh.

      | đếm cái gì | nhánh 429 | nhánh chung | phân biệt được? |
      |---|---|---|---|
      | số lượt gọi | 3 | 3 | **không** |
      | số khoảng giữa hai lượt gọi | **2** | **2** | **không** |
      | số lần ngủ | **3** | 2 | có, nhưng phải đọc log CRM |
      | câu lỗi cuối | `due to exhausted retries` | `after 3 retries` | **có, không cần log** |

      Nên câu "phân biệt được mà không cần đọc log của CRM" là **sai**. Thứ phân biệt được mà không cần log là **câu lỗi** (ô 2.4b), không phải số khoảng.

      Độ dài khoảng thì càng không dùng được: đo ra `134,21`s và `144,14`s, chẳng giống `10, 20, 30` mà ô này dự đoán, cũng chẳng giống `13,5 / 20 / 30` mà tôi mô phỏng, vì cả hai lần đều bỏ sót `~124` giây Gateway tự thử lại (ô 0.3). Đây là lần định chính **thứ ba** cho cùng một ô, và mỗi lần số hạng bỏ sót lại lớn hơn lần trước.

      Bài học ghi để lần sau đừng lặp: tôi đã hai lần tính lại con số dự đoán **từ code** rồi tin vào nó, trong khi cách rẻ hơn là chạy một lượt thật rồi đọc số. Phép mô phỏng ở bản trước còn làm tôi tự tin hơn mức đáng có, vì nó "khớp" với code mà vẫn thiếu hẳn tầng Gateway

      **ĐỊNH CHÍNH 10/09 — độ dài `10, 20, 30` và `4, 8` viết ở bản trước là SAI trên đường quan sát.** Đó là số trong `time.sleep()`, không phải khoảng giữa hai lượt gọi. `wait_for_rate_limit()` nằm **trong** `try`, ở đầu mỗi lượt, nên nó cộng thêm vào khoảng — và cộng bao nhiêu thì phụ thuộc lượt ngủ trước đó đã dài hơn nhịp hay chưa. Mô phỏng lại đúng vòng đó (`scratchpad/mo_phong_lui_lich.py`, chỉ tính, không ra mạng):

      | nhánh | nhịp mặc định trong code (3,5 / 0,5) | nhịp `.env.example` (7,5 / 1,5) |
      |---|---|---|
      | 429 | `13,5–16` · `20–22` · `30–32` | `17,5–21` · `20–22` · `30–32` |
      | chung | `7,5–8` · `8` | `11,5–13` · `11,5–13` |

      Hai điều phải biết trước khi đo. **Một:** khoảng thứ nhất bị nhịp đẩy lên, nên đừng so nó với `10`. Khoảng thứ hai và thứ ba của nhánh 429 thì sạch (`20`, `30`), vì ngủ 20s đã dài hơn mọi nhịp nên `elapsed < interval` không còn đúng. **Hai:** nếu production dùng nhịp `.env.example` thì chữ ký `4, 8` của nhánh chung **biến mất** — hai khoảng bằng nhau quanh `11,5–13`s. Ai đi so với `4, 8` sẽ kết luận "không khớp nhánh nào". Đây đúng là cái bẫy mà ý 3 mục 7 của `docs/reference/dua-crm-qua-gateway-10-09.md` cảnh báo, lần này rơi vào chính task của mình

- [x] 2.4b **Xong, và đây là mốc đối chiếu DUY NHẤT còn đứng được.** Đo ra đúng câu `Failed calling Gemini API due to exhausted retries.` → khớp **nhánh 429**. Câu lỗi nhận diện đúng nhánh trong khi số khoảng thì không (ô 2.4) và độ dài khoảng thì không (ô 2.3).
      Lý do nó chắc hơn: câu lỗi do **vị trí trong code** quyết định, không do cấu hình nhịp hay do Gateway chậm. Nhánh 429 rơi xuống `raise` ở **sau** vòng `for`; nhánh chung ném từ **trong** vòng. Hai chỗ, hai câu, không lẫn được
- [x] 2.5 **KHÔNG phải trường hợp hỏng. `429` tới được nhánh đúng.** Ô này viết sẵn kịch bản xấu: "đo được 2 khoảng `4` và `8`s → 429 không tới được nhánh đúng". Thực tế đo được **2 khoảng** — nhưng dài `134,21`s và `144,14`s, không phải `4` và `8`s. Nếu chỉ đếm khoảng rồi tra theo ô này thì sẽ kết luận **ngược hẳn sự thật**.
      Ba bằng chứng độc lập cho thấy nhánh 429 đã chạy: CRM tự in `[WARN] API Rate limit/Resource exhausted. Sleeping 10.2s / 20.4s / 31.4s` — đúng công thức `10 × attempt`; câu lỗi cuối là câu của nhánh 429 (ô 2.4b); và cả 3 lượt đều nhận `429` từ Gateway.
      **Việc phải làm không phải sửa CRM, mà là sửa ô 2.4 và 2.5 của change này** — đã sửa ở trên. Đúng tinh thần "MUST NOT sửa ngay rồi đo lại rồi báo là đạt": tôi không đụng gì vào CRM
- [x] 2.6 **Đã trả `rpm` về 15, và đã chứng minh bằng phép đo.** `git diff docker/gateway/config.gateway.yaml` **rỗng**, tức file về đúng bản đã commit. Rồi khởi động lại hai bản LiteLLM và gọi **hai lượt liên tiếp** cách nhau ~10 giây.
      **Bằng chứng là điều KHÔNG xảy ra: không lượt nào bị `429`.** Dưới `rpm: 1` thì lượt thứ hai chắc chắn bị từ chối, vì chính lượt hâm nóng của phép đo trước đã bị từ chối ngay. Nay cả hai lượt đều đi qua cửa hạn mức và tới được tầng nhà cung cấp, mất `9,52`s và `9,46`s.
      **Nhưng hai lượt đó KHÔNG thành công, vì một lỗi khác — xem ô 2.8.** Nên chỗ này phải nói cho đúng mức: đã chứng minh **hạn mức đã trả**, **chưa** chứng minh được tuyến CRM gọi thông. Hai điều khác nhau, không gộp
- [x] 2.7 **Đúng, và lần này chứng kiến trực tiếp.** Cả hai nhánh của CRM đều kết thúc bằng `RuntimeError`, và ở phép đo này lô đó **hỏng hẳn** chứ không "cuối cùng vẫn xong" — vì hạn mức bị bóp suốt cả 7 phút nên không lượt nào có cửa. Trong vận hành thật, hạn mức chỉ chạm trần trong thời gian ngắn, nên lô sẽ xong ở lượt 2 hoặc 3 và **kết quả cuối trông y như một lô bình thường**.
      Đó đúng là lý do ô 2.3 phải bấm giờ: thứ duy nhất lộ ra rằng CRM vừa mất 4 tới 7 phút cho một lô là **thời gian**, không phải kết quả

- [x] 2.8 **ĐÃ SỬA XONG 10/09. PHÁT HIỆN THẬT, ngoài phạm vi định đo: tuyến CRM trên Gateway hiện KHÔNG CÓ KHOÁ, nên nó đang chết.** Lộ ra lúc làm phép xác nhận ở ô 2.6. Hai lượt gọi đều **không** bị `429` (đúng như cần), nhưng cả hai trả `HTTP 500`:

      ```
      litellm.APIConnectionError: Missing Gemini API key.
      Set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.
      ```

      Truy ra bằng ba phép kiểm, không phải suy đoán:

      | kiểm gì | kết quả |
      |---|---|
      | `config.gateway.yaml` dòng 86 khai gì | `api_key: os.environ/KEY_BENCH_CRM_TEST` |
      | `.env` có `KEY_BENCH_CRM_TEST` không | **không**, chỉ có `KEY_BENCH_TEST` và `KEY_BENCH_CRM_TEST_GG_AIA_STU` |
      | biến đó trong container `litellm-1` | **rỗng** |

      Cơ chế làm nó **hỏng im lặng**: `docker-compose.yml` viết `KEY_BENCH_CRM_TEST: ${KEY_BENCH_CRM_TEST:-}`. Cái `:-` biến biến thiếu thành **chuỗi rỗng** thay vì báo lỗi, nên compose khởi động bình thường, LiteLLM báo healthy, `/health/liveliness` trả `200`, và tuyến chỉ chết đúng lúc có người gọi thật.

      **KHÔNG do phép đo này gây ra.** Việc duy nhất tôi sửa trong file cấu hình là `rpm`, và `git diff` đã rỗng trước khi phát hiện lỗi này. Ngày 09/09 tuyến còn chạy được, sổ có một lượt 4.009 token. Nên biến đã bị đổi tên **sau** thời điểm đó, và không ai đổi theo ở hai chỗ dùng nó.

      Nối với ô 1.5: ô đó đã bắt đúng lỗi này ở **nhật ký**, và ghi rằng tên thật là `KEY_BENCH_CRM_TEST_GG_AIA_STU`. Nhưng lúc đó chưa ai soát lại rằng **cấu hình Gateway và docker-compose cũng dùng tên cũ**. Cùng một lỗi, ba chỗ, mới sửa một chỗ.

      **Chưa sửa, và cần anh Tuấn quyết**, vì tên biến `..._GG_AIA_STU` gợi ý đó là khoá AI Studio, trong khi tuyến này là **Vertex express** (`api_base: aiplatform.googleapis.com`). Ở ô 1.5 khoá đó gọi `aiplatform` ra `200`, nên rất có thể nó thật sự là khoá express bị đặt tên gây hiểu nhầm — nhưng "rất có thể" chưa đủ để đi sửa cấu hình.
      **ĐÃ SỬA, và sửa ở bốn chỗ vì lỗi nằm ở bốn chỗ:**

      | file | sửa gì |
      |---|---|
      | `docker/gateway/config.gateway.yaml:86` | `os.environ/KEY_BENCH_CRM_TEST` → `..._GG_AIA_STU` |
      | `docker-compose.yml:130` | truyền tên biến mới; ghi chú cũ nói sai nên viết lại |
      | `docker/gateway/entrypoint.sh:16` | **thêm khoá vào vòng kiểm** — đây mới là chỗ chữa gốc |
      | `docker-compose.bench.yml` | cấp giá trị cố ý sai, vì bench dùng chung `entrypoint.sh` |
      | `.env.example` | ghi khoá này vào, vì câu báo lỗi chỉ người đọc sang đó |

      **Loại khoá: đã xác định bằng đo, không đoán từ tên.** Đọc tiền tố của cả bốn khoá trong `.env` (chỉ đọc tiền tố, không in giá trị): cả bốn đều `AQ.` và dài 53, và băm khác nhau nên là **bốn khoá riêng biệt**, không phải một khoá dán nhiều tên. Nên `KEY_BENCH_CRM_TEST_GG_AIA_STU` là **Vertex express**, đúng loại tuyến này cần, dù hậu tố tên nói ngược lại.
      Kèm một phát hiện phụ đáng soát tiếp: **`KEY_GOOGLE_AI_STU` cũng có tiền tố `AQ.`**, tức nó cũng là khoá Vertex express dù tên nói AI Studio. Hai tuyến `gemini-flash-preview` và `gemini-flash-lite` đang dùng khoá đó **mà không khai `api_base`**, nên chúng gọi vào cửa AI Studio. Chưa đo, **chưa kết luận** — nhưng nếu đúng thì tuyến của agent DMS cũng đang hỏng. Ghi thành việc riêng, không sửa lẫn vào đây.

      **Chữa gốc, không chỉ chữa triệu chứng.** Ghi chú trong `docker-compose.yml` **đã hứa** rằng "thiếu thì entrypoint dừng hẳn, giống ba khoá trên". Câu đó **sai từ lúc viết**: vòng kiểm trong `entrypoint.sh` chưa bao giờ có biến này. Nên đây không phải lỗi đánh máy tên biến, mà là **một phép bảo vệ được ghi trong tài liệu nhưng chưa từng được cài**. Đổi tên mà không thêm vào vòng kiểm thì lần sau đổi tên nữa lại chết im lặng y như vậy.
      Không dùng `${VAR:?}` của compose, vì `entrypoint.sh` đã ghi rõ lý do: compose nội suy biến cho **cả** file trước khi lọc profile, nên `:?` sẽ làm `docker compose up -d` của dashboard gãy theo dù người dùng không hề định bật Gateway.

      **Chứng minh bằng đo, cả hai chiều:**

      | phép kiểm | kết quả |
      |---|---|
      | thiếu khoá → entrypoint dừng | mã thoát `1`, `STOP: KEY_BENCH_CRM_TEST_GG_AIA_STU is missing.` |
      | có khoá → đi qua vòng kiểm | qua, tới `exec` cuối |
      | gọi thật qua Gateway | **HTTP 200**, `model = gemini-2.5-flash`, nội dung `'ok'` |
      | `docker compose config` cho cả `gateway` và `bench` | cả hai hợp lệ |

      **Ô 0.1 và mục 3 đã được mở khoá.** Tuyến CRM gọi thông trở lại
- [x] 2.9 **PHÁT HIỆN THẬT, và nó đụng tới cách dashboard đếm token: qua Gateway, token suy nghĩ nằm TRONG `completion_tokens`, không phải ngăn thứ ba.** Lộ ra khi làm phép xác nhận ở ô 2.8: lượt gọi đầu trả `HTTP 200` nhưng **nội dung rỗng**, trong khi vẫn tính 12 token ra. Không nới phép kiểm cho qua; gọi thêm hai lượt với hạn mức token ra cao hơn để phân loại:

      | `max_tokens` | nội dung | `finish_reason` | vào / ra / tổng | chi tiết token ra |
      |---|---|---|---|---|
      | 16 | *(rỗng)* | | 6 / 12 / 18 | không có |
      | 64 | `ok` | `stop` | 6 / 23 / 29 | `reasoning 22` + `text 1` |
      | 256 | `ok` | `stop` | 6 / 23 / 29 | `reasoning 22` + `text 1` |

      **Chứng minh được:**
      - `reasoning_tokens` **nằm trong** `completion_tokens`: `22 + 1 = 23`, đúng bằng `completion_tokens`
      - Sổ Gateway cũng vậy: `total = prompt + completion` trên **cả 3 dòng**, lệch `0`
      - **Gateway TÍNH TIỀN token suy nghĩ theo giá token ra.** Kiểm bằng số học, khớp tới 8 chữ số thập phân, **2 trên 2 dòng**:

        ```
        6 vào, 23 ra :  6/1e6 × 0,30  +  23/1e6 × 2,50  =  0,00005930   sổ ghi 0,00005930
        6 vào, 12 ra :  6/1e6 × 0,30  +  12/1e6 × 2,50  =  0,00003180   sổ ghi 0,00003180
        ```

      **KHÔNG phải rút lại bốn phép đo cũ.** Bốn lần đo trước đi **đường trực tiếp** tới `aiplatform.googleapis.com`, nơi Google trả `thoughts_token_count` tách riêng và `tổng ≠ vào + ra`. Phép đo này đi **qua LiteLLM**, và LiteLLM chuẩn hoá về hình dạng OpenAI nên nó **gộp** suy nghĩ vào `completion_tokens`. Cả hai đều đúng, ở hai tầng khác nhau. Điều phải nhớ là: **con số nào cũng phải kèm tầng đo được nó**, nếu không hai kết quả đúng sẽ trông như mâu thuẫn.

      **NÂNG TỪ SUY LUẬN LÊN ĐO ĐƯỢC, sau khi soi sổ.** Dòng `08:22:32` có `reasoning_tokens = 12` và **`text_tokens = 0`**. Không phải suy ra từ việc nội dung rỗng — sổ ghi thẳng con số `0`. Nên **suy luận và chữ ăn chung ngân sách `max_tokens`** là điều đo được, không phải phỏng đoán.
      **Phần vẫn chưa giải thích được:** vì sao lượt đó dừng ở `12` chứ không dùng hết `16`. Ghi CẢNH BÁO cho riêng câu hỏi này, không cho cả kết luận.
      **Điều đáng lo nhất, và nó đã xảy ra thật:** lượt gọi đó trả `HTTP 200`, **có tính tiền**, mà **không có câu trả lời**. Không phép kiểm nào kêu. Đây là một dạng hỏng im lặng nữa, cùng họ với lỗi ở ô 2.8.
      **ĐÃ ĐO CHIỀU NÀY LUÔN, và rủi ro là THẬT — nặng hơn dự đoán.** Chạy 5 bản ghi thật từ file `Phân loại dữ liệu công trình dự án CRM V4.xlsx` qua đúng `call_llm_batch` của CRM với câu nhắc production đầy đủ:

      | | |
      |---|---|
      | token vào | 5.189 |
      | token ra | **8.178** trên trần **8.192** |
      | trong đó suy nghĩ | **7.860 = 96%** |
      | còn cho câu trả lời | **318 = 4%** |
      | gửi / nhận | **5 bản ghi → 1 bản ghi** |
      | có báo lỗi | **không** |

      Bốn tầng che lỗi nối nhau: suy nghĩ ăn hết ngân sách → JSON cụt → `json_repair` (có sẵn trong image) vá được 1 object → vá thành công nên **không** ghi `failed_llm_response.txt` → `call_llm_batch` trả về bình thường. Chỉ vòng thử lại của `pipeline.py` mới đếm ra thiếu, và nó sẽ thử lại với **cùng** ngân sách.
      Lô production là **25** bản ghi chứ không phải 5. Đã ghi thành ý 6 mục 7 của `docs/reference/dua-crm-qua-gateway-10-09.md`
      **Việc phụ đã mở khoá:** cả 4 dòng đều mang `request_tags = ["crm-feedback", …]`, nên đây là lần đầu có dòng **vừa có tag vừa có token suy luận**. Mục `completion_tokens_details` trong `docs/reference/gateway-architecture-and-agent-integration.md` ghi rằng cột `fact_call.thinking_enabled` sẽ trống cho tới đúng lúc này. Nay điều kiện đã đủ, nên lần nạp tới cột đó phải hết trống — và nếu vẫn trống thì đó là phát hiện thật mới
## 3. Diễn tập mất Gateway giữa batch

- [x] 3.1 **XONG.** Chạy 20 dòng chia 5 lô, mỗi lô 4 dòng, tuần tự — đủ dài để can thiệp giữa chừng. Việc dừng Gateway bám vào **nhật ký** (`lo_xong` của lô 2) chứ không đếm giờ áng chừng, nên mốc can thiệp tái lập được. Nguyên văn ô cũ: Chạy harness với đủ số lượt để nó còn đang chạy khi ta can thiệp. Timeout mỗi lượt phải **trên 60 giây**: nhánh 429 ngủ 10+20+30 rồi mới bỏ, nên timeout ngắn hơn sẽ bị đọc thành treo

      **Đo trước một phần, 10/09 — bằng chính lớp `_GatewayModels`, không tốn lượt gọi nào.** Đo bốn kiểu hỏng mạng để biết CRM sẽ *thấy* gì:

      | kiểu hỏng | thời gian tới lúc báo lỗi | lỗi hệ thống |
      |---|---|---|
      | cổng đóng, host còn sống | **0,04**s | `ECONNREFUSED` |
      | tên miền không phân giải | **0,09**s | DNS |
      | IP không định tuyến được | 21,07s | `ECONNREFUSED` |
      | IP trong mạng Docker, không ai đáp ARP | 3,11s | `EHOSTUNREACH` |

      **Hệ quả cho ô 3.2 và 3.3:** dừng `gateway-lb` cho ra đúng dòng đầu bảng, tức CRM nhận lỗi trong **0,04 giây**, **không treo**. Nên nhánh chạy sẽ là **lùi lịch chung `4, 8` giây**, KHÔNG phải nhánh 429 — vì câu lỗi `Gateway khong ket noi duoc: ConnectError` không chứa chuỗi `429`.
      Nghĩa là ở mục 3 ta sẽ đo được **2 khoảng**, và lần này 2 khoảng là **đúng**, khác hẳn tình huống ở ô 2.5 nơi 2 khoảng lại là dấu hiệu sai. Phân biệt hai cảnh đó bằng **câu lỗi cuối** (ô 2.4b), đừng bằng số khoảng.
      Nỗi lo ghi trong ô này rằng "timeout ngắn hơn sẽ bị đọc thành treo" **không áp dụng** cho kiểu hỏng dừng container. Nó chỉ áp dụng nếu Gateway nhận kết nối rồi im — cảnh đó chưa dựng được và **chưa đo**
- [x] 3.2 **XONG — dừng đúng `gateway-lb`, KHÔNG dừng LiteLLM.** Dừng lúc `10:21:24`, ngay sau khi lô 2 ghi sổ xong, bằng một vòng chờ bám vào nhật ký chứ không phải đếm giờ áng chừng. Hai bản LiteLLM giữ nguyên `healthy` suốt diễn tập
- [x] 3.3 **XONG. Và lỗi CRM nhận được KHÁC với điều tôi dự đoán ở ô 3.1.**

      Dự đoán: `ECONNREFUSED` trong `0,04` giây. Thực tế:

      ```
      ConnectError: [Errno -5] No address associated with hostname
      ```

      Đây là **lỗi phân giải tên**, không phải từ chối kết nối. Lý do: Docker gỡ luôn bản ghi DNS khi container dừng, nên `gateway-lb` không còn phân giải được. Dừng bằng cách khác — chặn cổng, rút mạng — sẽ cho lỗi khác. **Kiểu dừng quyết định thông báo lỗi**, đừng đọc kết quả này thành "mọi kiểu mất Gateway đều cho lỗi DNS".
      Phần dự đoán ĐÚNG: nó hỏng **nhanh**, không treo.

      | | lô 3 | lô 4 | lô 5 |
      |---|---|---|---|
      | thời gian tới lúc bỏ lô | `21,48`s | `24,10`s | `24,05`s |

      Cấu thành `~24` giây: 3 lượt thử, mỗi lượt `wait_for_rate_limit()` ngủ `~4`s, cộng hai lần lùi lịch chung `4 + 8`s. Tức **2 khoảng**, đúng nhánh lùi lịch chung.

      **Câu lỗi cuối là `Failed calling Gemini API after 3 retries`** — câu của nhánh chung, không phải `due to exhausted retries` của nhánh 429. Đây là lần thứ hai mốc đối chiếu ở ô 2.4b tỏ ra dùng được, và lần này nó phân biệt **hai cảnh đều cho 2 khoảng**: mục 2 cho 2 khoảng vì nhánh 429 ngủ lần ba mà không gọi lại; mục 3 cho 2 khoảng vì nhánh chung chỉ ngủ hai lần. Đếm khoảng không tách được hai cảnh này, câu lỗi thì tách được.

      **Không bỏ dở giữa lô.** Lô hỏng thì **không dòng nào** trong lô được ghi sổ, mirror đúng `pipeline.py`. 8 dòng của lô 1 và 2 đã vào sổ trước lúc mất Gateway và còn nguyên
- [x] 3.4 **XONG.** Bật lại `gateway-lb`, chạy lại. Lần 2 **bỏ qua đúng 8 dòng đã xong**, chỉ làm 12 dòng còn thiếu, chia 3 lô.
  - [x] 3.4.1 **KHÔNG MẤT DÒNG — ĐẠT.** Mong đợi 20, trong sổ 20, thiếu `0`, thừa `0`. So bằng phép so **tập hợp** trên ActivityId, không so bằng số đếm
  - [x] 3.4.2 **KHÔNG ĐẾM ĐÔI — ĐẠT, và phải nói rõ phép kiểm nào mới có giá trị.**
        Phép kiểm **vô giá trị**: "mỗi ActivityId có đúng một bản ghi". Sổ là `dict` khoá theo ActivityId nên điều đó đúng **bằng cấu trúc**, không chứng minh gì. Ghi ra để không ai đọc nhầm nó thành bằng chứng.
        Phép kiểm **có giá trị**: đếm số lần mỗi dòng được **ghi sổ** qua cả hai lần chạy, lấy từ trường `ghi_so_ids` trong nhật ký. Ghi hai lần nghĩa là đã trả tiền phân loại hai lần. Kết quả: **0 dòng**.
        Phép kiểm **độc lập, bằng tiền**:

        | | trước khi chạy lại | sau | chênh |
        |---|---|---|---|
        | lượt gọi | 29 | 32 | **+3** |
        | token vào | 86.351 | 99.756 | +13.405 |
        | tiền | $0,203913 | $0,216257 | +$0,012344 |

        **`+3` đúng bằng số lô còn thiếu.** Chạy lại mù sẽ là `+5`. Tổng cả diễn tập: 5 lô việc, 5 lượt gọi thành công, **không lô nào chạy hai lần**
- [x] 3.5 **Đã nêu tách nhau ở 3.4.1 và 3.4.2**, mỗi vế một phép đo riêng, một kết luận riêng. Ở 3.4.2 còn tách thêm một tầng: phép kiểm nào là bằng chứng, phép kiểm nào chỉ là hệ quả của cấu trúc dữ liệu
- [x] 3.6 **XONG, và dùng CHÍNH `save_history_db_atomic` của CRM chứ không viết lại.** Diễn tập chỉ trỏ `config.DB_JSON_PATH` sang file riêng để không đụng file thật.
      Đo được: ngay sau lô 2 file chứa **đúng 8** bản ghi; sau khi lô 3, 4, 5 hỏng vẫn **đúng 8**; sau lần chạy 2 thành **20**. Ghi sau mỗi lô hoạt động đúng như `pipeline.py:688` mô tả.
      Đã **không** kiểm `config.CKPT_JSON` — xem ô 6.3, nó là cấu hình chết
- [x] 3.7 **Đã ghi.** Diễn tập chạy `scratchpad/drill_mat_gateway.py` bằng `--entrypoint python`, dùng lại 4 hàm của CRM và **không có đường nào** dẫn tới SharePoint, email hay Excel.
      Ai diễn tập bằng `pipeline.py` thật thì rủi ro để lại trạng thái nửa vời trên SharePoint là **có thật** (`pipeline.py:743`, `:849`).
      **Hai chỗ diễn tập KHÔNG tái hiện được, đừng đọc thành đã kiểm:**
      - `pipeline.py` chạy các lô **song song** bằng ThreadPool, diễn tập chạy **tuần tự**. Lỗi tranh chấp giữa các luồng khi cùng ghi `history_db` **chưa được kiểm**
      - `pipeline.py` còn một vòng thử lại **trong** một lô cho những dòng LLM không trả về; diễn tập không có vòng đó

## 4. Batch cỡ production

- [x] 4.1 **HOÃN CÓ CHỦ Ý — chốt bởi anh Tuấn, 10/09.** Không chạy, và **không tiêu quá trần**. Đây chính là điều ô này yêu cầu: dừng khi tới trần chứ không chạy tiếp rồi xin lỗi sau.
      Đã dùng **32 lượt** trên trần ~50 của ô 0.2.
- [x] 4.2 **HOÃN CÓ CHỦ Ý.** Giữ nguyên con số mục tiêu để lần sau khỏi đo lại: ngày cao nhất **502 lượt**, giờ cao nhất **365 lượt**.
      Cái giá đo được hôm nay, dùng để định trần cho lần sau:

      | cỡ lô | thời gian mỗi lượt | tiền mỗi lượt | 502 lượt tốn |
      |---|---|---|---|
      | 25 dòng | 39,4 s | $0,0257 | **5,5 tiếng**, $12,90 |
      | 5 dòng | 16,2 s | $0,0071 | **2,3 tiếng**, $3,57 |

      Ô 0.2 đoán đúng ngay từ đầu: **trần của mục này phải là trần THỜI GIAN**, không phải trần tiền. Nay có số để đặt trần đó.
      Thêm một ràng buộc chỉ lộ ra khi làm: file `Phân loại dữ liệu công trình dự án CRM V4.xlsx` chỉ có **220 dòng có dữ liệu**, nên 502 lượt sẽ phải **lặp lại cùng một tập đầu vào** nhiều lần. Đo tải thì được, đo chất lượng thì không.
- [x] 4.3 **HOÃN CÓ CHỦ Ý — nhưng phần đo được không cần tải thì đã có.** Trên 32 lượt của hôm nay: token và chi phí ở ô 4.7; số 429 là **6 lượt**, toàn bộ do phép ép ở mục 2 gây ra chứ không phải tải tự sinh.
      **Nhịp thực đạt và độ trễ phân vị thì KHÔNG lấy được** từ 32 lượt rời rạc này — chúng rải trong 4 tiếng, xen giữa nhiều phép thử khác nhau, nên không có đoạn nào chạy liên tục để tính lượt/phút. Cùng lý do đã ghi ở ô 2.1.
- [x] 4.4 **HOÃN CÓ CHỦ Ý — và ghi lại vì sao phép đối chiếu này vẫn đáng làm.** Hai con số cần so: `7,3` lượt/phút (`.env.example`: `7.5 + jitter 1.5`) và `16,0` (mặc định code: `3.5 + jitter 0.5`).
      Đo được nhịp thực đạt sẽ nói ra `.env` production đang đặt gì — thứ **chưa hỏi được nhóm CRM** (xem 8.4 của nhật ký change trước).
      Một manh mối thu được ở mục 3, chưa đủ kết luận: các lô hỏng mất `~24` giây cho 3 lượt thử, trong đó phần `wait_for_rate_limit()` chiếm `~4` giây mỗi lượt. `4` giây khớp nhịp **mặc định trong code** (`3,5 + ≤0,5`), **không** khớp nhịp `.env.example` (`7,5 + ≤1,5`). Nhưng đó là container thử nghiệm **không có `.env`**, nên nó chỉ xác nhận mặc định của code, **không nói gì về production**.
- [x] 4.5 **ĐẠT — và làm được mà không cần chạy tải production.** Ô này không phụ thuộc cỡ tải, nên đo luôn trên 32 lượt gọi thật của hôm nay. Nạp sổ bằng chính `scripts/refresh_gateway.py` của dự án:

      | | |
      |---|---|
      | `fact_call` nguồn gateway tăng | 388 → 420, đúng **+32** |
      | số dòng trong sổ LiteLLM hôm nay | **32** |
      | quy về `agent_id` | **7**, toàn bộ 32 dòng |
      | số định danh khác nhau | **1** (`svc.crm-feedback`) |
      | dòng rơi vào `bo_khong_tag` hôm nay | **0** |

      `32 = 32` là phép đối chiếu quan trọng nhất: **không dòng nào mất khỏi chiều agent**.
      Bộ nạp cũng tự báo `end_user empty 0 | identity unresolvable 0 | via MASTER KEY 0/37`.
      **Việc phụ đã mở khoá:** `thinking_enabled` nay có **7 dòng TRUE**, lần đầu cột này có dữ liệu — đúng điều kiện mà mục `completion_tokens_details` của `docs/reference/gateway-architecture-and-agent-integration.md` đã ghi là còn thiếu (xem ô 2.9)
- [x] 4.6 **ĐẠT.** Chạy `scripts/audit_db.py`, nhóm `J. Gateway row accounting`:

      ```
      [  ok  ] Every source row is either loaded or dropped for a named reason
               (420 dong da nap, tre 0s/nguong 420s) (502 rows checked)
      [ note ] Source rows dropped: no identity tag (81 dong, 1.332 token)
      [ note ] Source rows dropped: cache-hit duplicate row (1 dong, 352 token)
      ```

      **Không mục nào FAIL.** Hai mục `note` là dòng lịch sử, ngày từ `2026-08-29` tới `2026-09-07` — **không dòng nào của hôm nay**, khớp với ô 4.5 nơi 32/32 dòng đều nạp được.
      Ô này cũng không phụ thuộc cỡ tải nên đóng được mà không cần chạy mục 4.2
- [x] 4.7 **XONG cho phần đã chạy.** Toàn bộ change tiêu:

      | | |
      |---|---|
      | lượt gọi | **32** trên trần ~50 |
      | lượt bị từ chối (không tốn token) | 6 |
      | token vào / ra | 99.756 / 74.966 |
      | tiền | **$0,216257** |

      **Dưới trần cả về lượt lẫn tiền.** Phần đắt nhất không phải mục 2 hay 3 mà là các lô 25 dòng của phép đo cắt cụt: 6 lượt tốn `$0,154`, tức **71% tổng chi phí** của cả change.

## 5. Gateway làm chậm thêm bao nhiêu

- [x] 5.1 **HOÃN CÓ CHỦ Ý cùng cả mục 5.** Giữ nguyên ràng buộc phương pháp cho lần sau: phải chạy **xen kẽ** hai đường trên cùng tập đầu vào. Chạy hết đường này rồi mới sang đường kia là đo lẫn cả chuyện tải của Google trôi theo thời gian vào chênh lệch.
- [x] 5.2 **HOÃN CÓ CHỦ Ý — nhưng ô 2.1 đã cho một ví dụ cho thấy ràng buộc này đúng.** Trên 10 lượt thành công của tuyến CRM: trung vị `1,461`s, nhưng nhanh nhất `0,488`s và chậm nhất `38,239`s.
      Nếu tính cả 2 lượt hỏng có độ trễ `0,000`s thì trung vị tụt xuống `0,714`s — **một con số sai**. Đúng như ô này cảnh báo, và cái bẫy còn xuất hiện sớm hơn cả mục 5.
- [x] 5.3 **HOÃN CÓ CHỦ Ý, và đây là ô khó nhất của mục 5.** CRM **không còn giữ** khoá nhà cung cấp — đó là toàn bộ điểm của việc đi qua Gateway, không phải thiếu sót. Nên mốc so phải dùng khoá của **người vận hành**, và báo cáo phải ghi rõ đó là **mốc so**, không phải một đường production còn có thể chọn.
      Công cụ đã sẵn: `tools/do_duong_llm.py --duong truc-tiep --khoa-bien <TÊN BIẾN>` nhận khoá bằng **tên biến**, không nhận giá trị (ô 1.2).
- [x] 5.4 **HOÃN CÓ CHỦ Ý.** Ghi lại một manh mối thu được ngoài dự tính, để lần sau đỡ mò: hai bản LiteLLM mở cổng riêng (`LITELLM_1_PORT=4001`, `LITELLM_2_PORT=4002`, xem `.env.example`) **chính là để diễn tập sự cố**. Gọi thẳng vào `4001` rồi so với gọi qua `4000` sẽ tách được chặng nginx khỏi chặng LiteLLM mà không cần dụng cụ đo nào thêm.

## 6. Tài liệu

- [x] 6.1 **XONG — `docs/reference/ep-429-va-mat-gateway-10-09.md`.** Mỗi kết luận kèm số, và chỗ nào không có số thì nói thẳng là chưa đo.
      Nhật ký này tách khỏi `dua-crm-qua-gateway-10-09.md` (nhật ký của change trước) vì hai change trả lời hai câu hỏi khác nhau: change trước hỏi "nối được không", change này hỏi "hỏng thì sao"
- [x] 6.2 **XONG — tách thành hai mục riêng của nhật ký, không trộn.** Mục 2 là điều chứng minh được (9 mục, đều kèm số). Mục 3 là điều suy luận, kèm bảng ghi rõ **cần gì để chứng minh** từng điều.
      Mục 3 còn ghi hai thứ mà một báo cáo bình thường sẽ giấu đi:
      - **Ba lần trong một ngày suy đoán bị chính số đo bác bỏ** — hậu tố tên khoá, tuyến DMS, và trần timeout 300 giây. Cả ba đều suy từ **tên gọi hoặc đọc code**, và cả ba đều sai
      - **Hai lỗi phương pháp trong chính phép đo của tôi** — phép thử "gói tin rơi im lặng" dùng địa chỉ vẫn có thứ trả lời, và phép thử `json_repair` dùng chuỗi không có ký tự `]` nên chưa hề chạm tới nhánh cần thử
- [x] 6.3 **Xong — và việc này to hơn lúc viết ô task.** Đã bổ sung vào mục 7 ý 2 của `docs/reference/dua-crm-qua-gateway-10-09.md`. Ba thứ đo được thêm ngày 10/09, không phải suy từ tên file:
      - **Bảy chỗ trong `tests/test_automation.py` gán `config.CKPT_JSON`** (dòng 120, 202, 310, 387, 466, 541, 633) và **không chỗ nào đọc lại**. Bộ test làm cấu hình chết *trông như* còn sống
      - **Mục `11.2` của `docs/HANDOVER.md` không làm theo được.** Nó mở đầu bằng "Không mất dữ liệu! Hệ thống có checkpoint", rồi dặn `python run_pipeline.py 3` để chạy tiếp — mà **`run_pipeline.py` và `step3_call_llm.py` không tồn tại trong repo**. Kiểm bằng `find`, không phải bằng mắt
      - Dòng 584 và 800 bảo `del` file đó để chạy lại từ đầu. Lệnh **không có tác dụng**, nhưng người chạy tưởng đã xoá trạng thái cũ
      Nối với ô 3.6: đây là lý do phép đối chiếu ở mục 3 phải soi `classified_history_db.json`, và là lý do rủi ro **đếm đôi** ở ô 3.4.2 có đường tồn tại thật — người vận hành tin mình đã dọn sổ trong khi chưa
- [x] 6.6 **ĐÃ ĐO — NGHI VẤN CỦA TÔI SAI, và đo được mà KHÔNG tốn lượt gọi nào.**
      Nghi vấn cũ: cả bốn khoá trong `.env` đều tiền tố `AQ.` kể cả `KEY_GOOGLE_AI_STU`, nên hai tuyến `gemini-flash-preview` và `gemini-flash-lite` có thể đang dùng khoá Vertex để gọi cửa AI Studio.
      Không cần gọi thử: sổ đã ghi lại toàn bộ lịch sử của chính hai tuyến đó.

      | tuyến | lượt gọi | lượt **có token** | lần cuối |
      |---|---|---|---|
      | `gemini-flash-lite` (agent DMS) | 407 | **404** | 09/09 |
      | `gemini-flash-preview` | 18 | **17** | 08/09 |

      404 lượt thành công có token là bằng chứng đủ mạnh: khoá `AQ.` **dùng được** ở cửa AI Studio. Tuyến DMS không hỏng, và **không mở change nào**.
      Bài học ghi lại vì tôi đã suýt mở một change thừa: **tiền tố tên khoá không nói được khoá dùng ở cửa nào.** Đây là lần thứ hai trong ngày một suy đoán dựa trên tên bị số đo bác bỏ, lần trước là hậu tố `_GG_AIA_STU` (ô 2.8).
      **Cách rẻ hơn nên thử trước:** khi nghi một tuyến hỏng, hỏi sổ trước khi gọi thử. Sổ trả lời miễn phí
- [x] 6.4 **KHÔNG PHẢI LÀM — điều kiện của ô này không xảy ra.** Ô ghi "nếu 2.5 cho ra phát hiện thật (429 không tới nhánh đúng)". Ô 2.5 đo ra **429 CÓ tới đúng nhánh**, chứng minh bằng ba bằng chứng độc lập. Nên không có việc riêng nào phải tách.
      Đóng bằng cách **không làm**, giống ô 2.2 của change trước. Ghi rõ để người đọc sau không tưởng là bỏ sót
- [x] 6.5 **Phát hiện thật, tìm ra bằng đọc code trước khi đo — đã ghi thành ý 5 mục 7 của `docs/reference/dua-crm-qua-gateway-10-09.md`.** Nhánh 429 của CRM **ngủ 30 giây cho một lần thử lại không bao giờ xảy ra**. Nhánh chung có chốt `if attempt < max_retry` nên lượt 3 ném lỗi ngay; nhánh 429 **không có chốt đó**, nên lượt 3 vẫn ngủ `30`s (+≤2s) rồi `continue`, `range` hết, rơi xuống `raise`. Giá: **mỗi lần 429 dứt điểm tốn thêm 30–32 giây vô ích**.
      Không sửa ở change này — repo CRM không phải của mình. Ghi để báo lại nhóm CRM.
      **Ảnh hưởng tới phép đo mục 2:** đây là lý do nhánh 429 có 3 khoảng chứ không phải 2. Khoảng thứ ba **là khoảng ngủ vô ích đó**. Nên nếu ô 2.4 đo được 3 khoảng thì kết luận đúng là "429 tới được nhánh đúng", còn khoảng thứ ba **không** chứng minh có lượt gọi thứ tư — không có lượt nào cả
