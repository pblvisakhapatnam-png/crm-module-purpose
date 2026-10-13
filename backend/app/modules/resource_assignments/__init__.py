"""Resource Assignment (8A core, RPA-001): own machines allocated to the resource requirements.

An allocation holds one machine for one unit of a requirement over a period, on a stored eligibility decision;
it is replaced or freed, never deleted, and lists the kit going to site with it, trip by trip. Other modules are
read only through their services. Loading this package's service registers the port Resource Requirements reads
coverage and frees machines through (resource_requirements/ports.py).
"""
