#!/usr/bin/env python3
"""Generate PROVISIONAL benchmark reference results from a fixed synthetic SQLite snapshot.

Does not approve DRAFT metrics, implement runtime security, or score AI systems.
Requires: evaluation/benchmark/test_cases.csv and generated SQLite database.
Run from repository root:
  python evaluation/generate_reference_answers.py --database database/enterprise_synthetic.sqlite \
      --benchmark evaluation/benchmark/test_cases.csv \
      --manifest database/enterprise_synthetic.manifest.json \
      --output evaluation/benchmark/reference_answers.json

Results for cases without a fully specified independent calculation remain
PENDING_REFERENCE_IMPLEMENTATION. Policy/unsupported cases get behavioral
expectations, not fabricated numeric results. Never overwrite test_cases.csv.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

# Reference query IDs from evaluation/reference_queries.sql. Some cases require
# additional grouping/filters, so they are deliberately NOT mapped here.
CASE_QUERY = {
    'BA-01':'R14','BA-02':'R01','BA-03':'R19','BA-04':'R15','BA-05':'R06',
    'BA-06':'R05','BA-07':'R16','BA-08':'R17','BA-09':'R11','BA-10':'R18',
    'BD-01':'R01','BD-02':'R02','BD-03':'R04','BD-04':'R05','BD-05':'R11',
    'BD-06':'R13','BD-07':'R29','BD-08':'R09','BD-09':'R12','BD-10':'R10',
    'CA-01':'R19','CA-02':'R20','CA-03':'R21','CA-04':'R22','CA-05':'R23',
    'CA-06':'R24','CA-07':'R25','CA-08':'R26','CA-09':'R27','CA-10':'R28',
}
LAST_MONTH = {'BA-01','BA-04','BA-06','BA-08','BD-01','BD-02','BD-05','BD-08','BD-09'}
LAST_QUARTER = {'BA-02','BA-05','BA-09','BD-03','BD-04','BD-06','BD-10','CA-03','CA-06','CA-08'}
LAST_YEAR = {'BA-03','CA-02','CA-07','CA-10'}
LAST_SIX_COMPLETED = {'CA-01'}
LAST_SIX_MONTHS = {'CA-09'}
LAST_90_DAYS = {'BA-07'}
YEAR_TO_DATE = {'BD-07'}
# CA-04: matching prior/current completed calendar years; deterministic comparison.
YEAR_OVER_YEAR = {'CA-04'}
# CA-05 has no specified reporting period; an all-available-history window is
# explicitly recorded as a provisional interpretation, not a silent default.
ALL_HISTORY = {'CA-05'}
# BA-10 is a catalog snapshot, not a date-scoped sales calculation.
CATALOG_SNAPSHOT = {'BA-10'}
# AP-09 and AP-10 are behavioral expectations:
# AP-09 denies restricted product-cost disclosure pending approved controls.
# AP-10 requires clarification of the reporting period and sales metric.
# Neither case executes reference SQL or produces a numerical result.


def periods(asof):
    first_month = asof.replace(day=1)
    prior_month_end = first_month
    prior_month_start = (first_month - dt.timedelta(days=1)).replace(day=1)
    quarter_start_month = 1 + 3 * ((asof.month - 1)//3)
    current_q_start = dt.date(asof.year, quarter_start_month, 1)
    prev_q_end = current_q_start
    prev_q_start = dt.date(asof.year - (1 if quarter_start_month == 1 else 0),
                           10 if quarter_start_month == 1 else quarter_start_month - 3, 1)
    return {'month':(prior_month_start, prior_month_end),
            'quarter':(prev_q_start, prev_q_end),
            'year':(dt.date(asof.year-1,1,1),dt.date(asof.year,1,1))}


def add_months(d, offset):
    month_index = d.year * 12 + (d.month - 1) + offset
    return dt.date(month_index // 12, month_index % 12 + 1, 1)


def case_window(cid, asof, windows, manifest):
    if cid in LAST_MONTH: return windows['month'], 'previous_complete_month'
    if cid in LAST_QUARTER: return windows['quarter'], 'previous_complete_quarter'
    if cid in LAST_YEAR: return windows['year'], 'previous_complete_year'
    if cid in LAST_SIX_COMPLETED:
        return (add_months(asof.replace(day=1),-6),asof.replace(day=1)), 'six_complete_months'
    if cid in LAST_SIX_MONTHS:
        return (add_months(asof.replace(day=1),-5),asof+dt.timedelta(days=1)), 'six_months_including_current_partial'
    if cid in LAST_90_DAYS:
        return (asof-dt.timedelta(days=89),asof+dt.timedelta(days=1)), 'last_90_calendar_days_inclusive'
    if cid in YEAR_TO_DATE:
        return (dt.date(asof.year,1,1),asof+dt.timedelta(days=1)), 'year_to_date_inclusive'
    if cid in YEAR_OVER_YEAR:
        return windows['year'], 'prior_completed_year_vs_year_before'
    if cid in ALL_HISTORY:
        return (dt.date.fromisoformat(manifest['start_date']),asof+dt.timedelta(days=1)), 'all_available_history_provisional_interpretation'
    if cid in CATALOG_SNAPSHOT:
        return (asof,asof+dt.timedelta(days=1)), 'catalog_snapshot_as_of_date'
    raise ValueError('No supported date interpretation for '+cid)


def enrich(cid, rows):
    """Keep exact integer components; use string decimals for derived ratios."""
    from decimal import Decimal, ROUND_HALF_UP
    def ratio(n,d,scale=100):
        if not d: return None
        return str((Decimal(n)*Decimal(scale)/Decimal(d)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
    if cid in ('BD-09',):
        for r in rows:
            r['aov_usd'] = (str((Decimal(r['net_sales_cents']) / Decimal(r['completed_orders']) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if r['completed_orders'] else None)
    if cid=='CA-01':
        previous=None
        for r in rows:
            current=r['net_sales_cents'];r['mom_change_cents']=None if previous is None else current-previous
            r['mom_change_percent']=None if previous is None else ratio(current-previous,previous)
            previous=current
        # First month is baseline; no preceding month in requested six-month window.
    if cid=='CA-03':
        for r in rows:r['cancellation_rate_percent']=ratio(r['canceled_orders'],r['total_orders'])
    if cid=='CA-04':
        for r in rows:
            r['change_cents']=r['current_net_sales_cents']-r['prior_net_sales_cents']
            r['change_percent']=ratio(r['change_cents'],r['prior_net_sales_cents'])
        rows[:]=[r for r in rows if r['change_cents']>0]
    if cid=='CA-05':
        for r in rows:r['share_percent']=ratio(r['net_sales_cents'],r['total_net_sales_cents'])
    if cid=='CA-07':
        for r in rows:r['average_monthly_net_sales_usd']=str((Decimal(r['total_net_sales_cents'])/Decimal(r['months_in_window'])/100).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)) if r['months_in_window'] else None
    if cid=='BA-05':del rows[5:]
    return rows

def sql_blocks(path):
    """Extract independently maintained R01-R29 SELECT statements by labels."""
    import re
    raw = path.read_text(encoding='utf-8')
    found = {}
    for m in re.finditer(r'^-- (R\d{2})\.', raw, flags=re.MULTILINE):
        section = raw[m.end():]
        nxt = re.search(r'^-- R\d{2}\.', section, flags=re.MULTILINE)
        section = section[:nxt.start()] if nxt else section
        # Skip descriptive SQL comments, locate first SELECT.
        match = re.search(r'(?m)^(?:SELECT|WITH)\b', section)
        if match:
            statement = section[match.start():].split(';',1)[0].strip()
            found[m.group(1)] = statement
    return found


def choose_user(con, role, requested_scope):
    """Fail closed: verify active user and exact active mapped scope + role/scope type."""
    required = set(requested_scope.split('|'))
    if not required or any(not x.startswith('UNIT_') for x in required):
        raise ValueError('Scope is not an explicit business-unit set')
    candidates = con.execute('SELECT user_id FROM USERS WHERE role_name=? AND is_active=1', (role,)).fetchall()
    role_scopes = {'Sales Analyst':{'PRIMARY'}, 'Operations Manager':{'ASSIGNED'},
                   'Finance Analyst':{'FINANCE_AUTHORIZED'}}
    if role not in role_scopes:
        raise ValueError('Role has no approved transaction-data scope')
    for (user_id,) in candidates:
        rows = con.execute('''SELECT b.unit_code, a.access_scope FROM USER_BUSINESS_UNITS a
            JOIN BUSINESS_UNITS b ON b.business_unit_id=a.business_unit_id
            WHERE a.user_id=? AND a.is_active=1''', (user_id,)).fetchall()
        units = {code for code, scope in rows if scope in role_scopes[role]}
        if units == required and len(rows) == len(required):
            return user_id
    raise ValueError(f'No active {role} identity with exact approved scope {requested_scope}')


def main():
    p=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--database', type=Path, default=Path('database/enterprise_synthetic.sqlite'))
    p.add_argument('--benchmark', type=Path, default=Path('evaluation/benchmark/test_cases.csv'))
    p.add_argument('--manifest', type=Path, default=Path('database/enterprise_synthetic.manifest.json'))
    p.add_argument('--queries', type=Path, default=Path('evaluation/reference_queries.sql'))
    p.add_argument('--output', type=Path, default=Path('evaluation/benchmark/reference_answers.json'))
    args=p.parse_args()
    for f in (args.database,args.benchmark,args.manifest,args.queries):
        if not f.is_file(): p.error(f'Missing required file: {f}')
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    # Generator's dataset_sha256 is a logical row checksum, NOT a file hash.
    checksum_connection=sqlite3.connect(f'file:{args.database.resolve().as_posix()}?mode=ro',uri=True)
    h=hashlib.sha256()
    for table in sorted(manifest['row_counts']):
        for row in checksum_connection.execute(f'SELECT * FROM {table} ORDER BY 1, 2'):
            h.update(json.dumps([table,list(row)],separators=(',',':'),ensure_ascii=True).encode()+b'\n')
    checksum_connection.close()
    sha=h.hexdigest()
    if sha != manifest.get('dataset_sha256'):
        p.error('Logical dataset checksum does not match manifest. Regenerate or use matching manifest.')
    asof=dt.date.fromisoformat(manifest['as_of_date'])
    windows=periods(asof)
    queries=sql_blocks(args.queries)
    with args.benchmark.open(newline='',encoding='utf-8-sig') as f:
        cases=list(csv.DictReader(f))
    if not cases or len({r['test_case_id'] for r in cases})!=len(cases):
        p.error('Benchmark cases missing or duplicate IDs')
    con=sqlite3.connect(f'file:{args.database.resolve().as_posix()}?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    con.execute('PRAGMA foreign_keys=ON')
    if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok': p.error('SQLite integrity check failed')
    metric_status=con.execute('SELECT approval_status,COUNT(*) FROM BUSINESS_METRICS GROUP BY approval_status').fetchall()
    entries=[]
    for case in cases:
        cid=case['test_case_id']; score=case['scoring_rule']
        entry={'test_case_id':cid,'question':case['question'], 'scoring_rule':score}
        if score != 'REFERENCE_SQL_REQUIRED':
            entry.update(status='BEHAVIORAL_EXPECTATION_ONLY',expected_behavior=case['expected_behavior'],
                         note='Requires separate AI-response/policy evaluation; no database answer calculated.')
        elif cid not in CASE_QUERY:
            entry.update(status='PENDING_REFERENCE_IMPLEMENTATION',
                         note='Case-specific independently verified SQL or explicit period/metric interpretation required.')
        else:
            try:
                uid=choose_user(con,case['user_role'],case['authorized_scope'])
                ref=CASE_QUERY[cid]
                if ref not in queries: raise ValueError(f'Missing reference query {ref}')
                sql=queries[ref]
                if not sql.lstrip().upper().startswith('SELECT') and not sql.lstrip().upper().startswith('WITH'):
                    raise ValueError(f'Invalid reference query {ref}')
                (start,end),interpretation=case_window(cid,asof,windows,manifest)
                params={'user_id':uid,'start_date':start.isoformat(),'end_date':end.isoformat(),
                        'as_of_date':asof.isoformat()}
                if cid in YEAR_OVER_YEAR:
                    params['prior_start']=dt.date(start.year-1,start.month,start.day).isoformat()
                    params['prior_end']=start.isoformat()
                cur=con.execute(sql,params)
                values=[dict(zip([c[0] for c in cur.description],row)) for row in cur.fetchall()]
                values=enrich(cid,values)
                entry.update(status='PROVISIONAL_CALCULATED',reference_query_id=ref,
                             period_start=params['start_date'],period_end_exclusive=params['end_date'],
                             period_interpretation=interpretation,
                             scope=case['authorized_scope'],result=values,
                             note='Provisional: metric approval, case semantics, and independent review outstanding.')
            except (ValueError,sqlite3.Error) as exc:
                entry.update(status='PENDING_REFERENCE_IMPLEMENTATION',note=str(exc))
        entries.append(entry)
    con.close()
    from collections import Counter
    counts=dict(Counter(e['status'] for e in entries))
    result={'schema_version':'0.1','status':'PROVISIONAL_NOT_APPROVED',
            'as_of_date':asof.isoformat(),'dataset_sha256':sha,
            'metric_approval_statuses':dict(metric_status),'counts':counts,
            'warning':'Do not replace benchmark expected_result fields or treat this output as scored ground truth until approved and independently verified.',
            'cases':entries}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'Wrote {len(entries)} case records to {args.output}')
    for k,v in sorted(counts.items()):print(f'  {k}: {v}')
    if len(entries)!=50:print(f'WARNING: expected 50 benchmark cases, found {len(entries)}')

if __name__=='__main__':main()
