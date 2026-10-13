"""The Equipment Reference's write services (ERT-1), one module per concern.

`common` holds the module's errors and what more than one concern uses: the write lock, events, the
context a report is read against, and writing a machine's derived facts. Each concern module imports
`common` and nothing else under `services/` (CODING_STANDARDS.md, "When a service outgrows one file").
The structure's own read, `get_equipment_structure`, stays in `service.py`, which every consumer imports.
"""
