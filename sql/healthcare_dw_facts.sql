-- ============================================================
-- Healthcare Data Warehouse - TV3 Fact Tables and Loads
-- PostgreSQL. Run after healthcare_dw_dimensions.sql.
-- The loader creates temporary stg_* tables from data/processed/*.csv.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS dw;

CREATE TABLE IF NOT EXISTS dw.fact_admission (
    fact_admission_key BIGSERIAL PRIMARY KEY,
    admission_id       INT NOT NULL UNIQUE,
    admission_date_key INT NOT NULL REFERENCES dw.dim_date(date_key),
    patient_key        BIGINT NOT NULL REFERENCES dw.dim_patient(patient_key),
    disease_key        BIGINT REFERENCES dw.dim_disease(disease_key),
    department_key     BIGINT REFERENCES dw.dim_department(department_key),
    ward_key           BIGINT REFERENCES dw.dim_ward(ward_key),
    bed_key            BIGINT REFERENCES dw.dim_bed(bed_key),
    admission_type     VARCHAR(100),
    admission_status   VARCHAR(100),
    discharge_date     DATE,
    admission_count    SMALLINT NOT NULL DEFAULT 1 CHECK (admission_count = 1),
    length_of_stay_days INT CHECK (length_of_stay_days >= 0),
    overlapping_stay_flag BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS dw.fact_bed_occupancy (
    fact_bed_occupancy_key BIGSERIAL PRIMARY KEY,
    date_key               INT NOT NULL REFERENCES dw.dim_date(date_key),
    bed_key                BIGINT NOT NULL REFERENCES dw.dim_bed(bed_key),
    ward_key               BIGINT REFERENCES dw.dim_ward(ward_key),
    occupied_bed_count     SMALLINT NOT NULL CHECK (occupied_bed_count IN (0, 1)),
    available_bed_count    SMALLINT NOT NULL CHECK (available_bed_count IN (0, 1)),
    capacity_bed_count     SMALLINT NOT NULL DEFAULT 1 CHECK (capacity_bed_count = 1),
    UNIQUE (date_key, bed_key),
    CHECK (occupied_bed_count + available_bed_count = capacity_bed_count)
);

CREATE TABLE IF NOT EXISTS dw.fact_billing (
    fact_billing_key       BIGSERIAL PRIMARY KEY,
    bill_id                INT NOT NULL UNIQUE,
    billing_date_key       INT NOT NULL REFERENCES dw.dim_date(date_key),
    patient_key            BIGINT NOT NULL REFERENCES dw.dim_patient(patient_key),
    insurance_key          BIGINT REFERENCES dw.dim_insurance(insurance_key),
    department_key         BIGINT REFERENCES dw.dim_department(department_key),
    payment_status         VARCHAR(100),
    payment_mode           VARCHAR(100),
    total_amount           NUMERIC(15,2) NOT NULL CHECK (total_amount >= 0),
    insurance_covered_amount NUMERIC(15,2) NOT NULL CHECK (insurance_covered_amount >= 0),
    patient_payable_amount NUMERIC(15,2) NOT NULL CHECK (patient_payable_amount >= 0),
    billing_count          SMALLINT NOT NULL DEFAULT 1 CHECK (billing_count = 1)
);

CREATE TABLE IF NOT EXISTS dw.fact_billing_detail (
    fact_billing_detail_key BIGSERIAL PRIMARY KEY,
    billing_detail_id       INT NOT NULL UNIQUE,
    bill_id                 INT NOT NULL,
    billing_date_key        INT NOT NULL REFERENCES dw.dim_date(date_key),
    patient_key             BIGINT NOT NULL REFERENCES dw.dim_patient(patient_key),
    insurance_key           BIGINT REFERENCES dw.dim_insurance(insurance_key),
    department_key          BIGINT REFERENCES dw.dim_department(department_key),
    charge_type             VARCHAR(100),
    reference_id            INT,
    amount                  NUMERIC(15,2) NOT NULL CHECK (amount >= 0),
    detail_count            SMALLINT NOT NULL DEFAULT 1 CHECK (detail_count = 1)
);

CREATE TABLE IF NOT EXISTS dw.fact_diagnostic (
    fact_diagnostic_key BIGSERIAL PRIMARY KEY,
    patient_diagnostic_id INT NOT NULL UNIQUE,
    admission_id        INT NOT NULL,
    diagnostic_date_key INT NOT NULL REFERENCES dw.dim_date(date_key),
    patient_key         BIGINT NOT NULL REFERENCES dw.dim_patient(patient_key),
    doctor_key          BIGINT REFERENCES dw.dim_doctor(doctor_key),
    test_key            BIGINT NOT NULL REFERENCES dw.dim_diagnostic_test(test_key),
    department_key      BIGINT REFERENCES dw.dim_department(department_key),
    result_status       VARCHAR(100),
    diagnostic_count    SMALLINT NOT NULL DEFAULT 1 CHECK (diagnostic_count = 1)
);

CREATE TABLE IF NOT EXISTS dw.fact_prescription (
    fact_prescription_key BIGSERIAL PRIMARY KEY,
    prescription_id       INT NOT NULL UNIQUE,
    admission_id          INT NOT NULL,
    patient_key           BIGINT NOT NULL REFERENCES dw.dim_patient(patient_key),
    drug_key              BIGINT NOT NULL REFERENCES dw.dim_drug(drug_key),
    department_key        BIGINT REFERENCES dw.dim_department(department_key),
    disease_key           BIGINT REFERENCES dw.dim_disease(disease_key),
    dosage                VARCHAR(100),
    frequency             VARCHAR(100),
    duration_days         INT CHECK (duration_days > 0),
    prescription_count    SMALLINT NOT NULL DEFAULT 1 CHECK (prescription_count = 1)
);

CREATE TABLE IF NOT EXISTS dw.fact_staff_assignment (
    fact_staff_assignment_key BIGSERIAL PRIMARY KEY,
    assignment_id             INT NOT NULL UNIQUE,
    employee_key              BIGINT NOT NULL REFERENCES dw.dim_employee(employee_key),
    ward_key                  BIGINT NOT NULL REFERENCES dw.dim_ward(ward_key),
    shift                     VARCHAR(100),
    assignment_count          SMALLINT NOT NULL DEFAULT 1 CHECK (assignment_count = 1)
);

CREATE INDEX IF NOT EXISTS ix_fact_admission_date ON dw.fact_admission(admission_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_admission_department ON dw.fact_admission(department_key);
CREATE INDEX IF NOT EXISTS ix_fact_billing_date ON dw.fact_billing(billing_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_billing_detail_date ON dw.fact_billing_detail(billing_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_diagnostic_date ON dw.fact_diagnostic(diagnostic_date_key);

-- Load or refresh shared dimensions from the cleaned source files.
INSERT INTO dw.dim_patient (patient_id, gender, date_of_birth, blood_group, city, contact_number)
SELECT patient_id::INT, gender, NULLIF(date_of_birth, '')::DATE, blood_group, city, contact_number
FROM stg_patient
ON CONFLICT (patient_id) DO UPDATE SET
    gender = EXCLUDED.gender, date_of_birth = EXCLUDED.date_of_birth,
    blood_group = EXCLUDED.blood_group, city = EXCLUDED.city,
    contact_number = EXCLUDED.contact_number;

INSERT INTO dw.dim_disease (disease_id, disease_name, disease_category)
SELECT disease_id::INT, disease_name, disease_category FROM stg_disease
ON CONFLICT (disease_id) DO UPDATE SET
    disease_name = EXCLUDED.disease_name, disease_category = EXCLUDED.disease_category;

INSERT INTO dw.dim_department (department_id, department_name, department_type, floor_number, status)
SELECT department_id::INT, department_name, department_type,
       NULLIF(floor_number, '')::INT, status
FROM stg_department
ON CONFLICT (department_id) DO UPDATE SET
    department_name = EXCLUDED.department_name, department_type = EXCLUDED.department_type,
    floor_number = EXCLUDED.floor_number, status = EXCLUDED.status;

INSERT INTO dw.dim_ward (ward_id, ward_name, ward_type, total_beds, department_id)
SELECT ward_id::INT, ward_name, ward_type, NULLIF(total_beds, '')::INT,
       NULLIF(department_id, '')::INT
FROM stg_ward
ON CONFLICT (ward_id) DO UPDATE SET
    ward_name = EXCLUDED.ward_name, ward_type = EXCLUDED.ward_type,
    total_beds = EXCLUDED.total_beds, department_id = EXCLUDED.department_id;

INSERT INTO dw.dim_bed (bed_id, bed_number, bed_status, ward_id)
SELECT bed_id::INT, bed_number, bed_status, NULLIF(ward_id, '')::INT
FROM stg_bed
ON CONFLICT (bed_id) DO UPDATE SET
    bed_number = EXCLUDED.bed_number, bed_status = EXCLUDED.bed_status,
    ward_id = EXCLUDED.ward_id;

INSERT INTO dw.dim_doctor (doctor_id, employee_id, doctor_name, gender, role,
                           specialization, qualification, experience_years)
SELECT d.doctor_id::INT, e.employee_id::INT, e.employee_name, e.gender, e.role,
       d.specialization, d.qualification, NULLIF(d.experience_years, '')::INT
FROM stg_doctor d
JOIN stg_employee e ON e.employee_id::INT = d.employee_id::INT
ON CONFLICT (doctor_id) DO UPDATE SET
    employee_id = EXCLUDED.employee_id, doctor_name = EXCLUDED.doctor_name,
    gender = EXCLUDED.gender, role = EXCLUDED.role,
    specialization = EXCLUDED.specialization, qualification = EXCLUDED.qualification,
    experience_years = EXCLUDED.experience_years;

INSERT INTO dw.dim_employee (employee_id, employee_name, gender, role, employment_type,
                             date_of_joining, department_id)
SELECT employee_id::INT, employee_name, gender, role, employment_type,
       NULLIF(date_of_joining, '')::DATE, NULLIF(department_id, '')::INT
FROM stg_employee
ON CONFLICT (employee_id) DO UPDATE SET
    employee_name = EXCLUDED.employee_name, gender = EXCLUDED.gender,
    role = EXCLUDED.role, employment_type = EXCLUDED.employment_type,
    date_of_joining = EXCLUDED.date_of_joining, department_id = EXCLUDED.department_id;

INSERT INTO dw.dim_drug (drug_id, drug_name, brand_name, drug_category, unit_cost,
                         manufacturer_id, manufacturer_name, country,
                         reliability_rating, contract_status)
SELECT d.drug_id::INT, d.drug_name, d.brand_name, d.drug_category,
       NULLIF(d.unit_cost, '')::NUMERIC(15,2), m.manufacturer_id::INT,
       m.manufacturer_name, m.country, NULLIF(m.reliability_rating, '')::NUMERIC(3,2),
       m.contract_status
FROM stg_drug d
JOIN stg_drug_manufacturer m ON m.manufacturer_id::INT = d.manufacturer_id::INT
ON CONFLICT (drug_id) DO UPDATE SET
    drug_name = EXCLUDED.drug_name, brand_name = EXCLUDED.brand_name,
    drug_category = EXCLUDED.drug_category, unit_cost = EXCLUDED.unit_cost,
    manufacturer_id = EXCLUDED.manufacturer_id, manufacturer_name = EXCLUDED.manufacturer_name,
    country = EXCLUDED.country, reliability_rating = EXCLUDED.reliability_rating,
    contract_status = EXCLUDED.contract_status;

INSERT INTO dw.dim_insurance (patient_insurance_id, policy_number, patient_id,
                              insurance_provider_id, provider_name, provider_type,
                              coverage_percentage, policy_start_date, policy_end_date,
                              coverage_limit)
SELECT pi.patient_insurance_id::INT, pi.policy_number, pi.patient_id::INT,
       ip.insurance_provider_id::INT, ip.provider_name, ip.provider_type,
       NULLIF(pi.coverage_percentage, '')::NUMERIC(5,2),
       NULLIF(pi.policy_start_date, '')::DATE, NULLIF(pi.policy_end_date, '')::DATE,
       NULLIF(ip.coverage_limit, '')::NUMERIC(15,2)
FROM stg_patient_insurance pi
JOIN stg_insurance_provider ip
  ON ip.insurance_provider_id::INT = pi.insurance_provider_id::INT
ON CONFLICT (patient_insurance_id) DO UPDATE SET
    policy_number = EXCLUDED.policy_number, patient_id = EXCLUDED.patient_id,
    insurance_provider_id = EXCLUDED.insurance_provider_id,
    provider_name = EXCLUDED.provider_name, provider_type = EXCLUDED.provider_type,
    coverage_percentage = EXCLUDED.coverage_percentage,
    policy_start_date = EXCLUDED.policy_start_date, policy_end_date = EXCLUDED.policy_end_date,
    coverage_limit = EXCLUDED.coverage_limit;

INSERT INTO dw.dim_diagnostic_test (test_id, test_name, test_category, standard_cost, department_id)
SELECT test_id::INT, test_name, test_category, NULLIF(standard_cost, '')::NUMERIC(15,2),
       NULLIF(department_id, '')::INT
FROM stg_diagnostic_test
ON CONFLICT (test_id) DO UPDATE SET
    test_name = EXCLUDED.test_name, test_category = EXCLUDED.test_category,
    standard_cost = EXCLUDED.standard_cost, department_id = EXCLUDED.department_id;

-- The date dimension is daily so bed occupancy includes beds with zero occupancy.
WITH source_dates AS (
    SELECT admission_date::DATE AS full_date FROM stg_admission
    UNION ALL SELECT discharge_date::DATE FROM stg_admission WHERE NULLIF(discharge_date, '') IS NOT NULL
    UNION ALL SELECT bill_date::DATE FROM stg_billing
    UNION ALL SELECT test_date::DATE FROM stg_patient_diagnostic
), bounds AS (
    SELECT MIN(full_date) AS min_date, MAX(full_date) AS max_date FROM source_dates
), calendar AS (
    SELECT generated_date::DATE AS full_date
    FROM bounds, LATERAL generate_series(min_date, max_date, INTERVAL '1 day') AS generated_date
)
INSERT INTO dw.dim_date (date_key, full_date, day, month, month_name, quarter,
                         week, day_of_week, day_name, is_weekend)
SELECT TO_CHAR(full_date, 'YYYYMMDD')::INT, full_date,
       EXTRACT(DAY FROM full_date)::INT, EXTRACT(MONTH FROM full_date)::INT,
       TO_CHAR(full_date, 'FMMonth'), EXTRACT(QUARTER FROM full_date)::INT,
       EXTRACT(WEEK FROM full_date)::INT, EXTRACT(ISODOW FROM full_date)::INT,
       TO_CHAR(full_date, 'FMDay'), EXTRACT(ISODOW FROM full_date) IN (6, 7)
FROM calendar
ON CONFLICT (full_date) DO NOTHING;

INSERT INTO dw.fact_admission
    (admission_id, admission_date_key, patient_key, disease_key, department_key,
     ward_key, bed_key, admission_type, admission_status, discharge_date,
     admission_count, length_of_stay_days, overlapping_stay_flag)
SELECT a.admission_id::INT, dd.date_key, p.patient_key, dis.disease_key,
       dep.department_key, w.ward_key, bed.bed_key, a.admission_type, a.admission_status,
       NULLIF(a.discharge_date, '')::DATE, 1,
       NULLIF(a.length_of_stay_days, '')::INT,
       COALESCE(NULLIF(a.overlapping_stay_flag, '')::BOOLEAN, FALSE)
FROM stg_admission a
JOIN dw.dim_date dd ON dd.full_date = a.admission_date::DATE
JOIN dw.dim_patient p ON p.patient_id = a.patient_id::INT
LEFT JOIN dw.dim_disease dis ON dis.disease_id = NULLIF(a.disease_id, '')::INT
LEFT JOIN dw.dim_department dep ON dep.department_id = NULLIF(a.department_id, '')::INT
LEFT JOIN dw.dim_ward w ON w.ward_id = NULLIF(a.ward_id, '')::INT
LEFT JOIN dw.dim_bed bed ON bed.bed_id = NULLIF(a.bed_id, '')::INT
ON CONFLICT (admission_id) DO UPDATE SET
    admission_date_key = EXCLUDED.admission_date_key, patient_key = EXCLUDED.patient_key,
    disease_key = EXCLUDED.disease_key, department_key = EXCLUDED.department_key,
    ward_key = EXCLUDED.ward_key, bed_key = EXCLUDED.bed_key,
    admission_type = EXCLUDED.admission_type, admission_status = EXCLUDED.admission_status,
    discharge_date = EXCLUDED.discharge_date, length_of_stay_days = EXCLUDED.length_of_stay_days,
    overlapping_stay_flag = EXCLUDED.overlapping_stay_flag;

-- Occupancy is a daily snapshot. Expand stays into occupied bed-days first;
-- DISTINCT prevents overlapping admissions from counting a bed twice per day.
WITH date_bounds AS (
    SELECT MIN(admission_date::DATE) AS min_date,
           MAX(COALESCE(NULLIF(discharge_date, '')::DATE, admission_date::DATE)) AS max_date
    FROM stg_admission
), bed_days AS (
    SELECT b.bed_id::INT AS bed_id, w.ward_id::INT AS ward_id,
           generated_date::DATE AS full_date
    FROM stg_bed b
    LEFT JOIN stg_ward w ON w.ward_id::INT = b.ward_id::INT
    CROSS JOIN date_bounds bounds
    CROSS JOIN LATERAL generate_series(bounds.min_date, bounds.max_date, INTERVAL '1 day') AS generated_date
), occupied_bed_days AS (
    SELECT DISTINCT a.bed_id::INT AS bed_id,
           occupied_date::DATE AS full_date
    FROM stg_admission a
    CROSS JOIN LATERAL generate_series(
        a.admission_date::DATE,
        COALESCE(NULLIF(a.discharge_date, '')::DATE, a.admission_date::DATE),
        INTERVAL '1 day'
    ) AS occupied_date
    WHERE NULLIF(a.bed_id, '') IS NOT NULL
)
INSERT INTO dw.fact_bed_occupancy
    (date_key, bed_key, ward_key, occupied_bed_count, available_bed_count, capacity_bed_count)
SELECT dd.date_key, bed.bed_key, ward.ward_key,
       CASE WHEN occupied.bed_id IS NOT NULL THEN 1 ELSE 0 END,
       CASE WHEN occupied.bed_id IS NOT NULL THEN 0 ELSE 1 END,
       1
FROM bed_days bd
JOIN dw.dim_date dd ON dd.full_date = bd.full_date
JOIN dw.dim_bed bed ON bed.bed_id = bd.bed_id
LEFT JOIN dw.dim_ward ward ON ward.ward_id = bd.ward_id
LEFT JOIN occupied_bed_days occupied
       ON occupied.bed_id = bd.bed_id AND occupied.full_date = bd.full_date
ON CONFLICT (date_key, bed_key) DO UPDATE SET
    ward_key = EXCLUDED.ward_key, occupied_bed_count = EXCLUDED.occupied_bed_count,
    available_bed_count = EXCLUDED.available_bed_count,
    capacity_bed_count = EXCLUDED.capacity_bed_count;

WITH billing_context AS (
    SELECT b.*, a.patient_id, a.department_id,
           policy.insurance_key
    FROM stg_billing b
    JOIN stg_admission a ON a.admission_id::INT = b.admission_id::INT
    LEFT JOIN LATERAL (
        SELECT di.insurance_key
        FROM dw.dim_insurance di
        WHERE di.patient_id = a.patient_id::INT
          AND (di.policy_start_date IS NULL OR di.policy_start_date <= b.bill_date::DATE)
          AND (di.policy_end_date IS NULL OR di.policy_end_date >= b.bill_date::DATE)
        ORDER BY di.policy_start_date DESC NULLS LAST, di.insurance_key
        LIMIT 1
    ) policy ON TRUE
)
INSERT INTO dw.fact_billing
    (bill_id, billing_date_key, patient_key, insurance_key, department_key,
     payment_status, payment_mode, total_amount, insurance_covered_amount,
     patient_payable_amount, billing_count)
SELECT b.bill_id::INT, dd.date_key, p.patient_key, b.insurance_key, dep.department_key,
       b.payment_status, b.payment_mode, b.total_amount::NUMERIC(15,2),
       b.insurance_covered_amount::NUMERIC(15,2), b.patient_payable_amount::NUMERIC(15,2), 1
FROM billing_context b
JOIN dw.dim_date dd ON dd.full_date = b.bill_date::DATE
JOIN dw.dim_patient p ON p.patient_id = b.patient_id::INT
LEFT JOIN dw.dim_department dep ON dep.department_id = NULLIF(b.department_id, '')::INT
ON CONFLICT (bill_id) DO UPDATE SET
    billing_date_key = EXCLUDED.billing_date_key, patient_key = EXCLUDED.patient_key,
    insurance_key = EXCLUDED.insurance_key, department_key = EXCLUDED.department_key,
    payment_status = EXCLUDED.payment_status, payment_mode = EXCLUDED.payment_mode,
    total_amount = EXCLUDED.total_amount,
    insurance_covered_amount = EXCLUDED.insurance_covered_amount,
    patient_payable_amount = EXCLUDED.patient_payable_amount;

WITH billing_context AS (
    SELECT b.bill_id::INT AS bill_id, b.bill_date::DATE AS bill_date,
           a.patient_id::INT AS patient_id, a.department_id::INT AS department_id,
           policy.insurance_key
    FROM stg_billing b
    JOIN stg_admission a ON a.admission_id::INT = b.admission_id::INT
    LEFT JOIN LATERAL (
        SELECT di.insurance_key
        FROM dw.dim_insurance di
        WHERE di.patient_id = a.patient_id::INT
          AND (di.policy_start_date IS NULL OR di.policy_start_date <= b.bill_date::DATE)
          AND (di.policy_end_date IS NULL OR di.policy_end_date >= b.bill_date::DATE)
        ORDER BY di.policy_start_date DESC NULLS LAST, di.insurance_key
        LIMIT 1
    ) policy ON TRUE
)
INSERT INTO dw.fact_billing_detail
    (billing_detail_id, bill_id, billing_date_key, patient_key, insurance_key,
     department_key, charge_type, reference_id, amount, detail_count)
SELECT bd.billing_detail_id::INT, bc.bill_id, dd.date_key, p.patient_key,
       bc.insurance_key, dep.department_key, bd.charge_type,
       NULLIF(bd.reference_id, '')::INT, bd.amount::NUMERIC(15,2), 1
FROM stg_billing_detail bd
JOIN billing_context bc ON bc.bill_id = bd.bill_id::INT
JOIN dw.dim_date dd ON dd.full_date = bc.bill_date
JOIN dw.dim_patient p ON p.patient_id = bc.patient_id
LEFT JOIN dw.dim_department dep ON dep.department_id = bc.department_id
ON CONFLICT (billing_detail_id) DO UPDATE SET
    bill_id = EXCLUDED.bill_id, billing_date_key = EXCLUDED.billing_date_key,
    patient_key = EXCLUDED.patient_key, insurance_key = EXCLUDED.insurance_key,
    department_key = EXCLUDED.department_key, charge_type = EXCLUDED.charge_type,
    reference_id = EXCLUDED.reference_id, amount = EXCLUDED.amount;

INSERT INTO dw.fact_diagnostic
    (patient_diagnostic_id, admission_id, diagnostic_date_key, patient_key,
     doctor_key, test_key, department_key, result_status, diagnostic_count)
SELECT pd.patient_diagnostic_id::INT, a.admission_id::INT, dd.date_key, p.patient_key,
       doc.doctor_key, test.test_key, dep.department_key, pd.result_status, 1
FROM stg_patient_diagnostic pd
JOIN stg_admission a ON a.admission_id::INT = pd.admission_id::INT
JOIN dw.dim_date dd ON dd.full_date = pd.test_date::DATE
JOIN dw.dim_patient p ON p.patient_id = a.patient_id::INT
LEFT JOIN dw.dim_doctor doc ON doc.doctor_id = NULLIF(pd.doctor_id, '')::INT
JOIN dw.dim_diagnostic_test test ON test.test_id = pd.test_id::INT
LEFT JOIN dw.dim_department dep ON dep.department_id = test.department_id
ON CONFLICT (patient_diagnostic_id) DO UPDATE SET
    admission_id = EXCLUDED.admission_id, diagnostic_date_key = EXCLUDED.diagnostic_date_key,
    patient_key = EXCLUDED.patient_key, doctor_key = EXCLUDED.doctor_key,
    test_key = EXCLUDED.test_key, department_key = EXCLUDED.department_key,
    result_status = EXCLUDED.result_status;

INSERT INTO dw.fact_prescription
    (prescription_id, admission_id, patient_key, drug_key, department_key,
     disease_key, dosage, frequency, duration_days, prescription_count)
SELECT rx.prescription_id::INT, a.admission_id::INT, p.patient_key, drug.drug_key,
       dep.department_key, dis.disease_key, rx.dosage, rx.frequency,
       NULLIF(rx.duration_days, '')::INT, 1
FROM stg_prescription rx
JOIN stg_admission a ON a.admission_id::INT = rx.admission_id::INT
JOIN dw.dim_patient p ON p.patient_id = a.patient_id::INT
JOIN dw.dim_drug drug ON drug.drug_id = rx.drug_id::INT
LEFT JOIN dw.dim_department dep ON dep.department_id = a.department_id::INT
LEFT JOIN dw.dim_disease dis ON dis.disease_id = NULLIF(a.disease_id, '')::INT
ON CONFLICT (prescription_id) DO UPDATE SET
    admission_id = EXCLUDED.admission_id, patient_key = EXCLUDED.patient_key,
    drug_key = EXCLUDED.drug_key, department_key = EXCLUDED.department_key,
    disease_key = EXCLUDED.disease_key, dosage = EXCLUDED.dosage,
    frequency = EXCLUDED.frequency, duration_days = EXCLUDED.duration_days;

INSERT INTO dw.fact_staff_assignment
    (assignment_id, employee_key, ward_key, shift, assignment_count)
SELECT sa.assignment_id::INT, employee.employee_key, ward.ward_key, sa.shift, 1
FROM stg_staff_assignment sa
JOIN dw.dim_employee employee ON employee.employee_id = sa.employee_id::INT
JOIN dw.dim_ward ward ON ward.ward_id = sa.ward_id::INT
ON CONFLICT (assignment_id) DO UPDATE SET
    employee_key = EXCLUDED.employee_key, ward_key = EXCLUDED.ward_key,
    shift = EXCLUDED.shift;
