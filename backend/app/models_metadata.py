from app.core.database import Base

# The SQLAlchemy models describe only some of the tables, and some only in part: the migrations are the schema, written
# by hand, and the application reads and writes through SQL text. Alembic is given these models, but alembic/env.py
# refuses every command that would compare them with the database (TB-1 TB1-400; db/notes/migration-rules.md).
from app.modules.authorization.business_authority.configuration_models import (  # noqa: F401
    AuthorityConfigurationChange,
    AuthorityConfigurationEvaluation,
)
from app.modules.authorization.business_authority.models import (  # noqa: F401
    BusinessAuthorityAssignmentObject,
    BusinessAuthorityAssignmentRetraction,
    BusinessAuthorityAssignmentVersion,
    BusinessAuthorityObject,
    BusinessAuthorityRetraction,
    BusinessAuthorityRoleObject,
    BusinessAuthorityRoleRetraction,
    BusinessAuthorityRoleVersion,
    BusinessAuthorityRuleObject,
    BusinessAuthorityRuleRetraction,
    BusinessAuthorityRuleVersion,
    BusinessAuthorityVersion,
)
from app.modules.authorization.models import AuthzPermission, AuthzRolePermission  # noqa: F401
from app.modules.commercial_offers.models import (  # noqa: F401
    CommercialOfferCreditReview,
    CommercialOfferQuoteDocument,
    CommercialOfferSubmissionEvidence,
    CommercialOfferTcClauseAttachment,
)
from app.modules.documents.models import DocumentMetadata  # noqa: F401
from app.modules.events.models import BusinessEvent  # noqa: F401
from app.modules.identity.models import AppUser, Role, SignInAttempt, SignInStop, UserRole  # noqa: F401
from app.modules.terms_and_conditions.models import TermsAndConditionsClause  # noqa: F401
from app.modules.workflow.models import WorkflowStatus  # noqa: F401

target_metadata = Base.metadata
