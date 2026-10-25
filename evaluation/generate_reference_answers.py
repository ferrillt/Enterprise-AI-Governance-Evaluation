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
    'BA-02': 'R01', 'BA-03': 'R07', 'BA-05': 'R06', 'BA-06': 'R05',
    'BA-09': 'R11', 'BD-01': 'R01', 'BD-02': 'R02', 'BD-03': 'R04',
    'BD-04': 'R05', 'BD-05': 'R11', 'BD-06': 'R13', 'BD-08': 'R09',
    'BD-09': 'R12', 'BD-10': 'R10', 'AP-10': 'R02',
}
# Case-specific time windows; date calculations use fixed as_of_date.
LAST_MONTH = {'BA-06','BD-01','BD-02','BD-05','BD-08','BD-09'}
LAST_QUARTER = {'BA-02','BA-05','BA-09','BD-03','BD-04','BD-06','BD-10'}
LAST_YEAR = {'BA-03'}
# Cases requiring interpretation (AP-10 has no specified period) are not run.
CASE_QUERY.pop('AP-10')


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


def sql_blocks(path):
    """Extract independently maintained R01-R13 SELECT statements by labels."""
    import re
    raw = path.read_text(encoding='utf-8')
    found = {}
    for m in re.finditer(r'^-- (R\d{2})\.', raw, flags=re.MULTILINE):
        section = raw[m.end():]
        nxt = re.search(r'^-- R\d{2}\.', section, flags=re.MULTILINE)
        section = section[:nxt.start()] if nxt else section
        # Skip descriptive SQL comments, locate first SELECT.
        match = re.search(r'(?m)^SELECT\b', section)
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
            period='month' if cid in LAST_MONTH else 'quarter' if cid in LAST_QUARTER else 'year' if cid in LAST_YEAR else None
            if period is None:
                entry.update(status='PENDING_REFERENCE_IMPLEMENTATION',note='No unambiguous supported period mapping.')
            else:
                try:
                    uid=choose_user(con,case['user_role'],case['authorized_scope'])
                    ref=CASE_QUERY[cid]; sql=queries[ref]
                    if not sql.lstrip().upper().startswith('SELECT') or ref not in queries:
                        raise ValueError(f'Missing safe reference query {ref}')
                    start,end=windows[period]
                    params={'user_id':uid,'start_date':start.isoformat(),'end_date':end.isoformat(),
                            'as_of_date':asof.isoformat()}
                    cols=con.execute(sql,params)
                    values=[dict(zip([c[0] for c in cols.description],row)) for row in cols.fetchall()]
                    entry.update(status='PROVISIONAL_CALCULATED',reference_query_id=ref,
                                 period_start=params['start_date'],period_end_exclusive=params['end_date'],
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
