"""Resource Requirements (WRR-001): what a Work Order line needs on site, recorded by Operations.

A requirement asks for a number of units over a period - each unit one item of equipment described
through the platform's Equipment Reference - with the crew needed. It lets planning start before the
Work Order is released. It never changes the Work Order, reserves nothing and assigns nothing.

Work Order facts are read only through the `work_orders` service, never its repository or tables.
"""
