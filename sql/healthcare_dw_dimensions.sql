-- ============================================================
-- Healthcare Data Warehouse
-- TV2 - Dimension Tables
-- PostgreSQL
-- ============================================================

-- 1. Create database separately if needed:
-- CREATE DATABASE healthcare_dw;
--
-- Then connect to healthcare_dw before running the rest.

-- ============================================================
-- Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS dw;

-- ============================================================
-- 1. Dim_Date
-- Natural Key: full_date
-- Primary Key: date_key
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key        INT PRIMARY KEY,
    full_date       DATE NOT NULL UNIQUE,
    day             INT,
    month           INT,
    month_name      VARCHAR(20),
    quarter         INT,
    week            INT,
    day_of_week     INT,
    day_name        VARCHAR(20),
    is_weekend      BOOLEAN
);

-- ============================================================
-- 2. Dim_Patient
-- Source: patient
-- Natural Key: patient_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_patient (
    patient_key     BIGSERIAL PRIMARY KEY,
    patient_id      INT NOT NULL UNIQUE,
    gender          VARCHAR(20),
    date_of_birth   DATE,
    blood_group     VARCHAR(10),
    city            VARCHAR(100),
    contact_number  VARCHAR(30)
);

-- ============================================================
-- 3. Dim_Disease
-- Source: disease
-- Natural Key: disease_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_disease (
    disease_key       BIGSERIAL PRIMARY KEY,
    disease_id        INT NOT NULL UNIQUE,
    disease_name      VARCHAR(255),
    disease_category  VARCHAR(100)
);

-- ============================================================
-- 4. Dim_Department
-- Source: department
-- Natural Key: department_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_department (
    department_key   BIGSERIAL PRIMARY KEY,
    department_id    INT NOT NULL UNIQUE,
    department_name  VARCHAR(255),
    department_type  VARCHAR(100),
    floor_number     INT,
    status            VARCHAR(50)
);

-- ============================================================
-- 5. Dim_Ward
-- Source: ward + department
-- Natural Key: ward_id
--
-- department_id is retained as a source/business attribute.
-- It is NOT a FK to another Dimension in this Star Schema.
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_ward (
    ward_key       BIGSERIAL PRIMARY KEY,
    ward_id        INT NOT NULL UNIQUE,
    ward_name      VARCHAR(255),
    ward_type      VARCHAR(100),
    total_beds     INT,
    department_id  INT
);

-- ============================================================
-- 6. Dim_Bed
-- Source: bed + ward
-- Natural Key: bed_id
--
-- ward_id is retained as a source/business attribute.
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_bed (
    bed_key       BIGSERIAL PRIMARY KEY,
    bed_id        INT NOT NULL UNIQUE,
    bed_number    VARCHAR(50),
    bed_status    VARCHAR(50),
    ward_id       INT
);

-- ============================================================
-- 7. Dim_Doctor
-- Source: doctor + employee
-- Natural Key: doctor_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_doctor (
    doctor_key       BIGSERIAL PRIMARY KEY,
    doctor_id        INT NOT NULL UNIQUE,
    employee_id      INT,
    doctor_name      VARCHAR(255),
    gender           VARCHAR(20),
    role             VARCHAR(100),
    specialization   VARCHAR(255),
    qualification    VARCHAR(255),
    experience_years INT
);

-- ============================================================
-- 8. Dim_Employee
-- Source: employee + department
-- Natural Key: employee_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_employee (
    employee_key     BIGSERIAL PRIMARY KEY,
    employee_id      INT NOT NULL UNIQUE,
    employee_name    VARCHAR(255),
    gender           VARCHAR(20),
    role             VARCHAR(100),
    employment_type  VARCHAR(100),
    date_of_joining  DATE,
    department_id    INT
);

-- ============================================================
-- 9. Dim_Drug
-- Source: drug + drug_manufacturer
-- Natural Key: drug_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_drug (
    drug_key           BIGSERIAL PRIMARY KEY,
    drug_id            INT NOT NULL UNIQUE,
    drug_name          VARCHAR(255),
    brand_name         VARCHAR(255),
    drug_category      VARCHAR(100),
    unit_cost          NUMERIC(15,2),
    manufacturer_id    INT,
    manufacturer_name  VARCHAR(255),
    country            VARCHAR(100),
    reliability_rating NUMERIC(3,2),
    contract_status    VARCHAR(50)
);

-- ============================================================
-- 10. Dim_Insurance
-- Source: patient_insurance + insurance_provider
-- Natural Key: patient_insurance_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_insurance (
    insurance_key          BIGSERIAL PRIMARY KEY,
    patient_insurance_id   INT NOT NULL UNIQUE,
    policy_number          VARCHAR(100),
    patient_id             INT,
    insurance_provider_id  INT,
    provider_name          VARCHAR(255),
    provider_type          VARCHAR(100),
    coverage_percentage    NUMERIC(5,2),
    policy_start_date      DATE,
    policy_end_date        DATE,
    coverage_limit         NUMERIC(15,2)
);

-- ============================================================
-- 11. Dim_Diagnostic_Test
-- Source: diagnostic_test + department
-- Natural Key: test_id
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.dim_diagnostic_test (
    test_key         BIGSERIAL PRIMARY KEY,
    test_id          INT NOT NULL UNIQUE,
    test_name        VARCHAR(255),
    test_category    VARCHAR(100),
    standard_cost    NUMERIC(15,2),
    department_id    INT
);

-- ============================================================
-- Optional indexes for common Natural Key lookups
-- UNIQUE constraints above already create indexes in PostgreSQL.
-- Additional indexes are not required at this stage.
-- ============================================================

-- ============================================================
-- Verification
-- ============================================================

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'dw'
ORDER BY table_name;
