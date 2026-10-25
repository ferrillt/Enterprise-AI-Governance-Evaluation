"""Apply Milestone 2 governance corrections without rewriting unrelated content.
Run from the repository root: python scripts/update_governance_framework.py
"""
from pathlib import Path

path = Path('docs/governance-framework.md')
source = path.read_text(encoding='utf-8')
replacements = [
    ('| Product Standard Costs | Denied | Denied | Authorized Units | Metadata Only | Denied |',
     '| Product Standard Costs | Denied | Denied | Denied — Pending Policy Approval | Metadata Only | Denied |'),
    ('- **Denied:** No permission to perform the requested operation.',
     '- **Denied:** No permission to perform the requested operation.\n\n'
     '**Restricted Product-Cost Policy — AP-09:** `PRODUCTS.standard_cost_cents` is Restricted. '
     'Finance Analyst membership and authorized business-unit assignments do not, by themselves, grant cost access. '
     'Because `PRODUCTS` is a shared catalog without direct unit ownership, cost disclosure remains denied '
     'until an approved policy defines eligible product-to-unit relationships, explicit column permission, '
     'trusted scope enforcement, and negative authorization tests. This is a documented policy disposition, '
     'not evidence of an implemented runtime control. See [Data Dictionary](data-dictionary.md) '
     'and [Evaluation Benchmark](../evaluation/benchmark/test_cases.csv) (AP-09).'),
    ('These definitions are preliminary and will be refined during data modeling.',
     'The six metric definitions are specified in [Business Metrics](business-metrics.md). '
     'They remain `DRAFT` until an explicit simulated Data Owner approval decision is recorded, '
     'with version and effective date synchronized to `BUSINESS_METRICS`. '
     'Reference calculations are provisional until that approval and independent verification.'),
    ('- The business glossary requires finalized calculation definitions.',
     '- The six business metric definitions are documented, but formal approval remains pending.'),
    ('- The risk register and evaluation benchmark remain to be completed.',
     '- The risk register and 50-case evaluation benchmark are documented. The benchmark contains '
     '30 provisional analytical references and 20 behavioral expectations; runtime evaluation remains pending.'),
    ('**Document Status:** Draft — Milestone 1',
     '**Document Status:** Milestone 1 governance design baseline; Milestone 2 policy alignment updated. '
     'Restricted-cost enforcement, metric approval, and AI/runtime evaluation remain open.\n\n'
     '**Milestone 2 evidence:** The user-reported local automated suite passed 28 tests '
     '(14 data-quality; 14 reference-answer), zero failures, in 0.246 seconds. '
     'These tests do not establish production authorization or LLM behavior. '
     'See [Milestone 2 Review](milestone-2-review.md).'),
]
for old, new in replacements:
    if source.count(old) != 1:
        raise SystemExit(f'Expected exactly one occurrence, found {source.count(old)}: {old[:80]}')
    source = source.replace(old, new, 1)
path.write_text(source, encoding='utf-8')
print(f'Updated {path}')
