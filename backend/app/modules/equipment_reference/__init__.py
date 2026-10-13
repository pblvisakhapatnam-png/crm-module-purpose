"""The platform's Equipment Reference: the canonical equipment structure and the machines described by it
(ADR-037 with its ERT-1 refinement; WRR-001, ERT-1).

Classes, the types within each, and the capabilities that describe them, each capability in one fixed
unit - owned by the platform, serving Hiring and Transportation alike, and owned on the business side by
Fleet's Equipment Master owner. It is the counterpart of `hr_reference`: canonical and provider-neutral. No
Plum field name, Plum row or Plum value reaches a consumer from here.

Two kinds of record live here, and they change differently:

- The structure - version 2 since ERT-1, which added part classes and the crane carrier fitted to a crane -
  is loaded by migrations 20260908_0041 and 20260908_0042 and changes only by migration. Read it through
  `service.py`.
- Models, machines and fitted parts, their corrections, and the readings of Plum's values are managed
  records, written through `services/` by the Fleet Admin (Admin, until that role exists). Machines come
  from Plum's vehicle report through the transformer: `plum_report.py` reads and derives, `plum_source.py`
  implements `ports.py` for Plum, and an import changes nothing until its preview is confirmed. (The port
  and `plum_source.py` are not wired: nothing calls them - see `ports.py`; TB-1 TB1-610.)

Engine and chassis numbers are shown only to EQUIPMENT_IDENTITY_READ (Admin, for now).
"""
