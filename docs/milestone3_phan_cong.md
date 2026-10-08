# Milestone 3 — Phân công công việc

## Mục tiêu

Hoàn chỉnh hệ thống: DW chạy thật trên Postgres, OLAP queries, Dashboard, DSS cơ bản.

## Phân công

### TV1

- Chạy thật `scripts/load_facts.py` trên PostgreSQL, verify `COUNT(*)` từng fact.
- Xây Dashboard (4 cái theo phác thảo M1): Hospital Overview, Hospital Capacity, Financial & Insurance, Pharmacy & Diagnostic.

### TV2

- Viết bộ OLAP queries/views trả lời các câu hỏi nghiệp vụ và KPI đã liệt kê ở Milestone 1:
  - `vw_admissions_by_month`
  - `vw_bed_occupancy_rate`
  - `vw_billing_by_department`
  - (bổ sung thêm theo danh sách KPI ở `docs/milestone1_phan_tich_thiet_ke.docx`)
- Quyết định SCD Type (1 hoặc 2) cho các Dimension dễ đổi: `Dim_Ward.total_beds`, `Dim_Drug.unit_cost`.

### TV3

- Benchmark/tối ưu loader với `fact_bed_occupancy` (~900K dòng), thêm index nếu cần.
- Xây DSS cơ bản (`src/dss/`), hiện thực 3 luật cảnh báo theo M1:
  - Bed occupancy: <70% bình thường, 70–85% cần theo dõi, ≥85% áp lực cao.
  - Cảnh báo tồn kho thuốc: `current_stock < reorder_level`.
  - Cảnh báo khu vực cần chú ý (kết hợp nhập viện + LOS + công suất + nhân sự).



