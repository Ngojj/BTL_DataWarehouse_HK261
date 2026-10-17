# Dashboard (TV1)

Streamlit app đọc trực tiếp từ schema `dw` trên PostgreSQL (các bảng do `sql/healthcare_dw_dimensions.sql`
và `sql/healthcare_dw_facts.sql` tạo ra, nạp bởi `scripts/load_facts.py`).

## Chạy

Từ thư mục gốc repo:

```bash
pip install -r requirements.txt

export DW_DSN='postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'
streamlit run src/app/app.py
```

PowerShell:

```powershell
$env:DW_DSN = 'postgresql://postgres:MAT_KHAU@localhost:5432/healthcare_dw'
streamlit run src/app/app.py
```

## Các trang

`app.py` chỉ là router (`st.navigation`), không tự vẽ nội dung — toàn bộ giao diện nằm trong `app_pages/`.

| Trang | Nội dung |
| --- | --- |
| `app_pages/overview.py` (Hospital overview) | Tổng lượt nhập viện, tổng bệnh nhân, LOS trung bình, tổng chi phí, công suất giường mới nhất, xu hướng nhập viện theo tháng |
| `app_pages/hospital_capacity.py` | Tỷ lệ lấp đầy giường theo khu, cảnh báo khu vực áp lực cao, xu hướng công suất theo tháng, nhập viện/LOS theo khoa |
| `app_pages/financial_insurance.py` | Tổng chi phí, bảo hiểm chi trả vs. bệnh nhân tự trả, xu hướng theo thời gian, chi phí theo khoa, cơ cấu theo loại khoản mục |
| `app_pages/pharmacy_diagnostic.py` | Top thuốc được kê nhiều nhất, thuốc tồn kho thấp, thống kê chẩn đoán |
| `app_pages/dss_alerts.py` | Cảnh báo công suất giường, tồn kho thấp, khu vực cần chú ý — dùng lại `src/dss` (TV3, nhánh `TV3`, chưa merge vào `main`). Trang này tự ẩn nếu `src/dss` chưa có trên nhánh hiện tại. |

## Cấu trúc code

- `app.py` — entry point: `st.set_page_config` + `st.navigation` (router, icon cho từng trang trong sidebar).
- `db.py` — tạo SQLAlchemy engine từ biến môi trường `DW_DSN` (cache bằng `st.cache_resource`).
- `queries.py` — toàn bộ câu SQL, mỗi hàm trả về `pandas.DataFrame`/dict, cache bằng `st.cache_data`.
- `filters.py` — widget sidebar dùng chung (khoảng thời gian, khoa).
- `app_pages/` — nội dung từng trang (không dùng tên `pages/` để tránh Streamlit tự động phát hiện multipage kiểu cũ, chồng lên `st.navigation`).
- `../../.streamlit/config.toml` — theme (dense-dashboard, dual light/dark, màu xanh `#1D4ED8`/`#2563EB`).

## Lưu ý

- `fact_prescription` không có khóa ngày trực tiếp; các truy vấn theo thời gian ở trang Pharmacy join qua
  `fact_admission.admission_id` để lấy ngày nhập viện.
- `dim_date` chưa có cột `year`; các truy vấn trend dùng `DATE_TRUNC('month', full_date)` thay vì join theo năm/tháng.
- Trang Financial & Insurance hiển thị cảnh báo về sai lệch giữa `billing_detail.amount` và `billing.total_amount`
  (~99,9% hóa đơn lệch, xem `docs/huong_dan_chay_tv3.md`).
