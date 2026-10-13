"""The Hiring user test's practice data (TE-7, 2 October 2026): scenario `hiring-uat-seeded`.

Seeded once, on the Hiring test site's own database, the day before testing starts. Every date is counted from that
day, so the guide and the sheets say "in 5 days" rather than a date. Machine numbers, model names and the Plum report
are fixed and invented ("UAT-..."), so the guide can name them; a confirmed Plum report is the whole fleet, so this
seeds only on a database with no machine (the empty-fleet guard), once.

Who does what, as in real life: Sales (sales1) takes each enquiry to a Work Order and fills its lines; the Sales
Manager (manager1) approves the quotations; the Fleet Admin (admin1) brings in Plum's report and records the
machines' papers; Operations (ops1) records what each line needs and allocates. The demo users are retired on the
server afterwards, so testers see these as the practice data's authors.

What it holds, and what each part shows (docs/uat-hiring/PBL_HIRING_UAT_RUNBOOK.md has the full table):

  HU-1  Saurashtra Port Infra - Operations tester 1's Work Order. Three lines at three kinds of site: Dahej (Gujarat),
        Uran (Maharashtra), and contractor work at a central-government refinery near Vadodara (Gujarat). Two 250 t
        crawlers held on line 1 (one with a warning), with kit on two Trips (Own Load); a 100 t all-terrain crane
        whose permit covers Maharashtra only, held on line 2 in Maharashtra; line 3 left for the tester - the same
        crane is refused there, in Gujarat.
  HU-2  Konkan Refinery Services - Operations tester 2's. A crawler replaced before the job (history kept), a crane
        allocated and freed (the line open again), and an 80 t crawler held on a central-government port job whose
        insurance runs out before the job starts and whose sling's examination runs out during it.
  HU-3  Sabarmati Metro Builders - for Sales and Accounts: four lines billed by the month (two periods), the shift,
        the day and the hour; the contract period with an extension; holidays; a line whose site is not yet chosen,
        whose requirement therefore cannot be allocated.
  HU-4  Tapi Power Projects - an offer submitted and awaiting the customer, for the Sales tester to accept and turn
        into a Work Order.

  The fleet - one invented Plum report, confirmed: 250 t crawlers, 100 t all-terrain cranes (one with its carrier),
  80 t crawlers, and a crane whose Plum model name is not mapped; kit held for the 250 t and 80 t models. Their
  papers cover the eligibility rules: road papers "not applicable" on crawlers; a registration that wins over its
  mark; transport and non-transport registrations; a permit for one state and one for all India; a copy missing; a
  first-year PUC mark ending during a job; a renewal recorded without its copy; a sling examined 7 months ago next to
  a hook block examined 7 months ago; machines with nothing recorded, dated as added today, 8 and 15 days ago, so
  every stage of "A certificate not yet recorded" shows on the first day.

  No state or central-government rule is seeded: none is law yet (ELG-1 design, section 2). The Fleet Admin's sheet
  adds a test rule and ends it.

A second invented Plum report (`second_plum_report`) is kept in docs/uat-hiring/ for the Fleet Admin to upload: the
same machines and two more, one with its carrier to pair, and an odd capacity value to read.

Scenario `hiring-uat-fleet` (the user-test restart, 9 October 2026) seeds only what the owner decided the Hiring site
starts with: the same invented fleet and its papers, and PBL's holiday calendar for this year and the next, each
marked complete - no customer, offer, Work Order, requirement or allocation. The testers enter those themselves. It
refuses, writing nothing, where a machine or a waiting Plum report preview is held (the empty-fleet guard) or where
either calendar year is already started.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text

from app.core.database import SessionLocal
from app.shared import business_time

from .actors import resolve_actor
from .builders import (
    add_allocation_trip,
    add_equipment_kit,
    create_holiday_calendar_year,
    add_work_order_contract_extension,
    add_work_order_line_billing_terms_period,
    allocate_machine,
    create_equipment_model,
    create_resource_requirement,
    date_equipment_assets_added,
    equipment_asset_public_id,
    free_allocation,
    invented_plum_report,
    list_kit_on_trip,
    map_equipment_model_name,
    mark_certificate_not_applicable,
    record_equipment_certificate,
    replace_allocation,
    set_work_order_contract_period,
    set_work_order_holidays,
    set_work_order_line_detail,
    upload_and_publish_equipment_report,
)

SCENARIO_NAME = "hiring-uat-seeded"

# The PAN letters the Hiring customers take (customer index 15-18): A-J are the CRM pilot's seeded customers and M
# its hand-typed data sheet (scenarios._uat_pan), so the two data sets never meet on the GST register.
HIRING_CUSTOMER_FIRST_INDEX = 15

COMPETENT_PERSON = "Invented Competent Person (recognition TEST)"
CRAWLER_REASON = "Crawler crane: not equipped to travel on public roads on its own power (invented test mark)."
PUC_FIRST_YEAR_REASON = "First year after registration: PUC needed only from one year after (CMVR r.115(7)) - test mark."

# --- The fleet: one invented Plum report ------------------------------------------------------------------------

PLUM_NAMES = {
    "cc250": "ACME CC 250 CRAWLER",
    "ac100": "ACME AC 100 SUPER",
    "ac100_carrier": "ACME AC 100 CHASSIS",
    "cc80": "ACME CC 80 CRAWLER",
    # Not mapped: the Fleet Admin maps it on the Models page.
    "unmapped": "XCRANE 60 T TRUCK MOUNTED",
}


def _row(number: str, plum_name: str, capacity: str, year: str) -> dict[str, str]:
    """One machine as Plum's report holds it. Registration, chassis, engine, PAN and insurance numbers are invented
    (owner's test-data rule, 25 September 2026)."""
    return {
        "VehicleNo": number,
        "ScheduleMaintanceType": plum_name,
        "VehCategory": "CRANES",
        "Capacity": capacity,
        "CommencedYear": year,
        "Status": "Active",
        "Owner": "PBL UAT (INVENTED)",
        "EngineNo": f"ENG-{number}",
        "ChassisNo": f"CHS-{number}",
        "PAN": "AAAAA0000A",
    }


CC250 = [f"UAT-CC250-0{n}" for n in range(1, 7)]
AC100 = [f"UAT-AC100-0{n}" for n in range(1, 10)]
AC100_CARRIER = "UAT-AC100-01C"
CC80 = ["UAT-CC80-01", "UAT-CC80-02"]
UNMAPPED = "UAT-XC60-01"


def _first_report_rows() -> list[dict[str, str]]:
    return [
        *(_row(number, PLUM_NAMES["cc250"], "250", "2020") for number in CC250),
        *(_row(number, PLUM_NAMES["ac100"], "100", "2019") for number in AC100),
        _row(AC100_CARRIER, PLUM_NAMES["ac100_carrier"], "100", "2019"),
        *(_row(number, PLUM_NAMES["cc80"], "80", "2021") for number in CC80),
        _row(UNMAPPED, PLUM_NAMES["unmapped"], "60", "2014"),
    ]


def first_plum_report() -> str:
    return invented_plum_report(_first_report_rows(), title="Own Vehicle Complete Information Report (Hiring UAT, invented)")


def second_plum_report() -> str:
    """The report the Fleet Admin uploads on their sheet: every machine of the first, and two more - an all-terrain
    crane with its carrier, to pair, and a crawler whose capacity Plum wrote oddly ("250 T"), to read."""
    return invented_plum_report(
        [
            *_first_report_rows(),
            _row("UAT-AC100-10", PLUM_NAMES["ac100"], "100", "2023"),
            _row("UAT-AC100-10C", PLUM_NAMES["ac100_carrier"], "100", "2023"),
            _row("UAT-CC250-07", PLUM_NAMES["cc250"], "250 T", "2024"),
        ],
        title="Own Vehicle Complete Information Report (Hiring UAT, invented, second)",
    )


SECOND_REPORT_FILE = "PBL_HIRING_UAT_PLUM_REPORT_2.csv"


# --- The customers: the CRM pilot's own helper, with Maharashtra and Gujarat sites ------------------------------

HIRING_CUSTOMERS: list[dict[str, Any]] = [
    {
        "key": "hu1_saurashtra_port",
        "stage": "won_with_work_order",
        "name": "UAT-H Saurashtra Port Infra",
        "legal_name": "Saurashtra Port Infra Private Limited",
        "segment": "Infrastructure",
        "industry": "Marine and Port Construction",
        "gst_states": ["24", "27"],
        "addresses": [
            {"address_type_code": "REGISTERED_OFFICE", "address_line1": "Port House, Ashram Road", "city": "Ahmedabad",
             "district": "Ahmedabad", "state": "Gujarat", "postal_code": "380009", "is_primary": True},
            {"address_type_code": "SITE", "address_line1": "Jetty 3 and tank farm, Dahej Port (not a major port)", "city": "Dahej",
             "district": "Bharuch", "state": "Gujarat", "postal_code": "392130", "is_primary": False},
            {"address_type_code": "SITE", "address_line1": "Private container freight station, yard extension", "city": "Uran",
             "district": "Raigad", "state": "Maharashtra", "postal_code": "400702", "is_primary": False},
            {"address_type_code": "SITE", "address_line1": "Contractor work, central PSU refinery shutdown", "city": "Vadodara",
             "district": "Vadodara", "state": "Gujarat", "postal_code": "391320", "is_primary": False},
        ],
        "opportunity_name": "Cranes for jetty works, container yard and refinery shutdown",
        "requirement": "Two 250mt crawler cranes for jetty piling and erection at Dahej; an all-terrain crane on shifts at the Uran container yard; an all-terrain crane for the refinery shutdown near Vadodara.",
        "estimated_value": "7600000.00",
        "offer_title": "Crane hire - Dahej jetty, Uran yard and refinery shutdown",
        "lines": [
            ("Hiring of 250mt crawler crane for jetty piling and erection, monthly basis (2 cranes)", "Crane", "4", "Mon", "1200000.00"),
            ("Hiring of 100mt all-terrain crane at the container yard, shift basis", "Crane", "40", "Shifts", "14000.00"),
            ("Hiring of 100mt all-terrain crane for the refinery shutdown, day basis", "Crane", "20", "Days", "52000.00"),
        ],
    },
    {
        "key": "hu2_konkan_refinery",
        "stage": "won_with_work_order",
        "name": "UAT-H Konkan Refinery Services",
        "legal_name": "Konkan Refinery Services Limited",
        "segment": "Key Account",
        "industry": "Oil and Gas",
        "gst_states": ["27", "24"],
        "addresses": [
            {"address_type_code": "REGISTERED_OFFICE", "address_line1": "Nariman Bhavan, Nariman Point", "city": "Mumbai",
             "district": "Mumbai", "state": "Maharashtra", "postal_code": "400021", "is_primary": True},
            {"address_type_code": "SITE", "address_line1": "Private refinery expansion, plot 7", "city": "Ratnagiri",
             "district": "Ratnagiri", "state": "Maharashtra", "postal_code": "415612", "is_primary": False},
            {"address_type_code": "SITE", "address_line1": "Private pipeline terminal, Hazira", "city": "Surat",
             "district": "Surat", "state": "Gujarat", "postal_code": "394270", "is_primary": False},
            {"address_type_code": "SITE", "address_line1": "Contractor work, berth 5 at a major port", "city": "Mumbai",
             "district": "Mumbai", "state": "Maharashtra", "postal_code": "400001", "is_primary": False},
        ],
        "opportunity_name": "Cranes for refinery expansion, pipeline terminal and berth works",
        "requirement": "A 250mt crawler crane for the refinery expansion, an all-terrain crane at the Hazira terminal, and an 80mt crawler for berth works at a major port.",
        "estimated_value": "5400000.00",
        "offer_title": "Crane hire - Ratnagiri expansion, Hazira terminal, berth 5",
        "lines": [
            ("Hiring of 250mt crawler crane for refinery expansion, monthly basis", "Crane", "2", "Mon", "1250000.00"),
            ("Hiring of 100mt all-terrain crane at the pipeline terminal, day basis", "Crane", "30", "Days", "50000.00"),
            ("Hiring of 80mt crawler crane for berth works, shift basis", "Crane", "45", "Shifts", "11000.00"),
        ],
    },
    {
        "key": "hu3_sabarmati_metro",
        "stage": "won_with_work_order",
        "name": "UAT-H Sabarmati Metro Builders",
        "legal_name": "Sabarmati Metro Builders Private Limited",
        "segment": "Infrastructure",
        "industry": "Metro Rail Construction",
        "gst_states": ["24"],
        "addresses": [
            {"address_type_code": "REGISTERED_OFFICE", "address_line1": "Metro House, C G Road", "city": "Ahmedabad",
             "district": "Ahmedabad", "state": "Gujarat", "postal_code": "380006", "is_primary": True},
            {"address_type_code": "SITE", "address_line1": "Metro viaduct casting yard, Vatva", "city": "Ahmedabad",
             "district": "Ahmedabad", "state": "Gujarat", "postal_code": "382445", "is_primary": False},
            {"address_type_code": "SITE", "address_line1": "Metro station works, Sector 10", "city": "Gandhinagar",
             "district": "Gandhinagar", "state": "Gujarat", "postal_code": "382010", "is_primary": False},
        ],
        "opportunity_name": "Cranes for viaduct and station works",
        "requirement": "Cranes for the viaduct casting yard and station works on monthly, shift, day and hourly terms.",
        "estimated_value": "3900000.00",
        "offer_title": "Crane hire - viaduct casting yard and station works",
        "lines": [
            ("Hiring of 250mt crawler crane at the casting yard, monthly basis", "Crane", "3", "Mon", "1150000.00"),
            ("Hiring of 100mt all-terrain crane for station works, shift basis", "Crane", "30", "Shifts", "13500.00"),
            ("Hiring of 100mt all-terrain crane for launching support, day basis", "Crane", "10", "Days", "48000.00"),
            ("Hiring of 60mt truck-mounted crane on call, hourly basis", "Crane", "80", "Hrs", "2200.00"),
        ],
    },
    {
        "key": "hu4_tapi_power",
        "stage": "submitted_awaiting_response",
        "name": "UAT-H Tapi Power Projects",
        "legal_name": "Tapi Power Projects Limited",
        "segment": "Key Account",
        "industry": "Power Generation",
        "gst_states": ["24"],
        "addresses": [
            {"address_type_code": "REGISTERED_OFFICE", "address_line1": "Power House, Ring Road", "city": "Surat",
             "district": "Surat", "state": "Gujarat", "postal_code": "395002", "is_primary": True},
            {"address_type_code": "SITE", "address_line1": "Unit 3 boiler erection", "city": "Ukai",
             "district": "Tapi", "state": "Gujarat", "postal_code": "394680", "is_primary": False},
        ],
        "opportunity_name": "Crawler crane for boiler erection, Unit 3",
        "requirement": "A 250mt crawler crane for boiler erection at Unit 3, monthly basis, three months.",
        "estimated_value": "3600000.00",
        "offer_title": "Crane hire - boiler erection, Unit 3",
        "lines": [
            ("Hiring of 250mt crawler crane for boiler erection, monthly basis", "Crane", "3", "Mon", "1200000.00"),
        ],
    },
]


# --- Billing terms: complete sets, by basis (as the Slice 7D tests record them) ----------------------------------

def _terms(basis: str, rate: str) -> dict[str, Any]:
    from .scenarios import _MONTHLY_TERMS, _SHIFT_TERMS

    if basis == "MONTH":
        return {**_MONTHLY_TERMS, "normal_rate_amount": Decimal(rate)}
    if basis == "SHIFT":
        return {**_SHIFT_TERMS, "normal_rate_amount": Decimal(rate)}
    if basis == "DAY":
        return {**_SHIFT_TERMS, "billing_uom_code": "DAY", "contracted_hours_per_billing_unit": Decimal("12.00"), "normal_rate_amount": Decimal(rate)}
    if basis == "HOUR":
        # An hourly line has no contracted hours, off days, overtime, breakdown or shift pattern.
        return {
            "billing_uom_code": "HOUR",
            "normal_rate_amount": Decimal(rate),
            "customer_idle_treatment_code": "AS_WORKING_HOURS",
            "minimum_guarantee_code": "NONE",
            "fuel_treatment_code": "NONE",
            "extra_km_allowance_code": "NONE",
            "crew_code": "NONE",
        }
    raise ValueError(basis)


def _first_terms(actor: str, work_order: str, line: str, basis: str, rate: str) -> None:
    from .scenarios import _LINE_ONCE_TERMS

    add_work_order_line_billing_terms_period(
        actor_public_id=actor, work_order_public_id=work_order, line_public_id=line, **_terms(basis, rate), **_LINE_ONCE_TERMS
    )


# --- The scenario ---------------------------------------------------------------------------------------------


def scenario_hiring_uat_seeded(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    from .scenarios import UAT_GST_STATES, _seed_uat_customer

    # Maharashtra is a Hiring customer's GST state too (the CRM pilot's customers have none there).
    UAT_GST_STATES.setdefault("27", "Maharashtra")
    with SessionLocal() as db:
        manager = resolve_actor(db, "manager1")
        admin = resolve_actor(db, "admin1")
        ops = resolve_actor(db, "ops1")
    sales_id, admin_id, ops_id = actor["public_id"], admin["public_id"], ops["public_id"]
    today = business_time.india_today()

    customers = {
        customer["key"]: _seed_uat_customer(
            run_id=run_id, actor=actor, approver_public_id=manager["public_id"], customer=customer,
            index=HIRING_CUSTOMER_FIRST_INDEX + position,
        )
        for position, customer in enumerate(HIRING_CUSTOMERS)
    }
    fleet = _seed_fleet(admin_id=admin_id, today=today)

    hu1 = _work_order_lines(customers["hu1_saurashtra_port"])
    hu2 = _work_order_lines(customers["hu2_konkan_refinery"])
    hu3 = _work_order_lines(customers["hu3_sabarmati_metro"])
    demo = {
        "hu1": _seed_hu1(sales_id=sales_id, ops_id=ops_id, today=today, order=hu1, fleet=fleet),
        "hu2": _seed_hu2(sales_id=sales_id, ops_id=ops_id, today=today, order=hu2, fleet=fleet),
        "hu3": _seed_hu3(sales_id=sales_id, ops_id=ops_id, today=today, order=hu3),
        "hu4_offer_code": customers["hu4_tapi_power"]["commercial_offer"]["offer_code"],
    }
    return {**customers, "hiring_fleet": fleet.pop("records"), "hiring_demo": {**demo, "machines": fleet}}


# --- The restart's pre-load: the fleet and the holiday calendar only (9 October 2026) --------------------------

FLEET_SCENARIO_NAME = "hiring-uat-fleet"

# What a machine shows when no Work Order is seeded: hiring-uat-seeded's words for these three name its own jobs.
_FLEET_ONLY_SHOWS = {
    "UAT-CC250-02": "With a warning for a job running past about 15 days from now: its 12-month examination runs out then",
    "UAT-CC250-04": "With a warning for a job running past about 13 days from now: its 12-month examination runs out then",
    "UAT-CC80-02": "Its insurance runs out in 6 days: a job starting after that cannot have it",
}


class CalendarSeedRefused(RuntimeError):
    """A holiday calendar year the pre-load would start is already started: it is not the run's to replace."""


def calendar_years_to_seed(today: date) -> tuple[int, ...]:
    """This year and the next: the testers' Work Orders start in the coming weeks and run into next year."""
    return (today.year, today.year + 1)


def practice_calendar(year: int) -> list[tuple[str, str, str, list[str]]]:
    """A practice year of PBL's holiday calendar, as (month-day, kind, name, state codes - none for all of India):
    the fixed-date holidays, and Holi and Diwali for the two years the restart needs. PBL sets its own calendar;
    this one is for testing only."""
    holidays = [
        ("01-26", "NATIONAL", "Republic Day", []),
        ("05-01", "FESTIVAL", "Gujarat Day", ["IN-GJ"]),
        ("05-01", "NATIONAL", "Maharashtra Day", ["IN-MH"]),
        ("08-15", "NATIONAL", "Independence Day", []),
        ("10-02", "NATIONAL", "Gandhi Jayanti", []),
        ("12-25", "FESTIVAL", "Christmas", []),
    ]
    moving = {2026: [("03-04", "Holi"), ("11-08", "Diwali")], 2027: [("03-22", "Holi"), ("10-29", "Diwali")]}
    holidays += [(month_day, "FESTIVAL", name, []) for month_day, name in moving.get(year, [])]
    return sorted(holidays)


def require_calendar_years_free(years: tuple[int, ...]) -> None:
    """Refuse, before anything is written, a year someone has already started: seeding would replace their holidays,
    and cleanup would then remove the year as the run's."""
    with SessionLocal() as db:
        started = sorted(
            int(year)
            for year in db.execute(
                text("SELECT calendar_year FROM holiday_calendar_year WHERE calendar_year IN :years").bindparams(
                    bindparam("years", expanding=True)
                ),
                {"years": list(years)},
            ).scalars()
        )
    if started:
        raise CalendarSeedRefused(
            f"Refusing to seed: PBL's holiday calendar for {', '.join(map(str, started))} is already started in this "
            "database, and the pre-load starts this year and the next itself. Run it on a fresh database; nothing "
            "was written."
        )


def require_fleet_calendar_years_free() -> None:
    """The calendar half of the pre-load's guard, which run_scenario checks before it writes anything - the actor
    included (TE-8 round 1)."""
    require_calendar_years_free(calendar_years_to_seed(business_time.india_today()))


def scenario_hiring_uat_fleet(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    """The Hiring site's pre-load for the restart: the invented fleet with its papers and kit, exactly as
    hiring-uat-seeded records it, and this year's and next year's holiday calendar, marked complete. Nothing else.

    Its guards run in run_scenario, before anything is written (the empty fleet, the calendar years). Like every
    scenario, it is not one transaction: a failure part-way leaves what was written with no manifest, so on a test site
    the database is cleared and the pre-load loaded again (docs/deployment/UAT_RESET_2026-10_STEPS.md, step 5). The
    authors it writes as - `sales1`, the manifest's actor, and `admin1` - are created switched off with no password
    when missing (resolve_actor), as for every scenario on a site, and cleanup leaves them: they hold no data of the
    run's and cannot sign in."""
    today = business_time.india_today()
    years = calendar_years_to_seed(today)
    with SessionLocal() as db:
        admin_id = resolve_actor(db, "admin1")["public_id"]
    fleet = _seed_fleet(admin_id=admin_id, today=today)
    fleet["papers"].update(_FLEET_ONLY_SHOWS)
    calendar = [
        create_holiday_calendar_year(actor_public_id=admin_id, calendar_year=year, holidays=practice_calendar(year), complete=True)
        for year in years
    ]
    return {
        "hiring_fleet": {**fleet.pop("records"), "holiday_calendar_years": calendar},
        "hiring_demo": {"machines": fleet, "calendar_years": list(years)},
    }


def _work_order_lines(record: dict[str, Any]) -> dict[str, Any]:
    work_order = record["work_orders"][0]
    sites = [address for address in record["addresses"] if address.get("address_type_code") == "SITE"]
    registered = next(address for address in record["addresses"] if address.get("address_type_code") == "REGISTERED_OFFICE")
    return {
        "public_id": work_order["public_id"],
        "code": work_order["work_order_code"],
        "lines": work_order["line_public_ids"],
        "sites": [site["public_id"] for site in sites],
        "billing_gstin": record["gstins"][0]["public_id"],
        "billing_address": registered["public_id"],
    }


def _line(sales_id: str, order: dict[str, Any], index: int, site: int | None, central: bool | None) -> None:
    set_work_order_line_detail(
        actor_public_id=sales_id,
        work_order_public_id=order["public_id"],
        line_public_id=order["lines"][index],
        site_address_public_id=order["sites"][site] if site is not None else None,
        billing_gstin_public_id=order["billing_gstin"],
        billing_address_public_id=order["billing_address"],
        site_central_government=central,
    )


def _requirement(ops_id: str, order: dict[str, Any], index: int, *, units: int, start: date, end: date, type_code: str, capacity: str) -> dict[str, Any]:
    return create_resource_requirement(
        actor_public_id=ops_id,
        work_order_public_id=order["public_id"],
        line_public_id=order["lines"][index],
        units_required=units,
        required_from=start.isoformat(),
        required_to=end.isoformat(),
        equipment_class_code="CRANE",
        equipment_type_code=type_code,
        capabilities=[("RATED_CAPACITY", Decimal(capacity))],
        crew_operators_required=1,
        crew_helpers_required=1,
    )


def _seed_hu1(*, sales_id: str, ops_id: str, today: date, order: dict[str, Any], fleet: dict[str, Any]) -> dict[str, Any]:
    """Operations tester 1: three kinds of site; two crawlers held with kit on two trips; a crane whose permit covers
    Maharashtra held in Maharashtra; the central-government line in Gujarat left for the tester."""
    wo = order["public_id"]
    set_work_order_contract_period(
        actor_public_id=sales_id, work_order_public_id=wo, contract_start_date=(today - timedelta(days=2)).isoformat(),
        contract_end_basis_code="FIXED_DATE", contract_end_date=(today + timedelta(days=180)).isoformat(),
    )
    _line(sales_id, order, 0, site=0, central=False)   # Dahej, Gujarat
    _line(sales_id, order, 1, site=1, central=False)   # Uran, Maharashtra
    _line(sales_id, order, 2, site=2, central=True)    # central-government refinery, Gujarat
    _first_terms(sales_id, wo, order["lines"][0], "MONTH", "1200000.00")
    _first_terms(sales_id, wo, order["lines"][1], "SHIFT", "14000.00")
    _first_terms(sales_id, wo, order["lines"][2], "DAY", "52000.00")

    start, end = today + timedelta(days=5), today + timedelta(days=60)
    crawlers = _requirement(ops_id, order, 0, units=2, start=start, end=end, type_code="CRAWLER", capacity="200")
    # A short yard job, over before the Gujarat jobs start: the same crane is then free for them, and refused there.
    yard = _requirement(ops_id, order, 1, units=1, start=today + timedelta(days=1), end=today + timedelta(days=6), type_code="ALL_TERRAIN", capacity="80")
    shutdown = _requirement(ops_id, order, 2, units=1, start=today + timedelta(days=10), end=today + timedelta(days=30), type_code="ALL_TERRAIN", capacity="80")

    machines = fleet["machines"]
    first = allocate_machine(actor_public_id=ops_id, requirement_public_id=crawlers["public_id"], machine_public_id=machines["UAT-CC250-01"],
                             planned_from=start, planned_to=end, unit_number=1)
    kit = fleet["kit"]
    version = first["version"]
    for piece, quantity in ((kit["hook_block"], 1), (kit["counterweights"], 8), (kit["sling_ok"], 1)):
        version = list_kit_on_trip(actor_public_id=ops_id, assignment_public_id=first["public_id"], assignment_version=version,
                                   piece_public_id=piece, quantity=quantity)["assignment_version"]
    trip = add_allocation_trip(actor_public_id=ops_id, assignment_public_id=first["public_id"], assignment_version=version,
                               goes_on=start + timedelta(days=2), note="Boom inserts")
    version = trip["assignment_version"]
    for insert in kit["inserts"]:
        version = list_kit_on_trip(actor_public_id=ops_id, assignment_public_id=first["public_id"], assignment_version=version,
                                   piece_public_id=insert, trip_number=trip["trip_number"])["assignment_version"]
    second = allocate_machine(actor_public_id=ops_id, requirement_public_id=crawlers["public_id"], machine_public_id=machines["UAT-CC250-02"],
                              planned_from=start, planned_to=end, unit_number=2)
    in_maharashtra = allocate_machine(actor_public_id=ops_id, requirement_public_id=yard["public_id"], machine_public_id=machines["UAT-AC100-02"],
                                      planned_from=today + timedelta(days=1), planned_to=today + timedelta(days=6))
    return {
        "work_order_code": order["code"],
        "requirements": {
            "crawlers": crawlers["requirement_reference"],
            "yard": yard["requirement_reference"],
            "shutdown_open": shutdown["requirement_reference"],
        },
        "allocations": {"crawler_with_kit": first["reference"], "crawler_with_warning": second["reference"], "permit_maharashtra": in_maharashtra["reference"]},
    }


def _seed_hu2(*, sales_id: str, ops_id: str, today: date, order: dict[str, Any], fleet: dict[str, Any]) -> dict[str, Any]:
    """Operations tester 2: a crawler replaced before the job, a crane allocated and freed, and an 80 t crawler on a
    central-government port job whose papers run out before and during it."""
    wo = order["public_id"]
    set_work_order_contract_period(
        actor_public_id=sales_id, work_order_public_id=wo, contract_start_date=(today - timedelta(days=2)).isoformat(),
        contract_end_basis_code="FIXED_DATE", contract_end_date=(today + timedelta(days=180)).isoformat(),
    )
    _line(sales_id, order, 0, site=0, central=False)   # Ratnagiri, Maharashtra
    _line(sales_id, order, 1, site=1, central=False)   # Hazira, Gujarat
    _line(sales_id, order, 2, site=2, central=True)    # a major port, Maharashtra
    _first_terms(sales_id, wo, order["lines"][0], "MONTH", "1250000.00")
    _first_terms(sales_id, wo, order["lines"][1], "DAY", "50000.00")
    _first_terms(sales_id, wo, order["lines"][2], "SHIFT", "11000.00")

    machines = fleet["machines"]
    start, end = today + timedelta(days=5), today + timedelta(days=60)
    expansion = _requirement(ops_id, order, 0, units=1, start=start, end=end, type_code="CRAWLER", capacity="200")
    held = allocate_machine(actor_public_id=ops_id, requirement_public_id=expansion["public_id"], machine_public_id=machines["UAT-CC250-04"],
                            planned_from=start, planned_to=end)
    replaced = replace_allocation(
        actor_public_id=ops_id, assignment_public_id=held["public_id"], assignment_version=held["version"],
        machine_public_id=machines["UAT-CC250-03"], replace_from=start, reason_code="BREAKDOWN",
        note="Slew ring fault found at the yard inspection; replaced before dispatch.",
    )
    terminal = _requirement(ops_id, order, 1, units=1, start=today + timedelta(days=7), end=today + timedelta(days=40), type_code="ALL_TERRAIN", capacity="80")
    freed_from = allocate_machine(actor_public_id=ops_id, requirement_public_id=terminal["public_id"], machine_public_id=machines["UAT-AC100-01"],
                                  planned_from=today + timedelta(days=7), planned_to=today + timedelta(days=40))
    freed = free_allocation(
        actor_public_id=ops_id, assignment_public_id=freed_from["public_id"], assignment_version=freed_from["version"],
        reason_code="MACHINE_UNAVAILABLE", note="Needed at another site first; to be allocated again.",
    )
    berth_start = today + timedelta(days=12)
    berth = _requirement(ops_id, order, 2, units=1, start=berth_start, end=end, type_code="CRAWLER", capacity="50")
    on_berth = allocate_machine(actor_public_id=ops_id, requirement_public_id=berth["public_id"], machine_public_id=machines["UAT-CC80-02"],
                                planned_from=berth_start, planned_to=end)
    list_kit_on_trip(actor_public_id=ops_id, assignment_public_id=on_berth["public_id"], assignment_version=on_berth["version"],
                     piece_public_id=fleet["kit"]["sling_8t"])
    return {
        "work_order_code": order["code"],
        "requirements": {"expansion": expansion["requirement_reference"], "terminal_open": terminal["requirement_reference"], "berth": berth["requirement_reference"]},
        "allocations": {"replaced": held["reference"], "replacement": replaced["reference"], "freed": freed["reference"], "berth": on_berth["reference"]},
    }


def _seed_hu3(*, sales_id: str, ops_id: str, today: date, order: dict[str, Any]) -> dict[str, Any]:
    """Sales and Accounts: four billing bases (the monthly line in two periods), the contract with an extension,
    holidays, and a line whose site is not chosen - its requirement cannot be allocated until it is."""
    wo = order["public_id"]
    set_work_order_contract_period(
        actor_public_id=sales_id, work_order_public_id=wo, contract_start_date=(today - timedelta(days=30)).isoformat(),
        contract_end_basis_code="FIXED_DATE", contract_end_date=(today + timedelta(days=60)).isoformat(),
        contract_notes="Viaduct casting yard and station works; extension expected for the last span.",
    )
    add_work_order_contract_extension(
        actor_public_id=sales_id, work_order_public_id=wo, new_end_date=(today + timedelta(days=150)).isoformat(),
        received_date=(today - timedelta(days=2)).isoformat(), customer_reference="SMB/EXT/01",
        extension_notes="Extended for the last span and station finishing.",
    )
    set_work_order_holidays(
        actor_public_id=sales_id, work_order_public_id=wo, holidays_answer_code="CALENDAR_CHANGED",
        holidays=[
            ((today + timedelta(days=20)).isoformat(), "FESTIVAL", "Site festival holiday (practice data)"),
            ((today + timedelta(days=45)).isoformat(), "NATIONAL", "National holiday (practice data)"),
        ],
    )
    # Metro works, as a contractor: a central-government site (the hint on the Work Order page names a metro).
    _line(sales_id, order, 0, site=0, central=True)
    _line(sales_id, order, 1, site=1, central=True)
    _line(sales_id, order, 2, site=0, central=True)
    # The hourly line's site is not chosen: its "Central-government site?" stays unanswered too.
    _line(sales_id, order, 3, site=None, central=None)
    lines = order["lines"]
    _first_terms(sales_id, wo, lines[0], "MONTH", "1150000.00")
    from .scenarios import _MONTHLY_TERMS

    add_work_order_line_billing_terms_period(
        actor_public_id=sales_id, work_order_public_id=wo, line_public_id=lines[0], expected_period_count=1,
        expected_latest_term_revision=1, effective_from=today + timedelta(days=31),
        **{**_MONTHLY_TERMS, "normal_rate_amount": Decimal("1210000.00")},
    )
    _first_terms(sales_id, wo, lines[1], "SHIFT", "13500.00")
    _first_terms(sales_id, wo, lines[2], "DAY", "48000.00")
    _first_terms(sales_id, wo, lines[3], "HOUR", "2200.00")
    no_site = _requirement(ops_id, order, 3, units=1, start=today + timedelta(days=8), end=today + timedelta(days=40), type_code="TRUCK_MOUNTED_TELESCOPIC", capacity="50")
    return {"work_order_code": order["code"], "requirements": {"no_site": no_site["requirement_reference"]}}


# --- The fleet and its papers ----------------------------------------------------------------------------------


def _seed_fleet(*, admin_id: str, today: date) -> dict[str, Any]:
    """Models mapped, the first report confirmed (the carrier paired), kit held, and every machine's papers."""
    cc250 = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="CC 250", class_code="CRANE", type_code="CRAWLER",
                                   capabilities=[("RATED_CAPACITY", Decimal("250")), ("MAIN_BOOM_LENGTH", Decimal("72"))])
    ac100 = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="AC 100", class_code="CRANE", type_code="ALL_TERRAIN",
                                   capabilities=[("RATED_CAPACITY", Decimal("100")), ("MAIN_BOOM_LENGTH", Decimal("60"))])
    ac100_carrier = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="AC 100", class_code="CRANE_CARRIER")
    cc80 = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="CC 80", class_code="CRANE", type_code="CRAWLER",
                                  capabilities=[("RATED_CAPACITY", Decimal("80")), ("MAIN_BOOM_LENGTH", Decimal("48"))])
    for key, model in (("cc250", cc250), ("ac100", ac100), ("ac100_carrier", ac100_carrier), ("cc80", cc80)):
        map_equipment_model_name(actor_public_id=admin_id, source_name=PLUM_NAMES[key], model_public_id=model["public_id"])
    report = first_plum_report()
    imported = upload_and_publish_equipment_report(actor_public_id=admin_id, content=report, report_date=today, pairs=[(AC100_CARRIER, AC100[0])])
    numbers = [*CC250, *AC100, AC100_CARRIER, *CC80, UNMAPPED]
    machines = {number: equipment_asset_public_id(number) for number in numbers}

    fits_250, fits_80 = [cc250["public_id"]], [cc80["public_id"]]
    hook = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="CC 250 hook block 250 t", class_code="HOOK_BLOCK", type_code="HOOK_BLOCK",
                                  capabilities=[("RATED_CAPACITY", Decimal("250")), ("WEIGHT", Decimal("3.1"))], fits_model_public_ids=fits_250)
    weight = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="CC 250 counterweight block 10 t", class_code="COUNTERWEIGHT",
                                    type_code="UPPER_COUNTERWEIGHT", capabilities=[("WEIGHT", Decimal("10"))], fits_model_public_ids=fits_250)
    insert = create_equipment_model(actor_public_id=admin_id, maker="ACME", model_name="CC 250 boom insert 9 m", class_code="BOOM_JIB_SECTION",
                                    type_code="MAIN_BOOM_INSERT", capabilities=[("LENGTH", Decimal("9")), ("WEIGHT", Decimal("1.1"))], fits_model_public_ids=fits_250)
    sling_20 = create_equipment_model(actor_public_id=admin_id, maker="LIFTCO", model_name="Sling 20 t", class_code="LIFTING_TACKLE", type_code="SLING",
                                      capabilities=[("RATED_CAPACITY", Decimal("20")), ("WEIGHT", Decimal("0.03"))], fits_model_public_ids=fits_250)
    sling_8 = create_equipment_model(actor_public_id=admin_id, maker="LIFTCO", model_name="Sling 8 t", class_code="LIFTING_TACKLE", type_code="SLING",
                                     capabilities=[("RATED_CAPACITY", Decimal("8")), ("WEIGHT", Decimal("0.02"))], fits_model_public_ids=fits_80)
    holder = CC250[0]
    hooks = add_equipment_kit(actor_public_id=admin_id, kit_model_public_id=hook["public_id"], count=2, from_machine_number=holder)
    [weights] = add_equipment_kit(actor_public_id=admin_id, kit_model_public_id=weight["public_id"], count=12, from_machine_number=holder)
    inserts = add_equipment_kit(actor_public_id=admin_id, kit_model_public_id=insert["public_id"], count=2, from_machine_number=holder)
    slings = add_equipment_kit(actor_public_id=admin_id, kit_model_public_id=sling_20["public_id"], count=2, from_machine_number=holder)
    [sling_8t] = add_equipment_kit(actor_public_id=admin_id, kit_model_public_id=sling_8["public_id"], count=1, from_machine_number=CC80[1])

    papers = _seed_papers(admin_id=admin_id, today=today, machines=machines, hooks=hooks, slings=slings, sling_8t=sling_8t)
    # "A certificate not yet recorded": nothing recorded on these; dated as added 15 and 8 days ago (see the builder).
    date_equipment_assets_added(days_ago_by_asset={machines["UAT-CC250-06"]: 15, machines["UAT-AC100-08"]: 8})

    second = second_plum_report()
    return {
        "machines": machines,
        "kit": {
            "hook_block": hooks[0]["public_id"],
            "hook_block_examined_7_months_ago": hooks[1]["public_id"],
            "counterweights": weights["public_id"],
            "inserts": [item["public_id"] for item in inserts],
            "sling_ok": slings[0]["public_id"],
            "sling_examined_7_months_ago": slings[1]["public_id"],
            "sling_8t": sling_8t["public_id"],
        },
        "kit_references": {
            "hook_blocks": [item["reference"] for item in hooks],
            "counterweights": weights["reference"],
            "inserts": [item["reference"] for item in inserts],
            "slings_20t": [item["reference"] for item in slings],
            "sling_8t": sling_8t["reference"],
        },
        "papers": papers,
        "records": {
            "equipment_models": [cc250, ac100, ac100_carrier, cc80, hook, weight, insert, sling_20, sling_8],
            "equipment_imports": [{"public_id": imported["public_id"]}],
            "equipment_report_fingerprints": [hashlib.sha256(second.encode("utf-8")).hexdigest()],
            "equipment_source_names": [*PLUM_NAMES.values()],
        },
    }


def _years(day: date, count: int) -> date:
    try:
        return day.replace(year=day.year + count)
    except ValueError:  # 29 February
        return day.replace(year=day.year + count, day=28)


def _seed_papers(*, admin_id: str, today: date, machines: dict[str, str], hooks: list[dict[str, Any]], slings: list[dict[str, Any]], sling_8t: dict[str, Any]) -> dict[str, str]:
    """Each machine's papers, and what each shows. Returns, by machine number, what it is there to show."""

    serial = iter(range(1, 1000))

    def paper(
        number_or_id: str, kind: str, *, issued: date, until: date | None, issued_by: str = "Invented Authority (TEST)",
        starts: date | None = None, **extra: Any,
    ) -> None:
        asset = machines.get(number_or_id, number_or_id)
        record_equipment_certificate(
            actor_public_id=admin_id, asset_public_id=asset, kind_code=kind,
            # Invented numbers (owner's test-data rule, 25 September 2026).
            number=f"UAT-CERT-{next(serial):03d}",
            issued_by=issued_by, issued_on=issued, valid_from=starts or issued, valid_until=until, **extra,
        )

    def not_applicable(number: str, kind: str, reason: str = CRAWLER_REASON, until: date | None = None) -> None:
        mark_certificate_not_applicable(actor_public_id=admin_id, asset_public_id=machines[number], kind_code=kind, reason=reason, until=until)

    def examined(number_or_id: str, days_ago: int, *, load_test_days_ago: int = 400) -> None:
        paper(number_or_id, "THOROUGH_EXAMINATION", issued=today - timedelta(days=days_ago), until=None, issued_by=COMPETENT_PERSON)
        paper(number_or_id, "LOAD_TEST", issued=today - timedelta(days=load_test_days_ago), until=None, issued_by=COMPETENT_PERSON)

    def road_papers(number: str, *, registered_as: str, registered_days_ago: int = 1100, insurance_until: int = 300, with_insurance_copy: bool = True) -> None:
        registered = today - timedelta(days=registered_days_ago)
        paper(number, "REGISTRATION", issued=registered, until=_years(registered, 15) - timedelta(days=1), registered_as_code=registered_as, issued_by="Invented RTO (TEST)")
        paper(number, "INSURANCE", issued=today - timedelta(days=60), until=today + timedelta(days=insurance_until), issued_by="Invented Insurance Co (TEST)", with_copy=with_insurance_copy)
        paper(number, "ROAD_TAX", issued=registered, until=None, issued_by="Invented Transport Department (TEST)")

    def puc(number: str, until: int = 150) -> None:
        paper(number, "POLLUTION_UNDER_CONTROL", issued=today - timedelta(days=30), until=today + timedelta(days=until), issued_by="Invented Testing Centre (TEST)")

    def fitness_and_permit(number: str, permit_in: str) -> None:
        paper(number, "FITNESS", issued=today - timedelta(days=100), until=today + timedelta(days=265), issued_by="Invented RTO (TEST)")
        paper(number, "PERMIT", issued=today - timedelta(days=100), until=today + timedelta(days=265), valid_in_code=permit_in, issued_by="Invented RTO (TEST)")

    shows: dict[str, str] = {}
    road = ("REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX")

    # 250 t crawlers: road papers "not applicable" (a crawler is very likely not a motor vehicle).
    for number, exam_days_ago, what in (
        ("UAT-CC250-01", 30, "Can be allocated: road papers not applicable, examinations in date"),
        ("UAT-CC250-02", 350, "Allocated with a warning: its 12-month examination runs out during the job"),
        ("UAT-CC250-03", 45, "Can be allocated"),
        ("UAT-CC250-04", 352, "With a warning: examination runs out during the job (replaced on HU-2)"),
        ("UAT-CC250-05", 40, "Cannot be allocated: a registration saying transport wins over its 'not applicable' mark, so fitness and a permit are needed"),
    ):
        for kind in road:
            not_applicable(number, kind)
        examined(number, exam_days_ago)
        shows[number] = what
    registered = today - timedelta(days=200)
    paper("UAT-CC250-05", "REGISTRATION", issued=registered, until=_years(registered, 5), registered_as_code="TRANSPORT", issued_by="Invented RTO (TEST)")
    shows["UAT-CC250-06"] = "Nothing recorded, added 15 days ago: 'not yet recorded' has reached Admin, Operations and Management"

    # 100 t all-terrain cranes: wheeled, so motor vehicles - no road paper may be marked "not applicable".
    carrier = AC100_CARRIER
    registered = today - timedelta(days=1100)
    paper(carrier, "REGISTRATION", issued=registered, until=_years(registered, 15) - timedelta(days=1), registered_as_code="NON_TRANSPORT", issued_by="Invented RTO (TEST)")
    paper(carrier, "INSURANCE", issued=today - timedelta(days=60), until=today + timedelta(days=300), issued_by="Invented Insurance Co (TEST)")
    puc(carrier)
    paper(carrier, "ROAD_TAX", issued=registered, until=None, issued_by="Invented Transport Department (TEST)")
    examined("UAT-AC100-01", 60)
    shows["UAT-AC100-01"] = "Can be allocated anywhere: non-transport, its road papers on its carrier UAT-AC100-01C"

    road_papers("UAT-AC100-02", registered_as="TRANSPORT")
    puc("UAT-AC100-02")
    fitness_and_permit("UAT-AC100-02", "IN-MH")
    examined("UAT-AC100-02", 60)
    shows["UAT-AC100-02"] = "Transport vehicle, permit for Maharashtra only: can be allocated in Maharashtra, not in Gujarat"

    road_papers("UAT-AC100-03", registered_as="TRANSPORT")
    puc("UAT-AC100-03")
    fitness_and_permit("UAT-AC100-03", "IN")
    examined("UAT-AC100-03", 60)
    shows["UAT-AC100-03"] = "Transport vehicle, all-India permit: can be allocated in any state"

    road_papers("UAT-AC100-04", registered_as="TRANSPORT")
    puc("UAT-AC100-04")
    examined("UAT-AC100-04", 60)
    shows["UAT-AC100-04"] = "Cannot be allocated: registered as transport, no fitness and no permit"

    road_papers("UAT-AC100-05", registered_as="NON_TRANSPORT", with_insurance_copy=False)
    puc("UAT-AC100-05")
    examined("UAT-AC100-05", 60)
    shows["UAT-AC100-05"] = "Cannot be allocated: its insurance is recorded but the copy is not attached"

    road_papers("UAT-AC100-06", registered_as="NON_TRANSPORT", registered_days_ago=120)
    not_applicable("UAT-AC100-06", "POLLUTION_UNDER_CONTROL", reason=PUC_FIRST_YEAR_REASON, until=today + timedelta(days=25))
    examined("UAT-AC100-06", 60)
    shows["UAT-AC100-06"] = "First-year PUC marked not applicable until 25 days from now: a warning for a job running past it"

    road_papers("UAT-AC100-07", registered_as="NON_TRANSPORT", insurance_until=20)
    puc("UAT-AC100-07")
    # The renewal, issued today, takes over in 21 days - recorded without its copy.
    paper("UAT-AC100-07", "INSURANCE", issued=today, starts=today + timedelta(days=21), until=today + timedelta(days=386),
          issued_by="Invented Insurance Co (TEST)", with_copy=False)
    examined("UAT-AC100-07", 60)
    shows["UAT-AC100-07"] = "Insurance runs out in 20 days; the renewal is recorded without its copy, so the cover still ends then"
    shows["UAT-AC100-08"] = "Nothing recorded, added 8 days ago: 'not yet recorded' has reached Admin and Operations"
    shows["UAT-AC100-09"] = "Nothing recorded, added today: 'not yet recorded' reaches Admin only - for the Fleet Admin to record"

    # 80 t crawlers: the reminders' stages.
    for kind in ("REGISTRATION", "ROAD_TAX"):
        not_applicable("UAT-CC80-01", kind)
    paper("UAT-CC80-01", "INSURANCE", issued=today - timedelta(days=30), until=today + timedelta(days=20), issued_by="Invented Insurance Co (TEST)")
    paper("UAT-CC80-01", "POLLUTION_UNDER_CONTROL", issued=today - timedelta(days=30), until=today + timedelta(days=10), issued_by="Invented Testing Centre (TEST)")
    paper("UAT-CC80-01", "THOROUGH_EXAMINATION", issued=today - timedelta(days=30), until=today + timedelta(days=5), issued_by=COMPETENT_PERSON)
    paper("UAT-CC80-01", "LOAD_TEST", issued=today - timedelta(days=400), until=today - timedelta(days=2), issued_by=COMPETENT_PERSON)
    shows["UAT-CC80-01"] = "Papers running out in 20, 10 and 5 days, a load test run out 2 days ago: each reminder at a different stage"
    for kind in ("REGISTRATION", "POLLUTION_UNDER_CONTROL", "ROAD_TAX"):
        not_applicable("UAT-CC80-02", kind)
    paper("UAT-CC80-02", "INSURANCE", issued=today - timedelta(days=30), until=today + timedelta(days=6), issued_by="Invented Insurance Co (TEST)")
    examined("UAT-CC80-02", 30)
    shows["UAT-CC80-02"] = "Held on HU-2's berth job from 12 days ahead: its insurance runs out before the job starts"
    shows[UNMAPPED] = "Its Plum model name is not mapped: judged by the rule for every crane until the Fleet Admin maps it"

    # Kit: a hook block and a sling both examined 7 months ago - the sling's interval is 6 months (IS 12735).
    examined(hooks[0]["public_id"], 60)
    examined(hooks[1]["public_id"], 210)
    examined(slings[0]["public_id"], 30)
    examined(slings[1]["public_id"], 210)
    paper(sling_8t["public_id"], "THOROUGH_EXAMINATION", issued=today - timedelta(days=155), until=None, issued_by=COMPETENT_PERSON)
    paper(sling_8t["public_id"], "LOAD_TEST", issued=today - timedelta(days=155), until=None, issued_by=COMPETENT_PERSON)
    return shows
