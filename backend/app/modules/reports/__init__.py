"""CRM operational reporting module.

Read-only aggregate views over records owned by the Leads, Opportunities,
Commercial Offers and Work Orders modules. This module owns no tables, adds no
migration, and never writes. It therefore emits no `business_event`: reads are
not meaningful business actions (see AGENTS.md, "Every meaningful business
action should create a business_event").

Cross-module reads here are deliberate and bounded. ADR-017 permits a
consuming surface to read another module's data through a documented read
model; this module is that read model for operational reporting. It reproduces
no business rule and makes no lifecycle decision - every status grouping below
is imported from the owning module's own contract rather than restated.
"""
