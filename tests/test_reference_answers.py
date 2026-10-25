"""Independent checks for provisional benchmark reference answers.

Run from repository root:
  python -m unittest discover -s tests -p "test_*.py" -v

Requires the generated database, manifest, benchmark CSV, and reference_answers.json.
Does not certify production authorization, approve metric definitions, or test AI output.
"""
import csv
import datetime as dt
import hashlib
import json
import sqlite3
import unittest
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'database/enterprise_synthetic.sqlite'
MANIFEST = ROOT / 'database/enterprise_synthetic.manifest.json'
BENCHMARK = ROOT / 'evaluation/benchmark/test_cases.csv'
ANSWERS = ROOT / 'evaluation/benchmark/reference_answers.json'
CALCULATED = 'PROVISIONAL_CALCULATED'
BEHAVIORAL = 'BEHAVIORAL_EXPECTATION_ONLY'
PENDING = 'PENDING_REFERENCE_IMPLEMENTATION'


def money_ratio(numerator, denominator, scale=100):
    if not denominator:
        return None
    return str((Decimal(numerator) * Decimal(scale) / Decimal(denominator)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP))


class ReferenceAnswerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for path in (DB, MANIFEST, BENCHMARK, ANSWERS):
            if not path.is_file():
                raise FileNotFoundError(f'Missing {path.relative_to(ROOT)}; generate the database and reference answers first')
        cls.manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        cls.answers = json.loads(ANSWERS.read_text(encoding='utf-8'))
        with BENCHMARK.open(encoding='utf-8-sig', newline='') as stream:
            cls.benchmark = {r['test_case_id']: r for r in csv.DictReader(stream)}
        cls.cases = {r['test_case_id']: r for r in cls.answers['cases']}
        cls.db = sqlite3.connect(f'file:{DB.resolve().as_posix()}?mode=ro', uri=True)
        cls.db.row_factory = sqlite3.Row
        cls.db.execute('PRAGMA query_only=ON')
        cls.units = {r['unit_code']: r['business_unit_id'] for r in cls.db.execute(
            'SELECT unit_code, business_unit_id FROM BUSINESS_UNITS')}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def scope(self, cid):
        return {self.units[x] for x in self.cases[cid]['scope'].split('|')}

    def order_rows(self, cid, date_field='completed_date', status='COMPLETED'):
        case = self.cases[cid]
        units = self.scope(cid)
        orders = self.db.execute('SELECT * FROM ORDERS').fetchall()
        return [o for o in orders if o['business_unit_id'] in units
                and (status is None or o['order_status'] == status)
                and o[date_field] is not None
                and case['period_start'] <= o[date_field] < case['period_end_exclusive']]

    def amounts(self, orders):
        ids = {o['order_id'] for o in orders}
        gross = discount = 0
        for item in self.db.execute('SELECT * FROM ORDER_ITEMS'):
            if item['order_id'] in ids:
                gross += item['quantity'] * item['unit_price_cents']
                discount += item['discount_amount_cents']
        return gross, discount, gross - discount

    def single(self, cid):
        rows = self.cases[cid]['result']
        self.assertEqual(len(rows), 1, cid)
        return rows[0]

    def test_01_all_cases_and_scoring_rules_match_benchmark(self):
        self.assertEqual(len(self.benchmark), 50)
        self.assertEqual(set(self.cases), set(self.benchmark))
        self.assertEqual(len(self.answers['cases']), 50)
        for cid, case in self.cases.items():
            with self.subTest(case=cid):
                self.assertEqual(case['question'], self.benchmark[cid]['question'])
                self.assertEqual(case['scoring_rule'], self.benchmark[cid]['scoring_rule'])

    def test_02_status_counts_are_consistent(self):
        counts = Counter(c['status'] for c in self.cases.values())
        self.assertEqual(counts, {CALCULATED: 30, BEHAVIORAL: 18, PENDING: 2})
        self.assertEqual(dict(counts), self.answers['counts'])
        self.assertEqual({cid for cid, c in self.cases.items() if c['status'] == PENDING},
                         {'AP-09', 'AP-10'})
        for cid, c in self.cases.items():
            with self.subTest(case=cid):
                if c['status'] == CALCULATED:
                    self.assertIn('result', c)
                    self.assertIsInstance(c['result'], list)
                    self.assertIn('reference_query_id', c)
                else:
                    self.assertNotIn('result', c)

    def test_03_manifest_checksum_and_as_of_date(self):
        self.assertEqual(self.answers['as_of_date'], self.manifest['as_of_date'])
        digest = hashlib.sha256()
        for table in sorted(self.manifest['row_counts']):
            for row in self.db.execute(f'SELECT * FROM {table} ORDER BY 1, 2'):
                digest.update(json.dumps([table, list(row)], separators=(',', ':'),
                                         ensure_ascii=True).encode() + b'\n')
        self.assertEqual(digest.hexdigest(), self.manifest['dataset_sha256'])
        self.assertEqual(self.answers['dataset_sha256'], digest.hexdigest())

    def test_04_scope_and_period_boundaries(self):
        asof = dt.date.fromisoformat(self.manifest['as_of_date'])
        first = asof.replace(day=1)
        prev_month = (first - dt.timedelta(days=1)).replace(day=1)
        for cid in ('BA-01', 'BA-04', 'BA-06', 'BA-08', 'BD-01', 'BD-02', 'BD-05', 'BD-08', 'BD-09'):
            with self.subTest(case=cid):
                c = self.cases[cid]
                self.assertEqual((c['period_start'], c['period_end_exclusive']),
                                 (prev_month.isoformat(), first.isoformat()))
        for cid, c in self.cases.items():
            if c['status'] == CALCULATED:
                with self.subTest(case=cid):
                    self.assertEqual(c['scope'], self.benchmark[cid]['authorized_scope'])
                    self.assertTrue(set(c['scope'].split('|')).issubset(self.units))
                    self.assertLess(c['period_start'], c['period_end_exclusive'])

    def test_05_gross_and_net_sales_independent_item_arithmetic(self):
        for cid, field, component in (
            ('BA-02', 'gross_sales_cents', 0), ('BD-01', 'gross_sales_cents', 0),
            ('BD-02', 'net_sales_cents', 2), ('BD-08', 'discount_total_cents', 1)):
            with self.subTest(case=cid):
                expected = self.amounts(self.order_rows(cid))[component]
                result = self.single(cid)
                self.assertIn(field, result)
                self.assertEqual(result[field], expected)

    def test_06_order_cohort_and_distinct_counts(self):
        self.assertEqual(self.single('BA-01')['completed_orders_placed'],
                         len(self.order_rows('BA-01', 'order_date', 'COMPLETED')))
        self.assertEqual(self.single('BA-04')['canceled_orders'],
                         len(self.order_rows('BA-04', 'order_date', 'CANCELED')))

    def test_07_aov_components_and_completion_date(self):
        for cid in ('BA-06', 'BD-04'):
            with self.subTest(case=cid):
                orders = self.order_rows(cid)
                expected_net = self.amounts(orders)[2]
                row = self.single(cid)
                self.assertEqual(row['net_sales_cents'], expected_net)
                self.assertEqual(row['completed_orders'], len(orders))

    def test_08_cancellation_rate_components(self):
        for cid in ('BD-03',):
            with self.subTest(case=cid):
                orders = self.order_rows(cid, 'order_date', None)
                row = self.single(cid)
                self.assertEqual(row['total_orders'], len(orders))
                self.assertEqual(row['canceled_orders'], sum(o['order_status'] == 'CANCELED' for o in orders))

    def test_09_catalog_snapshot(self):
        expected = self.db.execute('SELECT COUNT(*) FROM PRODUCTS WHERE is_active=1').fetchone()[0]
        self.assertEqual(self.single('BA-10')['active_products'], expected)

    def test_10_category_totals_match_net_sales(self):
        for cid in ('BA-09', 'BD-05'):
            with self.subTest(case=cid):
                expected = self.amounts(self.order_rows(cid))[2]
                actual = sum(r['category_net_sales_cents'] for r in self.cases[cid]['result'])
                self.assertEqual(actual, expected)

    def test_11_monthly_net_sales_reconciliation(self):
        cid = 'BA-03'
        orders = self.order_rows(cid)
        expected = defaultdict(int)
        ids = {o['order_id']: o['completed_date'][:7] for o in orders}
        for i in self.db.execute('SELECT order_id, quantity, unit_price_cents, discount_amount_cents FROM ORDER_ITEMS'):
            if i['order_id'] in ids:
                expected[ids[i['order_id']]] += i['quantity'] * i['unit_price_cents'] - i['discount_amount_cents']
        actual = {r['sales_month']: r['net_sales_cents'] for r in self.cases[cid]['result']}
        self.assertEqual(actual, dict(expected))

    def test_12_behavioral_cases_have_no_fabricated_numbers(self):
        for cid, case in self.cases.items():
            if case['status'] == BEHAVIORAL:
                with self.subTest(case=cid):
                    self.assertEqual(case['expected_behavior'], self.benchmark[cid]['expected_behavior'])
                    self.assertNotIn('result', case)

    def test_13_pending_policy_cases_not_silently_approved(self):
        for cid in ('AP-09', 'AP-10'):
            with self.subTest(case=cid):
                self.assertEqual(self.cases[cid]['status'], PENDING)
                self.assertNotIn('result', self.cases[cid])
        self.assertEqual(self.answers['status'], 'PROVISIONAL_NOT_APPROVED')

    def test_14_reported_values_do_not_cross_scope(self):
        # Independent unit-by-unit sales arithmetic: scoped values must not include UNIT_C.
        for cid in ('BA-02', 'BD-01', 'BD-02'):
            with self.subTest(case=cid):
                selected = self.order_rows(cid)
                self.assertTrue(all(o['business_unit_id'] in self.scope(cid) for o in selected))
                gross, _, net = self.amounts(selected)
                row = self.single(cid)
                self.assertEqual(row.get('gross_sales_cents', gross), gross)
                self.assertEqual(row.get('net_sales_cents', net), net)


if __name__ == '__main__':
    unittest.main()
