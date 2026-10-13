# ERP NFR Full Text Extract

> **Authority banner.** This is a derived full-text extract, not current technical design authority. The formal source `.docx` controls wherever extraction is inaccurate, and controls as evidence of the original source wording generally. Later approved decisions and frozen contracts may refine or supersede the position stated below; where they do, the later decision controls and the text below remains preserved as historical input, not as a contradiction to be silently fixed. Do not treat the body of this extract as current technical design authority.
>
> Source `.docx`: `docs/source/current/requirements/PBL_ERP_Non_Functional_Requirements_2026-05-19.docx`
>
> See also: [`docs/source/SOURCE_DOCUMENT_REGISTER.md`](../../source/SOURCE_DOCUMENT_REGISTER.md), [`docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md`](../../source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md), [`docs/reference/erp-source-extracts/README.md`](README.md).

> Extracted from the source `.docx` using a local PowerShell Open XML text/table extractor because pandoc was not available. The source `.docx` remains the source of truth. Table-heavy, embedded-object, image, header/footer, footnote or complex formatting areas may be imperfect.

ERP – NON-FUNCTIONAL REQUIREMENTS SPECIFICATION

PRIVATE AND CONFIDENTIAL – LIMITED CIRCULATION ONLY

## NON-FUNCTIONAL REQUIREMENTS (NFR)

## Usability, Navigation and User Experience

### Drill-Down Capability

The system shall provide drill-down functionality from summary-level reports, dashboards, and financial statements to originating transactions and associated documents using a consistent navigation structure across modules.

### User-Configurable Reporting

Authorized users shall be able to create, modify, and save operational and financial reports using a built-in drag-and-drop report builder without requiring custom development. The report builder shall support filters, grouping, sorting, calculated fields, and export to standard formats (Excel, PDF, CSV).

### Role-Based User Experience

The system shall provide role-based views and simplified workflows for operational users while retaining full auditability and traceability.

### Efficient Data Entry

The system shall support templates, defaults, bulk upload, copy/replicate functionality, and keyboard-efficient entry.

### Accessibility

The system shall support standard accessibility practices including adjustable scaling and keyboard navigation.

## Security and Access Control

### Authentication

Multi-Factor Authentication (MFA) for privileged users.

Support for SSO (Azure AD, Google, SAML/OIDC or equivalent).

### Authorization

Role-Based Access Control (RBAC) down to module, action, and field level where required.

Data-level scoping (branch/site/project/customer-based restrictions).

### Secure Remote Access

Encrypted access (TLS 1.2+ or higher).

Support secure remote access mechanisms (VPN, Zero Trust, or equivalent).

### Session Management

Configurable session timeout.

Device/session management controls.

### Data Encryption

Encryption in transit.

Encryption at rest for sensitive data including financial and personal data.

## Auditability and Traceability

### Comprehensive Audit Logs

The system shall record:

User ID

Timestamp

Before and after values

Nature of action (create/edit/delete/approve/reject)

### Workflow Traceability

All workflow transitions shall record approver identity, timestamp, status change, and remarks.

### Document Control

Attachments shall be version-controlled or protected against unauthorized modification.

### Searchable Audit Logs

Authorized users shall be able to search audit logs by user, transaction, module, date range, or amount.

## Business Rules and Control Framework

### Configuration-Driven Rules Engine

The ERP shall provide a configuration-driven business rules framework enabling implementation of:

Field validations

Mandatory fields

Cross-field validations

Status transition gating

Approval matrices (amount-based, role-based, branch-based)

Document attachment requirements

Role-based gating controls

### Administrative Control

Rules shall be configurable by authorized administrators without modifying core system code.

Rules shall support versioning and effective dates.

Rules shall be deployable from Test/UAT to Production through controlled promotion.

### Upgrade-Safe Extensions

Where configuration is insufficient, extensions shall be implemented through upgrade-safe mechanisms without modifying core application code.

### Control Classification

Vendor shall classify each major control as:

Configurable

Workflow-configurable

Requires extension

## Integration Architecture

### API-First Architecture

The system shall expose secure, documented APIs and/or webhooks for master data, transactions, and event notifications.

### Decoupled Integrations

All integrations shall be implemented via loosely coupled connectors or middleware without altering core ERP functionality.

### Standard Connectors

Where applicable, the system shall support standard connectors for banking, document management, cloud storage, email, and collaboration platforms.

### Third-Party Systems

The system shall support integration with:

Banking APIs

GPS/Telematics systems

Messaging platforms

IoT platforms

### Integration Monitoring

The system shall provide monitoring dashboards for integrations including retries and failure handling.

## Use of Third-Party Platforms and Standard Components

### Preference for Established Platforms

The solution shall leverage mature third-party platforms where appropriate to ensure standardization, reliability, and faster deployment.

### Avoid Reinventing Existing Capabilities

Where proven solutions exist (workflow engines, reporting tools, automation platforms, identity systems), the vendor shall prioritize integration unless demonstrably inefficient or cost-prohibitive.

### Cost Transparency

Vendor shall clearly disclose licensing, recurring costs, dependency risks, and upgrade considerations for any third-party component proposed.

### Loose Coupling

Third-party integrations shall not tightly bind core ERP logic and must allow replacement without major redesign.

## Performance and Scalability

### Performance Targets

95% of standard interactions shall respond within 2 seconds under normal load.

Heavy reports shall support background execution.

### Scalability

The system shall support multi-branch, multi-year operations without significant performance degradation.

### Peak Load Stability

The system shall maintain stability during high-load cycles (month-end, payroll, billing).

## Availability and Business Continuity

### Uptime

Vendor shall specify uptime SLA (minimum 99.5% monthly recommended).

### Backup

Automated backups and tested restore procedures shall be provided.

### Disaster Recovery

Vendor shall define RPO and RTO parameters.

### Graceful Degradation

If external systems are unavailable, transactions shall queue and retry without data loss.

## Data Integrity and Governance

### Referential Integrity

Strict enforcement of master-data relationships.

### Duplicate Prevention

Controls to prevent duplicate transactions, especially from integrations.

### Precision and Rounding

Support configurable precision and consistent rounding rules.

### Data Retention Configuration

Support configurable retention policies by data category.

## Mobile and Field Readiness

### Mobile Compatibility

Modules designated for field use shall be accessible via mobile or tablet through responsive UI or dedicated applications.

### Field Capture

Support capture of documents, photographs, signatures, and optional location metadata.

### Intermittent Connectivity

Support store-and-forward capability where feasible.

## AI Readiness and Intelligent Assistance

### AI Integration Capability

The system shall support secure APIs and event streaming to enable integration with AI-driven services.

### Context-Based Help

The system shall provide context-sensitive help accessible from each screen.

### Embedded Knowledge Base

The ERP shall support an embedded searchable knowledge repository.

### AI-Assisted Help (Preferred)

Where feasible, the system should support AI-driven assistance capable of:

Natural language interaction

Explaining fields and validations

Guiding users through workflows

Suggesting corrective actions

### Administrative Control

Help content shall be administratively manageable without modifying core code.

## Records Management and Regulatory Compliance

### Records Management Framework

The ERP shall support structured governance of record creation, classification, retention, archival, retrieval, and disposal.

### Retention Policies

Configurable retention rules shall support:

Time-based triggers

Event-based triggers

Controlled archival and disposal

### Legal Hold

The system shall support legal hold capability to suspend deletion where required.

### Immutability

Records requiring regulatory preservation shall be tamper-evident or version-controlled.

### Secure Archival

Archived records shall remain searchable and retrievable.

### Indian Regulatory Compliance Support

The system shall support compliance with applicable Indian regulations, including:

Information Technology Act, 2000

Digital Personal Data Protection Act, 2023

CERT-In directions

Mechanisms shall support data minimization, access controls, consent management (where applicable), and logging of access to personal data.

### Standards Alignment

Records management and security framework should align with:

ISO 15489

ISO 27001

ISO 27701

Vendor shall indicate certification status where applicable.

## Monitoring and Operational Visibility

### System Health Monitoring

Administrative dashboards shall provide visibility into system health and background jobs.

### Error Handling

Clear error reporting and retry mechanisms shall be available.

## Implementation, Migration and Upgrade

### Upgrade Safety

Customizations shall remain upgrade-safe and not require core modification.

### Data Migration

Vendor shall provide methodology and tools for migrating master data, open transactions, and historical records.

### Training and Documentation

Vendor shall provide role-based training and administrative documentation.

### Support SLA

Vendor shall define support response and resolution timelines and escalation matrix.

## General Points

### Validations:- Any deadlines, renewal dates etc... to be validated and alerts to be setup

