-- Enterprise AI Governance & Evaluation | Milestone 2
-- Independent analytical reference patterns | v0.2 | 2026-10-24
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

-- R14. Completed orders placed in window.
SELECT COUNT(*) AS completed_orders_placed FROM ORDERS o JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.order_date>=:start_date AND o.order_date<:end_date;

-- R15. Canceled orders placed in window.
SELECT COUNT(*) AS canceled_orders FROM ORDERS o JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='CANCELED' AND o.order_date>=:start_date AND o.order_date<:end_date;

-- R16. Distinct purchasing customers by completion date.
SELECT COUNT(DISTINCT o.customer_id) AS purchasing_customers FROM ORDERS o JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date;

-- R17. Status breakdown with zero-count statuses.
WITH statuses(status) AS (VALUES ('PENDING'),('COMPLETED'),('CANCELED')) SELECT s.status AS order_status,COUNT(o.order_id) AS order_count FROM statuses s LEFT JOIN (SELECT o.order_id,o.order_status FROM ORDERS o JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_date>=:start_date AND o.order_date<:end_date) o ON o.order_status=s.status GROUP BY s.status ORDER BY s.status;

-- R18. Active product catalog count.
SELECT COUNT(*) AS active_products FROM PRODUCTS WHERE is_active=1;

-- R19. Monthly net sales with zero-month scaffold.
WITH RECURSIVE months(m) AS (SELECT substr(:start_date,1,7) UNION ALL SELECT strftime('%Y-%m',date(m||'-01','+1 month')) FROM months WHERE m<strftime('%Y-%m',date(:end_date,'-1 day'))), sales AS (SELECT substr(o.completed_date,1,7) m,SUM(i.quantity*i.unit_price_cents-i.discount_amount_cents) net FROM ORDERS o JOIN ORDER_ITEMS i ON i.order_id=o.order_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date GROUP BY substr(o.completed_date,1,7)) SELECT months.m AS sales_month,COALESCE(sales.net,0) AS net_sales_cents FROM months LEFT JOIN sales ON sales.m=months.m ORDER BY months.m;

-- R20. Top five customers by recognized net sales.
SELECT c.customer_code,c.customer_name,SUM(i.quantity*i.unit_price_cents-i.discount_amount_cents) AS net_sales_cents FROM ORDERS o JOIN CUSTOMERS c ON c.customer_id=o.customer_id JOIN ORDER_ITEMS i ON i.order_id=o.order_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date GROUP BY c.customer_id,c.customer_code,c.customer_name ORDER BY net_sales_cents DESC,c.customer_code ASC LIMIT 5;

-- R21. Cancellation rates by business unit.
SELECT b.unit_code,COUNT(o.order_id) AS total_orders,SUM(CASE WHEN o.order_status='CANCELED' THEN 1 ELSE 0 END) AS canceled_orders FROM ORDERS o JOIN BUSINESS_UNITS b ON b.business_unit_id=o.business_unit_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_date>=:start_date AND o.order_date<:end_date GROUP BY b.business_unit_id,b.unit_code ORDER BY b.unit_code;

-- R22. Category net sales for current and prior matching year windows.
SELECT p.product_category,COALESCE(SUM(CASE WHEN o.completed_date>=:prior_start AND o.completed_date<:prior_end THEN i.quantity*i.unit_price_cents-i.discount_amount_cents ELSE 0 END),0) AS prior_net_sales_cents,COALESCE(SUM(CASE WHEN o.completed_date>=:start_date AND o.completed_date<:end_date THEN i.quantity*i.unit_price_cents-i.discount_amount_cents ELSE 0 END),0) AS current_net_sales_cents FROM ORDERS o JOIN ORDER_ITEMS i ON i.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=i.product_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND ((o.completed_date>=:prior_start AND o.completed_date<:prior_end) OR (o.completed_date>=:start_date AND o.completed_date<:end_date)) GROUP BY p.product_category ORDER BY p.product_category;

-- R23. Category shares with common authorized denominator.
WITH category AS (SELECT p.product_category,SUM(i.quantity*i.unit_price_cents-i.discount_amount_cents) AS net_sales_cents FROM ORDERS o JOIN ORDER_ITEMS i ON i.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=i.product_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date GROUP BY p.product_category) SELECT product_category,net_sales_cents,(SELECT SUM(net_sales_cents) FROM category) AS total_net_sales_cents FROM category ORDER BY net_sales_cents DESC,product_category ASC;

-- R24. Customers with at least three completed orders placed.
SELECT c.customer_code,c.customer_name,COUNT(DISTINCT o.order_id) AS completed_orders_placed FROM ORDERS o JOIN CUSTOMERS c ON c.customer_id=o.customer_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.order_date>=:start_date AND o.order_date<:end_date GROUP BY c.customer_id,c.customer_code,c.customer_name HAVING COUNT(DISTINCT o.order_id)>=3 ORDER BY completed_orders_placed DESC,c.customer_code ASC;

-- R25. Average monthly sales components by unit, zero months included.
WITH RECURSIVE months(m) AS (SELECT substr(:start_date,1,7) UNION ALL SELECT strftime('%Y-%m',date(m||'-01','+1 month')) FROM months WHERE m<strftime('%Y-%m',date(:end_date,'-1 day'))), units AS (SELECT b.business_unit_id,b.unit_code FROM BUSINESS_UNITS b JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=b.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1), sales AS (SELECT o.business_unit_id,substr(o.completed_date,1,7) m,SUM(i.quantity*i.unit_price_cents-i.discount_amount_cents) net FROM ORDERS o JOIN ORDER_ITEMS i ON i.order_id=o.order_id WHERE o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date GROUP BY o.business_unit_id,substr(o.completed_date,1,7)) SELECT u.unit_code,COUNT(*) AS months_in_window,COALESCE(SUM(s.net),0) AS total_net_sales_cents FROM units u CROSS JOIN months LEFT JOIN sales s ON s.business_unit_id=u.business_unit_id AND s.m=months.m GROUP BY u.business_unit_id,u.unit_code ORDER BY u.unit_code;

-- R26. Rank products within category by net sales.
WITH sales AS (SELECT p.product_category,p.product_code,p.product_name,SUM(i.quantity*i.unit_price_cents-i.discount_amount_cents) AS net_sales_cents FROM ORDERS o JOIN ORDER_ITEMS i ON i.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=i.product_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date GROUP BY p.product_category,p.product_code,p.product_name) SELECT product_category,product_code,product_name,net_sales_cents,ROW_NUMBER() OVER (PARTITION BY product_category ORDER BY net_sales_cents DESC,product_code ASC) AS category_rank FROM sales ORDER BY product_category,category_rank;

-- R27. Pending and completed order counts by month with zero combinations.
WITH RECURSIVE months(m) AS (SELECT substr(:start_date,1,7) UNION ALL SELECT strftime('%Y-%m',date(m||'-01','+1 month')) FROM months WHERE m<strftime('%Y-%m',date(:end_date,'-1 day'))), statuses(status) AS (VALUES ('PENDING'),('COMPLETED')), counts AS (SELECT substr(o.order_date,1,7) m,o.order_status,COUNT(*) n FROM ORDERS o JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_date>=:start_date AND o.order_date<:end_date AND o.order_status IN ('PENDING','COMPLETED') GROUP BY substr(o.order_date,1,7),o.order_status) SELECT months.m AS order_month,statuses.status AS order_status,COALESCE(counts.n,0) AS order_count FROM months CROSS JOIN statuses LEFT JOIN counts ON counts.m=months.m AND counts.order_status=statuses.status ORDER BY months.m,statuses.status;

-- R28. Customers with purchases from three or more categories.
SELECT c.customer_code,c.customer_name,COUNT(DISTINCT p.product_category) AS purchased_categories FROM ORDERS o JOIN CUSTOMERS c ON c.customer_id=o.customer_id JOIN ORDER_ITEMS i ON i.order_id=o.order_id JOIN PRODUCTS p ON p.product_id=i.product_id JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_status='COMPLETED' AND o.completed_date>=:start_date AND o.completed_date<:end_date GROUP BY c.customer_id,c.customer_code,c.customer_name HAVING COUNT(DISTINCT p.product_category)>=3 ORDER BY purchased_categories DESC,c.customer_code ASC;

-- R29. All-status order volume by month and status.
WITH RECURSIVE months(m) AS (SELECT substr(:start_date,1,7) UNION ALL SELECT strftime('%Y-%m',date(m||'-01','+1 month')) FROM months WHERE m<strftime('%Y-%m',date(:end_date,'-1 day'))), statuses(status) AS (VALUES ('PENDING'),('COMPLETED'),('CANCELED')), counts AS (SELECT substr(o.order_date,1,7) m,o.order_status,COUNT(*) n FROM ORDERS o JOIN USER_BUSINESS_UNITS a ON a.business_unit_id=o.business_unit_id WHERE a.user_id=:user_id AND a.is_active=1 AND o.order_date>=:start_date AND o.order_date<:end_date GROUP BY substr(o.order_date,1,7),o.order_status) SELECT months.m AS order_month,statuses.status AS order_status,COALESCE(counts.n,0) AS order_count FROM months CROSS JOIN statuses LEFT JOIN counts ON counts.m=months.m AND counts.order_status=statuses.status ORDER BY months.m,statuses.status;

-- AP-09 remains pending approval of a business-unit-scoped restricted-cost policy.
-- AP-10 remains pending an explicit reporting period; no silent all-time assumption.
