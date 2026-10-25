#!/usr/bin/env python3
"""DQ-01..DQ-14 checks for the generated synthetic SQLite dataset.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_*.py' -v

Override the database with EAI_DATABASE=/path/to/database.sqlite.
These checks validate the dataset, not production authorization enforcement.
"""
import datetime as dt
import json
import os
import sqlite3
import unittest
from pathlib import Path

DB = Path(os.environ.get('EAI_DATABASE', 'database/enterprise_synthetic.sqlite'))
TABLES = ('BUSINESS_UNITS', 'CUSTOMERS', 'PRODUCTS', 'ORDERS', 'ORDER_ITEMS',
          'USERS', 'USER_BUSINESS_UNITS', 'BUSINESS_METRICS')


class DataQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB.is_file():
            raise RuntimeError(f'Database not found: {DB}. Run generate_synthetic_data.py first.')
        cls.db = sqlite3.connect(f'{DB.resolve().as_uri()}?mode=ro', uri=True)
        cls.db.execute('PRAGMA foreign_keys=ON')

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def scalar(self, sql):
        return self.db.execute(sql).fetchone()[0]

    def test_dq01_primary_keys_and_uniqueness(self):
        for table in TABLES:
            with self.subTest(table=table):
                self.assertGreater(self.scalar(f'SELECT COUNT(*) FROM {table}'), 0)
                self.assertEqual(self.scalar(f'SELECT COUNT(*) FROM {table}'),
                                 self.scalar(f'SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {table})'))
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM USER_BUSINESS_UNITS'),
                         self.scalar('SELECT COUNT(*) FROM (SELECT DISTINCT user_id,business_unit_id FROM USER_BUSINESS_UNITS)'))

    def test_dq02_foreign_keys_and_integrity(self):
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.scalar('PRAGMA integrity_check'), 'ok')

    def test_dq03_required_fields(self):
        for table in TABLES:
            cols = self.db.execute(f'PRAGMA table_info({table})').fetchall()
            for _, name, _, required, pk, _ in cols:
                if required or pk:
                    with self.subTest(table=table, column=name):
                        self.assertEqual(self.scalar(f'SELECT COUNT(*) FROM {table} WHERE "{name}" IS NULL'), 0)

    def test_dq04_calendar_dates_and_completion(self):
        for table, column in [('CUSTOMERS','created_date'),('ORDERS','order_date'),
                              ('ORDERS','completed_date'),('BUSINESS_METRICS','effective_date')]:
            for (value,) in self.db.execute(f'SELECT {column} FROM {table} WHERE {column} IS NOT NULL'):
                with self.subTest(table=table, column=column, value=value):
                    self.assertEqual(dt.date.fromisoformat(value).isoformat(), value)
        self.assertEqual(self.scalar("""SELECT COUNT(*) FROM ORDERS WHERE
            (order_status='COMPLETED' AND (completed_date IS NULL OR completed_date<order_date))
            OR (order_status<>'COMPLETED' AND completed_date IS NOT NULL)"""), 0)
        for (stamp,) in self.db.execute('SELECT granted_at FROM USER_BUSINESS_UNITS'):
            self.assertTrue(stamp.endswith('Z'))
            self.assertIsNotNone(dt.datetime.fromisoformat(stamp.replace('Z','+00:00')).utcoffset())

    def test_dq05_integer_currency(self):
        for col in ('unit_price_cents','discount_amount_cents'):
            self.assertEqual(self.scalar(f"SELECT COUNT(*) FROM ORDER_ITEMS WHERE typeof({col})<>'integer' OR {col}<0"), 0)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM PRODUCTS WHERE typeof(standard_cost_cents)<>'integer' OR standard_cost_cents<0"), 0)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM ORDERS WHERE currency_code<>'USD'"), 0)

    def test_dq06_positive_quantities(self):
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM ORDER_ITEMS WHERE quantity<=0'), 0)

    def test_dq07_line_discounts(self):
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM ORDER_ITEMS WHERE discount_amount_cents>quantity*unit_price_cents'), 0)

    def test_dq08_order_statuses(self):
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM ORDERS WHERE order_status NOT IN ('COMPLETED','PENDING','CANCELED')"), 0)
        self.assertEqual(self.scalar('SELECT COUNT(DISTINCT order_status) FROM ORDERS'), 3)

    def test_dq09_customer_unit_consistency(self):
        self.assertEqual(self.scalar('''SELECT COUNT(*) FROM ORDERS o JOIN CUSTOMERS c
            ON o.customer_id=c.customer_id WHERE o.business_unit_id<>c.business_unit_id'''), 0)

    def test_dq10_authorization_mapping_quality(self):
        self.assertEqual(self.scalar('''SELECT COUNT(*) FROM USER_BUSINESS_UNITS a JOIN USERS u USING(user_id)
            WHERE (u.role_name='Sales Analyst' AND a.access_scope<>'PRIMARY')
               OR (u.role_name='Operations Manager' AND a.access_scope<>'ASSIGNED')
               OR (u.role_name='Finance Analyst' AND a.access_scope<>'FINANCE_AUTHORIZED')
               OR u.role_name IN ('Data Steward','System Administrator')'''), 0)
        self.assertEqual(self.scalar('''SELECT COUNT(*) FROM USERS u WHERE u.is_active=1
            AND u.role_name='Sales Analyst' AND
            (SELECT COUNT(*) FROM USER_BUSINESS_UNITS a WHERE a.user_id=u.user_id
             AND a.is_active=1 AND a.access_scope='PRIMARY')<>1'''), 0)
        self.assertEqual(self.scalar('''SELECT COUNT(*) FROM USER_BUSINESS_UNITS a JOIN USERS u USING(user_id)
            WHERE a.is_active=1 AND u.is_active=0'''), 0)

    def test_dq11_orders_have_items(self):
        self.assertEqual(self.scalar('''SELECT COUNT(*) FROM ORDERS o WHERE NOT EXISTS
            (SELECT 1 FROM ORDER_ITEMS i WHERE i.order_id=o.order_id)'''), 0)

    def test_dq12_manifest_and_reproducibility_metadata(self):
        manifest = DB.with_suffix('.manifest.json')
        self.assertTrue(manifest.is_file(), f'Missing generation manifest: {manifest}')
        data = json.loads(manifest.read_text(encoding='utf-8'))
        self.assertIsInstance(data['seed'], int)
        self.assertEqual(len(data['dataset_sha256']), 64)
        self.assertEqual(len(data['schema_sha256']), 64)
        for table in TABLES:
            self.assertEqual(data['row_counts'][table], self.scalar(f'SELECT COUNT(*) FROM {table}'))
        # Actual repeat-generation checksum comparison belongs in an integration test.

    def test_dq13_restricted_cost_column_present(self):
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(PRODUCTS)')}
        self.assertIn('standard_cost_cents', columns)
        self.assertGreater(self.scalar('SELECT COUNT(*) FROM PRODUCTS WHERE standard_cost_cents IS NOT NULL'), 0)
        # Negative authorization/security testing requires a trusted query-execution layer.

    def test_dq14_basic_benchmark_fixture_coverage(self):
        self.assertGreaterEqual(self.scalar('SELECT COUNT(DISTINCT business_unit_id) FROM ORDERS'), 3)
        self.assertGreaterEqual(self.scalar('SELECT COUNT(DISTINCT product_category) FROM PRODUCTS'), 3)
        self.assertGreater(self.scalar('SELECT COUNT(*) FROM ORDER_ITEMS WHERE discount_amount_cents>0'), 0)
