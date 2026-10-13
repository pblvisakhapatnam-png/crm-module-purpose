from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import (
    get_database_settings_summary,
    get_foundation_table_status,
    verify_database_connection,
)
from app.core.errors import handle_database_error, handle_request_validation_error
from app.modules.accounts.routes import router as accounts_router
from app.modules.commercial_offers.routes import router as commercial_offers_router
from app.modules.documents.routes import router as documents_router
from app.modules.eligibility.routes import router as eligibility_router
from app.modules.equipment_reference.routes import router as equipment_reference_router
from app.modules.events.errors import EventCredentialRefusedError, handle_event_credential_refused
from app.modules.events.routes import router as events_router
from app.modules.holiday_calendar.routes import router as holiday_calendar_router
from app.modules.identity.routes import router as auth_router
from app.modules.interactions.routes import router as interactions_router
from app.modules.leads.routes import router as leads_router
from app.modules.opportunities.routes import router as opportunities_router
from app.modules.reports.routes import router as reports_router
from app.modules.resource_assignments.routes import router as resource_assignments_router
from app.modules.resource_requirements.routes import router as resource_requirements_router
from app.modules.terms_and_conditions.routes import router as terms_and_conditions_router
from app.modules.work_orders.routes import router as work_orders_router
from app.modules.workflow.routes import router as workflow_router

settings = get_settings()

app = FastAPI(
    title="PBL CRM + Equipment Hiring API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A database error that escapes a route is logged without its text, which can carry customer values.
app.add_exception_handler(SQLAlchemyError, handle_database_error)
# FastAPI's 422 answer, written so that text it cannot encode as UTF-8 no longer turns it into a 500.
app.add_exception_handler(RequestValidationError, handle_request_validation_error)
# Text shaped like a credential is never recorded in the event log: the save is refused with a plain 422 (TB1-500).
app.add_exception_handler(EventCredentialRefusedError, handle_event_credential_refused)

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(accounts_router)
app.include_router(leads_router)
app.include_router(opportunities_router)
app.include_router(commercial_offers_router)
app.include_router(terms_and_conditions_router)
app.include_router(work_orders_router)
app.include_router(workflow_router)
app.include_router(documents_router)
app.include_router(interactions_router)
app.include_router(reports_router)
app.include_router(equipment_reference_router)
app.include_router(resource_requirements_router)
app.include_router(eligibility_router)
app.include_router(resource_assignments_router)
app.include_router(holiday_calendar_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "pbl-crm-hiring-backend",
        "environment": settings.app_env,
    }


@app.get("/api/platform/config-summary")
def platform_config_summary() -> dict[str, object]:
    """Non-sensitive platform configuration summary for smoke testing."""
    return {
        "app_env": settings.app_env,
        "database": get_database_settings_summary(),
    }


@app.get("/api/platform/db-health")
def platform_db_health() -> dict[str, object]:
    """Verify database connectivity and foundation table presence."""
    db_result = verify_database_connection()
    return {
        "status": "ok",
        "database": db_result,
        "foundation_tables": get_foundation_table_status(),
    }

