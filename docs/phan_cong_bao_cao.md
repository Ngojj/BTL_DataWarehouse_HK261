# Phân công viết báo cáo + thuyết trình

Mỗi thành viên viết phần báo cáo của mình và tự thuyết trình đúng phần đó.

## TV1

**Viết:**
- Giới thiệu đề tài, phân tích yêu cầu nghiệp vụ, phạm vi (dựa trên `docs/milestone1_phan_tich_thiet_ke.docx`)
- Hiện thực hệ thống: backend chạy thật (DB, loader, verify), Dashboard/Frontend (5 trang)
- Đánh giá kết quả, hạn chế, hướng phát triển (tổng hợp: billing_detail lệch 99,9%, `dim_date` thiếu `year`, `fact_staff_assignment`/`fact_prescription` thiếu chiều ngày, SCD edge case)
- Kết luận

**Thuyết trình:** phần tương ứng ở trên.

## TV2

**Viết:**
- Cơ sở lý thuyết: ETL, Fact, Dimension, SCD (dựa trên `docs/ly_thuyet_ETL_Dim_Fact.md`)
- Thiết kế kho dữ liệu: star schema, mô hình Fact/Dimension (`docs/Dimenson_design/`)
- OLAP: 10 view phân tích (`sql/healthcare_olap_views.sql`)

**Thuyết trình:** phần tương ứng ở trên.

## TV3

**Viết:**
- Cơ sở lý thuyết: MSS/DSS, khái niệm và giai đoạn ra quyết định (chưa có tư liệu sẵn — cần viết mới)
- ETL: quy trình nạp Fact, benchmark/tối ưu loader (`docs/TV3_fact_loading.md`, `docs/TV3_dss_benchmark.md`)
- Thiết kế & hiện thực DSS: 3 luật cảnh báo (`src/dss/engine.py`)

**Thuyết trình:** phần tương ứng ở trên.


