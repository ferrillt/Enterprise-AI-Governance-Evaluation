# Enterprise AI Governance & Evaluation
## Data and AI Governance Framework

**Version:** 1.0  
**Date:** October 24, 2026  
**Status:** Draft — Milestone 1  
**Business Domain:** Enterprise Sales and Operations  
**Related Documents:** [Project Charter](project-charter.md) | [System Requirements](requirements.md) | [System Architecture](architecture.md)

---

## 1. Purpose

This document establishes the data and artificial intelligence (AI) governance framework for the Enterprise AI Governance & Evaluation project.

The framework defines the policies, responsibilities, classifications, authorization controls, metadata standards, and oversight mechanisms required to support secure and reliable AI-generated analytical responses.

The project uses synthetic enterprise sales and operations data to demonstrate how established enterprise data management practices can be incorporated into AI-enabled analytical systems.

The governance framework emphasizes accountability, least-privilege access, analytical consistency, transparency, and measurable risk management.

## 2. Governance Objectives

The framework will support the following objectives:

1. Establish accountability for enterprise data, business definitions, and AI-generated analytical results.
2. Define consistent data classifications and access policies.
3. Enforce role-based authorization independently of LLM-generated instructions.
4. Maintain approved business metadata and calculation definitions.
5. Prevent unauthorized analytical access and unsafe query execution.
6. Establish traceability for analytical requests and governance decisions.
7. Identify, assess, and manage AI-related risks.
8. Support measurable evaluation of governance effectiveness.
9. Document governance limitations, residual risks, and opportunities for improvement.

## 3. Governance Principles

| Principle | Description |
|---|---|
| Accountability | Governance responsibilities and decisions shall have identified owners. |
| Least Privilege | Access shall be limited to the minimum permissions required for authorized activities. |
| Separation of Duties | AI generation, policy enforcement, and data execution shall remain logically separate. |
| Data Quality | Analytical data and business definitions shall be documented and validated. |
| Transparency | Analytical responses shall provide sufficient evidence for independent verification. |
| Traceability | Requests, policy decisions, and evaluation outcomes shall be recorded. |
| Security by Design | Governance and security controls shall be integrated into system architecture. |
| Human Oversight | Significant governance and policy changes shall require authorized human review. |
| Continuous Evaluation | Governance effectiveness shall be measured through repeatable testing. |

## 4. Governance Framework Alignment

The project will use the National Institute of Standards and Technology (NIST) AI Risk Management Framework (AI RMF) as its primary AI governance reference.

The framework will also incorporate applicable security considerations from the OWASP Top 10 for Large Language Model Applications.

### 4.1 NIST AI RMF Alignment

| NIST Function | Project Application |
|---|---|
| Govern | Define governance policies, responsibilities, oversight, and risk accountability. |
| Map | Identify AI use cases, stakeholders, data dependencies, and potential impacts. |
| Measure | Evaluate analytical accuracy, authorization compliance, reliability, latency, and cost. |
| Manage | Implement controls, document residual risks, and respond to evaluation findings. |

The project will use these functions as organizing principles rather than claim formal NIST certification or compliance.

### 4.2 OWASP Security Alignment

Relevant LLM application risks include:

- Prompt injection
- Sensitive information disclosure
- Improper output handling
- Excessive agency
- Insecure downstream tool interactions
- Weak authorization enforcement
- Uncontrolled resource consumption

The threat model will identify applicable risks and map them to architectural controls and verification activities.

## 5. Governance Roles and Responsibilities

The project will simulate an enterprise governance operating model.

| Role | Governance Responsibility |
|---|---|
| Project Sponsor | Establish governance objectives and approve major policy direction. |
| Enterprise AI Solution Architect | Maintain architectural alignment with governance and security requirements. |
| Data Owner | Approve business data usage, classifications, and access boundaries. |
| Data Steward | Maintain metadata, business definitions, and data quality rules. |
| Security Lead | Define authorization requirements and evaluate security controls. |
| AI Evaluation Lead | Maintain benchmarks, evaluate results, and report governance effectiveness. |
| System Administrator | Maintain system configuration without automatically receiving unrestricted business-data access. |
| Business User | Access approved analytical information within assigned permissions. |

For this independent portfolio project, these responsibilities will be simulated by the project author. Governance decisions will be documented through version-controlled records and review checklists.

### 5.1 Responsibility Assignment

| Activity | Accountable Role | Responsible Role |
|---|---|---|
| Approve data classifications | Data Owner | Data Steward |
| Maintain business glossary | Data Owner | Data Steward |
| Define access policies | Security Lead | Enterprise AI Solution Architect |
| Implement policy enforcement | Enterprise AI Solution Architect | System Administrator |
| Approve analytical metric definitions | Data Owner | Data Steward |
| Validate evaluation methodology | AI Evaluation Lead | Enterprise AI Solution Architect |
| Review governance risks | Project Sponsor | Security Lead |
| Maintain audit evidence | Security Lead | System Administrator |

In a production environment, these responsibilities would be assigned to distinct authorized personnel where separation of duties is required.

## 6. Data Governance Model

### 6.1 Data Domains

The initial enterprise data environment will include:

| Data Domain | Description |
|---|---|
| Customer | Customer identifiers, segments, and organizational relationships |
| Sales | Orders, order items, transaction status, and sales amounts |
| Product | Product catalog, categories, and standard costs |
| Organization | Business units, regions, and reporting structures |
| Identity and Access | Simulated users, roles, and authorized business-unit scopes |
| Business Metadata | Approved analytical metrics, definitions, and calculation rules |

### 6.2 Data Ownership

Each data domain shall have a designated logical owner responsible for approving data definitions, classifications, and permitted uses.

Data stewards shall maintain documentation and identify inconsistencies requiring owner review.

Ownership and stewardship assignments will be recorded in the metadata catalog.

## 7. Data Classification Framework

The project will use four data classification levels.

| Classification | Description | Example |
|---|---|---|
| Public | Information approved for unrestricted analytical use | Synthetic product category names |
| Internal | General enterprise operational information | Aggregated synthetic order counts |
| Confidential | Business information requiring authorized access | Customer-level sales transactions |
| Restricted | Information requiring explicit authorization | Simulated sensitive customer or financial attributes |

All data will be synthetic. Classifications will represent enterprise governance scenarios rather than indicate that real confidential information is present.

### 7.1 Classification Rules

- Data elements shall have documented classification labels.
- Access shall be evaluated against the classification and authorized business scope.
- Classification changes shall require documented approval.
- Analytical results shall inherit applicable restrictions when aggregation does not adequately protect restricted information.
- Derived data shall not automatically be considered less sensitive than its source data.
- Unclassified or ambiguously classified data shall be denied until its permitted use is established.

### 7.2 Data Classification Register

| Entity | Default Classification | Governance Consideration |
|---|---|---|
| Customers | Confidential | Customer identifiers and attributes require authorized access. |
| Orders | Confidential | Transaction records are restricted by business-unit scope. |
| Order Items | Confidential | Detailed sales information inherits order-level restrictions. |
| Products | Internal | Product categories may be broadly available; costs may require additional restrictions. |
| Business Units | Internal | Organizational reporting information is subject to approved access. |
| Users | Restricted | Identity and role information shall not be exposed through ordinary analytical queries. |
| Business Metrics | Internal | Approved metric definitions may be shared with authorized analytical users. |

Field-level exceptions will be documented in the detailed data dictionary.

## 8. Access-Control Framework

### 8.1 Authorization Model

The system will use role-based access control (RBAC) combined with business-unit and data-classification restrictions.

Authorization decisions shall use trusted application identity and policy information.

The LLM shall not create, modify, or override user permissions.

The policy engine shall evaluate:

1. Requesting user identity
2. Assigned role
3. Authorized business-unit scope
4. Requested data objects and attributes
5. Applicable classification restrictions
6. Requested analytical operation

Access shall be denied when required authorization information is missing or cannot be validated.

### 8.2 Initial Access-Control Matrix

The following matrix defines proposed access permissions for the synthetic enterprise environment.

| Data or Operation | Sales Analyst | Operations Manager | Finance Analyst | Data Steward | System Administrator |
|---|---|---|---|---|---|
| Aggregated Sales Metrics | Assigned Unit | Assigned Units | Authorized Units | Metadata Only | No Default Access |
| Customer-Level Sales | Assigned Unit | Assigned Units | Authorized Units | No Default Access | No Default Access |
| Product Catalog | Read | Read | Read | Read | Configuration Only |
| Product Standard Costs | Denied | Denied | Denied — Pending Policy Approval | Metadata Only | Denied |
| Business Glossary | Read | Read | Read | Maintain | Configuration Only |
| User Permissions | Denied | Denied | Denied | Denied | Maintain |
| Modify Transaction Data | Denied | Denied | Denied | Denied | Denied |
| Modify Governance Policies | Denied | Denied | Denied | Propose | Controlled Administration |

**Permission definitions:**

- **Assigned Unit:** Access limited to the user's primary authorized business unit.
- **Assigned Units:** Access limited to explicitly assigned business units.
- **Authorized Units:** Access limited to approved financial reporting scopes.
- **Metadata Only:** Access to definitions and documentation, not underlying restricted records.
- **Maintain:** Permission to update designated metadata or configuration through a controlled administrative process.
- **Configuration Only:** Access to system configuration without automatic access to business data.
- **Denied:** No permission to perform the requested operation.

**Restricted Product-Cost Policy — AP-09:** `PRODUCTS.standard_cost_cents` is Restricted. Finance Analyst membership and authorized business-unit assignments do not, by themselves, grant cost access. Because `PRODUCTS` is a shared catalog without direct unit ownership, cost disclosure remains denied until an approved policy defines eligible product-to-unit relationships, explicit column permission, trusted scope enforcement, and negative authorization tests. This is a documented policy disposition, not evidence of an implemented runtime control. See [Data Dictionary](data-dictionary.md) and [Evaluation Benchmark](../evaluation/benchmark/test_cases.csv) (AP-09).

The matrix represents proposed policy behavior. Detailed permissions will be implemented and verified during subsequent milestones.

### 8.3 Row-Level Authorization

Business-unit restrictions shall be enforced through trusted application logic and controlled database access mechanisms.

The initial SQLite implementation will not be represented as providing native enterprise row-level security.

The query execution component shall prevent generated SQL from bypassing business-unit restrictions through joins, subqueries, aggregations, or other query structures.

### 8.4 Column-Level Authorization

Restricted columns shall be excluded from unauthorized query contexts and blocked during SQL validation.

The system shall not rely exclusively on hiding column names from the LLM as an authorization mechanism.

### 8.5 Authorization Failure Handling

When authorization fails, the system shall:

- Reject the affected analytical operation.
- Avoid returning restricted data or revealing protected values through error messages.
- Record the authorization decision.
- Return an appropriate denial message.
- Prevent further execution of the rejected query.

## 9. Business Glossary Governance

### 9.1 Purpose

The business glossary will establish consistent definitions for analytical terminology and calculations.

Approved definitions will be maintained independently of LLM-generated responses.

### 9.2 Initial Business Metrics

| Metric | Proposed Definition | Governance Rule |
|---|---|---|
| Gross Sales | Sum of item quantity multiplied by unit price before discounts | Use documented transaction scope and reporting period. |
| Net Sales | Gross sales less applicable discounts for eligible orders | Exclude canceled orders under the approved calculation policy. |
| Order Volume | Count of distinct orders within the reporting period | Report order status or explicitly define included statuses. |
| Cancellation Rate | Canceled orders divided by total eligible orders | Use a consistent denominator and reporting period. |
| Average Order Value | Net sales divided by the number of eligible orders | Apply the approved net sales and order eligibility definitions. |
| Product Sales | Net sales aggregated by product or category | Respect product, transaction, and business-unit access restrictions. |

The six metric definitions are specified in [Business Metrics](business-metrics.md). They remain `DRAFT` until an explicit simulated Data Owner approval decision is recorded, with version and effective date synchronized to `BUSINESS_METRICS`. Reference calculations are provisional until that approval and independent verification.

### 9.3 Metadata Requirements

Each approved metric shall include:

- Unique metric identifier
- Business name and description
- Calculation expression
- Source entities and attributes
- Inclusion and exclusion rules
- Reporting period and aggregation conventions
- Data owner and steward
- Approval status and version
- Applicable classification and access restrictions

### 9.4 Change Management

Changes to approved business definitions shall be documented and version controlled.

Each change shall identify the affected metric, rationale, approving role, effective date, and potential impacts on analytical results.

Changes affecting benchmark calculations shall trigger review of associated reference queries and expected outcomes.

## 10. Data Quality Governance

The project will establish data quality controls for the synthetic dataset.

| Dimension | Governance Expectation |
|---|---|
| Completeness | Required analytical attributes shall be populated according to defined rules. |
| Validity | Data values shall conform to approved types, ranges, and business constraints. |
| Consistency | Related entities and business calculations shall use consistent definitions. |
| Uniqueness | Primary keys and defined unique identifiers shall not contain unintended duplicates. |
| Referential Integrity | Foreign-key relationships shall reference valid parent records. |
| Timeliness | Reporting dates and transaction periods shall be documented and interpreted consistently. |
| Accuracy | Synthetic records and calculated metrics shall conform to generation rules and reference calculations. |

Data quality checks shall be automated where practical and recorded as part of dataset generation and evaluation.

## 11. AI Governance Controls

### 11.1 Model and Configuration Governance

The system shall document:

- LLM provider and model identifier
- Model version or release identifier when available
- Prompt and context configuration
- Generation parameters
- Approved tools and execution permissions
- Evaluation configuration
- Known limitations and observed failure modes

Changes affecting analytical behavior shall be documented before comparative evaluation.

### 11.2 AI Output Governance

AI-generated SQL and analytical explanations shall be treated as untrusted until validated.

The system shall not assume that a syntactically valid query produces a correct business answer.

Responses shall be evaluated for:

- Analytical correctness
- Consistency with approved business definitions
- Authorized data scope
- Appropriate handling of unsupported questions
- Verifiable calculation evidence
- Absence of fabricated data or unsupported claims

### 11.3 Human Oversight

Human review shall be required for changes to:

- Authorization policies
- Data classifications
- Approved business metric definitions
- Evaluation acceptance criteria
- System security boundaries
- Material architectural assumptions

For this independent project, reviews will be documented as design decisions rather than represented as approvals by an actual enterprise governance board.

## 12. AI Risk Management

The project will maintain a risk register aligned with its architecture and evaluation objectives.

### 12.1 Risk Categories

| Category | Example Risks |
|---|---|
| Analytical | Incorrect calculations, invalid SQL, unsupported conclusions |
| Security | Unauthorized disclosure, prompt injection, policy bypass |
| Governance | Inconsistent metric definitions, unclear ownership |
| Operational | Service failure, latency, unexpected cost |
| Data Quality | Missing records, inconsistent values, invalid relationships |
| Evaluation | Benchmark bias, insufficient test coverage, irreproducible results |

### 12.2 Risk Assessment

Each identified risk shall include:

- Unique risk identifier
- Description and potential impact
- Likelihood assessment
- Impact assessment
- Assigned owner
- Planned mitigation
- Verification activity
- Residual risk assessment
- Current status

The detailed risk register will be maintained in [risk-register.md](risk-register.md).

### 12.3 Risk Response

Risks shall be managed through avoidance, mitigation, transfer where applicable, or documented acceptance.

Critical unresolved security risks shall prevent the affected capability from proceeding to implementation or evaluation until an acceptable response is defined.

## 13. Auditability and Monitoring

### 13.1 Audit Events

The system shall record sufficient information to reconstruct analytical processing and governance decisions.

| Event | Required Information |
|---|---|
| Analytical Request | Request identifier, timestamp, user role, configuration |
| Authorization Decision | Policy identifier, requested scope, allow/deny outcome |
| SQL Validation | Validation outcome, rule identifier, rejection reason |
| Query Execution | Execution status, duration, approved query reference |
| AI Model Invocation | Model identifier, configuration, usage information |
| Evaluation | Benchmark identifier, expected outcome, actual outcome |
| Governance Change | Changed policy or metric, rationale, version, reviewer |

### 13.2 Log Protection

Audit logs shall avoid unnecessary exposure of sensitive data.

The implementation will use synthetic information, minimize recorded content, and separate operational logs from analytical results where appropriate.

Production retention schedules, centralized monitoring, and regulatory recordkeeping requirements are outside the initial project scope.

### 13.3 Monitoring Metrics

Governance monitoring will include:

- Unauthorized request attempts
- SQL validation failures
- Analytical accuracy
- Unsupported request frequency
- Reliability and execution failures
- Response latency
- Token usage and estimated cost
- Data quality exceptions

## 14. Governance Evaluation

The project will assess governance effectiveness through predefined evaluation scenarios.

### 14.1 Evaluation Areas

| Governance Area | Evaluation Approach |
|---|---|
| Authorization | Verify that permitted requests succeed and unauthorized requests are denied. |
| Data Classification | Test access to Internal, Confidential, and Restricted information. |
| Business Definitions | Compare analytical results with approved metric calculations. |
| SQL Validation | Test prohibited operations and unauthorized database references. |
| Prompt Injection | Evaluate attempts to bypass instructions or execution policies. |
| Traceability | Verify that requests and decisions are linked to recorded evidence. |
| Operational Oversight | Assess latency, reliability, usage, and cost reporting. |

### 14.2 Governance Success Measures

The initial governed configuration targets include:

- Zero successful unauthorized data disclosures within the defined security test suite.
- At least 90% analytical accuracy on supported benchmark questions.
- At least 95% successful completion of authorized, supported requests.
- Complete traceability for evaluated requests.
- Documented governance decisions and residual risks.

These targets are proposed acceptance criteria and do not represent measured performance.

## 15. Governance Implementation Phases

| Phase | Governance Deliverables |
|---|---|
| Milestone 1 | Governance framework, classifications, roles, access-control matrix, and risk identification |
| Milestone 2 | Implemented metadata catalog, business glossary, synthetic data classifications, and policy configuration |
| Milestone 3 | Metadata integration and initial governance-aware analytical processing |
| Milestone 4 | Enforced authorization, SQL validation, audit logging, and controlled execution |
| Milestone 5 | Governance effectiveness evaluation, residual risk assessment, and final documentation |

## 16. Requirements Traceability

| Governance Area | Related Requirements |
|---|---|
| Data Classification | DR-04, NFR-07 |
| Access Control | FR-04, GSR-01–GSR-05 |
| Business Glossary | FR-02, DR-07, BR-01–BR-08 |
| SQL Governance | FR-05, FR-06, GSR-03–GSR-05 |
| AI Output Governance | FR-07, FR-09, ER-01–ER-08 |
| Auditability | FR-08, NFR-06, GSR-07 |
| Risk Management | GSR-08–GSR-10 |
| Governance Evaluation | NFR-01–NFR-03, ER-01–ER-08 |

## 17. Governance Verification Criteria

The Milestone 1 governance review will verify that:

1. Governance objectives and principles are documented.
2. Roles, ownership, and accountability are defined.
3. Data domains and classifications are established.
4. An access-control matrix covers at least four user roles.
5. Authorization responsibilities are separated from LLM behavior.
6. Business glossary ownership and change management are defined.
7. Data quality expectations are documented.
8. AI risk categories and assessment responsibilities are established.
9. Audit and monitoring requirements are identified.
10. Governance controls are traceable to system requirements.

Verification confirms the completeness of the governance design. Operational enforcement will be tested during subsequent milestones.

## 18. Known Limitations and Open Items

The initial governance framework has the following limitations:

- Roles and approval authorities are simulated.
- Data classification policies have not yet been implemented.
- The six business metric definitions are documented, but formal approval remains pending.
- SQLite does not provide native enterprise row-level security.
- The policy enforcement mechanism requires implementation and testing.
- Formal regulatory compliance assessment is outside project scope.
- The risk register and 50-case evaluation benchmark are documented. The benchmark contains 30 provisional analytical references and 20 behavioral expectations; runtime evaluation remains pending.
- Governance effectiveness has not yet been measured.

These limitations will be addressed or documented through subsequent project milestones.

## 19. References

National Institute of Standards and Technology. (2023). *Artificial intelligence risk management framework (AI RMF 1.0).* https://doi.org/10.6028/NIST.AI.100-1

National Institute of Standards and Technology. (2024). *Artificial intelligence risk management framework: Generative artificial intelligence profile (NIST AI 600-1).* https://doi.org/10.6028/NIST.AI.600-1

OWASP Foundation. (n.d.). *OWASP Top 10 for large language model applications.* https://genai.owasp.org/llm-top-10/

---

**Document Status:** Milestone 1 governance design baseline; Milestone 2 policy alignment updated. Restricted-cost enforcement, metric approval, and AI/runtime evaluation remain open.

**Milestone 2 evidence:** The user-reported local automated suite passed 28 tests (14 data-quality; 14 reference-answer), zero failures, in 0.246 seconds. These tests do not establish production authorization or LLM behavior. See [Milestone 2 Review](milestone-2-review.md).
