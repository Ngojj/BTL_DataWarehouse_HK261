# TV3 - Bảng Fact và Tải Dữ Liệu

TV3 triển khai bảy bảng fact từ thiết kế Milestone 1. Trước tiên hãy chạy DDL của dimension; sau đó bộ tải sẽ stage các file CSV đã làm sạch, cập nhật lại các dòng dimension và nạp dữ liệu fact trong một giao dịch PostgreSQL.

## Điều kiện tiên quyết và cách chạy

1. Tạo cơ sở dữ liệu PostgreSQL và chạy `sql/healthcare_dw_dimensions.sql` khi đã kết nối vào cơ sở dữ liệu đó.
2. Cài đặt dependency Python bằng lệnh `python3 -m pip install -r requirements.txt`.
3. Kiểm tra các file CSV đã xử lý mà không cần kết nối đến cơ sở dữ liệu:

   ```sh
   python3 scripts/load_facts.py --validate-only
   ```

4. Tải hoặc làm mới dimension và fact. Đặt `DW_DSN` thành chuỗi kết nối PostgreSQL của cơ sở dữ liệu đích:

   ```sh
   export DW_DSN='******HOST:5432/DATABASE'
   python3 scripts/load_facts.py
   ```

Bộ tải sử dụng các bảng staging tạm thời và `INSERT ... ON CONFLICT` để các lần chạy lặp lại với cùng một snapshot nguồn được an toàn. Mỗi lần chạy sẽ commit trong một giao dịch duy nhất. Không đưa thông tin xác thực thật vào source control.

## Grain và ánh xạ của các fact

| Fact | Grain / nguồn | Ánh xạ khóa dimension | Đo lường chính |
| --- | --- | --- | --- |
| `fact_admission` | Một dòng cho mỗi `admission_id` từ `admission` | Ngày nhập viện, bệnh nhân, bệnh, khoa, khu, giường | `admission_count = 1`, thời gian nằm viện |
| `fact_bed_occupancy` | Một dòng cho mỗi giường mỗi ngày theo lịch, được sinh ra từ `bed` và `admission` | Ngày, giường, khu | Số giường occupied, available và capacity |
| `fact_billing` | Một dòng cho mỗi `bill_id` từ `billing` | Ngày hóa đơn, bệnh nhân và khoa từ lần nhập viện; chính sách bảo hiểm có hiệu lực vào ngày hóa đơn | Tổng tiền, số tiền được bảo hiểm chi trả, số tiền bệnh nhân phải trả; `billing_count = 1` |
| `fact_billing_detail` | Một dòng cho mỗi `billing_detail_id` từ `billing_detail` | Ngày hóa đơn, bệnh nhân, khoa và bảo hiểm kế thừa qua `bill_id` | Số tiền charge; `detail_count = 1` |
| `fact_diagnostic` | Một dòng cho mỗi `patient_diagnostic_id` | Ngày xét nghiệm, bệnh nhân từ admission, bác sĩ, xét nghiệm, khoa từ bài xét nghiệm | `diagnostic_count = 1` |
| `fact_prescription` | Một dòng cho mỗi `prescription_id` | Bệnh nhân, thuốc, khoa và bệnh từ lần nhập viện | Số ngày dùng thuốc; `prescription_count = 1` |
| `fact_staff_assignment` | Một dòng cho mỗi `assignment_id` | Nhân viên và khu | `assignment_count = 1` |

Tỷ lệ lấp đầy giường được tính theo snapshot hàng ngày: một lần nhập viện chiếm giường được gán từ ngày nhập viện đến ngày xuất viện, tính cả hai đầu mút. Loader bung mỗi lần lưu trú thành các ngày giường được sử dụng rồi loại cặp giường/ngày trùng nhau, nên các lần nhập viện chồng lấn không tính cùng một giường hai lần trong một ngày. Mỗi giường đóng góp một đơn vị capacity; điều này cho phép dashboard tổng hợp số giường occupied, available và total một cách nhất quán.

`billing_detail.bill_id` được giữ lại như một định danh nghiệp vụ degenerate, không dùng để join fact tables khi thực hiện aggregation. Bối cảnh hóa đơn được giải quyết từ các dòng source billing/admission để tránh nhân lên số liệu hóa đơn theo số dòng chi tiết. Dimension bảo hiểm có grain là patient-policy, vì vậy billing sẽ chọn chính sách bắt đầu gần nhất và có hiệu lực vào ngày hóa đơn.

## Kiểm tra xác thực

`--validate-only` kiểm tra xem tất cả 19 file CSV đã xử lý có tồn tại, các cột bắt buộc có mặt, khóa chính là duy nhất và không rỗng, các tham chiếu foreign-key không bị orphaned, và ngày nhập viện, hóa đơn, và chẩn đoán là định dạng ISO hợp lệ. Một lần kiểm tra thành công không cần thông tin xác thực PostgreSQL.

## Milestone 3: benchmark và DSS

Loader in thời gian từng câu SQL và tổng thời gian kết thúc nạp. Dùng `python scripts/load_facts.py --timings-csv benchmark_tv3.csv` để lưu số đo vào CSV. `fact_bed_occupancy` bung admission thành các ngày giường bận rồi loại cặp giường/ngày trùng lặp trước khi ghép với toàn bộ ngày giường; các index phục vụ tra occupancy theo ngày/khu, admission theo khu/ngày và assignment theo khu.

Chạy DSS bằng `python -m src.dss` sau khi đặt `DW_DSN` và nạp DW. Quy tắc cảnh báo, cách tính khu cần chú ý, cách chạy trên Windows/Linux và các giới hạn dữ liệu được mô tả trong [TV3 DSS và benchmark](TV3_dss_benchmark.md). Hướng dẫn chạy toàn bộ quy trình nằm ở [Hướng dẫn chạy TV3](huong_dan_chay_tv3.md).
