# TV3 — DSS cơ bản và benchmark loader

## 1. Phạm vi đã hiện thực

TV3 trong Milestone 3 có hai phần: theo dõi hiệu năng loader tập trung vào `fact_bed_occupancy`, và DSS cơ bản gồm ba luật cảnh báo của Milestone 1. DSS chỉ cung cấp thông tin để quản lý xem xét; không thay thế quyết định nghiệp vụ/y tế.

## 2. Benchmark và tối ưu loader

Loader bung từng admission thành các ngày giường được sử dụng, loại cặp `bed_id/date` trùng nhau để xử lý admissions chồng lấn, rồi ghép kết quả với toàn bộ lịch `bed/date`. Cách này tránh truy vấn `EXISTS` quét staging admission cho từng cặp giường/ngày.

Mỗi câu SQL hiện in thời gian chạy sau khi hoàn tất. Thời gian tổng in ở `Load committed successfully` bao gồm staging, SQL, đếm dòng và commit. Để lưu số đo từng câu SQL:

```bash
python scripts/load_facts.py --timings-csv benchmark_tv3.csv
```

File CSV gồm số thứ tự câu SQL, phần đầu câu lệnh và số giây. Tìm câu có `WITH date_bounds AS (` để xem phần occupancy. Loader tạo các index cho truy vấn DW phổ biến, gồm `(date_key, ward_key)` trên occupancy, `(ward_key, admission_date_key)` trên admission và `(ward_key)` trên staff assignment. Index làm truy vấn DSS theo khu/ngày nhanh hơn nhưng có thêm chi phí khi nạp; dùng CSV timing để quyết định có giữ chúng trong workload thực tế.

Để so sánh công bằng, chạy cùng bộ CSV và cấu hình máy/PostgreSQL, ghi lại thời gian tổng và thời gian riêng câu occupancy. So sánh trước/sau trên cùng máy và cùng database; `ON CONFLICT` làm lần chạy sau là upsert nên trạng thái cache/database có thể khác lần đầu. Không diễn giải chênh lệch giữa hai máy hoặc hai lần chạy khác cấu hình là hiệu quả riêng của thuật toán.

## 3. Các luật DSS

Chạy sau khi đã nạp DW và đặt `DW_DSN`:

```bash
python -m src.dss
```

Trên Linux có thể cần `python3 -m src.dss`. Tùy chọn:

```bash
python -m src.dss --lookback-days 60
python -m src.dss --inventory-csv data/processed/drug_inventory.csv
```

Lệnh in JSON với ba phần:

### 3.1 Occupancy theo khu

Lấy snapshot mới nhất trong `fact_bed_occupancy`, tính `occupied_beds / capacity_beds` theo khu:

- `< 70%`: `NORMAL`
- `70%` đến `< 85%`: `WATCH`
- `>= 85%`: `HIGH_PRESSURE`

Ranh giới 85% được xếp vào mức áp lực cao theo yêu cầu M1 “từ 85% trở lên”. Đây là ngưỡng minh họa do nhóm đề xuất, không phải tiêu chuẩn y tế.

### 3.2 Tồn kho thuốc

Đọc `current_stock`, `reorder_level` và `drug_id` từ `data/processed/drug_inventory.csv`. Chỉ phát cảnh báo `LOW_STOCK` nếu `current_stock < reorder_level`; bằng mức reorder thì chưa cảnh báo. Tên thuốc được tra qua `dw.dim_drug`.

### 3.3 Khu vực cần chú ý

Admissions và LOS được tính trong cửa sổ gần nhất (mặc định 30 ngày), kết thúc ở ngày snapshot occupancy mới nhất trong DW. Bốn chỉ báo bất lợi:

1. Occupancy từ 70% trở lên.
2. Admissions của khu cao hơn trung bình admissions giữa các khu trong cửa sổ.
3. LOS trung bình của khu cao hơn trung bình LOS giữa các khu có LOS.
4. Số assignment nhân sự của khu thấp hơn trung bình assignment giữa các khu.

Điểm là số chỉ báo bất lợi (0–4). Khu được `attention_flag = true` khi có ít nhất 2 chỉ báo; trường `reasons` cho biết lý do. Vì M1 không quy định ngưỡng số cho luật kết hợp, đây là heuristic tương đối để ưu tiên rà soát. Assignment là số dòng phân công được lưu trong nguồn, không phải FTE hay số nhân viên đang trực theo thời gian thực.

## 4. Giới hạn dữ liệu/diễn giải

- `drug_inventory` hiện là nguồn CSV đã xử lý, không phải fact table trong DW. DSS đọc CSV này để phản ánh quy mô hiện tại của mô hình.
- `fact_staff_assignment` không có ngày hiệu lực/ca trực chuẩn hóa theo thời gian, nên staffing chỉ dùng như số assignment hiện có.
- Nếu không có snapshot occupancy trong DW, các phần cảnh báo theo khu sẽ trả danh sách rỗng; cần nạp fact trước.
