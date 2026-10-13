# ERP Functional Specification Full Text Extract

> **Authority banner.** This is a derived full-text extract, not current technical design authority. The formal source `.docx` controls wherever extraction is inaccurate, and controls as evidence of the original source wording generally. Later approved decisions and frozen contracts may refine or supersede the position stated below; where they do, the later decision controls and the text below remains preserved as historical input, not as a contradiction to be silently fixed. Do not treat the body of this extract as current technical design authority.
>
> Source `.docx`: `docs/source/current/requirements/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx`
>
> See also: [`docs/source/SOURCE_DOCUMENT_REGISTER.md`](../../source/SOURCE_DOCUMENT_REGISTER.md), [`docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md`](../../source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md), [`docs/reference/erp-source-extracts/README.md`](README.md).

> Extracted from the source `.docx` using a local PowerShell Open XML text/table extractor because pandoc was not available. The source `.docx` remains the source of truth. Table-heavy, embedded-object, image, header/footer, footnote or complex formatting areas may be imperfect.

ERP – FUNCTIONAL REQUIREMENTS SPECIFICATION

PRIVATE AND CONFIDENTIAL – LIMITED CIRCULATION ONLY

1 Functional Requirements: Transportation Sales & Operations Module 5

1.1 CRM: Lead Ingestion & Opportunity Management 5

1.2 Market Rate Discovery & Vendor Communication 5

1.3 Quotation & PBL T&C Master 6

1.4 Work Order, Addressing & GST Complexity 6

1.5 Fleet Planning & Execution (Own & Hired) 6

1.6 Real-Time Monitoring & Cost Capture 7

1.7 Billing & Profitability analysis 7

2 Functional Requirements: Equipment Hire Module 8

2.1 CRM: Lead & Opportunity Management 8

2.2 Quotation & Commercial Rule Engine 8

2.3 Work Order (Contract) Structure & Governance 9

2.4 Billing Basis & Overtime Logic 10

2.5 Site Execution & Log Sheet Management 11

2.6 Fleet & Crew Operations 12

2.7 Compliance & Logistics Control 12

2.8 Invoicing & Financial Governance 13

3 Functional Requirements: Equipment Maintenance Module 14

3.1 Asset Registry & Component Hierarchy 14

3.2 Preventive Maintenance (PM) & Scheduling 14

3.3 Breakdown Maintenance & Job Cards 15

3.4 Equipment-Specific Maintenance Checklists 15

3.5 Tyre Management System 15

3.6 Maintenance Compliance & Statutory Gating 16

3.7 Inventory & Spares Integration 16

3.8 Reporting & Performance Analytics 17

4 Functional Requirements: Purchase & Inventory Module 18

4.1 Vendor Master & Compliance Governance 18

4.2 Procurement Lifecycle (P2P) 18

4.3 Inventory & Warehouse Management 19

4.4 Consumption & Issue Logic 19

4.5 Financial Integration & Payment Control 19

4.6 Reporting & Analytics 20

5 Functional Requirements: HR & Payroll Module 21

5.1 Employee & Operator Master Data 21

5.2 Site-Based Attendance & Equipment Linkage 21

5.3 Payroll Processing & Calculations 21

5.4 Statutory Compliance & Regulatory Integration 22

5.5 Advances & Reimbursement Management 22

5.6 HR Compliance Gating for Operations 23

5.7 Reporting & Performance Analytics 23

6 Functional Requirements: Accounts & Finance Module 24

6.1 General Ledger & Financial Architecture 24

6.2 Accounts Receivable (Order-to-Cash Financials) 24

6.3 Accounts Payable (Procure-to-Pay Financials) 25

6.4 Banking & The "Bank API" Mandate 25

6.5 Taxation & Statutory Compliance 25

6.6 Costing & Profitability Rule Engine 26

6.7 Budgeting & Financial Approvals 26

6.8 Configurable Reporting & Audit 26

7 Business Rules: 27

7.1 CRM & Sales Governance 27

7.2 Hiring Contract & Hierarchy Rules 27

7.3 Operational Execution & Fuel Governance 27

7.4 Billing & Financial Logic 28

7.5 Compliance & Statutory Controls 28

7.6 Equipment Maintenance & Assets 29

8 Controls: 29

8.1 Hard Gating Controls (Prevention) 29

8.2 Monitoring & Risk Warnings (Early Warning System) 30

8.3 Validation & Reconciliation Controls 30

8.4 Automated Escalation Workflows 31

9 ANNEXURES 32

9.1 Annexure-1 - Leads 32

9.2 Annexure-2 - Opportunities 34

9.3 Annexure-3 Terms and Conditions 37

9.4 Annexure-8 – Employee Master 39

9.5 Annexure-10 – Log Sheet 42

9.6 Annexure-11 48

9.7 Annexure-14 53

9.8 Annexure-15 58

9.9 Annexure-16 59

9.10 Annexure-17 60

9.11 Annexure-20 61

9.12 Annexure-21 61

## Functional Requirements: Transportation Sales & Operations Module

The Transportation module must handle the complete lifecycle of heavy transportation and project logistics, from initial lead ingestion to trip-level profitability analysis.

### CRM: Lead Ingestion & Opportunity Management

#### Automated Lead Ingestion: The ERP must automatically ingest leads from integrated external sources such as Tender Tiger, Projects Today, and mail campaigns.

#### Source Metadata Persistence: The system must capture and store the original communication (email, RFQ, portal submission) and source metadata for every lead.

#### Enquiry Trigger: A Lead must only convert to an Opportunity once a formal enquiry (RFQ, tender document, or recorded verbal confirmation) is received.

#### Structured Activity Logging: For every lead and opportunity, the system must enforce logging of all telephone calls, customer visits (with geo-coordinates), and WhatsApp or email communications.

#### Technical & Regulatory Feasibility: Before quoting, the system must support recording and attaching outcomes of site surveys, route surveys, load dimension validations, and technical risk assessments.

#### Ready to Quote Gating: An opportunity must be marked "Ready to Quote" by an authorized user before operational rate discovery can proceed.

### Market Rate Discovery & Vendor Communication

#### OE Assignment: The system must allow assigning one or more Operational Executives (OEs) to an opportunity to conduct market rate discovery.

#### WhatsApp Vendor Enquiry: The ERP must support sending standardized enquiry templates to vendors via WhatsApp and parsing their responses directly into structured rates within the system.

#### Communication Audit Trail: All vendor negotiations, including broker vs. fleet owner distinctions and multiple rate revisions, must be linked to the Opportunity and preserved for auditing.

#### Margin Validation Controls: The system must automatically compare proposed quotes against predefined margin thresholds; any deviation requires a mandatory workflow approval and a recorded justification.

### Quotation & PBL T&C Master

#### PBL T&C Master Library: The ERP must maintain a master library of PBL’s standard Terms & Conditions, categorized by risk type (Financial, Regulatory, etc.) and business line.

#### Contextual Clause Selection: When preparing a quote, the system must allow users to select relevant T&C clauses while preventing the omission of mandatory clauses without secondary approval.

#### Quote Versioning: The system must archive all previous quote versions and require a mandatory "Reason for Revision" before generating a new quotation number.

### Work Order, Addressing & GST Complexity

#### Hierarchical Address Management: As per the core requirement for multi-site flexibility, the system must support defining unique Billing Addresses and Shipping Addresses at the Work Order Line level.

#### Line-Level T&C Overrides: While defaulting from the header, the system must provide the flexibility to customize T&Cs for each specific transportation line item.

#### Automated GST Determination: The system must automatically determine GST (CGST, SGST, IGST) at the invoice line level based on the Billing GSTIN, Shipping State, and Place of Supply.

#### Risk & Penalty Clause Tracking: Every Work Order must individually track and trigger alerts for deadline-based clauses, including Liquidated Damages (LD), EMD/Security Deposit refunds, and document submission deadlines.

### Fleet Planning & Execution (Own & Hired)

#### Real-Time Fleet Status: The system must track the live status of all own vehicles (Idle, In Transit, Maintenance, Breakdown, or Expected Available based on ETA).

#### Conditional Allocation: The system must allow users to pre-allocate a vehicle to a future trip based on its projected availability at a specific unloading location, with risk visibility if the prior trip is delayed.

#### GC Creation & Cost Center: Every trip must generate a unique Goods Consignment (GC) note, which automatically creates a standalone cost center to capture all trip-related revenue and expenses.

#### Compliance Gating: Dispatch must be programmatically blocked if critical documents (Driving License, RC, Insurance, Fitness Certificate, or E-way bill) are expired or invalid.

#### Hired Vehicle Controls: If a third-party vehicle is hired, the system must capture the reason for hiring and mandate validation of the driver and cleaner documents (DL, Aadhaar) via integration with services like Surepass.

#### Transshipment Workflow: In breakdown scenarios, the system must support a transshipment workflow to assign a new vehicle, transfer the consignment, and preserve a full audit trail of additional costs.

### Real-Time Monitoring & Cost Capture

#### GPS Integration: The ERP must integrate with GPS providers (e.g., FleetX, Traccar) to provide real-time tracking, auto-updated ETAs, and E-way bill expiry alerts at least 2 days prior to expiration.

#### Granular Cost Capture: The system must capture all enroute expenses—including fuel, toll, driver/cleaner payments, port charges, loading/unloading, and detention—and post them directly to the trip cost center.

#### Bank API-Only Payments: Mandatory Control: All driver advances, vendor payments, and settlements must be initiated through the ERP and processed via Bank API only to prevent cash-based transactions.

### Billing & Profitability analysis

#### Proforma & Final Invoicing: The system must support generating periodic or trip-based proforma invoices, ensuring all contractual T&C compliance checks are met before the final invoice is posted.

#### LD & Retention Adjustments: Any Liquidated Damages (LD) or retentions/security deposits must be automatically reflected in the final invoice and the trip P&L.

#### Trip-Level P&L: Each GC must produce an independent P&L report showing Net Margin by calculating Revenue minus Vendor/Fleet costs, advances, and penalty impacts.

#### Aggregated Reporting: The system must support the aggregation of trip profitability data at the Work Order line, Customer, Branch, and Equipment levels.

## Functional Requirements: Equipment Hire Module

### CRM: Lead & Opportunity Management

#### Automated Lead Ingestion: The system must automatically ingest leads from integrated external sources including Probe42, Projects Today, and Tender Tiger.

#### Manual Lead Entry: Marketing or Sales users must be able to manually create leads from walk-ins, phone calls, references, and events.

#### Source Metadata Capture: For every lead, the system must capture source metadata, original communication documents, and timestamps.

NOTE: Refer to Annexure-1 for the comprehensive set of mandatory lead fields.

#### Lead Nurturing & Activity Logging: The system must record all communications (calls, emails, meetings) in a chronological, user-stamped log linked to the lead.

#### Lead Status Lifecycle: The system must enforce a structured lifecycle (New → Contacted → Under Nurturing → Qualified → Lost/Not Interested).

#### Mandatory Loss Remarks: The system must not allow a lead or quotation to be marked "Lost" or "Not Interested" without capturing mandatory user remarks and reason codes.

#### Task & Reminder Management: Users must be able to create tasks (follow-ups, meetings) with automated reminders sent via SMS or WhatsApp.

#### Lead-to-Opportunity Conversion: A lead must only convert to an Opportunity once a formal RFQ or enquiry is received.

#### Opportunity Preparation: The system must support the attachment of site surveys, route surveys, technical feasibility notes, and risk assessments before quoting.

NOTE: Refer to Annexure-2 for the detailed Opportunity data structure.

### Quotation & Commercial Rule Engine

#### Multi-Line Equipment Quoting: The system must allow quoting for multiple equipment items (Cranes, Manlifts, Forklifts) within a single quotation.

#### Contextual T&C Selection: The system must provide a master library of PBL Terms and Conditions, allowing users to select and customize clauses for each quote.

#### Rate Discovery & Benchmarking: The system must allow users to cross-check historical contract rates for similar equipment to ensure competitive pricing.

#### Margin Validation Workflow: The ERP must automatically evaluate quoted margins against predefined thresholds; deviations must trigger mandatory workflow approvals.

#### Quotation Sharing: Only approved quotations may be shared with customers through integrated channels (Email, WhatsApp, MS Teams).

#### NOTE: Refer to Annexure-3 for the library of standard T&Cs used in quotations.

#### Revision & Versioning: Every revision must generate a new version number while maintaining linkage to the original RFQ and audit trail of changes.

### Work Order (Contract) Structure & Governance

#### Multi-Site Line-Level Addressing: Since equipment in one Work Order may be deployed at different locations, the system must support the definition of unique Shipping Addresses and Billing GSTNs at the Work Order Line level rather than only at the header.

#### Line-Level T&C Flexibility: The system must allow individual Terms and Conditions to be customized per equipment line item, with the ability to default header-level T&Cs for speed of entry.

#### Documentation related to invoices:

Work orders specify documents to be submitted with invoices – the system should allow specifying all such documents (e.g. log sheets, employee PF, ESI returns etc.)

If the documents are already available in other parts of the system, it should be possible to map them to the invoice so that they are automatically attached to the invoice before the billing due date

#### PAN-Based Customer Master: The system must maintain a PAN-based hierarchy where multiple GSTN-based billing addresses are maintained as child records under one Parent Customer.

#### Billing Address Lock: Once an E-Invoice is generated for a Work Order line, the associated Billing Address must be locked from further changes.

#### Customers can reject invoices for various reasons; this is usually a rare occurrence but can happen. If an invoice has been rejected by the customer:

If the invoice rejection happens within 24 hours, we are allowed to cancel the invoice in the GST portal and re-upload an invoice; the system should allow cancellation of an invoice, without the need to raise an adjustment credit note.

In case the customer rejects the invoice after 24 hours, the GST portal does not allow us to cancel the invoice but allows us to issue a credit note for the full invoice; the system must enable the creation of this Credit Note.

When an invoice is cancelled / credit note for the full invoice is issued, the system should release the locks enabling the reissue of the invoice on the basis of the log sheet entries, with corrections required by the customer.

In such cases, the system must automatically reverse the accounting entries also

#### Contract Validity Gating: "Contract Valid From" and "Valid To" dates are mandatory; the system must block log sheet generation and billing beyond the validity date unless an approved extension is recorded.

#### Proactive Expiry Alerts: The system must trigger alerts to Sales Managers and Fleet Executives 30 days prior to contract expiry to plan for extensions or de-mobilization.

#### Extension Management: The system must support contract renewals by either extending with same terms (new WO auto-created) or revised terms (mandatory approval required).

#### Credit Limit Gating: The system must validate the customer's credit limit against active contracts and outstanding receivables before allowing a new Work Order to be confirmed.

### Billing Basis & Overtime Logic

#### Four Billing UOMs: The system must support Hour, Shift, Day, and Month-based billing as defined per line item.

#### Hour-Based Billing: Invoices are raised based only on actual working hours; no OT and Breakdown logic applicable. See example below.

#### Shift/Day-Based Billing: Invoices are raised on the basis of per shift/day; OT and Breakdown deductions apply based on contractual hours per shift. See example below.

#### Month-Based:

In Month-based billing, there are two Overtime (OT) Modes:

OT Normal Hours: In this type, if the equipment and operator are made available by PBL to the customer, the number of hours such availability is made are all eligible for OT rates.

OT Engine Hours: In this type, if the equipment and operator are made available by PBL to the customer, but the customer uses fewer hours than the available hours, then the number of hours eligible for OT rates will be the actual hours used based on the hour meter readings – these readings are available both from the log sheet and from the hour meter cloud data. Reconciling the two will be required.

In Month-based billing, the number of contracted hours must be completed before OT can be claimed, i.e.

if the number of hours worked is less than the contracted hours and no OT hours were clocked, then only the worked hours will be paid for, pro-rata.

if the number of hours worked is less than the contracted hours and OT hours were clocked, then the OT hours are set off against the shortfall and IF any OT hours remain after the contracted hour limit is reached, only those hours are considered for OT payment.

#### Different rates may apply for normal working hours, OT hours, breakdown hours and 2nd shift hours (when 2nd shift worked), Holidays – the contract will drive these rates.

#### If the contract specified monthly rates (e,g, Rs. 1 lakh per month), the pro-rated hourly rates will vary month to month based on number of days in the month.

#### Different days in the week may have different working times specified against them.

#### OT rates may be specified as a % of normal rates or a separate rate may be specified.

#### Sometimes even if the work is done on a holiday (weekly off, public holiday etc.), customer may ask us to bill it as OT hours on a normal day due to restrictions placed by their ERP system.

NOTE:- Please see Annexure-10 for various types of Billing calculations based on an example log sheet scenario

### Site Execution & Log Sheet Management

#### Automated Log Sheet Generation: The system must auto-generate a daily log sheet for every active equipment line from the start of the contract until expiry or transshipment.

#### Mandatory Data Capture: Personnel must update actual start/end times, breakdown periods, and opening/closing HMR and Odometer readings daily.

#### Fuel Reconciliation (Customer Scope): If fuel is customer-supplied, the system must calculate Fuel Variance: Expected (Agreed Avg × Working Hours) vs. Actual Consumption.

#### Fuel Deduction Entry: Excess consumption must automatically generate a "Parked Deduction" entry for review by the billing department before final posting.

#### Equipment Transshipment: In the event of an equipment replacement, the system must stop log sheets for the old unit and initiate new sheets for the replacement unit while preserving the audit trail.

#### Extra KM & Crew Charges: The system must auto-calculate charges for extra kilometers beyond contractual limits and for additional operators/helpers beyond the agreed crew scope.

NOTE: Refer to Annexure-10 for the exhaustive log sheet format.

### Fleet & Crew Operations

#### Equipment Assignment History: The system must maintain a complete history of every asset assigned to a Work Order, including registration, HSN, and asset value.

#### Hired Equipment Control: The system must not allow posting of vendor log sheets unless a corresponding Vendor Purchase Order has been posted in the ERP.

#### Crew Assignment & Attendance: The ERP must mandate the assignment of specific crew (from Employee Master) per shift and generate daily attendance sheets for PBL-owned equipment.

#### Crew Change Logic: Attendance generation must automatically stop for old crew and start for newly assigned crew upon transshipment.

### Compliance & Logistics Control

#### Mobilization Integration: Upon Work Order posting, the system must automatically generate a mobilization Transportation order under "PBL Own Loads".

#### Mobilization Reversal Logic: If the equipment exceeds a defined "Minimum Contract Months," the system must auto-generate a credit note against the mobilization invoice.

#### De-Mobilization Integration: Upon completion of a Work Order, the system must, if the Work Order specifies it, automatically generate a de-mobilization Transportation order under "PBL Own Loads".

#### In some work orders, demobilisation is applicable only if the contract concludes before some time frame (say, 1 year) and is not applicable on completion of the time frame. The system should keep track of this and prevent billing if not applicable.

#### HR Compliance Gating: The system must block an invoice from being marked "Ready for Submission" until mandatory HR documents (PF/ESI challans, Wage Register, Bank transfer proof) are uploaded and verified.

#### Gate Pass Submission: Work Order closure must be blocked until all Equipment and Personnel Gate Passes are recorded as returned to the customer.

#### Fuel Exit Reconciliation: The system must record closing fuel quantity at demobilization and block contract closure if fuel reconciliation is pending.

### Invoicing & Financial Governance

#### Draft Invoice Generation: Approved log sheets must automatically convert into draft invoices based on the contract's billing frequency (Weekly/Monthly).

#### Submission Tracking: The system must track how invoices were submitted (Digital, Manual, Portal) and capture physical courier POD details.

#### Multi-Level Escalation: The system must automatically suggest customer escalation contacts based on overdue days: 0–15 (Level 1), 16–30 (Level 2), 30+ (Level 3).

#### Equipment-Level Profitability: The system must support real-time P&L reporting for each equipment line, site, and customer, accounting for revenue, OT, fuel variance, crew costs, and vendor costs.

#### Supporting Documents:- The system must attach all mandatory documents to the draft invoice as defined at the work order level.

Alerts should be sent / workflows should be set up so that users responsible for these documents make them available to the system in a timely manner, before the draft invoice is generated

## Functional Requirements: Equipment Maintenance Module

### Asset Registry & Component Hierarchy

#### Master Asset Registry: The system must maintain a comprehensive registry of all equipment types, including Telescopic Cranes, Crawler Cranes, Manlifts, Trailers, and Prime Movers as defined in Annexure-21.

#### Parent-Child Asset Relationship: The system must support a hierarchical asset structure where a primary machine (e.g., Manitowoc M 2250) is the parent, and major assemblies (Boom Butt, Crawlers, Upperworks) or returnable tools (Tool Box, Sledge Hammers) are child assets.

#### Asset-Specific Metadata: Each asset record must mandatorily capture technical parameters including Make, Model, Year of Mfg, Tank Capacity, and HSN codes as detailed in Annexure-20.

#### Technical Specification Storage: The system must allow for the storage and retrieval of specific load lifting charts, boom lengths, and counterweight configurations for cranes.

#### Fixed Asset & Inventory Linkage: Returnable tools and child items must be linked to the Inventory module to ensure they are tracked during mobilization and de-mobilization.

#### Tools should be tagged as OEM (Supplied by OEM along with Equipment) or General (Purchased Locally)

### Preventive Maintenance (PM) & Scheduling

#### Usage-Based Maintenance Triggers: The system must automatically trigger maintenance alerts based on real-time usage data (HMR/Hours or Odometer/KM) captured from the operational log sheets.

#### Equipment will have child modules: each child module may attract different maintenance patterns. (Example:- Upper Carriage for a crane requires maintenance cycle based on hour meter reading. And lower carriage for a crane requires maintenance cycle based on kilo meter reading)

#### For maintenance items not included in the OEM preventive maintenance check list but required by PBL or PBL’S Client will be added to custom checklists and will be scheduled as per the check list specifications.

#### When service is done by external vendor spares supplied by that vendor while servicing the equipment is listed in a parts invoice by the vendor. These needs to be added automatically to the inventory and issued to the equipment by the ERP or if the software allows non inventory items this is also an acceptable option.

#### All the service items in the preventive, predictive, PBL Checklists, Customer Checklist should be picked from service master.

#### If an item requiring service is under warranty system should alert before allowing service order to be created.

### Predictive Maintenance (PM) & Scheduling

#### Time-Based Maintenance Triggers: The system must support calendar-based scheduling (Daily, Weekly, and Monthly) for specific inspection tasks.

#### Maintenance Code Master: The system must utilize a standardized library of Maintenance Codes defining the "What to Do" (e.g., Engine Oil Level Check) and the "Frequency" (e.g., every 50 hours) as listed in Annexure-14.

#### Auto-Generated PM Work Orders: Upon reaching a usage threshold (e.g., 250 hours), the system must auto-generate a Preventive Maintenance Job Card and assign it to the relevant workshop or site mechanic.

#### Maintenance jobs should be assigned to mechanics and workshops in a balanced manner so that load is equally distributed.

#### It should be possible to assign multiple mechanics to one job

#### It should be possible to map mechanic skill sets and mechanics to service items in the service master.

#### Estimated vs. Actual Time Tracking: For every maintenance code, the system must track the estimated time for completion against the actual time taken by the technician.

### Breakdown Maintenance & Job Cards

#### Breakdown Notification: Site supervisors must be able to log a breakdown directly via the mobile interface, which must immediately alert the Fleet and Maintenance departments.

#### Job Card Lifecycle: Every maintenance activity must be governed by a unique Job Card that tracks the lifecycle from "Reported" to "In Progress" to "Completed" and "Verified."

#### Root Cause Analysis (RCA): The system must require a mandatory "Root Cause" and "Action Taken" entry before a Job Card can be closed.

#### RCA should be closed only by Maintenance HOD

#### Breakdown-Operation Integration: Breakdown start and end times recorded in the Job Card must automatically sync with the Hiring Module to calculate breakdown deductions on customer invoices.

#### Mechanic Assignment: The system must allow for the assignment of Job Cards to specific mechanics or external vendors, tracking their individual productivity and workload.

### Equipment-Specific Maintenance Checklists

#### Dynamic Checklist Logic: The system must present maintenance teams with specialized checklists based on the category of the equipment (e.g., Crawler Crane vs. Manlift) as detailed in Annexure-14. For example:

Crawler Crane Specifics: Checklists for crawler cranes must include critical checks for A-Frame structures, gantry pulley sets, and crawler pad tensioning.

Manlift Specifics: Checklists for manlifts must mandate verification of emergency stop switches, inclination sensors, foot pedals, and platform leveling systems.

Hydraulic Axle Specifics: Maintenance for hydraulic axles must include hub bearing adjustments and brake lining wear checks.

Mobile Crane Specifics: Checklists must include Load Moment Indicator (LMI) calibration, Anemometer functionality, and aviation light status.

#### Digital Signature/Confirmation: Technicians must mark each checklist item as "OK" or "Defective," with the ability to attach photographs of the defect.

### Tyre Management System

#### Tyre Lifecycle Tracking: The system must track every tyre from procurement (GRN) to scrap, utilizing unique Tyre Serial Numbers and RFID tags, if available.

#### Tyre Position Mapping: The system must maintain a visual map of tyre positions for each vehicle type (e.g., PM-FRT-LH, TR-AX1-RH-IN) as defined in Annexure-15(A).

#### NSD Monitoring: The system must support the recording of Non-Skid Depth (NSD) readings during routine inspections.

#### Pressure Monitoring: The system must support the recording of air pressure (PSI) readings during routine inspections.

#### Where available NSD & Pressure readings should be derived from API integration with BPW; where not available manual entry should be facilitated.

#### There are criteria specified by tyre manufactures about NSDs for tyre rotation, re-treading and replacement. Notifications should be setup for all these criteria.

#### PSI Master Validation: Actual PSI readings must be validated against the Recommended PSI Master (e.g., 120-140 PSI for 11.00 x 20 Radial tyres) as listed in Annexure-16.

#### Tyre Action Engine: Based on inspection data, the system must suggest actions such as "Rotate Tyre," "Send for Retreading," or "Scrap."

#### Tyre Costing: The system must track the cost-per-kilometer (CPK) for each tyre brand and model to assist in procurement decision-making.

### Maintenance Compliance & Statutory Gating

#### RTO & Regulatory Tracking: The system must track and trigger alerts for the expiry of Registration Certificates (RC), Fitness Certificates (FC), Road Tax, Pollution (PUC), and National Permits.

#### Load Test Certification: For all lifting equipment, the system must mandate the upload of valid Load Test Certificates and block equipment deployment if the certificate has expired.

#### Note that certifications will be required at both equipment level and component level (fire cylinder, first-aid box etc. & Tools where needed -shackle, slings etc..)

#### Insurance Governance: The system must track insurance policy numbers and validity dates, providing a 30-day look-ahead report for renewals.

#### External Service Validation: For maintenance performed by external vendors, the system must require the upload of the service report and invoice before the Job Card is finalized.

### Inventory & Spares Integration

#### Spares Indenting: Mechanics must be able to raise an indent for spare parts directly from the Job Card.

#### Automatic Stock Check: The system must check the current stock level in the central yard or site-specific store before allowing a purchase requisition.

#### Maintenance-Purchase Workflow: If a part is not in stock, the system must auto-route the requirement to the Purchase department, linked to the specific Job Card and Equipment Number.

#### If a part is available at a different location, this should be visible to the Purchase department decision makers.

#### It should be possible to map spares to service items in the service master.

#### During preventive maintenance expected spares should be automatically indented for issue.

#### Consumption Analysis: The system must provide reports on "High Frequency" vs. "High Value" spares consumed per equipment type.

### Reporting & Performance Analytics

#### Equipment History Ledger: The system must provide a one-click history report for any asset, showing all past preventive maintenance, predictive maintenance, breakdowns, spare parts replaced, and total maintenance costs.

#### MTBF & MTTR: The system must automatically calculate Mean Time between Failures (MTBF) and Mean Time to Repair (MTTR) for the fleet.

#### Workshop Productivity: Reports must show the turnaround time (TAT) for Job Cards by workshop or by mechanic.

#### Maintenance Cost vs. Revenue: The system must provide a report comparing the maintenance cost of an asset against the rental/transportation revenue it generated during the same period.

#### Analytic report to be generated to identify No of service incidents due to preventive, predictive, break down Maintenance and calculation cost and spare usage.

## Functional Requirements: Purchase & Inventory Module

### Vendor Master & Compliance Governance

#### Centralized Vendor Registry: The system must maintain a unified master for all suppliers, service providers, and brokers.

#### Mandatory Document Validation: Vendor creation must be gated by mandatory uploads:

PAN,

GST Certificate,

Bank Details (Cancelled Cheque),

194C Declarations.

MSME Classification with mandate documents with Validity dates.Email address

Contact address

#### Surepass Integration: The system must integrate with Surepass API to automatically validate PAN, GSTN, and Bank Account ownership during the onboarding process.

#### Broker vs. Fleet Owner Distinction: For transportation vendors, the system must distinguish between Brokers (intermediaries) and Fleet Owners (asset owners) to apply correct TDS and payment rules.

#### Multi-Level Contact Management: Each vendor record must support multiple contact persons for different functions (Sales, Accounts, Dispatch) with integrated WhatsApp communication logs.

### Procurement Lifecycle (P2P)

#### Multi-Source Indenting: The system must support Purchase Requisitions (Indents) originating from:

WhatsApp

Email

ERP

#### Maintenance Job Cards: Auto-populated based on specific spare part needs for a machine.

#### Operational Requirements: Mobilization tools or site-specific consumables.

#### Stock Thresholds: Auto-triggering when stock falls below a defined "Re-order Point."

#### Request for Quotation (RFQ): The system must allow users to send digital RFQs to multiple vendors simultaneously via Email or WhatsApp.

#### The system should allow attachments to the RFQ.

#### Comparative Statement (CS): The ERP must generate an automated comparison of received quotes, highlighting the lowest price (L1), delivery lead times, and payment terms.

#### Workflow-Based Approval: Purchase Orders (PO) must follow a hierarchy-based approval workflow defined by the total value and department.

### Inventory & Warehouse Management

#### Multi-Location Inventory: The system must track stock across the Central Yard, Regional Branches, and temporary Site Stores.

#### Goods Receipt Note (GRN): All incoming materials must be recorded via a GRN, which must be gated by a "Three-Way Match" (matching PO quantity, DC quantity, and actual received quantity).

#### GRN should contain fields to record gate entry date and time.

#### GRN should allow entry of Expiry date for items that are flagged as having a shelf-life.

#### Quality Check (QC) Gating: For critical spares (e.g., crane wire ropes, engine components), the system must hold the stock in "Restricted" status until a digital QC clearance is posted.

#### Stock Valuation: The ERP must support Weighted Average or Standard Costing for inventory valuation.

#### Returnable Tools Tracking: As per Annexure-11(B), the system must track "Returnable Tools" (e.g., Sledge Hammers, Socket Sets) issued to specific equipment or sites, ensuring they are returned during de-mobilization.

#### Item master should allow a PBL Item code along with supplier item code

#### Item master should allow local name of the item to be mentioned along with standard item name.

#### Item master should allow shelf life of item to be recorded and track where needed

### Consumption & Issue Logic

#### Issue Against Job Card: Spare parts must only be issued against an active Maintenance Job Card number to ensure accurate equipment-level costing.

#### Consumables vs. Fixed Assets: The system must distinguish between consumables (oil, filters) and serialized fixed assets (tyres, batteries) that require individual lifecycle tracking.

#### Inter-Store Transfers (IST): The system must support the movement of stock between branches using an IST/Delivery Challan workflow with "Transit Stock" visibility.

#### Stock Adjustment & Physical Verification: The system must provide a module for periodic physical stock-taking and generate "Gain/Loss" vouchers with mandatory approval for adjustments.

#### Batteries / Tyres / other spares scrapping as well as selling are described in Annexure-22

### Financial Integration & Payment Control

#### Automated Voucher Creation: Upon GRN and Vendor Invoice posting, the system must automatically generate the Purchase Voucher and update the Ledger.

#### TDS & GST Compliance: The system must automatically calculate TDS (under 194C or 194Q) and validate GST input tax credit (ITC) eligibility.

#### Bank API-Only Payments: Mandatory Control: All vendor settlements must be initiated through the ERP and processed via Bank API only. The system must block and escalate any attempt to record a cash payment for vendor invoices.

#### Advance Management: The system must track advances paid to vendors and ensure they are adjusted/set-off against final invoices before closing the voucher.

### Reporting & Analytics

#### Equipment-Level Consumption: A report showing the total cost of spares and consumables consumed by a specific machine over its lifetime.

#### Vendor Performance Scorecard: Analytics on vendor performance based on lead time, quality rejections, and price stability.

#### Ageing & Dead Stock Analysis: Reporting on inventory that has not moved for 90/180/365 days to prevent capital lock-up.

#### Price Variance Report: A report comparing actual purchase prices against historical averages or quoted prices.

#### Audit schedule report should be created by the system at specified frequencies.

TOOLS REQUIREMENT

How to handle tools allocated with an equipment or employee

Previously we have report on Trip Sheet, Now we needs to map Equipment Master Level.

## Functional Requirements: HR & Payroll Module

### Employee & Operator Master Data

#### The system must maintain a centralized Employee Master for all staff, including specialized roles such as Crane Operators, JLG Operators, Trailer Drivers, and Helpers as listed in Annexure-13

#### The system must integrate with SurePass API to perform real-time validation of Aadhaar, PAN, and Bank Account details during on-boarding.

#### System should allow multiple attachments per employee

#### System should ensure that all onboading tasks are assigned and completed as per checklist in Annexure 23.

#### For all driving and operating staff, the system must mandatorily capture and track License Number, License Type, Badge Number, and Issuing Authority as defined in Annexure-17.

#### The system must provide automated alerts to both the employee and the HR manager 60, 30, and 15 days prior to the expiry of any statutory document (Driving License)

#### The system must support the attachment of digital copies of all KYC documents, training certificates, and medical fitness reports to the employee profile. Covered in Annexure-23

#### The system must maintain a historical log of all previous designations, site deployments and salary revisions for every employee.

### Site-Based Attendance & Equipment Linkage

#### The system must automatically generate daily attendance records based on the "Daily Crew Log" captured in the Equipment Hire and Transportation modules.

#### Attendance for operators and helpers must be programmatically linked to the specific Equipment Number they are assigned to for that shift.

#### The system must support attendance recording for "Idle Time" when a crew member is present but the equipment is undergoing maintenance or is not assigned to a Work Order.

#### For HR purposes, the system must transfer site attendance from the log sheet related to the work order

#### The system must allow site supervisors to mark attendance via a mobile interface with geo-fencing or geo-tagging to ensure the user is physically present at the site.

### Payroll Processing & Calculations

#### The system must support flexible salary structures including components for Basic, HRA, Conveyance, and site-specific allowances (e.g., Food & Accommodation allowance mentioned in Annexure-8.

#### Overtime (OT) for crew members must be automatically calculated based on the net working hours recorded in approved machine log sheets as mentioned in Annexure-9

#### The system must automatically calculate deductions for Professional Tax (PT), Income Tax (TDS), and any disciplinary fines.

#### System should calculate TDS based on regulations

#### System should integrate with KDK/similar Software for TDS Returns and certificate issues.

#### Mandatory Control: All salary and incentive payments must be initiated through the ERP and processed via Bank API (SBI); cash-based salary payments are strictly prohibited.

### Statutory Compliance & Regulatory Integration

#### The system must automatically calculate Provident Fund (PF) contributions based on the latest regulatory percentages.

#### The system must automatically calculate Employee State Insurance (ESI) contributions based on the latest regulatory percentages. Annexure-25

#### The system must generate Electronic Challan-cum-Return (ECR) files for PF and ESI that are ready for upload to the respective government portals. Annexure-25

#### The system must support the generation of Form 16 and other tax-related documents at the end of the financial year.

#### The system must integrate with WhatsApp API to automatically dispatch monthly payslips and Form 16 directly to the employee's registered mobile number.

### Advances & Reimbursement Management

#### The system must allow employees to request advances (e.g., "Driver Advance") directly through the ERP or mobile interface.

#### The system should allow the HOD to request the advance on behalf of an Employee in their team.

#### All approved advances must be auto-deducted from the subsequent month's payroll unless a multi-month recovery plan is defined.

### HR Compliance Gating for Operations

#### The system must act as a "hard gate" for the billing process by verifying that all HR compliance documents for a specific service period are uploaded.

#### Before an invoice can be generated, the system must confirm that PF and ESI challans for the crew assigned to that specific Work Order have been posted.

#### The system must generate a "Monthly HR Compliance Certificate" per customer work order, summarizing wage payments and statutory deposits.

#### If an employee is marked for "Transfer" (moving from one site to another), the system must automatically update the relevant compliance requirements for the new site.

### Reporting & Performance Analytics

#### The system must provide a "Crew Productivity Report" comparing actual machine working hours against paid crew hours.

#### The system must generate monthly attrition reports categorized by role, site, and reason for leaving. Annexure-26

#### The HR dashboard must provide real-time visibility into the "Compliance Health" of all active sites.

#### Authorized users must be able to configure custom reports for headcount, labour cost per project, and OT trends without specialized programming.

## Functional Requirements: Accounts & Finance Module

### General Ledger & Financial Architecture

#### The system must maintain a hierarchical Chart of Accounts (COA) that supports multi-GSTIN with multi-branch and multi-departmental accounting.

#### Each GSTIN should treated as a separate Entity, we can see global level COA, BS, P&L and GSTIN wise COA, BS, and P&L.

#### The system must support the definition of "Cost Centres" for every individual Equipment Asset and every Goods Consignment (GC) Trip.

#### The system must enforce double-entry accounting principles for all automated and manual vouchers.

#### The system must maintain a real-time Trial Balance, Profit & Loss Statement, and Balance Sheet with drill-down capabilities to the source document.

#### Any aggregated data to source document drill-down capabilities

#### The system must allow for the definition of multiple Financial Years with the ability to lock prior periods after audit completion.

### Accounts Receivable (Order-to-Cash Financials)

#### The system must automatically generate Sales Vouchers upon the posting of a Final Invoice from the Hiring or Transportation modules.

#### The system must support a "Parent PAN vs. Child GSTN" hierarchy, ensuring that outstanding balances are trackable at both the individual project level and the aggregate customer level. Outstanding balances required at site, state and consolidated level.

#### The system must provide an automated Credit Limit engine that blocks quotes if the customer's total exposure exceeds their approved limit.

#### The system must track "Retention Money" or "Security Deposits" as separate ledger balances, linked to specific customer contracts.

#### The system must support the processing of Receipts via Bank API integration, automatically setting off payments against the oldest outstanding invoice unless specific set off details are available.

#### The system must provide a multi-stage Ageing Report (0–15, 16–30, 31–45,46-60, 60+ days) with integrated contact details for follow-up.

#### The system should allow an authorized user to configure aging buckets.

### Accounts Payable (Procure-to-Pay Financials)

#### The system must automatically generate Purchase Vouchers upon the approval of a GRN (Goods Receipt Note) or a Hired Vehicle Log Sheet.

#### The system must enforce a "Three-Way Match" (PO vs. GRN vs. Invoice) before any vendor invoice is queued for payment.

#### The system must allow for the recording of Vendor Advances, with a mandatory "Set-off" requirement against the final invoice.

#### The system must maintain a dedicated ledger for Broker payments, tracking loading advances separately from final settlements. Consolidated data based on different slicers like period, vehicle No can draw the report based on the broker slicer.

#### The system must support the management of Diesel Card balances, reconciling monthly statements from providers (e.g., IOCL) against daily fuel logs.

### Banking & The "Bank API" Mandate

#### MANDATORY CONTROL: The system must process all outgoing payments (Vendors, Crew, Salaries, and Advances) through a direct Bank API integration (currently SBI).

#### The system is strictly forbidden from allowing "Cash" as a payment mode for any operational or vendor-related expenditure.

#### The system must provide a real-time Bank Reconciliation Statement (BRS) by fetching daily bank statements via API.

#### The system must require a multi-level approval workflow (Checker/Maker) within the ERP before a payment instruction is transmitted to the bank.

#### The system must automatically capture the UTR (Unique Transaction Reference) number from the bank API and update the relevant voucher upon successful payment.

### Taxation & Statutory Compliance

#### The system must integrate with regulatory portals (via Webtel/KDK) for the automated generation of E-Invoices and E-Way Bills.

#### The system should integrate with 3rd party tools / apps for automatic updating of TDS, GST etc taxation rules and rates.

#### The system must automatically calculate TDS (Tax Deducted at Source) based on the vendor category and the 194C/194Q sections.

#### The system must provide a GST Reconciliation tool to match the "Purchase Register" with GSTR-2A/2B data to ensure Input Tax Credit (ITC) eligibility.

#### The system must support the tax logic for SEZ (Zero-Rated), Export, and BOS (Bill of Supply) transactions as defined in the customer master.

#### The system must generate "Form 16A" for vendors and "Form 16" for employees automatically at the end of the required periods.

#### TDS Rules changes w.e.f FY 2026-27. Get the details from Accounts Department & Update here accordingly. Please see Annexure-24

### Costing & Profitability Rule Engine

#### The system must generate a "Trip Profitability Report" for every GC, subtracting all en-route expenses and vendor costs from the trip revenue.

#### System must capture all operational expenses such as Insurance, Tyre, Battery, Spares, road taxes, repairs, staff expenses, staff salaries, staff incentives, staff OT etc., tagging them against the trip, equipment, customer, work order etc.

#### Income should be tagged whenever the service is closed, to the trip, equipment, customer, work order etc.

#### The system must generate an "Equipment Profitability Report" for every hired and owned asset, factoring in rental revenue, fuel variance, maintenance costs, and crew salaries.

#### The system must capture "Opportunity Cost" for idle equipment based on its average monthly rental value.

#### The system must allow for the allocation of "Indirect Overheads" (Branch rent, Admin salaries) to projects or assets based on a configurable percentage or usage ratio.

### Budgeting & Financial Approvals

#### The system must allow the Finance Department to define "Monthly Expense Budgets" for each branch and site.

#### Any expenditure exceeding the defined budget must trigger an automated escalation to the CFO or Managing Director.

#### The system must support a configurable approval matrix based on the voucher value, document value, document type and voucher type.

### Configurable Reporting & Audit

#### The system must provide a "User-Configurable Report Builder" allowing authorized users to create custom views without coding.

#### The system must maintain a "Global Audit Log" capturing the User ID, Timestamp, and "Before/After" values for every financial transaction modified or deleted. Logs can’t be modified/destroyed.

#### The system must provide a "Compliance Dashboard" showing the status of pending TDS payments, GST filings, and PF/ESI deposits.

#### Ledger printing (layout needs to be designed) or can be user-friendly and can be user self defined.

#### System should allow exports to various formats, at least Excel, csv, pdf.

## Business Rules:

### CRM & Sales Governance

#### Lead Stage Gate: A Lead must only convert to an "Opportunity" upon formal receipt of an enquiry or RFQ.

#### Sales Activity Audit: The system must capture all communications (calls, visits, WhatsApp) in a time-stamped log before a quote can be raised.

#### Mandatory Loss Remarks: Users must provide a reason code and detailed remarks before marking a lead or opportunity as "Lost."

#### Margin Control: Any quotation with a profit margin below the defined threshold requires mandatory workflow approval from management.

#### Quote Versioning: Every revision of a quote must generate a new version number; the "Reason for Revision" must be recorded.

#### T&C Customization: Users must be able to select and customize specific Terms and Conditions from a master library for each quotation line.

### Hiring Contract & Hierarchy Rules

#### Line-Level Independence: The system must support unique Shipping Addresses and Billing GSTNs for each equipment line item within a single Work Order.

#### T&C Flexibility: Each equipment line item must allow for individual customization of T&Cs, though header-level defaults may be applied.

#### Contract Validity Gating: The system must block all operational activities (log sheet generation) once the "Contract Valid To" date is exceeded.

#### Proactive Expiry Alerts: Automated alerts must be sent to Sales and Fleet teams 30 days before a contract expires.

#### Credit Limit Block: Confirmation of a Work Order must be programmatically blocked if the customer’s total exposure exceeds their credit limit.

#### Mobilization Reversal Logic: Reversal rules (e.g., minimum months of deployment) must be calculated and applied at the individual contract line level.

### Operational Execution & Fuel Governance

#### Daily Log Generation: A daily machine log sheet must be generated for every active equipment line item from contract start to expiry.

#### Data Precedence: In the event of a discrepancy between GPS tracking data and a physical log sheet, the customer-signed log sheet shall be the final authority for billing.

#### Transshipment Protocol: When equipment is replaced, the system must terminate the old log sheet series and initiate a new one for the replacement asset effective immediately.

#### Idle Time Billing: Idle hours caused by customer-side issues are billable; these must be recorded on the customer-signed log sheet and treated as working hours.

#### Fuel Sensor Integration: The ERP must integrate directly with fuel sensors (via FleetX, Omnicomm, etc.) to capture real-time consumption data.

#### Fuel Variance Calculation: The system must reconcile "Actual Consumption" (from sensors) against "Expected Consumption" (Agreed Average × Working Hours) to identify deductions.

### Billing & Financial Logic

#### Calculation Precision: All intermediate billing calculations (such as pro-rata month units) must be performed with 9-digit precision.

#### Final Value Rounding: The final invoice amount derived from intermediate calculations must be rounded to 2 decimal places.

#### OT Calculation Modes: The system must support both "Cumulative" (monthly total) and "Available" (daily/shift-based) overtime triggers.

#### Breakdown Deduction Math: Deductions for equipment unavailability must be calculated as Breakdown Hours × Hourly Breakdown Rate.

#### Deduction Offsetting: If enabled in the Work Order, the system must allow users to offset breakdown deductions using same-day overtime hours.

### Compliance & Statutory Controls

#### Bank API Mandate: All payments, including vendor settlements, employee advances, and salaries, must be processed through Bank API integration; cash payments are strictly prohibited.

#### HR Compliance Gating: An invoice cannot be moved to "Ready for Submission" until PF/ESI challans and Wage Registers for the relevant period are verified.

#### Vendor Gating: The system must block the posting of vendor log sheets if no corresponding Vendor Purchase Order is active in the ERP.

#### Surepass Verification: All new vendors and drivers must be validated via Surepass for PAN, GSTN, and Driving License authenticity.

#### TDS Rate Logic: The system should default to the lower applicable TDS rate but must alert the user and allow a manual override if a reason is provided.

#### E-Invoice/E-Way Bill Integration: The system must auto-generate E-Invoices and E-Way Bills through integrated regulatory portals (e.g., Webtel).

### Equipment Maintenance & Assets

#### Usage-Driven PM: Preventive Maintenance work orders must be auto-triggered based on HMR (Hours) or Odometer (KM) data pulled from log sheets.

#### Asset Hierarchy: Major assemblies and returnable tools Annexure-11(A) must be tracked as child assets linked to the parent machine.

#### Tire Lifecycle Management: Every tire must be tracked by a unique ID (Serial/RFID) from GRN through rotations and retreading to scrap.

#### Compliance Tracking: The system must track and alert for the expiry of RTO permits, Fitness Certificates, and Insurance for the entire fleet.

## Controls:

### Hard Gating Controls (Prevention)

#### These controls programmatically block an action until specific criteria are met.

#### Vendor Advance Cap: The system must enforce a hard validation rule preventing any Vendor or Broker Advance from exceeding 90% of the total contracted amount before the "Trip Completion" or "Log Sheet Approval" status is reached.

#### Three-Way Match (Purchase): The system must block the posting of a Purchase Invoice unless the quantity and rate match the Purchase Order (PO) and the Goods Receipt Note (GRN) within a 0% tolerance.

#### Duplicate Invoice Prevention: The system must block the creation of any vendor voucher where the combination of "Vendor Name" and "Vendor Invoice Number" already exists in the database.

#### Address & GST Lock: Once an E-Invoice has been generated for a specific Work Order line, the associated Billing Address and GSTN must be locked to prevent post-facto changes that would invalidate tax compliance.

#### Contract Closure Gate: The system must prevent a Work Order from being marked as "Closed" until the "Return Date" is populated for all Equipment and Personnel Gate Passes associated with that project.

#### Permits such as labor license, work permits etc…as specified in the work order need to be checked and validated before employee can be assigned to a job/site.

### Monitoring & Risk Warnings (Early Warning System)

These controls do not block the user but provide critical information and checklists to prevent future penalties.

#### LD Risk Profiler: The system must continuously monitor contract milestones (e.g., mobilization deadlines, document submission dates). If a milestone is approaching and unfulfilled, the system must:

Trigger a "Risk of LD" warning to the Sales and Operations Managers.

Present a Checklist of Unfulfilled Tasks required to mitigate the Liquidated Damages risk.

#### Maintenance Soft-Lock: During equipment allocation for a new Work Order or Trip, the system must check the Preventive Maintenance (PM) status. If PM is due or overdue, the system must display a Warning message to the user while still allowing the allocation to proceed.

#### E-Way Bill Expiry Monitor: The system must trigger an automated alert to the Fleet Executive and the Driver exactly 48 hours before an active E-Way Bill is set to expire.

#### Asset Documentation Warning: During the allocation process, the system must provide a warning if the "Load Test Certificate" or "Fitness Certificate" is within 15 days of expiry.

### Validation & Reconciliation Controls

These controls ensure data integrity through multi-source cross-checking.

#### Three-Way Fuel Reconciliation: The system must automatically reconcile fuel data from three distinct sources:

Integrated Sensors: Live data from machine fuel sensors.

Supplier API: Automated transaction data from fuel providers (IOCL/HPCL).

Log Sheets: Manual consumption entries signed by the customer.

#### Fuel Discrepancy Escalation: Any discrepancy exceeding a 5% tolerance between the three fuel sources must be automatically flagged and escalated to the Operations Head for manual review.

#### Intermediate Calculation Lock: The system must lock all intermediate pro-rata and unit calculations at 9-digit precision to ensure that final invoice amounts remain consistent and audit-traceable before being rounded to 2 decimals.

#### TDS Deviation Audit: While users may override the default lower TDS rate (as per Business Rule 5.5), the system must require a mandatory "Reason for Deviation" and send an automated notification of the change to the Finance Head.

### Automated Escalation Workflows

These controls trigger communication when specific thresholds are breached.

#### Fuel Variance Deduction Alert: If the fuel sensor integration reports a negative variance (Actual vs. Expected) that exceeds the contractual tolerance, the system must automatically create a "Parked Deduction" alert in the Billing Dashboard for the user to review before invoice finalization.

#### Unsigned Log Sheet Alert: If a log sheet is uploaded without the "Customer Sign-off" checkbox and digital signature attachment, the system must flag the record as "Non-Billable" and alert the Site Supervisor.

#### Payment Exception Report: The system must generate a daily report of any payment attempts that were rejected by the Bank API (SBI) or that were manually flagged for review due to incorrect vendor banking metadata.

## ANNEXURES

NOTE: ANNEXURES ARE FROM EXISTING SOURCES AND SHOULD NOT BE UNDERSTOOD AS SPECIFYING TECHNICAL DESIGN

### Annexure-1 - Leads

General

Lead code : In the application, real objects like customers, vendors, employees etc are called entities. These entities are identified with a unique entity code and the entity name.. This field is mandatory for completion of the form. This field is data is auto sequenced with prefix as "LEA". The data "Readonly".

Lead : In the application, real objects like customers, vendors, employees etc are called entities. These entities are identified with a unique entity code and the entity name.. This field is mandatory for completion of the form. The data is captured using a "TEXT BOX".

Lead Date : This field is mandatory for completion of the form. The data "Readonly".

Cust/Account : While picking this picker (Cust/Account); the application automatically fills data to other fields like : 'Cust/Account', 'Cus/Acc Code', . . The data is captured using a "SQL PICKER".

Lead Status : The current stage of the client lead indicating the lead to customer life cycle. This plays a major role in lead management. This field is mandatory for completion of the form. The data is captured using a "COMBO". Acceptable values are Prospect,Opportunity,Closed

Assigned to Name : The data is captured using a "".

Industry : The industry to which the lead belongs to.. The drop down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "COMBO".

Aprx Prj Cost : Annul turnover of the company. The form field accepts only numeric data. The data is captured using a "TEXT BOX". The data entered in this field is rounded off to two decimals.

Prj Start Dt : The data is captured using a "DATE NORMAL".

Prj End Dt : The data is captured using a "DATE NORMAL".

Sales Person : Sales persons are the executives who book orders. These sales persons / account manager are attached to the specific customer or can be picked while preparing the invoice based on the business model of the company, Based on this sales person or account manager various reports can be derived at. Each of the sales person and account manager are identified by a code and name. This field is mandatory for completion of the form. The data "Readonly".

Lead Owner : This field is mandatory for completion of the form. The data "Readonly".

Lead Source : Lead generated from a specific source. eg: Customer Reference, Partners etc.. The drop down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "COMBO".

Contact Person : Every entity such as customer or vendor or employee etc may have a contact person (some times self). This person may sometimes be associated with an email and mobile number as contact details.. The data is captured using a "TEXT BOX".

Email : Every entity such as customer or vendor or employee etc may have a contact person (some times self). This person may sometimes be associated with an email and mobile number as contact details.. The data is captured using a "EMAIL".

Mobile : Every entity such as customer or vendor or employee etc may have a contact person (some times self). This person may sometimes be associated with an email and mobile number as contact details.. The form field accepts only numeric data. The data is captured using a "SMS".

Phone : The data is captured using a "TEXT BOX".

Remarks : The data is captured using a "TEXT AREA".

Address

City : The city is a part of the address and used for customer, vendors, employees etc to indicate their address, this is followed by district name, state name and country with zip which could be used o indicate the locality. The drop down details are defined in the applicable lookup object. The data is captured using a "OPTIONAL PICKER".

Address1 : The address 1 indicates the building name or street and is generally used for customer, vendors, employees etc to indicate their address, this is followed by address2 which could be used o indicate the locality . The data is captured using a "TEXT BOX".

Address2 : The address 1 indicates the building name or street and is generally used for customer, vendors, employees etc to indicate their address, this is followed by address2 which could be used o indicate the locality . The data is captured using a "TEXT BOX".

Address3 : The data is captured using a "TEXT BOX".

State : The state is a part of the address and used for customer, vendors, employees etc to indicate their address, this is followed by district name, state name and country with zip which could be used o indicate the locality . The data "Readonly".

Country : The country is a part of the address and used for customer, vendors, employees etc to indicate their address, this is followed by district name, state name and country with zip which could be used o indicate the locality . The data is captured using a "TEXT BOX".

Zip : The ZIP ode is a part of the address and used for customer, vendors, employees etc to indicate their address, this is followed by district name, state name and country with zip which could be used o indicate the locality . The data is captured using a "TEXT BOX".

Website : The data is captured using a "URL".

### Annexure-2 - Opportunities

#### HEADER

Opp No : This field is mandatory for completion of the form. This field is data is auto sequenced with prefix as "OPP". The data "Readonly".

Opp Date : This field is mandatory for completion of the form. The data "Readonly".

Lead Name : In the application, real objects like customers, vendors, employees etc are called entities. These entities are identified with a unique entity code and the entity name. This field is mandatory for completion of the form. The data is captured using a "TEXT BOX".

Customer : While picking this picker (Customer); the application automatically fills data to other fields like : 'Parentcode', 'Customer', . . The data is captured using a "SQL PICKER".

Opp Status : .. .. The data is captured using a "COMBO". Acceptable values are RFQ,Not quoted,Quote Raised,Win,Lost,Publish

Opp Close Date : This field is mandatory for completion of the form. The data is captured using a "DATE NORMAL".

RFQ No : This field is mandatory for completion of the form. The data is captured using a "TEXT BOX".

RFQ Date : This field is mandatory for completion of the form. The data is captured using a "DATE NORMAL".

Topic : This field is mandatory for completion of the form. The data is captured using a "TEXTAREA SMALL".

Aprox.Value : The form field accepts only numeric data. The data is captured using a "TEXT BOX".

Rating : The status of any record indicates, if the record is active or inactive for example a customer or a vendor or a product can be in active or inactive stage. In the application only the active records participate in the picking the details into other records and any other business logic. .. This field is mandatory for completion of the form. The data is captured using a "COMBO". Acceptable values are Hot,Warm,Cold

Remarks : On various documents, vouchers, masters and process documents there is a provision for the user to enter the comments or notes or remarks. Sometimes these comments are auto inserted by the application in case of document posting etc... The data is captured using a "TEXT AREA".

Terms & Conditions : This field is mandatory for completion of the form. The data is captured using a "JSON".

Tab: Info

Lead Source : The data is captured using a "COMBO". Acceptable values are Advertisement, Employee Referral, External Referral, Customer Referral, Partner, Marketing Agency, Public Relations, Seminar - Internal, Seminar - External, Trade Show,Web,Word of mouth,Website,Phone Enquiry, Purchased List, Sales Team,Campaign,Management,Other,ATOM

Sales Person : While picking this picker (Sales Person); the application automatically fills data to other fields like : 'Sales Person', . . This field is mandatory for completion of the form. The data is captured using a "SQL PICKER".

Acc Manager : While picking this picker (Acc Manager); the application automatically fills data to other fields like : 'Acc Manager', 'Acc Manager Name', . . This field is mandatory for completion of the form. The data is captured using a "SQL PICKER".

Industry : .. .. The drop down details are defined in the applicable lookup object. The data is captured using a "COMBO".

#### LINES

Cust/Lead : This field is mandatory for completion of the form. The data "Readonly".

Opp No : This field is mandatory for completion of the form. The data "Readonly".

Service Name : While picking this picker (Service Name); the application automatically fills data to other fields like : 'Service Name', 'Service Code', 'UOM', . . This field is mandatory for completion of the form. The data is captured using a "SQL PICKER".

Origin : While picking this picker (Origin); the application automatically fills data to other fields like : 'Origin', . . The drop down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "SQL PICKER".

Loading Points: The drop-down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "TEXTAREA SMALL".

Destination: While picking this picker (Destination); the application automatically fills data to other fields like : 'Destination', . . The drop down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "SQL PICKER".

Unloading Points: The drop down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "TEXTAREA SMALL".

Type of Movement: This field is mandatory for completion of the form. The data is captured using a "COMBO". Acceptable values are One Way,Round Trip

Type Of Material: This field is mandatory for completion of the form. The data is captured using a "TEXTAREA SMALL".

Tentative Start : This field is mandatory for completion of the form. The data is captured using a "DATE NORMAL".

Tentative End : This field is mandatory for completion of the form. The data is captured using a "DATE NORMAL".

Quote Date : The data is captured using a "DATE NORMAL".

Type of Vehicle : While picking this picker (Type of Vehicle); the application automatically fills data to other fields like : 'Type of Vehicle', . . The drop down details are defined in the applicable lookup object. This field is mandatory for completion of the form. The data is captured using a "SQL PICKER".

Min Garnt In MT : The form field accepts only numeric data. This field is mandatory for completion of the form. The data is captured using a "TEXT BOX". The data entered in this field is rounded off to two decimals.

UOM : The data "Readonly".

Quantity : The form field accepts only numeric data. This field is mandatory for completion of the form. The data is captured using a "TEXT BOX". The data entered in this field is rounded off to two decimals.

Enquiry From OE : This field is mandatory for completion of the form. The data is captured using a "MULTI SELECT".

Tab: Marketing

Mkt Rate : The form field accepts only numeric data. The data is captured using a "TEXT BOX".

Supplier : While picking this picker (Supplier); the application automatically fills data to other fields like : 'Supplier', . . The data is captured using a "SQL PICKER".

Remarks : The data is captured using a "TEXT AREA".

Dimension : This field is mandatory for completion of the form. The data is captured using a "JSON".

Measurement : The data "Readonly".

Form Validations

 Quote Margin Should More than or Equal to Least Margin

### Annexure-3 T&C (Transportation)

Terms & Conditions

1. Transportation charges: -The above-said transportation charges are fixed and applicable GST will be 18% charged extra on the service amount. 2. Scope of Loading & Unloading: -Loading and Unloading shall be arranged by you at your cost. 3. Transit Insurance: -Transit insurance shall be arranged by you at your cost. 4. Transit Documents: -All mandatory transit documents for movement of cargo will be provided by you. 5. Free Time:-We will allow free time at loading and Unloading Points as mentioned above. 6. Detention Charges: -after free time detention charges will be charged per day or part of a day. The rates are as mentioned above. 7. Settlement of bills:-Payments should be made within 30 Days on submission of bills. 8. En-route/RTO Charges:-You should reimburse any RTO charges/ Penalties or any other similar expenses incurred up on submission of receipts. 9. Billing Address:-We will raise the invoice at the address mentioned in the work order. So kindly confirm the billing address in the work order. If not provided we will raise the invoice as per place of supply rules of GST. 10. Account Statement:-You shall submit a statement of our account at the end of this contract or at the end of financial year whichever is earlier. 11. Consignor & Consignee address with contact person name email ID & cell No:-You shall provide the relevant information for smooth execution of the transportation for auto alerts of SMS & Emails updating stage wise information to the concerned. 12. This quote is valid Upto:-3 days from the date of submission 13. Other Terms:-RTA challans including 14.Tolerance %:-You shall allow 0.50% Tolerance on the Gross weight of loaded quantity and any deduction will be accepted beyond 0.5 % tolerance limit only.

Note:- 1) In case deviation in dimensions, weight, loading point or unloading point, price will be renegotiated accordingly.

2) PBL will issue only digitally signed invoices in case if you need physical invoices Rs. xxxxx will be charged additionally.

3) In case of any services issues please mail to customersupport@pbltransport.co.in.

NOTE:- The above Terms and Conditions are dynamic and will be updated at the time of raise the quote.

T&C (Hiring)

TERMS AND CONDITIONS:

Equipment Hire charges: Hire charges for 100 MT Crawler Crane shall be Rs.xxxxx/-

Mobilization Charges:- It is your scope and shall be charged Rs.xxxx/- for entire mobilization.

Demobilization Charges:- If equipment works beyond xx Months then No demobilisation charges lived, on other hand Rs.xxxxx will be charged at the time of De-Mobilization of the crane.

GST:- Applicable GST on Tax invoice shall be charged as per GST rules..

Working hours: The above said monthly charges is for Normal working days excluding Sundays and holidays comprising of 10 Hours working per day Excluding 1 Hour lunch break. Break down hours shall be deducted on pro-rata basis.

OT Charges:- Beyond the stiupulated work hours as per “Working Hours” Clause, we will charge Rs.xxx per hour as Extra Over Time Charge.

Food & Accommodation: We will provide food & accommodation to crew at our own cost.

Diesel: Diesel will be supplied by you on free basis @ xxx Ltrs per hour and in marching @ xxx Ltrs per hour. If it consumes more than this then the rate of the diesel will be charged by you as a Debit Note.

Advance: You have to pay an advance of Rs.2, 50,000/- after commissioning of the crane at site.

> Annexures 8 to 20 and 22 to 26 are not part of this copy. They cover Equipment Hiring, HR, maintenance, tyres and finance, which the CRM does not need. PBL keeps the full specification.

### Annexure-21:- Type of Equipment

Type of Equipment

Telescopic Cranes

Mobile Tower Cranes

Crawler Cranes

Derrick

Excavator

Farana

Forklift

Four Wheeler

Hydraulic Axles

Manlifts

Palfinger

Puller

Trailer Bed

Prime Movers

Two Wheelers
