

Sau khi xác định các Dimension, bước tiếp theo là xác định các Fact và Dimension mà từng Fact sử dụng. Một Dimension có thể được nhiều Fact dùng chung; mô hình này được gọi là **Fact Constellation** (hay **Galaxy Schema**).

## Grain của Fact

Grain mô tả ý nghĩa của một bản ghi trong Fact. Cần xác định grain trước khi thiết kế bảng Fact để bảo đảm mỗi dòng có ý nghĩa rõ ràng và không bị trùng lặp.

| Fact | Grain |
| --- | --- |
| `Fact_Admission` | 1 bản ghi cho 1 lượt nhập viện |
| `Fact_Bed_Occupancy` |1 bản ghi cho 1 giường tại 1 ngày|
| `Fact_Billing` | 1 bản ghi cho 1 hóa đơn |
| `Fact_Billing_Detail` | 1 bản ghi cho 1 khoản mục trong hóa đơn |
| `Fact_Diagnostic` | 1 bản ghi cho 1 lần xét nghiệm/chẩn đoán |
| `Fact_Prescription` | 1 bản ghi cho 1 dòng thuốc trong đơn |
| `Fact_Staff_Assignment` | 1 bản ghi cho 1 lần phân công nhân viên |

## Mô hình tổng thể
                    Dim_Date
                       │
       ┌───────────────┼─────────────────┐
       │               │                 │
       ▼               ▼                 ▼
Fact_Admission   Fact_Billing    Fact_Diagnostic
       │               │                 │
       │               │                 ├── Dim_Doctor
       │               │                 ├── Dim_Diagnostic_Test
       │               │                 └── Dim_Department
       │               │
       │               ├── Dim_Insurance
       │               ├── Dim_Patient
       │               └── Dim_Department
       │
       ├── Dim_Patient
       ├── Dim_Disease
       ├── Dim_Department
       ├── Dim_Ward
       └── Dim_Bed


Fact_Billing_Detail
       │
       ├── Dim_Date
       ├── Dim_Patient
       ├── Dim_Insurance
       └── Dim_Department


Fact_Prescription
       │
       ├── Dim_Patient
       ├── Dim_Drug
       ├── Dim_Department
       └── Dim_Disease


Fact_Staff_Assignment
       │
       ├── Dim_Employee
       └── Dim_Ward


Fact_Bed_Occupancy
       │
       ├── Dim_Date
       ├── Dim_Ward
       └── Dim_Bed

Fact_Bed_Occupancy sử dụng trực tiếp Dim_Date, Dim_Ward và Dim_Bed. Điều này cho phép phân tích tình trạng sử dụng giường theo ngày, theo giường và theo khu vực.

`Fact_Billing_Detail` có grain là từng khoản mục và liên kết với hóa đơn qua `bill_id`. Khi nạp dữ liệu, có thể lấy ngữ cảnh ngày, bệnh nhân và các Dimension liên quan từ hóa đơn tương ứng. Đây vẫn là Fact riêng, không nên nối trực tiếp hai bảng Fact để tổng hợp vì có thể làm nhân bản số liệu.

Các Fact dùng chung những Dimension như `Dim_Date`, `Dim_Patient` và `Dim_Department`. Vì vậy, mô hình tổng thể là **Fact Constellation / Galaxy Schema**, gồm nhiều Star Schema có các Dimension dùng chung.
