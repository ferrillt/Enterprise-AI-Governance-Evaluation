# Enterprise AI Governance & Evaluation
## Business Metrics and Calculation Standards

**Version:** 0.1  
**Date:** October 24, 2026  
**Status:** Draft — Milestone 2  
**Milestone:** M2 — Data and Governance Foundation  
**Business Domain:** Enterprise Sales and Operations

**Related Documents:** [System Requirements](requirements.md) | [Data Dictionary](data-dictionary.md) | [Governance Framework](governance-framework.md) | [Evaluation Plan](evaluation-plan.md) | [Evaluation Benchmark](../evaluation/benchmark/test_cases.csv)

---

## 1. Purpose

This document proposes authoritative, testable definitions for enterprise sales and operations metrics used by the governed natural-language-to-SQL analytics system. It resolves preliminary calculation conventions in BR-01–BR-08 and DR-07, and supplies a specification for implementation, independent benchmark reference SQL, and subsequent evaluation.

The definitions below are **proposed for approval**, not yet implemented or verified. The data owner approves metric semantics; the data steward maintains definitions; the evaluation lead independently validates reference queries. For this portfolio project, approvals are documented design decisions by the project author, not claims of external enterprise sign-off.

## 2. Source Data and Shared Conventions

### 2.1 Sources

| Table | Required Fields | Usage |
|---|---|---|
| `ORDERS` | `order_id`, `business_unit_id`, `customer_id`, `order_date`, `completed_date`, `order_status`, `currency_code` | Order identity, status, reporting date, authorization scope |
| `ORDER_ITEMS` | `order_item_id`, `order_id`, `product_id`, `quantity`, `unit_price_cents`, `discount_amount_cents` | Sales and discounts |
| `PRODUCTS` | `product_id`, `product_code`, `product_category` | Product and category breakdowns |
| `CUSTOMERS` | `customer_id`, `business_unit_id`, `customer_segment` | Customer analyses |
| `BUSINESS_UNITS` | `business_unit_id`, `unit_code` | Authorized organizational reporting |
| `BUSINESS_METRICS` | `metric_code`, `metric_version`, `approval_status`, `effective_date`, `calculation_rule` | Governed metric metadata |

`PRODUCTS.standard_cost_cents` is **not required** for the six sales metrics and must not be retrieved incidentally. Cost/profit metrics require a separately approved restricted-cost policy.

### 2.2 Currency, units, and arithmetic

- The initial dataset supports **USD only**. Reject or clarify requests requiring other currencies or conversion rates.
- `unit_price_cents` is a price **per unit**; `discount_amount_cents` is a discount **for the entire order line**, not per unit.
- `line_gross_cents = quantity * unit_price_cents`.
- `line_net_cents = line_gross_cents - discount_amount_cents`.
- Valid line data require positive integer quantity, nonnegative integer prices and discounts, and `0 <= discount_amount_cents <= line_gross_cents`.
- Sum monetary amounts as **integer cents**. Convert to USD only for presentation (`cents / 100`). Do not round individual line items or use floating-point sums to establish reference totals.
- Monetary reporting rounds to two decimal places using decimal half-up rounding **only at the final presentation stage**. Ratios and percentages use unrounded intermediate amounts and round to two decimal places for display; independent scoring may compare underlying exact numerators and denominators.
- For division by zero, return **not applicable (`NULL`)**, never zero, infinity, or an invented value. State the reason in the response.

### 2.3 Order status and eligibility

The approved status vocabulary in the proposed data dictionary is `PENDING`, `COMPLETED`, and `CANCELED`.

| Analytical concept | Included status | Excluded status |
|---|---|---|
| Recognized gross sales | `COMPLETED` | `PENDING`, `CANCELED` |
| Recognized net sales | `COMPLETED` | `PENDING`, `CANCELED` |
| Discount amount on eligible sales | `COMPLETED` | `PENDING`, `CANCELED` |
| Completed order count / AOV denominator | `COMPLETED` | `PENDING`, `CANCELED` |
| All-status order volume | All three | None |
| Cancellation rate | `CANCELED` numerator; all three denominator | None from the three-status vocabulary |
| Canceled-order gross value (explicit diagnostic) | `CANCELED` | `PENDING`, `COMPLETED` |

**Important distinction:** Gross Sales, when used without a qualifier, means *recognized gross sales before discounts on completed orders*. The gross value of canceled or pending orders is available only as a separately labeled diagnostic, never added to recognized sales. This makes BA-02/BD-01 and BD-10 consistent without counting canceled orders as revenue.

`completed_date` must be present and not earlier than `order_date` for completed orders. Non-completed orders must not be assigned recognized revenue. No returns, refunds, tax, shipping, partial fulfillment, multi-currency conversion, or historical cost adjustments are modeled; requests requiring these concepts must be qualified or rejected.

### 2.4 Reporting date and time conventions

- The system uses a documented **evaluation as-of date** (`as_of_date`), not the execution machine's current date, for deterministic benchmark results.
- All calendar boundaries are UTC dates; reporting intervals are **start-inclusive and end-exclusive**: `date >= start_date AND date < end_date`.
- **Order volume and cancellation rate** use `ORDERS.order_date` (order-cohort basis).
- **Recognized sales, discounts, product sales, and AOV** use `ORDERS.completed_date` (completion basis).
- **Completed order counts** requested as orders *placed* in a period use `order_date` with status `COMPLETED`; completed-order counts for AOV use `completed_date` to align numerator and denominator. Always label the date basis.
- “Last month” means the previous **complete calendar month**; “last quarter” means the previous complete calendar quarter; “last year” means the previous complete calendar year.
- “This year to date” means January 1 through `as_of_date`, inclusive; implement as an exclusive upper bound of the next calendar day.
- “Last N completed months” excludes the current partial month. “Last 90 days” includes the 90 calendar dates ending on `as_of_date`.
- Year-over-year comparisons use matched calendar windows and date bases. Month-over-month calculations use chronologically adjacent months.
- If `as_of_date`, the requested period, or the date basis cannot be resolved safely, ask for clarification or document an explicit interpretation; do not silently use today's date.

### 2.5 Authorized scope and joins

All analytical calculations must apply trusted role and business-unit authorization **before aggregation**. For sales and orders, filter on `ORDERS.business_unit_id` using approved application-enforced access controls. Never derive scope from user-supplied text or generated SQL alone. No query may reveal data from unauthorized units, including through totals, comparisons, joins, or zero/suppression behavior.

Join `ORDERS` to `ORDER_ITEMS` on `order_id`; join to `PRODUCTS` only when a product dimension is requested. Count orders with `COUNT(DISTINCT ORDERS.order_id)` when item joins would otherwise duplicate orders. Never sum an order-level amount after multiplying rows through an item join.

Configurations A, B, and C share essential authorization, restricted-column, read-only execution, and denial-on-failure controls. Approved metric definitions may be made available as enriched LLM context only in configurations B and C; the independent benchmark reference implementation uses the definitions in this document for **all** configurations.

## 3. Metric Catalog

| Code | Metric | Unit | Default Date Basis | Default Eligibility |
|---|---|---|---|---|
| `GROSS_SALES` | Gross Sales | USD | Completion date | Completed orders |
| `NET_SALES` | Net Sales | USD | Completion date | Completed orders |
| `ORDER_VOLUME` | Order Volume | Orders | Order date | All statuses; breakdown when requested |
| `CANCELLATION_RATE` | Cancellation Rate | Percent | Order date | Canceled / all orders |
| `AVERAGE_ORDER_VALUE` | Average Order Value (AOV) | USD/order | Completion date | Completed orders |
| `PRODUCT_SALES` | Product Sales | USD | Completion date | Completed orders; net sales |

### 3.1 Gross Sales — `GROSS_SALES`

**Definition:** Total selling value before discounts for completed order items within the authorized scope and reporting period.

**Formula (integer cents):**

`SUM(ORDER_ITEMS.quantity * ORDER_ITEMS.unit_price_cents)`

Filter `ORDERS.order_status = 'COMPLETED'`, use `completed_date`, and restrict authorized business units. Group by requested unit, month, quarter, or other approved dimension. Present as USD. Exclude pending and canceled orders from the default metric.

**Diagnostic exception:** For “gross sales from canceled orders” (BD-10), compute the same pre-discount formula on `CANCELED` orders using **order date** and label the result **Canceled-Order Gross Value (Not Recognized Sales)**. It is not part of `GROSS_SALES`.

### 3.2 Net Sales — `NET_SALES`

**Definition:** Total recognized sales value after line-level discounts for completed orders.

**Formula (integer cents):**

`SUM((ORDER_ITEMS.quantity * ORDER_ITEMS.unit_price_cents) - ORDER_ITEMS.discount_amount_cents)`

Filter completed orders by `completed_date` and authorized unit. Because discounts are line-level amounts, subtract each discount **once per order item**, not once per purchased unit. Net sales must be nonnegative under the approved line constraints.

**Discount amount on eligible orders:** `SUM(ORDER_ITEMS.discount_amount_cents)` for completed orders on the same completion-date basis. This is a supporting calculation for BD-08, not a seventh core metric.

### 3.3 Order Volume — `ORDER_VOLUME`

**Definition:** Number of distinct orders placed within the requested reporting period and authorized scope.

**Formula:** `COUNT(DISTINCT ORDERS.order_id)`

Use `order_date`. By default include all three statuses; when a status is specified, filter to that status. For breakdowns, group by `order_status` and preserve zero-count status/period combinations through a reporting calendar/status scaffold where required. A request for “completed orders placed last month” filters status `COMPLETED` but still uses `order_date`.

### 3.4 Cancellation Rate — `CANCELLATION_RATE`

**Definition:** Percentage of orders placed in a reporting period that have status `CANCELED` in the fixed dataset snapshot.

**Formula:**

`100 * COUNT(DISTINCT CASE WHEN order_status = 'CANCELED' THEN order_id END) / COUNT(DISTINCT order_id)`

Both numerator and denominator use `order_date`, the same authorized unit scope, and all orders in the cohort. Pending orders remain in the denominator. A zero denominator yields `NULL` / not applicable. Because status is observed at the dataset snapshot, this is a **snapshot cohort cancellation rate**, not a final lifetime cancellation probability.

### 3.5 Average Order Value — `AVERAGE_ORDER_VALUE`

**Definition:** Net sales from completed orders divided by the number of distinct completed orders in the same completion-date reporting period and authorized scope.

**Formula:**

`NET_SALES_cents / COUNT(DISTINCT completed ORDERS.order_id)`

The numerator and denominator both use `completed_date`. Return USD/order. A zero completed-order denominator yields `NULL` / not applicable. For per-unit AOV, calculate each unit's numerator and denominator separately. For a combined scope, divide combined net sales by combined completed orders; **never average unit AOVs**.

### 3.6 Product Sales — `PRODUCT_SALES`

**Definition:** Recognized net sales attributed to a product or product category.

**Formula (integer cents):**

`SUM((ORDER_ITEMS.quantity * ORDER_ITEMS.unit_price_cents) - ORDER_ITEMS.discount_amount_cents)`

Filter completed orders on `completed_date` and authorized units, then group by `PRODUCTS.product_id`, `product_code`, or `product_category`. Product Sales measures **net monetary sales**, not units sold. Inactive catalog products remain eligible if they appear on historical completed orders. Product-cost fields must not be selected.

For top-N rankings, sort by net sales descending and use a deterministic secondary key (e.g., `product_code` ascending). For category share, divide category net sales by total net sales within the **same authorized scope and period**; a zero total yields `NULL` / not applicable.

## 4. Supporting Analytical Conventions

These calculations support benchmark questions but are not additional entries in the six-metric catalog.

| Analysis | Definition / Rule |
|---|---|
| Distinct purchasing customers | `COUNT(DISTINCT ORDERS.customer_id)` for completed orders; default completion-date basis unless question explicitly says orders placed |
| Customers with 3+ completed orders | Group by customer; `COUNT(DISTINCT order_id) >= 3`; use order date when question says “placed” |
| Distinct purchased categories | Count distinct product categories from completed order items per customer in authorized scope |
| Monthly net sales | Net Sales grouped by completion calendar month; include zero-sales months when comparing a fixed calendar window |
| Average monthly net sales | Sum each calendar month's net sales, including zero months, then divide by number of months in the specified window |
| Month-over-month change | Current-month net sales minus previous-month net sales; percent change = 100 × difference / previous-month net sales; `NULL` if prior month is zero |
| Year-over-year change | Current matching-period net sales minus prior matching-period net sales; percentage is `NULL` when prior value is zero |
| Order status breakdown | Distinct order count for each approved status, with zero-count groups included when required |
| Gross vs. net comparison | Compare recognized gross and net sales on identical completed-order, completion-date, and authorized-unit scopes |
| Discount total | Sum line-level discounts on completed orders within authorized scope and completion-date period |

**Ambiguity handling:** “Revenue,” “sales,” “purchased,” and “eligible orders” can imply different date/status rules. Use these definitions where the requested intent is unambiguous; otherwise state the interpretation or ask for clarification, consistent with BR-06. Do not invent unavailable refund, margin, profit, or customer lifetime value data.

## 5. Reference SQL Patterns (Illustrative)

These SQL fragments demonstrate expected calculation semantics; they are **not** the independent, executed benchmark reference queries. The application must inject a trusted authorized-unit restriction through a verified query mechanism, not by accepting an LLM-written `IN` clause. All date parameters and user scopes are trusted, typed inputs.

### 5.1 Net sales by month

```sql
SELECT strftime('%Y-%m', o.completed_date) AS sales_month,
       SUM(oi.quantity * oi.unit_price_cents - oi.discount_amount_cents)
           AS net_sales_cents
FROM ORDERS AS o
JOIN ORDER_ITEMS AS oi ON oi.order_id = o.order_id
WHERE o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date
  AND o.completed_date < :end_date
  /* Additional trusted business-unit restriction required */
GROUP BY strftime('%Y-%m', o.completed_date)
ORDER BY sales_month;
```

### 5.2 Cancellation rate

```sql
SELECT COUNT(DISTINCT CASE WHEN o.order_status = 'CANCELED'
                           THEN o.order_id END) AS canceled_orders,
       COUNT(DISTINCT o.order_id) AS total_orders
FROM ORDERS AS o
WHERE o.order_date >= :start_date
  AND o.order_date < :end_date
  /* Additional trusted business-unit restriction required */;
```

The reference calculator divides the first count by the second using exact decimal arithmetic, returning `NULL` if `total_orders = 0`.

### 5.3 Average order value

```sql
SELECT SUM(oi.quantity * oi.unit_price_cents - oi.discount_amount_cents)
           AS net_sales_cents,
       COUNT(DISTINCT o.order_id) AS completed_orders
FROM ORDERS AS o
JOIN ORDER_ITEMS AS oi ON oi.order_id = o.order_id
WHERE o.order_status = 'COMPLETED'
  AND o.completed_date >= :start_date
  AND o.completed_date < :end_date
  /* Additional trusted business-unit restriction required */;
```

Compute AOV from these two components; do not average line values or previously aggregated AOVs. The patterns above are **not safe to execute without the required independently enforced scope controls**.

## 6. Metric Metadata, Ownership, and Approval

Each metric's `BUSINESS_METRICS` record shall contain its `metric_code`, `metric_name`, narrative definition, descriptive `calculation_rule`, `source_entities`, `metric_version`, `effective_date`, and `approval_status`. Enforce uniqueness of (`metric_code`, `metric_version`) to preserve history.

The initial proposed version for all six metrics is `1.0`, with status `DRAFT` until formally reviewed. Upon approval, the data owner (simulated by the project author) records the decision and effective date, and the data steward updates the version-controlled metadata. Only `APPROVED` versions may be treated as authoritative by the governed metadata service. The `calculation_rule` field must never be executed as arbitrary SQL.

If a metric changes, record the reason, affected requirements, benchmark cases, implementation changes, approval decision, and new version. Previously generated expected results must be regenerated or explicitly retained with their original metric version. The evaluation lead verifies that all compared AI configurations use the same approved reference semantics.

## 7. Validation and Acceptance Tests

| Test ID | Requirement | Expected Result |
|---|---|---|
| BM-01 | Gross and net sales use only completed orders | Pending/canceled amounts excluded from recognized totals |
| BM-02 | Discounts are per line, not per unit | `gross - sum(line discounts)` equals net |
| BM-03 | Order counts are distinct after joins | Multi-line orders counted once |
| BM-04 | Cancellation numerator and denominator use same order-date cohort | Rate reproducible and within 0–100% |
| BM-05 | AOV numerator and denominator share completion-date period | Correct ratio; no average-of-averages |
| BM-06 | Zero denominators | Return `NULL` / not applicable |
| BM-07 | Date boundaries use fixed as-of date and half-open intervals | Boundary cases assigned correctly |
| BM-08 | Product/category aggregation | Totals reconcile to scoped net sales |
| BM-09 | Unit restrictions applied before aggregation | No out-of-scope values disclosed |
| BM-10 | Restricted product cost excluded | No incidental `standard_cost_cents` access |
| BM-11 | Fixed-seed data and metric version | Repeated reference calculations match |
| BM-12 | Canceled-order gross diagnostic | Labeled separately from recognized gross sales |
| BM-13 | Zero-activity months and status combinations | Explicit zeros where reporting requires them |
| BM-14 | Deterministic ranking | Equal-value ties resolved by stable key |
| BM-15 | Currency and presentation rounding | Integer cents preserved; displayed values follow rules |
| BM-16 | Authorization failures and unsupported concepts | Denial or clarification, never fabricated values |

No test results are asserted here. Implement tests after the schema and dataset are available, and record their outcomes as Milestone 2 evidence.

## 8. Benchmark Traceability

| Metric / Convention | Representative Benchmark Cases | Requirements |
|---|---|---|
| Gross Sales | BA-02, BD-01, BD-06, BD-10 | BR-01, BR-05 |
| Net Sales | BA-03, BA-09, BD-02, BD-06, CA-01 | BR-02, BR-04, BR-05 |
| Order Volume | BA-01, BA-04, BA-08, BD-07, CA-06, CA-09 | BR-03, BR-04 |
| Cancellation Rate | BD-03, CA-03 | BR-03, BR-05 |
| Average Order Value | BA-06, BD-04, BD-09 | BR-02, BR-05 |
| Product Sales | BA-05, BD-05, CA-05, CA-08 | BR-02, BR-04, BR-08 |
| Other analytical conventions | BA-07, BD-08, CA-02, CA-04, CA-07, CA-10 | BR-04–BR-08 |
| Authorization and restricted data | AP category | FR-04, GSR-01–GSR-05 |
| Ambiguous / unsupported requests | AU category | BR-06–BR-08 |

The 50-case benchmark inventory exists, but numerical reference answers and executable independently verified SQL remain pending. These must be established against a frozen dataset and approved metric version, not inferred from model responses.

## 9. Open Decisions and Dependencies

| ID | Decision / Dependency | Resolution Needed |
|---|---|---|
| BM-D01 | Approve completed-order revenue recognition and diagnostic canceled-order gross value | Data owner review before metric approval |
| BM-D02 | Approve `completed_date` for sales and `order_date` for order-cohort metrics | Data owner and evaluation review |
| BM-D03 | Fix `as_of_date` and generator coverage window | Dataset configuration and benchmark review |
| BM-D04 | Approve rounding/tolerance rules for numeric scoring | Evaluation plan and reference verification |
| BM-D05 | Decide handling of late status changes in fixed snapshots | Synthetic data generator specification |
| BM-D06 | Approve cost-access policy for shared product catalog | Separate authorization decision; not needed for six core sales metrics |
| BM-D07 | Approve metric version and metadata lifecycle | Data owner/steward sign-off |

**Change impact:** Upon approval, update DD-01, DD-02, DD-06, and DD-07 in `data-dictionary.md` to reference this document as their resolved design source, while leaving implementation/testing tasks open as applicable. Update benchmark expected behaviors only if a genuine semantic conflict is found, and preserve an auditable change record.

## 10. Milestone 2 Acceptance Considerations

Design acceptance requires reviewed formulas, status/date conventions, classification/access implications, and traceability to the benchmark. Implementation acceptance additionally requires populated `BUSINESS_METRICS` records, working schema and synthetic data, independent reference SQL, and passing BM-01–BM-16 tests.

---

**Document Status:** Draft — Milestone 2  
**Next Planned Activity:** Review and approve metric definitions, then implement the SQLite schema, reproducible dataset, and independently verified benchmark reference queries.
