#!/usr/bin/env python3
"""Deterministic synthetic SQLite dataset for Enterprise AI Governance & Evaluation.

Requires Python 3.9+ and SQLite 3.37+ (STRICT tables). Standard library only.
Run from repository root:
  python scripts/generate_synthetic_data.py --schema database/schema.sql \
      --output database/enterprise_synthetic.sqlite --seed 20261024 --as-of-date 2026-10-24

WARNING: Synthetic demonstration data only. This generator does not implement
runtime authorization, benchmark reference answers, or security controls.
"""
import argparse
import calendar
import datetime as dt
import hashlib
import json
import random
import sqlite3
from collections import Counter
from pathlib import Path

VERSION = "0.1"
METRICS = [
    ("GROSS_SALES", "Gross Sales", "Completed order-line value before discounts", "Sum quantity times unit_price_cents on completed orders by completed_date", "ORDERS,ORDER_ITEMS"),
    ("NET_SALES", "Net Sales", "Completed order-line value after line discounts", "Sum quantity times unit_price_cents minus discount_amount_cents on completed orders by completed_date", "ORDERS,ORDER_ITEMS"),
    ("ORDER_VOLUME", "Order Volume", "Distinct orders placed, all statuses by default", "Count distinct order_id by order_date", "ORDERS"),
    ("CANCELLATION_RATE", "Cancellation Rate", "Canceled orders divided by all orders in placed-date cohort", "Count canceled orders / count all orders by order_date; NULL for zero denominator", "ORDERS"),
    ("AVERAGE_ORDER_VALUE", "Average Order Value", "Net sales per completed order", "Completed-order net sales divided by distinct completed orders using completed_date", "ORDERS,ORDER_ITEMS"),
    ("PRODUCT_SALES", "Product Sales", "Completed-order net sales by product or category", "Sum line net cents on completed orders by completed_date and product", "ORDERS,ORDER_ITEMS,PRODUCTS"),
]


def iso_day(value):
    return dt.date.fromisoformat(value)


def shift_month(d, offset):
    y = d.year + (d.month - 1 + offset) // 12
    m = (d.month - 1 + offset) % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def random_day(rng, start, end):
    return start + dt.timedelta(days=rng.randrange((end - start).days + 1))


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--schema', type=Path, default=Path('database/schema.sql'))
    p.add_argument('--output', type=Path, default=Path('database/enterprise_synthetic.sqlite'))
    p.add_argument('--seed', type=int, default=20261024)
    p.add_argument('--as-of-date', default='2026-10-24', help='Frozen benchmark as-of date (YYYY-MM-DD)')
    p.add_argument('--months', type=int, default=30, help='Months of historical order dates')
    p.add_argument('--orders-per-unit', type=int, default=720)
    p.add_argument('--customers-per-unit', type=int, default=60)
    p.add_argument('--overwrite', action='store_true', help='Replace an existing database')
    p.add_argument('--manifest', type=Path, help='Optional JSON run manifest; defaults beside database')
    return p.parse_args()


def assert_integrity(conn, expected_orders):
    assert conn.execute('PRAGMA foreign_key_check').fetchall() == [], 'Foreign-key violations'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite integrity failure'
    count = conn.execute('SELECT COUNT(*) FROM ORDERS').fetchone()[0]
    assert count == expected_orders and count > 0, 'Unexpected/empty orders'
    checks = {
        'missing_order_items': '''SELECT COUNT(*) FROM ORDERS o WHERE NOT EXISTS
            (SELECT 1 FROM ORDER_ITEMS i WHERE i.order_id=o.order_id)''',
        'invalid_order_dates': '''SELECT COUNT(*) FROM ORDERS WHERE
            (order_status='COMPLETED' AND (completed_date IS NULL OR completed_date<order_date))
            OR (order_status<>'COMPLETED' AND completed_date IS NOT NULL)''',
        'cross_unit_orders': '''SELECT COUNT(*) FROM ORDERS o JOIN CUSTOMERS c
            ON c.customer_id=o.customer_id WHERE o.business_unit_id<>c.business_unit_id''',
        'invalid_discounts': '''SELECT COUNT(*) FROM ORDER_ITEMS WHERE
            discount_amount_cents>quantity*unit_price_cents''',
        'missing_sales_analyst_scope': '''SELECT COUNT(*) FROM USERS u WHERE role_name='Sales Analyst' AND u.is_active=1
            AND (SELECT COUNT(*) FROM USER_BUSINESS_UNITS a WHERE a.user_id=u.user_id
                AND a.is_active=1 AND a.access_scope='PRIMARY')<>1''',
        'unauthorized_scope_types': '''SELECT COUNT(*) FROM USER_BUSINESS_UNITS a JOIN USERS u USING(user_id)
            WHERE (u.role_name='Sales Analyst' AND a.access_scope<>'PRIMARY')
               OR (u.role_name='Operations Manager' AND a.access_scope<>'ASSIGNED')
               OR (u.role_name='Finance Analyst' AND a.access_scope<>'FINANCE_AUTHORIZED')
               OR u.role_name IN ('Data Steward','System Administrator')''',
    }
    for name, query in checks.items():
        violations = conn.execute(query).fetchone()[0]
        assert violations == 0, f'{name}: {violations} violation(s)'
    gross, discounts, net = conn.execute('''SELECT
        COALESCE(SUM(i.quantity*i.unit_price_cents),0),
        COALESCE(SUM(i.discount_amount_cents),0),
        COALESCE(SUM(i.quantity*i.unit_price_cents-i.discount_amount_cents),0)
        FROM ORDERS o JOIN ORDER_ITEMS i USING(order_id)
        WHERE o.order_status='COMPLETED' ''').fetchone()
    assert gross - discounts == net, 'Sales reconciliation failed'
    return {'checks_passed': len(checks) + 3, 'gross_sales_cents': gross,
            'eligible_discount_cents': discounts, 'net_sales_cents': net}


def main():
    a = parse_args()
    if a.months < 18 or a.orders_per_unit < 100 or a.customers_per_unit < 10:
        raise SystemExit('Require --months >= 18, --orders-per-unit >= 100, --customers-per-unit >= 10')
    asof = iso_day(a.as_of_date)
    start = shift_month(asof.replace(day=1), -(a.months - 1))
    if not a.schema.is_file():
        raise SystemExit(f'Schema not found: {a.schema}. Run from repository root or pass --schema.')
    if a.output.exists():
        if not a.overwrite:
            raise SystemExit(f'Output already exists: {a.output}. Use --overwrite to replace it.')
        a.output.unlink()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    conn = sqlite3.connect(a.output)
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        conn.executescript(a.schema.read_text(encoding='utf-8'))
        with conn:
            units = [(1,'UNIT_A','North Division','North',1),
                     (2,'UNIT_B','South Division','South',1),
                     (3,'UNIT_C','West Division','West',1)]
            conn.executemany('INSERT INTO BUSINESS_UNITS VALUES (?,?,?,?,?)', units)
            categories = ['Electronics','Office Supplies','Furniture','Accessories','Software']
            products = []
            for pid in range(1, 31):
                cat = categories[(pid - 1) % len(categories)]
                products.append((pid,f'PRD_{pid:03d}',f'Synthetic {cat} Item {pid:02d}',cat,
                                 rng.randint(500, 35000),int(pid != 30)))
            conn.executemany('INSERT INTO PRODUCTS VALUES (?,?,?,?,?,?)', products)
            customer_rows = []
            for unit in range(1,4):
                for n in range(1,a.customers_per_unit+1):
                    cid=(unit-1)*a.customers_per_unit+n
                    customer_rows.append((cid,unit,f'CUST_{cid:04d}',f'Synthetic Customer {cid:04d}',
                                          ['SMB','Mid-Market','Enterprise'][n%3],
                                          (start-dt.timedelta(days=120)).isoformat(),1))
            conn.executemany('INSERT INTO CUSTOMERS VALUES (?,?,?,?,?,?,?)',customer_rows)
            users = [
                (1,'SA_A','Synthetic Sales Analyst A','Sales Analyst',1,1),
                (2,'SA_B','Synthetic Sales Analyst B','Sales Analyst',2,1),
                (3,'OPS_AB','Synthetic Operations Manager','Operations Manager',1,1),
                (4,'FIN_AB','Synthetic Finance Analyst','Finance Analyst',1,1),
                (5,'STEWARD','Synthetic Data Steward','Data Steward',None,1),
                (6,'ADMIN','Synthetic System Administrator','System Administrator',None,1),
                (7,'SA_INACTIVE','Synthetic Inactive Analyst','Sales Analyst',3,0),
                (8,'SA_C','Synthetic Sales Analyst C','Sales Analyst',3,1),
            ]
            conn.executemany('INSERT INTO USERS VALUES (?,?,?,?,?,?)',users)
            stamp=asof.isoformat()+'T00:00:00Z'
            grants=[(1,1,'PRIMARY',stamp,1),(2,2,'PRIMARY',stamp,1),
                    (3,1,'ASSIGNED',stamp,1),(3,2,'ASSIGNED',stamp,1),
                    (4,1,'FINANCE_AUTHORIZED',stamp,1),(4,2,'FINANCE_AUTHORIZED',stamp,1),
                    (7,3,'PRIMARY',stamp,0),(8,3,'PRIMARY',stamp,1)]
            conn.executemany('INSERT INTO USER_BUSINESS_UNITS VALUES (?,?,?,?,?)',grants)
            metrics=[(idx,code,name,definition,rule,source,'1.0',asof.isoformat(),'DRAFT')
                     for idx,(code,name,definition,rule,source) in enumerate(METRICS,1)]
            conn.executemany('INSERT INTO BUSINESS_METRICS VALUES (?,?,?,?,?,?,?,?,?)',metrics)
            orders=[]; items=[]; order_id=0; item_id=0
            # Guaranteed monthly coverage for units A and B, plus stochastic variability.
            for unit in range(1,4):
                for n in range(a.orders_per_unit):
                    order_id+=1
                    month_idx = n % a.months
                    first = shift_month(start,month_idx)
                    last = min(asof,shift_month(first,1)-dt.timedelta(days=1))
                    # Create occasional empty-activity months for UNIT_C while preserving history.
                    if unit==3 and month_idx in (3,9,15):
                        first=shift_month(start,(month_idx+1)%a.months)
                        last=min(asof,shift_month(first,1)-dt.timedelta(days=1))
                    placed=random_day(rng,first,last)
                    status=['COMPLETED','COMPLETED','COMPLETED','COMPLETED','PENDING','CANCELED'][rng.randrange(6)]
                    completed=None
                    if status=='COMPLETED':
                        completed=(placed+dt.timedelta(days=rng.randrange(min(8,(asof-placed).days+1)))).isoformat()
                    cid=(unit-1)*a.customers_per_unit+1+rng.randrange(a.customers_per_unit)
                    orders.append((order_id,f'ORD_{order_id:07d}',cid,unit,placed.isoformat(),status,completed,'USD'))
                    # Every order has 1-4 items; line-level discount is not per-unit.
                    for line in range(1,rng.randint(1,4)+1):
                        item_id+=1
                        qty=rng.randint(1,6)
                        price=rng.randint(750,75000)
                        gross=qty*price
                        discount=0 if rng.random()<0.55 else rng.randint(1,gross//3)
                        items.append((item_id,order_id,line,rng.randint(1,30),qty,price,discount))
            conn.executemany('INSERT INTO ORDERS VALUES (?,?,?,?,?,?,?,?)',orders)
            conn.executemany('INSERT INTO ORDER_ITEMS VALUES (?,?,?,?,?,?,?)',items)
        validation=assert_integrity(conn,3*a.orders_per_unit)
        counts={t:conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in
                ['BUSINESS_UNITS','CUSTOMERS','PRODUCTS','ORDERS','ORDER_ITEMS','USERS','USER_BUSINESS_UNITS','BUSINESS_METRICS']}
        statuses=dict(conn.execute('SELECT order_status,COUNT(*) FROM ORDERS GROUP BY order_status'))
        # Logical checksum is independent of SQLite file layout and insertion timestamp.
        h=hashlib.sha256()
        for table in sorted(counts):
            for row in conn.execute(f'SELECT * FROM {table} ORDER BY 1, 2'):
                h.update(json.dumps([table,list(row)],separators=(',',':'),ensure_ascii=True).encode()+b'\n')
        manifest={'generator_version':VERSION,'seed':a.seed,'as_of_date':a.as_of_date,
                  'start_date':start.isoformat(),'end_date':asof.isoformat(),
                  'schema_sha256':hashlib.sha256(a.schema.read_bytes()).hexdigest(),
                  'dataset_sha256':h.hexdigest(),'row_counts':counts,
                  'order_status_counts':statuses,'validation':validation,
                  'notes':['Synthetic records only','Metric definitions remain DRAFT',
                           'Benchmark scenario coverage and authorization enforcement require separate tests']}
        target=a.manifest or a.output.with_suffix('.manifest.json')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps({'database':str(a.output),'manifest':str(target),**manifest},indent=2))
    except Exception:
        conn.close()
        if a.output.exists(): a.output.unlink()
        raise
    finally:
        conn.close()


if __name__=='__main__':
    main()
