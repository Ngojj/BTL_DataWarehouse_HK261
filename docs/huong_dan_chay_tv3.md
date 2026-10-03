# Hướng dẫn chạy TV3: Fact và nạp dữ liệu

## 1. Mở terminal tại thư mục dự án

Trong VS Code, mở repo rồi chọn **Terminal → New Terminal**. Kiểm tra terminal đang ở thư mục có `README.md`:

```text
README.md
scripts/
sql/
data/
```

Nếu terminal chưa ở đó, dùng `cd` với đường dẫn nơi chính bạn lưu dự án. Ví dụ cú pháp:

```powershell
# Windows PowerShell — thay đường dẫn bên dưới bằng đường dẫn trên máy bạn
cd "<đường-dẫn-thư-mục-dự-án-của-bạn>"
```

```bash
# Linux — thay đường dẫn bên dưới bằng đường dẫn trên máy bạn
cd "<đường-dẫn-thư-mục-dự-án-của-bạn>"
```

## 2. Tạo database và các bảng dimension

### Tạo database

Trong pgAdmin, kết nối tới PostgreSQL, nhấp phải **Databases → Create → Database...**, đặt tên `healthcare_dw` rồi lưu. Nếu database đã tồn tại thì dùng database đó, không cần tạo lại.

### Chạy dimension SQL

Trong pgAdmin, nhấp phải database `healthcare_dw` → **Query Tool**. Dùng nút **Open File** trong Query Tool để mở `sql/healthcare_dw_dimensions.sql` từ thư mục dự án của bạn, rồi nhấn **Execute** (biểu tượng tia sét/F5). Khi hộp chọn file mở ra, duyệt đến nơi bạn đã lưu repo; không cần dùng đường dẫn của máy khác.

## 3. Cài dependency Python

Tạo virtual environment từ terminal tại thư mục dự án.

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn việc kích hoạt script, có thể bỏ qua bước activate và gọi Python trong virtual environment trực tiếp:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Nếu Linux báo thiếu `venv`, cài gói `python3-venv` bằng trình quản lý gói của bản phân phối rồi tạo lại virtual environment.

## 4. Kiểm tra CSV đầu vào

Tại thư mục gốc dự án, chạy:

```bash
python scripts/load_facts.py --validate-only
```

Trên một số bản Linux, nếu lệnh python không tồn tại, dùng python3. Trên Windows nếu chưa kích hoạt virtual environment, có thể dùng Python nằm trong thư mục .venv thay cho Python toàn cục.

Tiếp tục khi thấy `Input validation passed`. Bước này kiểm tra CSV, cột bắt buộc, khóa chính, khóa ngoại và một số trường ngày; nó chưa kết nối hoặc nạp dữ liệu vào PostgreSQL.

## 5. Cấu hình kết nối PostgreSQL

Bạn cần tên user PostgreSQL, mật khẩu, host, port và database. Với cài đặt local mặc định thường dùng host `localhost`, port `5432`, database `healthcare_dw`; hãy thay user/mật khẩu theo cấu hình của bạn.

**Windows PowerShell:**

```powershell
$env:DW_DSN = 'postgresql://postgres:MAT_KHAU_CUA_BAN@localhost:5432/healthcare_dw'
```

**Linux:**

```bash
export DW_DSN='postgresql://postgres:MAT_KHAU_CUA_BAN@localhost:5432/healthcare_dw'
```

Thay `MAT_KHAU_CUA_BAN` bằng mật khẩu PostgreSQL của bạn. Nếu mật khẩu có ký tự đặc biệt như `@`, `:`, `/` hoặc `#`, cần URL-encode ký tự đó trong DSN. Không ghi mật khẩu thật vào mã nguồn hoặc commit lên Git. Biến môi trường chỉ còn trong cửa sổ terminal hiện tại; mở terminal mới thì cần đặt lại.

**Linux dùng xác thực peer:** nếu `psql -U postgres` báo `Peer authentication failed`, đây thường là do PostgreSQL yêu cầu user Linux trùng với role DB khi kết nối qua socket. Có thể đặt mật khẩu role `postgres` bằng:

```bash
sudo -u postgres psql
```

Trong dấu nhắc PostgreSQL chạy `\password postgres`, nhập mật khẩu hai lần rồi thoát bằng `\q`. Loader kết nối TCP qua `localhost` theo DSN ở trên.

## 6. Chạy loader TV3

Từ thư mục gốc dự án, chạy:

```bash
python scripts/load_facts.py
```

Nếu cần, dùng python3 scripts/load_facts.py trên Linux hoặc dùng Python trong virtual environment .venv trên Windows.

Loader nạp CSV vào các bảng staging tạm, cập nhật dimension, rồi nạp bảy fact trong một transaction. Terminal in `Running SQL ...` để báo tiến độ. Lần chạy thành công sẽ kết thúc bằng `Load committed successfully` và số dòng của từng fact.

Không chạy riêng `sql/healthcare_dw_facts.sql` bằng pgAdmin/`psql`: file này cần các bảng `stg_*` do loader tạo ra.

## 7. Kiểm tra kết quả trong pgAdmin

Mở Query Tool của database `healthcare_dw`, chạy:

```sql
SELECT 'fact_admission' AS fact, COUNT(*) FROM dw.fact_admission
UNION ALL SELECT 'fact_bed_occupancy', COUNT(*) FROM dw.fact_bed_occupancy
UNION ALL SELECT 'fact_billing', COUNT(*) FROM dw.fact_billing
UNION ALL SELECT 'fact_billing_detail', COUNT(*) FROM dw.fact_billing_detail
UNION ALL SELECT 'fact_diagnostic', COUNT(*) FROM dw.fact_diagnostic
UNION ALL SELECT 'fact_prescription', COUNT(*) FROM dw.fact_prescription
UNION ALL SELECT 'fact_staff_assignment', COUNT(*) FROM dw.fact_staff_assignment;
```

## Xử lý lỗi thường gặp

| Thông báo / tình huống | Nguyên nhân và cách xử lý |
| --- | --- |
| `database "healthcare_dw" already exists` | Database đã tồn tại; tiếp tục dùng database đó. |
| `Peer authentication failed for user "postgres"` | Linux đang dùng xác thực peer qua socket. Đặt mật khẩu role `postgres` như phần 5 và kết nối Python qua `localhost`. |
| `relation "stg_patient" does not exist` | Đã chạy file fact trực tiếp. Chạy `scripts/load_facts.py`; loader tự tạo và nạp staging. |
| `could not change directory ... Permission denied` với `sudo -u postgres` | Đây là cảnh báo quyền thư mục khi chạy dưới user Linux `postgres`. Dùng pgAdmin để chạy dimension SQL như phần 2, hoặc bảo đảm user dịch vụ có thể đọc file. |
| PowerShell báo không nhận `psql` | Không cần `psql` nếu dùng pgAdmin theo hướng dẫn này. Nếu muốn dùng `psql`, cần cài PostgreSQL Command Line Tools và thêm thư mục `bin` vào PATH. |
| `KeyboardInterrupt` sau khi nhấn Ctrl+C | Tiến trình đã bị ngắt. Loader dùng một transaction nên phần chưa commit của lần chạy đó sẽ rollback. Chạy lại sau khi tiến trình cũ đã dừng hẳn. |
| Loader chạy lâu | Theo dõi dòng `Running SQL ...` trong terminal. Chỉ coi hoàn tất khi thấy `Load committed successfully`. |

## Ghi chú về số liệu hóa đơn

Trong dữ liệu nguồn hiện tại, tổng `billing_detail.amount` không khớp `billing.total_amount` ở phần lớn hóa đơn. ETL giữ lại giá trị nguồn và không tự điều chỉnh các khoản tiền. Vì vậy, không nên dùng hai fact này để khẳng định tổng các dòng chi tiết bằng tổng hóa đơn nếu chưa xử lý hoặc giải thích sai lệch.
