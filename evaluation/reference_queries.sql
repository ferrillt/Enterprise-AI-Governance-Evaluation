-- Enterprise AI Governance & Evaluation | Milestone 2
-- Independent analytical reference patterns | v0.1 | 2026-10-24
-- Design source: docs/business-metrics.md and docs/data-dictionary.md
-- SQLite 3.37+; execute on a validated, fixed synthetic dataset.
-- IMPORTANT: These are reference calculations, NOT an application query gateway.
-- They do not authenticate callers, enforce read-only execution, or implement
-- complete role/column policy. Never expose this file as user-executable SQL.
-- Use the SAME frozen as_of_date, metric versions, and authorized units for
-- every AI configuration and the independent evaluator.
-- Each SELECT is a separately usable reference query. Parameters are SQLite
-- named parameters supplied by a TRUSTED test harness, not LLM output:
--   :start_date       inclusive YYYY-MM-DD
--   :end_date         exclusive YYYY-MM-DD
--   :as_of_date       fixed evaluation date (for harness period derivation)
--   :user_id          synthetic USERS.user_id, assigned by trusted harness
-- The harness must verify the role, user status, grant status, scope type,
-- and applicable object/column permissions before running a query.
-- The explicit scope join below is defense-in-depth only; it is NOT a
-- substitute for those checks. In particular, a Data Steward or System
-- Administrator has no default transaction access.
-- Only APPROVED metric definitions may be used as authoritative; the current
-- synthetic generator inserts DRAFT versions, so these patterns remain
-- candidate references until metric approval and independent verification.
-- Monetary outputs are integer cents. Convert/round at presentation stage.
-- A zero denominator returns NULL. No query selects restricted product costs.

-- R01. Gross sales (recognized): completed orders, completion-date basis.
SELECT COALESCE(SUM(i.quantity * i.unit_price_cents), 0) AS gross_sales_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date;

-- R02. Net sales (recognized): discount is once per line.
SELECT COALESCE(SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents), 0)
       AS net_sales_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date;

-- R03. Order volume: ALL statuses, placed-date basis.
SELECT COUNT(DISTINCT o.order_id) AS order_volume
FROM ORDERS AS o
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_date >= :start_date AND o.order_date < :end_date;

-- R04. Cancellation rate: same placed-date cohort for both counts.
-- Keep numerator and denominator for exact independent decimal arithmetic.
SELECT COUNT(DISTINCT CASE WHEN o.order_status = 'CANCELED' THEN o.order_id END)
         AS canceled_orders,
       COUNT(DISTINCT o.order_id) AS total_orders,
       CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN NULL
            ELSE 100.0 * COUNT(DISTINCT CASE WHEN o.order_status = 'CANCELED'
                                              THEN o.order_id END)
                        / COUNT(DISTINCT o.order_id) END AS cancellation_pct_preview
FROM ORDERS AS o
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_date >= :start_date AND o.order_date < :end_date;

-- R05. AOV: completed-order net sales / distinct completed orders,
-- both on completion-date basis. Compute final USD value with Decimal.
SELECT COALESCE(SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents), 0)
         AS net_sales_cents,
       COUNT(DISTINCT o.order_id) AS completed_orders,
       CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN NULL
            ELSE 1.0 * SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents)
                        / COUNT(DISTINCT o.order_id) END AS aov_cents_preview
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date;

-- R06. Product sales: net sales by product, stable tie break.
SELECT p.product_code, p.product_name,
       SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents)
         AS product_net_sales_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN PRODUCTS AS p ON p.product_id = i.product_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date
GROUP BY p.product_id, p.product_code, p.product_name
ORDER BY product_net_sales_cents DESC, p.product_code ASC;

-- R07. Net sales by calendar month within the requested completion-date
-- window. A calendar scaffold is required to add zero-activity months.
SELECT substr(o.completed_date, 1, 7) AS sales_month,
       SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents)
         AS net_sales_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date
GROUP BY substr(o.completed_date, 1, 7)
ORDER BY sales_month;

-- R08. Status breakdown by placed date. A status scaffold is required
-- if zero-count statuses must be shown.
SELECT o.order_status, COUNT(DISTINCT o.order_id) AS order_count
FROM ORDERS AS o
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_date >= :start_date AND o.order_date < :end_date
GROUP BY o.order_status
ORDER BY o.order_status;

-- R09. Eligible discount total (completed, completion-date basis).
SELECT COALESCE(SUM(i.discount_amount_cents), 0) AS discount_total_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date;

-- R10. Canceled-order gross diagnostic: NOT recognized gross sales.
-- Uses placed-date basis because canceled orders have no completed_date.
SELECT COALESCE(SUM(i.quantity * i.unit_price_cents), 0)
         AS canceled_order_gross_value_cents_not_recognized
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'CANCELED'
  AND o.order_date >= :start_date AND o.order_date < :end_date;

-- R11. Net sales by product category.
SELECT p.product_category,
       SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents)
         AS category_net_sales_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN PRODUCTS AS p ON p.product_id = i.product_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date
GROUP BY p.product_category
ORDER BY category_net_sales_cents DESC, p.product_category ASC;

-- R12. Net sales and completed orders per business unit (for per-unit AOV).
SELECT b.unit_code,
       COALESCE(SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents), 0)
         AS net_sales_cents,
       COUNT(DISTINCT o.order_id) AS completed_orders
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN BUSINESS_UNITS AS b ON b.business_unit_id = o.business_unit_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date
GROUP BY b.business_unit_id, b.unit_code
ORDER BY b.unit_code;

-- R13. Reconciliation of recognized gross, discounts and net.
SELECT COALESCE(SUM(i.quantity * i.unit_price_cents), 0) AS gross_cents,
       COALESCE(SUM(i.discount_amount_cents), 0) AS discount_cents,
       COALESCE(SUM(i.quantity * i.unit_price_cents - i.discount_amount_cents), 0)
         AS net_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS i ON i.order_id = o.order_id
JOIN USER_BUSINESS_UNITS AS a ON a.business_unit_id = o.business_unit_id
WHERE a.user_id = :user_id AND a.is_active = 1
  AND o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date AND o.completed_date < :end_date;

-- Remaining work: implement a trusted parameterized runner; calendar/status
-- scaffolds; exact Decimal formatting; benchmark-case-specific queries for
-- all 50 cases; authorization negative tests; versioned expected answers.
