CREATE SCHEMA IF NOT EXISTS dw;

-- =====================================================
-- 1. Total Admissions theo tháng
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_admissions_by_month AS
SELECT
    EXTRACT(YEAR FROM d.full_date)::INT AS year,
    d.month,
    d.month_name,
    COUNT(*) AS total_admissions
FROM dw.fact_admission f
JOIN dw.dim_date d
    ON d.date_key = f.admission_date_key
GROUP BY
    EXTRACT(YEAR FROM d.full_date),
    d.month,
    d.month_name;

-- =====================================================
-- 2. Average Length of Stay theo tháng
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_average_length_of_stay AS
SELECT
    EXTRACT(YEAR FROM d.full_date)::INT AS year,
    d.month,
    d.month_name,
    AVG(f.length_of_stay_days) AS avg_length_of_stay_days
FROM dw.fact_admission f
JOIN dw.dim_date d
    ON d.date_key = f.admission_date_key
WHERE f.length_of_stay_days IS NOT NULL
GROUP BY
    EXTRACT(YEAR FROM d.full_date),
    d.month,
    d.month_name;

-- =====================================================
-- 3. Total Beds, Occupied Beds, Available Beds,
--    Bed Occupancy Rate theo ngày và khoa/khu vực
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_bed_occupancy_rate AS
SELECT
    d.full_date,
    f.ward_key,
    SUM(f.capacity_bed_count) AS total_beds,
    SUM(f.occupied_bed_count) AS occupied_beds,
    SUM(f.available_bed_count) AS available_beds,
    ROUND(
        100.0 * SUM(f.occupied_bed_count)
        / NULLIF(SUM(f.capacity_bed_count), 0),
        2
    ) AS bed_occupancy_rate
FROM dw.fact_bed_occupancy f
JOIN dw.dim_date d
    ON d.date_key = f.date_key
GROUP BY d.full_date, f.ward_key;

-- =====================================================
-- 4. Bed Occupancy Rate theo tháng và khu vực
-- Tính theo tổng bed-days, tránh cộng lặp công suất
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_bed_occupancy_by_month AS
SELECT
    EXTRACT(YEAR FROM d.full_date)::INT AS year,
    EXTRACT(MONTH FROM d.full_date)::INT AS month,
    f.ward_key,
    SUM(f.capacity_bed_count) AS total_bed_days,
    SUM(f.occupied_bed_count) AS occupied_bed_days,
    SUM(f.available_bed_count) AS available_bed_days,
    ROUND(
        100.0 * SUM(f.occupied_bed_count)
        / NULLIF(SUM(f.capacity_bed_count), 0),
        2
    ) AS bed_occupancy_rate
FROM dw.fact_bed_occupancy f
JOIN dw.dim_date d
    ON d.date_key = f.date_key
GROUP BY
    EXTRACT(YEAR FROM d.full_date),
    EXTRACT(MONTH FROM d.full_date),
    f.ward_key;

-- =====================================================
-- 5. Staff Assignments theo nhân viên, khu vực, ca
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_staff_assignments AS
SELECT
    e.employee_id,
    e.employee_name,
    e.role,
    w.ward_id,
    w.ward_name,
    f.shift,
    SUM(f.assignment_count) AS total_assignments
FROM dw.fact_staff_assignment f
JOIN dw.dim_employee e
    ON e.employee_key = f.employee_key
JOIN dw.dim_ward w
    ON w.ward_key = f.ward_key
GROUP BY
    e.employee_id, e.employee_name, e.role,
    w.ward_id, w.ward_name, f.shift;

-- =====================================================
-- 6. Total Billing, Insurance Covered, Patient Payable
--    theo tháng và khoa
-- =====================================================
-- =====================================================
-- 6. Total Billing, Insurance Covered, Patient Payable
--    theo tháng và khoa
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_billing_by_department AS
SELECT
    EXTRACT(YEAR FROM d.full_date)::INT AS year,
    d.month,
    d.month_name,
    dep.department_name,
    COUNT(*) AS total_bills,
    SUM(f.total_amount) AS total_billing,
    SUM(f.insurance_covered_amount) AS insurance_covered_amount,
    SUM(f.patient_payable_amount) AS patient_payable_amount
FROM dw.fact_billing f
JOIN dw.dim_date d
    ON d.date_key = f.billing_date_key
LEFT JOIN dw.dim_department dep
    ON dep.department_key = f.department_key
GROUP BY
    EXTRACT(YEAR FROM d.full_date),
    d.month,
    d.month_name,
    dep.department_name;

-- =====================================================
-- 7. Insurance Covered Amount theo nhà cung cấp
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_insurance_covered_amount AS
SELECT
    i.insurance_provider_id,
    i.provider_name,
    SUM(f.insurance_covered_amount) AS total_insurance_covered
FROM dw.fact_billing f
LEFT JOIN dw.dim_insurance i
    ON i.insurance_key = f.insurance_key
GROUP BY i.insurance_provider_id, i.provider_name;

-- =====================================================
-- 8. Patient Payable Amount theo phương thức thanh toán
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_patient_payable_amount AS
SELECT
    f.payment_status,
    f.payment_mode,
    SUM(f.patient_payable_amount) AS total_patient_payable,
    COUNT(*) AS total_bills
FROM dw.fact_billing f
GROUP BY f.payment_status, f.payment_mode;

-- =====================================================
-- 9. Drug Usage: số dòng kê đơn theo thuốc
-- Lưu ý: đây không phải tổng số lượng thuốc sử dụng
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_drug_usage AS
SELECT
    dr.drug_id,
    dr.drug_name,
    dr.drug_category,
    COUNT(*) AS prescription_lines,
    SUM(f.duration_days) AS total_prescribed_days
FROM dw.fact_prescription f
JOIN dw.dim_drug dr
    ON dr.drug_key = f.drug_key
GROUP BY dr.drug_id, dr.drug_name, dr.drug_category;

-- =====================================================
-- 10. Diagnostic Count theo tháng, xét nghiệm, khoa
-- =====================================================
CREATE OR REPLACE VIEW dw.vw_diagnostic_count AS
SELECT
    EXTRACT(YEAR FROM d.full_date)::INT AS year,
    d.month,
    t.test_name,
    t.test_category,
    dep.department_name,
    COUNT(*) AS diagnostic_count
FROM dw.fact_diagnostic f
JOIN dw.dim_date d
    ON d.date_key = f.diagnostic_date_key
JOIN dw.dim_diagnostic_test t
    ON t.test_key = f.test_key
LEFT JOIN dw.dim_department dep
    ON dep.department_key = f.department_key
GROUP BY
    EXTRACT(YEAR FROM d.full_date), d.month, t.test_name, t.test_category,
    dep.department_name;