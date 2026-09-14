# pull-merge-completeness Specification

## Purpose
TBD - created by archiving change stop-a-later-pull-from-shrinking-an-earlier-one. Update Purpose after archive.
## Requirements
### Requirement: Lần kéo sau MUST NOT làm co giá trị của lần kéo trước

Khi gộp nhiều lần kéo Monitoring, nếu hai lần kéo cho **cùng khoá** (mọi cột trừ `value`) mà **khác giá trị**, bản gộp SHALL giữ **giá trị lớn hơn**. Luật "bản mới thắng" MUST NOT còn được dùng.

Lý do đo ngày 14/09/2026. Quét 6 lần kéo 1 phút × 7 project, khoảng 2,95 triệu dòng: có 14 điểm lệch, **cả 14 đều là lần kéo sau báo nhỏ hơn**. Ở 5 điểm có nhân chứng đếm lượt độc lập (`api_request_count`, histogram độ trễ), nhân chứng nghiêng về số cũ. Ở 4 điểm khác, số mới bằng 0 nằm giữa một chuỗi đều. 5 điểm còn lại không có nhân chứng, nhưng lần kéo mới thiếu dòng ngay sát điểm đó. Luật "bản mới thắng" đã bỏ 11.262 token.

Luật "bản cũ thắng" cũng cho đúng 14/14 trên dữ liệu đã có. "Số lớn hơn" được chọn vì nó đúng thêm ở một trường hợp chưa gặp nhưng đã biết: dữ liệu về muộn làm lần kéo sau báo **lớn** hơn.

#### Scenario: Lần kéo sau báo nhỏ hơn

- **WHEN** lần kéo cũ có `value` 4406 và lần kéo mới có `value` 944 trên cùng khoá
- **THEN** bản gộp SHALL chứa đúng một dòng cho khoá đó, với `value` 4406

#### Scenario: Lần kéo sau báo lớn hơn

- **WHEN** lần kéo cũ có `value` 5 và lần kéo mới có `value` 6 trên cùng khoá
- **THEN** bản gộp SHALL chứa đúng một dòng cho khoá đó, với `value` 6

#### Scenario: Khoá chỉ có ở một lần kéo

- **WHEN** một khoá có ở lần kéo cũ nhưng không có ở lần kéo mới
- **THEN** bản gộp SHALL vẫn chứa dòng đó

#### Scenario: Hai lần kéo trùng khít

- **WHEN** hai lần kéo cho cùng khoá, cùng giá trị
- **THEN** bản gộp SHALL chứa đúng một dòng, không nhân đôi

### Requirement: Mọi ca lệch SHALL để lại dấu vết đọc được sau khi lệnh kết thúc

Mỗi lần gộp **có ghi kết quả ra tệp** SHALL ghi mọi ca lệch ra một tệp nằm cạnh tệp hoặc thư mục kết quả. Tệp gồm khoá, tên và giá trị của hai lần kéo, và giá trị được giữ. Tệp SHALL được ghi **kể cả khi không có ca lệch nào**, khi đó chỉ có dòng tiêu đề, để phân biệt "không lệch" với "chưa chạy". Lần gộp chỉ in kết quả ra màn hình (ví dụ `merge_latency_daily.py` không có `--out`) SHALL in ca lệch ra `stderr`.

Tệp ca lệch MUST NOT nằm trong thư mục mà khâu nạp quét tìm dữ liệu. Lý do: `db/load_monitoring.py` nạp mọi `*.csv` trong thư mục gộp, nên một tệp ca lệch đặt ở đó sẽ bị nạp như dữ liệu của một project.

Với khâu nạp số nhà cung cấp, vốn chỉ đọc file và không ghi vào `data/`, dấu vết SHALL là dòng log: mỗi ca lệch một dòng, cộng một dòng tổng.

Lý do: trước change này, `merge_monitoring.py` chỉ **in** ca lệch ra màn hình. 14 ca lệch và 11.262 token đã trôi qua mà không ai đọc.

#### Scenario: Gộp có ca lệch

- **WHEN** gộp Monitoring gặp 14 ca lệch
- **THEN** tệp ca lệch SHALL có đúng 14 dòng dữ liệu
- **AND** con số in ra màn hình SHALL bằng số dòng đó

#### Scenario: Gộp không có ca lệch

- **WHEN** gộp không gặp ca lệch nào
- **THEN** tệp ca lệch SHALL vẫn tồn tại, chỉ có dòng tiêu đề

#### Scenario: Khâu nạp đọc thư mục gộp

- **WHEN** `db/load_monitoring.py` nạp bản gộp vừa sinh
- **THEN** số project nó đọc SHALL bằng số project của bản gộp
- **AND** tệp ca lệch MUST NOT được nạp

### Requirement: Bước gộp SHALL chỉ đọc thư mục kéo đúng khuôn tên

Khi không được chỉ định danh sách lần kéo, bước gộp SHALL chỉ đọc những thư mục có tên đúng khuôn của lần kéo sản xuất. Mọi thư mục khác SHALL bị bỏ qua, và danh sách bị bỏ qua SHALL được in ra.

| Nguồn | Khuôn được gộp | Nơi sinh ra khuôn đó |
|---|---|---|
| Monitoring | `^\d{4}-\d{2}-\d{2}-1m$` | `scripts/pull_monitoring.py:309-318`; tài khoản mặc định không thêm hậu tố |
| Histogram độ trễ | `^\d{4}-\d{2}-\d{2}-\d+d-1m$` | `scripts/pull_latency_distribution.py:170-171` |

Lý do, đo ngày 14/09/2026. `merge_monitoring.py` hiện quét **mọi** thư mục. Thư mục `2026-09-04-1h-dinhthinhan18111971` là lần kéo bằng tài khoản cá nhân. Nó mang theo 133 dòng, 112.546 token của `project-e62bad30-a591-407b-ba7`, một project không thuộc 8 agent. Bản gộp hiện tại sạch chỉ vì tệp đó đã bị xoá bằng tay.

Khuôn phải loại cả lần kéo **1 giờ**, vì khoá gộp không chứa độ mịn. Ở Monitoring, tổng của cả giờ ghi tem `HH:00` sẽ đụng khoá với giá trị một phút cùng tem, và luật "số lớn hơn" sẽ luôn chọn tổng cả giờ. Ở histogram, điểm 1 giờ khác khoá với điểm 1 phút, nên sẽ bị cộng chồng lên. Thư mục `2026-09-04-1h` hiện không có dòng dữ liệu nào, nên ảnh hưởng hôm nay là 0. Rủi ro này đọc ra từ mã, chưa gặp trên dữ liệu.

Lần kéo mang tên tài khoản vẫn là nguồn **đúng** của `db/load_provider.py`, qua khuôn riêng của nó (`^\d{4}-\d{2}-\d{2}-\d+[mh]-.+$`). Yêu cầu này không đổi khuôn đó.

#### Scenario: Thư mục kéo bằng tài khoản khác nằm cùng chỗ

- **WHEN** thư mục kéo Monitoring có `2026-09-04-1h-dinhthinhan18111971`
- **THEN** bản gộp MUST NOT chứa tệp nào của `project-e62bad30-a591-407b-ba7`
- **AND** tên thư mục đó SHALL xuất hiện trong danh sách bị bỏ qua được in ra

#### Scenario: Lần kéo độ mịn 1 giờ nằm cùng chỗ

- **WHEN** thư mục kéo có `2026-09-04-1h`
- **THEN** bước gộp MUST NOT đọc tệp nào trong đó

#### Scenario: Người vận hành chỉ định rõ danh sách lần kéo

- **WHEN** bước gộp được gọi với danh sách lần kéo tường minh (`--dot` hoặc `--in`)
- **THEN** nó SHALL đọc đúng danh sách đó, kể cả tên không khớp khuôn
- **AND** SHALL in cảnh báo cho mỗi tên không khớp khuôn

#### Scenario: Mốc nghiệm thu không đổi khi có bộ lọc

- **WHEN** gộp Monitoring mặc định trên các thư mục hiện có
- **THEN** tập lần kéo được đọc SHALL đúng là 6 thư mục `2026-08-06-1m`, `2026-08-13-1m`, `2026-08-17-1m`, `2026-08-29-1m`, `2026-09-05-1m`, `2026-09-12-1m`
- **AND** đây là đúng tập đã dùng để đo mốc 14 ca lệch và +11.262 token

### Requirement: Gộp histogram độ trễ SHALL đọc mọi lần kéo

`scripts/merge_latency_daily.py` SHALL gộp **mọi** lần kéo đúng khuôn trong `data/raw_google_console/do_tre_phan_bo/`. Với cùng project, cùng phút, cùng chuỗi (service, method, location, credential), nếu nhiều lần kéo có điểm đó thì SHALL giữ điểm có `count` lớn hơn, rồi mới cộng histogram theo ngày. Luật dừng khi gặp `bucketOptions` thứ hai SHALL giữ nguyên.

Lý do: script hiện đòi đúng một lần kéo, và `scripts/update_dashboard.py` bước 7 gọi nó không có `--in` trên thư mục có 4 lần kéo, nên thoát 1 (đã chạy thật 14/09). `latency-daily.csv` hiện bắt đầu từ 09/06, trong khi lần kéo 08/08 còn dữ liệu tháng 5.

#### Scenario: Bước 7 chạy trên thư mục có nhiều lần kéo

- **WHEN** `update_dashboard.py` bước 7 chạy trên thư mục có 4 lần kéo
- **THEN** mã thoát SHALL là 0

#### Scenario: Ngày cũ không bị rơi

- **WHEN** gộp trên các lần kéo hiện có trên đĩa
- **THEN** ngày sớm nhất trong `latency-daily.csv` SHALL không muộn hơn 2026-05-01

#### Scenario: Cùng một phút có ở hai lần kéo

- **WHEN** hai lần kéo cùng có một phút của một chuỗi, với `count` 4 và 3
- **THEN** histogram của ngày đó SHALL chỉ cộng điểm có `count` 4, một lần

### Requirement: Nạp số nhà cung cấp SHALL đọc mọi lần kéo mang tên tài khoản

`db/load_provider.py`, khi không có `--dir`, SHALL đọc **mọi** thư mục kéo khớp khuôn `<ngày>-<độ mịn>-<tài khoản>`. Với cùng ngày, project, model và đại lượng, SHALL giữ số lớn hơn và ghi ca lệch ra log. Phép đối chiếu nhánh PerDay với PerMinute SHALL vẫn chạy trong từng lần kéo.

Lý do: bộ nạp hiện chỉ đọc lần kéo mới nhất. Mỗi lần dựng lại xoá sạch `fact_provider_daily`, nên lần kéo thứ hai sẽ làm mất các ngày chỉ lần kéo đầu có.

#### Scenario: Hai lần kéo, một ngày bị cắt ở mép

- **WHEN** lần kéo A có ngày D đầy đủ, còn lần kéo B chỉ có một phần ngày D
- **THEN** `fact_provider_daily` SHALL giữ số của lần kéo A cho ngày D

#### Scenario: Ngày chỉ có ở lần kéo cũ

- **WHEN** ngày D chỉ có ở lần kéo cũ
- **THEN** sau khi dựng lại, `fact_provider_daily` SHALL vẫn có ngày D

### Requirement: Luật gộp mới SHALL được nghiệm thu bằng số trên dữ liệu thật

Trước khi coi là xong, gộp Monitoring trên 6 lần kéo 1 phút hiện có SHALL cho ra đúng các con số đã đo ngày 14/09/2026. MUST NOT nới phép so cho vừa.

| Phép đo | Giá trị |
|---|---|
| Số ca lệch | 14 |
| Số ca lần kéo sau nhỏ hơn / lớn hơn | 14 / 0 |
| Chênh token giữa luật mới và luật cũ | +11.262 |
| `tranquil-post-471401-c1`, `paid_tier_3_input_token_count`, 11/06 00:00 UTC | 4406 |

Giới hạn đã biết, và SHALL được ghi lại chứ không giấu: với **phân vị** độ trễ (`ALIGN_PERCENTILE_95/99`), "lớn hơn" không đồng nghĩa với "đủ hơn". Cả 4 ca phân vị trong 14 ca đều nằm sát vùng mà lần kéo mới thiếu dòng, nên luật mới chọn đúng, nhưng đó là do trùng hợp chứ không phải do nguyên tắc.

#### Scenario: Chạy gộp trên dữ liệu hiện có

- **WHEN** `scripts/merge_monitoring.py` chạy trên 6 lần kéo 1 phút hiện có
- **THEN** cả bốn con số trong bảng SHALL khớp

#### Scenario: Có thêm lần kéo mới làm số ca lệch đổi

- **WHEN** có thêm lần kéo và số ca lệch khác 14
- **THEN** mốc SHALL được đo lại trên tập lần kéo mới và ghi lại kèm ngày
- **AND** MUST NOT sửa mốc chỉ để phép so đạt

