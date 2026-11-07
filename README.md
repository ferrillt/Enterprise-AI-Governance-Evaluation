# Enterprise AI Governance & Evaluation

## Project Overview

This project explores how enterprise data governance, business metadata, and validation controls influence the accuracy, reliability, security, and operational performance of AI-generated analytical responses.

Using a synthetic enterprise sales and operations dataset, the project will design, implement, and evaluate a governed AI analytics solution that supports natural-language business questions while enforcing defined data-access policies and analytical validation requirements.

The project emphasizes enterprise AI architecture, governance, security, and measurable evaluation rather than the development of a standalone AI chatbot.

## Project Objectives

- Design an enterprise AI analytics architecture with clearly defined components, interfaces, and security boundaries.
- Establish a synthetic relational dataset with documented schemas, data classifications, and business definitions.
- Implement role-based authorization, SQL validation, and controlled analytical execution.
- Evaluate AI-generated analytical responses against independently verified reference results.
- Compare baseline, metadata-enriched, and governed AI configurations.
- Measure analytical accuracy, authorization compliance, reliability, latency, and estimated operating cost.
- Demonstrate requirements traceability, risk management, reproducibility, and evidence-based architectural decision-making.

## Technology Stack

Planned technologies include:

- **Python:** AI orchestration, governance controls, data processing, and evaluation.
- **SQL and SQLite:** Relational data storage and analytical query execution.
- **Large Language Model API:** Natural-language interpretation and SQL generation.
- **pandas:** Data processing and evaluation analysis.
- **pytest:** Automated testing and verification.
- **Git and GitHub:** Version control, documentation, and project management.

Technology selections may be refined during implementation.

## Architecture and Governance

The proposed architecture separates user interaction, AI orchestration, governance and policy enforcement, enterprise data access, and evaluation and monitoring.

Governance controls will be implemented independently of LLM-generated instructions. The system will use trusted authorization context, approved business definitions, restricted database access, and SQL validation to support controlled analytical processing.

The governance approach draws on the NIST AI Risk Management Framework and relevant OWASP guidance for LLM applications.

## Evaluation Approach

The project will compare three AI analytics configurations:

| Configuration | Description |
|---|---|
| A — Baseline | AI-generated analytics using approved database schema information |
| B — Metadata-Enriched | Baseline analytics supplemented with approved business glossary and metric definitions |
| C — Governed | Metadata-enriched analytics with enhanced authorization, validation, and result verification controls |

All configurations will retain essential security and execution safeguards.

The planned evaluation includes 50 benchmark cases across five categories: basic analytics, business definitions, complex analytics, authorization and policy, and ambiguous or unsupported requests.

Performance will be assessed using analytical accuracy, authorization compliance, reliability, response latency, estimated model cost, and reproducibility.

## Project Documentation

The following documents establish the approved Milestone 1 architecture and requirements baseline, including the formal acceptance review and evaluation benchmark inventory.

| Document | Description |
|---|---|
| [Project Charter](docs/project-charter.md) | Business problem, project objectives, scope, stakeholders, milestones, and success criteria |
| [System Requirements](docs/requirements.md) | Functional, nonfunctional, data, security, and evaluation requirements |
| [System Architecture](docs/architecture.md) | Logical architecture, component responsibilities, data model, trust boundaries, and architectural decisions |
| [Governance Framework](docs/governance-framework.md) | Data classification, authorization, business glossary governance, AI oversight, and policy controls |
| [Risk Register](docs/risk-register.md) | Risk identification, assessment methodology, mitigation strategies, ownership, and verification planning |
| [Evaluation Plan](docs/evaluation-plan.md) | Benchmark design, experimental configurations, evaluation metrics, scoring, and reproducibility procedures |
| [Milestone 1 Review](docs/milestone-1-review.md) | Milestone 1 acceptance assessment and closure record |
| [Evaluation Benchmark](evaluation/benchmark/test_cases.csv) | Fifty benchmark cases with expected behaviors |
| [Data Dictionary](docs/data-dictionary.md) | Milestone 2 physical data model, entity attributes, relationships, data classifications, authorization mappings, and data-quality rules |
| [Business Metrics](docs/business-metrics.md) | Authoritative business metric definitions, calculation rules, reporting conventions, validation criteria, and benchmark traceability |

The Milestone 1 documents constitute the approved architecture and requirements baseline. The data dictionary begins the Milestone 2 physical design and remains subject to review and implementation verification.

## Project Milestones

| Milestone | Focus | Status |
|---|---|---|
| M1 | Architecture and Requirements | Completed - Design Baseline Approved |
| M2 | Data and Governance Foundation | Conditional Acceptance — Technical Validation Complete; Governance Closure Pending |
| M3 | AI Analytics Implementation | Not Started |
| M4 | Governance and Validation | Not Started |
| M5 | Evaluation and Publication | Not Started |

## Current Project Status

**Milestone 1 — Architecture and Requirements: Completed — Design Baseline Approved**

Milestone 1 established the project charter, requirements, architecture, governance framework, risk register, evaluation plan, and 50-case benchmark inventory.

**Milestone 2 — Data and Governance Foundation: Conditional Acceptance — Technical Validation Complete; Governance Closure Pending**

Implemented components include the SQLite schema, deterministic synthetic-data generator, business metric specifications, provisional reference queries, reference-answer generation, and automated validation tests.

The documented October 24, 2026 local test run passed all 28 tests: 14 data-quality tests and 14 reference-answer tests, with no failures or errors.

Formal Milestone 2 closure remains pending alignment of the restricted-cost access policy, approval or documented deferral of business metric definitions, documentation updates, and retention of reproducibility evidence.

These tests validate the implemented data foundation and provisional reference calculations. They do not establish AI response accuracy, runtime authorization enforcement, or production security.

See the [Milestone 2 Review](docs/milestone-2-review.md) for the acceptance assessment, test evidence, and remaining actions.

**Subsequent work:** AI integration, runtime governance controls, and comparative evaluation.

**Next Phase: Milestone 2 — Data and Governance Foundation**

Planned activities include:

- Refining the physical SQLite data model and data dictionary prior to schema implementation.
- Establishing business-unit authorization mappings and common security safeguards.
- Documenting authoritative business metric calculations.
- Developing a reproducible synthetic enterprise dataset.
- Preparing independently verified benchmark reference queries and expected results.

The AI analytics system has not yet been implemented, and its performance and security targets have not yet been verified.

## Planned Next Steps

1. Align the governance access matrix with AP-09 by documenting restricted product-cost access as denied pending policy approval.
2. Record approval or an explicit approved deferral for each business metric definition, keeping document and database versions consistent.
3. Update remaining outdated project documentation.
4. Regenerate and retain benchmark reference answers, the dataset manifest, checksums, and test evidence; document which generated artifacts are committed or maintained locally.
5. Record the Milestone 2 closure decision after the remaining conditions are addressed.
6. Implement AI analytics integration, runtime authorization and SQL validation controls, and comparative evaluation in subsequent milestones.

## References

- [NIST Artificial Intelligence Risk Management Framework (AI RMF 1.0)](https://doi.org/10.6028/NIST.AI.100-1)
- [NIST Generative Artificial Intelligence Profile (AI 600-1)](https://doi.org/10.6028/NIST.AI.600-1)
- [OWASP Top 10 for Large Language Model Applications](https://genai.owasp.org/llm-top-10/)

---
