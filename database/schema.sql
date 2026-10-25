-- Enterprise AI Governance & Evaluation
-- Milestone 2 | SQLite physical schema | Version 0.1 | 2026-10-24
-- Design sources: docs/data-dictionary.md and docs/business-metrics.md
-- DDL only: no seed data, role enforcement, read-only connection configuration,
-- SQL validation, benchmark reference answers, or audit implementation.
-- Enable foreign keys separately on EVERY application database connection.
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS BUSINESS_UNITS (
    business_unit_id INTEGER PRIMARY KEY,
    unit_code TEXT NOT NULL UNIQUE CHECK (length(trim(unit_code)) > 0),
    unit_name TEXT NOT NULL CHECK (length(trim(unit_name)) > 0),
    region TEXT NOT NULL CHECK (length(trim(region)) > 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
) STRICT;

CREATE TABLE IF NOT EXISTS CUSTOMERS (
    customer_id INTEGER PRIMARY KEY,
    business_unit_id INTEGER NOT NULL,
    customer_code TEXT NOT NULL UNIQUE CHECK (length(trim(customer_code)) > 0),
    customer_name TEXT NOT NULL CHECK (length(trim(customer_name)) > 0),
    customer_segment TEXT NOT NULL CHECK (length(trim(customer_segment)) > 0),
    created_date TEXT NOT NULL CHECK (length(created_date) = 10 AND created_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    FOREIGN KEY (business_unit_id) REFERENCES BUSINESS_UNITS(business_unit_id),
    UNIQUE (customer_id, business_unit_id) -- supports composite order/customer scope FK
) STRICT;

CREATE TABLE IF NOT EXISTS PRODUCTS (
    product_id INTEGER PRIMARY KEY,
    product_code TEXT NOT NULL UNIQUE CHECK (length(trim(product_code)) > 0),
    product_name TEXT NOT NULL CHECK (length(trim(product_name)) > 0),
    product_category TEXT NOT NULL CHECK (length(trim(product_category)) > 0),
    standard_cost_cents INTEGER NOT NULL CHECK (standard_cost_cents >= 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
) STRICT;

CREATE TABLE IF NOT EXISTS ORDERS (
    order_id INTEGER PRIMARY KEY,
    order_number TEXT NOT NULL UNIQUE CHECK (length(trim(order_number)) > 0),
    customer_id INTEGER NOT NULL,
    business_unit_id INTEGER NOT NULL,
    order_date TEXT NOT NULL CHECK (length(order_date) = 10 AND order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    order_status TEXT NOT NULL CHECK (order_status IN ('PENDING', 'COMPLETED', 'CANCELED')),
    completed_date TEXT CHECK (completed_date IS NULL OR (length(completed_date) = 10 AND completed_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')),
    currency_code TEXT NOT NULL CHECK (currency_code = 'USD'),
    FOREIGN KEY (business_unit_id) REFERENCES BUSINESS_UNITS(business_unit_id),
    FOREIGN KEY (customer_id, business_unit_id) REFERENCES CUSTOMERS(customer_id, business_unit_id),
    CHECK (
        (order_status = 'COMPLETED' AND completed_date IS NOT NULL AND completed_date >= order_date)
        OR (order_status IN ('PENDING', 'CANCELED') AND completed_date IS NULL)
    )
) STRICT;

CREATE TABLE IF NOT EXISTS ORDER_ITEMS (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    discount_amount_cents INTEGER NOT NULL CHECK (discount_amount_cents >= 0),
    FOREIGN KEY (order_id) REFERENCES ORDERS(order_id),
    FOREIGN KEY (product_id) REFERENCES PRODUCTS(product_id),
    UNIQUE (order_id, line_number),
    -- Avoid multiplication overflow in SQLite signed 64-bit integer arithmetic.
    CHECK (unit_price_cents = 0 OR quantity <= 9223372036854775807 / unit_price_cents),
    CHECK (discount_amount_cents <= quantity * unit_price_cents)
) STRICT;

CREATE TABLE IF NOT EXISTS USERS (
    user_id INTEGER PRIMARY KEY,
    user_code TEXT NOT NULL UNIQUE CHECK (length(trim(user_code)) > 0),
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
    role_name TEXT NOT NULL CHECK (role_name IN ('Sales Analyst', 'Operations Manager', 'Finance Analyst', 'Data Steward', 'System Administrator')),
    business_unit_id INTEGER,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    FOREIGN KEY (business_unit_id) REFERENCES BUSINESS_UNITS(business_unit_id)
) STRICT;

CREATE TABLE IF NOT EXISTS USER_BUSINESS_UNITS (
    user_id INTEGER NOT NULL,
    business_unit_id INTEGER NOT NULL,
    access_scope TEXT NOT NULL CHECK (access_scope IN ('PRIMARY', 'ASSIGNED', 'FINANCE_AUTHORIZED')),
    granted_at TEXT NOT NULL CHECK (length(trim(granted_at)) > 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    PRIMARY KEY (user_id, business_unit_id),
    FOREIGN KEY (user_id) REFERENCES USERS(user_id),
    FOREIGN KEY (business_unit_id) REFERENCES BUSINESS_UNITS(business_unit_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS BUSINESS_METRICS (
    metric_id INTEGER PRIMARY KEY,
    metric_code TEXT NOT NULL CHECK (length(trim(metric_code)) > 0),
    metric_name TEXT NOT NULL CHECK (length(trim(metric_name)) > 0),
    metric_definition TEXT NOT NULL CHECK (length(trim(metric_definition)) > 0),
    calculation_rule TEXT NOT NULL CHECK (length(trim(calculation_rule)) > 0),
    source_entities TEXT NOT NULL CHECK (length(trim(source_entities)) > 0),
    metric_version TEXT NOT NULL CHECK (length(trim(metric_version)) > 0),
    effective_date TEXT NOT NULL CHECK (length(effective_date) = 10 AND effective_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    approval_status TEXT NOT NULL CHECK (approval_status IN ('DRAFT', 'APPROVED', 'RETIRED')),
    UNIQUE (metric_code, metric_version)
) STRICT;

-- Indexes chosen for expected joins, filters, and authorized-scope lookups.
CREATE INDEX IF NOT EXISTS idx_customers_business_unit ON CUSTOMERS(business_unit_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON ORDERS(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_unit_order_date ON ORDERS(business_unit_id, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_unit_completion ON ORDERS(business_unit_id, completed_date) WHERE order_status = 'COMPLETED';
CREATE INDEX IF NOT EXISTS idx_orders_status ON ORDERS(order_status);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON ORDER_ITEMS(product_id);
CREATE INDEX IF NOT EXISTS idx_user_business_units_unit ON USER_BUSINESS_UNITS(business_unit_id);
CREATE INDEX IF NOT EXISTS idx_metrics_approval ON BUSINESS_METRICS(metric_code, approval_status);

COMMIT;

-- Application/test obligations not expressible as ordinary immediate constraints:
-- 1. Each ORDERS row must have >= 1 ORDER_ITEMS row at dataset validation time.
-- 2. Strict calendar validity (e.g., February 30) and granted_at UTC timestamp parsing.
-- 3. Authorization role/scope alignment, active-user checks, Sales Analyst exactly
--    one active PRIMARY mapping, and administrative grant/revocation audit events.
-- 4. Product-cost column access, row-level unit authorization, and read-only SQL
--    execution are NOT enforced by this schema; enforce via trusted application.
-- 5. Integer SUM() overflow and full-dataset aggregate ranges need data-quality tests.
-- 6. Existing tables are not migrated by IF NOT EXISTS; use explicit migrations.
-- Suggested checks after population: PRAGMA foreign_key_check; PRAGMA integrity_check;
