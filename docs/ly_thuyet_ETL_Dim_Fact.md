# Lý thuyết nền: ETL, Fact, Dimension

> Tài liệu tham khảo cá nhân — tổng hợp lý thuyết cốt lõi để hiểu và bảo vệ các quyết định thiết kế trong đề tài
> *Healthcare Data Warehouse and Decision Support System*. Các ví dụ minh họa lấy trực tiếp từ thiết kế của nhóm
> (`docs/Dimenson_design/star_schema.md`, `sql/healthcare_dw_dimensions.sql`).

## 1. ETL là gì — và tại sao phải làm

**ETL = Extract – Transform – Load**: quy trình đưa dữ liệu từ hệ thống tác nghiệp (OLTP — nơi bệnh viện nhập
liệu hàng ngày: admission, billing...) vào kho dữ liệu (OLAP — nơi phục vụ phân tích, báo cáo).

| Bước | Ý nghĩa | Trong project |
|---|---|---|
| **Extract** | Đọc dữ liệu thô từ nguồn, giữ nguyên, chưa sửa gì | Notebook M2, mục 1: `pd.read_csv` 19 bảng từ `data/raw/` |
| **Transform** | Làm sạch, chuẩn hóa, kiểm tra ràng buộc, biến đổi cấu trúc nguồn (quan hệ chuẩn hóa – 3NF) thành cấu trúc đích (star schema – denormalized) | Notebook M2, mục 3–4 (check FK, business rule, chuẩn hóa `contact_number`...) → map sang `dw.dim_*` / `dw.fact_*` |
| **Load** | Ghi dữ liệu đã transform vào kho đích | `data/processed/` (CSV trung gian) → `INSERT`/`COPY` vào `dw.dim_*`, `dw.fact_*` |

**Tại sao không query thẳng vào DB tác nghiệp để làm báo cáo?**

- DB tác nghiệp (OLTP) thiết kế để **ghi nhanh, giao dịch nhỏ, chuẩn hóa cao (3NF)** nhằm tránh trùng lặp — ví
  dụ `admission` chỉ lưu `department_id`, muốn biết tên khoa phải `JOIN department`. Chạy hàng loạt câu JOIN
  phức tạp trên DB đang phục vụ nhập liệu thực tế sẽ làm chậm hệ thống, thậm chí khóa bảng.
- Dữ liệu tác nghiệp thường **rải rác nhiều hệ thống/bảng** (ở đây là 19 bảng rời) — cần gom, làm sạch, chuẩn
  hóa về một mô hình thống nhất trước khi phân tích được.
- DW cần lưu **lịch sử** để so sánh xu hướng theo thời gian, trong khi hệ OLTP thường chỉ giữ trạng thái hiện
  tại (ví dụ `bed.bed_status` chỉ có giá trị *hiện tại*, không biết hôm qua giường nào trống).

→ ETL là cầu nối biến dữ liệu tác nghiệp rời rạc, chuẩn hóa, thành dữ liệu phân tích tập trung, sạch, đúng cấu
trúc cho DW.

## 2. Fact (bảng Sự kiện) là gì

**Fact = bảng chứa các số đo định lượng (measures) của một sự kiện nghiệp vụ**, cộng với các khóa ngoại trỏ tới
Dimension để biết "số đo đó gắn với ngữ cảnh nào".

Ví dụ `Fact_Admission`:

```
admission_id (degenerate dim) | date_key | patient_key | department_key | ward_key | bed_key | disease_key
| length_of_stay_days (measure)
```

- **Measure** (số đo): cột số có thể tổng hợp — ví dụ `length_of_stay_days`, `total_amount` (ở `Fact_Billing`).
  Đây là cái người quản lý *muốn tính tổng/trung bình*.
- **Foreign key tới Dimension**: `date_key`, `patient_key`... cho biết số đo đó thuộc về bệnh nhân nào, khoa
  nào, ngày nào.
- **Grain** (hạt — khái niệm quan trọng nhất khi thiết kế Fact): *một dòng trong Fact tương ứng với đúng một
  gì?* Phải chốt grain **trước khi** tạo bảng, nếu sai (ví dụ lẫn "1 lượt nhập viện" với "1 ngày nằm viện"
  trong cùng 1 Fact) thì `SUM()` sẽ ra số sai (double-counting).

| Fact | Grain |
|---|---|
| `Fact_Admission` | 1 dòng = 1 lượt nhập viện |
| `Fact_Bed_Occupancy` | 1 dòng = 1 giường tại 1 ngày |
| `Fact_Billing` | 1 dòng = 1 hóa đơn |
| `Fact_Billing_Detail` | 1 dòng = 1 khoản mục trong hóa đơn |
| `Fact_Diagnostic` | 1 dòng = 1 lần xét nghiệm/chẩn đoán |
| `Fact_Prescription` | 1 dòng = 1 dòng thuốc trong đơn |
| `Fact_Staff_Assignment` | 1 dòng = 1 lần phân công nhân viên |

**Phân loại measure:**

- *Additive* — cộng được theo mọi chiều: `total_amount`, `length_of_stay_days`.
- *Semi-additive* — cộng được theo một số chiều nhưng không phải tất cả: `Fact_Bed_Occupancy` (số giường đang
  dùng) cộng được theo khoa nhưng **không cộng được theo ngày** (cộng 7 ngày liên tiếp của 1 giường không ra số
  có ý nghĩa) — đúng dạng *periodic snapshot fact*.
- *Non-additive* — không cộng được, chỉ tính trung bình/tỷ lệ: `coverage_percentage`, `Bed_Occupancy_Rate`.

## 3. Dimension (bảng Chiều) là gì

**Dimension = bảng chứa thông tin mô tả, ngữ cảnh** (ai, cái gì, ở đâu, khi nào) để trả lời câu hỏi "lọc theo
gì / nhóm theo gì". Dimension trả lời cho trục **WHO/WHAT/WHERE/WHEN**, Fact trả lời **HOW MUCH/HOW MANY**.

Ví dụ `Dim_Patient`: `patient_key (surrogate), patient_id (natural key), gender, date_of_birth, blood_group, city`.

Hai khái niệm quan trọng:

- **Natural key** (`patient_id`): khóa gốc từ hệ nguồn.
- **Surrogate key** (`patient_key`, kiểu `BIGSERIAL`): khóa nhân tạo, sinh riêng cho DW.

**Tại sao cần thêm surrogate key thay vì dùng thẳng `patient_id`?**

1. Tách DW khỏi phụ thuộc cấu trúc khóa của hệ nguồn (nếu sau này đổi hệ nguồn/merge nhiều nguồn có khóa
   trùng, DW vẫn ổn định).
2. Phục vụ **SCD (Slowly Changing Dimension)** — khi một thuộc tính dimension thay đổi theo thời gian (ví dụ
   bệnh nhân chuyển `city`), SCD Type 2 cần tạo **dòng mới** với surrogate key mới nhưng cùng natural key, để
   giữ lại lịch sử. Nếu dùng `patient_id` làm khóa chính thì không thể có 2 dòng cho cùng 1 bệnh nhân.
3. Join nhanh hơn (khóa số nguyên tăng dần, không phải lo trùng giữa các nguồn).

### 3.1 SCD (Slowly Changing Dimension) — dimension đổi theo thời gian

**SCD = dimension có thuộc tính thay đổi theo thời gian** (không nhanh như Fact, nhưng vẫn đổi — vài tháng/năm
1 lần). Vấn đề cần giải quyết: khi giá trị đổi, báo cáo quá khứ không được bị tính nhầm theo giá trị mới.

Ví dụ: `drug.unit_cost` hôm nay 50.000đ, sau đổi 65.000đ. Nếu xử lý sai, tính "chi phí thuốc đã kê quý 1" (lúc
giá còn 50.000đ) có thể vô tình lấy giá hiện tại (65.000đ) nhân ngược lại cho dữ liệu quý 1 → sai, dù giao dịch
đó đã xảy ra với giá cũ.

**3 cách xử lý hay dùng:**

| Type | Cách làm | Giữ lịch sử? | Khi nào dùng |
|---|---|---|---|
| **Type 1** | Ghi đè trực tiếp giá trị cũ | ❌ Không | Đổi do sửa lỗi, hoặc không ai cần biết giá trị cũ |
| **Type 2** | Thêm **dòng mới** (surrogate key mới, cùng natural key), đánh dấu bằng `valid_from`/`valid_to`/`is_current` | ✅ Có | Báo cáo quá khứ bắt buộc dùng đúng giá trị tại đúng thời điểm |
| **Type 3** | Thêm cột `previous_xxx` cạnh cột hiện tại | 1 lớp gần nhất | Ít dùng, chỉ so sánh trước/sau 1 lần đổi gần nhất |

**Quyết định của nhóm (phạm vi giới hạn theo thời gian còn lại):** áp dụng **Type 2** cho 2 dimension ảnh hưởng
trực tiếp tới KPI đang có trên dashboard — `Dim_Ward` (theo dõi `total_beds`, ảnh hưởng tỷ lệ lấp đầy giường)
và `Dim_Drug` (theo dõi `unit_cost`, ảnh hưởng chi phí thuốc). Các dimension còn lại giữ **Type 1** vì không
ảnh hưởng KPI nào đang triển khai.

**Minh hoạ Type 2 cho `Dim_Drug`** (đã implement + verify thật trong `sql/healthcare_dw_facts.sql`):

| drug_key (PK) | drug_id | unit_cost | valid_from | valid_to | is_current |
|---|---|---|---|---|---|
| 29 | 1 | 252.00 | 1900-01-01 | 2026-11-04 | false |
| 252 | 1 | 999999.99 | 2026-11-05 | NULL | true |

Khi `Fact_Prescription` ghi nhận đơn thuốc, nó join tới **đúng `drug_key` có hiệu lực tại ngày nhập viện**
(`dim_drug.valid_from <= admission_date <= dim_drug.valid_to`), không phải lúc nào cũng lấy `is_current = true`.
Dòng đầu tiên seed `valid_from = 1900-01-01` (không phải ngày nạp) vì nguồn dữ liệu là 1 bản snapshot, không
phải change-log — không biết giá đó có hiệu lực từ ngày nào thật, nên seed sớm để phủ hết toàn bộ lịch sử quan
sát được (2020–2025); chỉ khi phát hiện thay đổi thật ở lần nạp sau mới dùng ngày nạp làm `valid_from` của
phiên bản mới.

**Giới hạn đã biết:** `Fact_Staff_Assignment` không có cột ngày (hạn chế đã ghi nhận từ trước), nên không join
theo thời gian được như trên — phải fallback về `is_current = true`.

## 4. Tại sao tách Fact/Dimension (Star Schema) thay vì giữ nguyên 3NF như hệ nguồn?

| Lý do | Giải thích |
|---|---|
| **Tốc độ truy vấn** | Hệ nguồn chuẩn hóa (3NF) tối ưu cho *ghi* (insert/update nhanh, không trùng lặp). DW tối ưu cho *đọc hàng loạt* (aggregate hàng chục nghìn dòng). Star schema giảm số lượng JOIN cần thiết — Fact chỉ join trực tiếp tới Dimension, không phải join nhiều tầng như 3NF (`admission → ward → department`). |
| **Dễ hiểu với người dùng nghiệp vụ** | Nhà quản lý không cần biết chuẩn hóa dữ liệu — chỉ cần biết "có bảng Admission (số liệu), và các bảng mô tả Patient/Ward/Date để lọc theo". Mô hình gần với cách con người nghĩ ("theo khoa nào, theo tháng nào"). |
| **Phù hợp cho OLAP (roll-up/drill-down/slice/dice)** | Công cụ BI và câu lệnh OLAP đều giả định sẵn cấu trúc Fact + Dimension. Ví dụ "chi phí theo quý, theo khoa" chính là roll-up trên `Dim_Date` và `Dim_Department`. |
| **Lưu lịch sử mà hệ OLTP không giữ** | `bed.bed_status` không có lịch sử — phải tự sinh `Fact_Bed_Occupancy` (snapshot theo ngày) trong ETL. Đây là lý do DW ≠ bản sao của OLTP. |
| **Tách biệt "đo cái gì" và "theo ngữ cảnh nào"** | Khi thêm 1 chiều phân tích mới (ví dụ thêm `Dim_Insurance`), chỉ cần thêm cột FK vào Fact liên quan, không phải sửa cấu trúc toàn hệ thống. |

## 5. Tóm tắt quy trình áp dụng cho BTL

```
OLTP (19 bảng CSV, 3NF)
   │  EXTRACT (đọc raw)
   ▼
Raw DataFrames
   │  TRANSFORM (clean: FK, business rule, format — đã làm ở Milestone 2)
   │  TRANSFORM (reshape: tách Fact đo lường / Dimension mô tả)
   ▼
dw.dim_* (11 bảng, có surrogate key)        dw.fact_* (7 bảng, có grain rõ, FK tới dim)
   │                                                  │
   └──────────────────  LOAD  ─────────────────────────┘
                             ▼
                   Star / Galaxy Schema hoàn chỉnh
                             │
                    Dashboard (OLAP query) + DSS (cảnh báo)
```

Nắm các mục trên là đủ để trả lời phần lý thuyết trong báo cáo và phần Q&A khi thuyết trình: **ETL là gì / tại
sao cần**, **Fact là gì / grain là gì**, **Dimension là gì / surrogate key để làm gì**, **SCD là gì / vì sao
chọn Type 2 cho `Dim_Ward`/`Dim_Drug`**, **tại sao denormalize thành star schema**.
