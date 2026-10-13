"""The tool's own session factory, whose database errors cannot carry a password hash.

SQLAlchemy formats a failed statement's parameters into the error's text, and for `create` and
`reset-password` one of those parameters is the generated password hash. That is what makes a
database error dangerous here at all: every route by which one could reach the terminal - the
message, a traceback, the exception chain left behind an interruption during cleanup - is a route
for the hash.

Guarding those routes one at a time is unbounded, so the tool's engine sets `hide_parameters`
instead: the parameters are never put into the exception, and there is nothing to leak by any
route, including ones no guard covers. The tool reports a database error by its kind alone and
never wants its text, so this costs it nothing.

The application's engine has hidden them too since TB-1 TB1-503; the tool keeps its own engine, so
its protection does not depend on that setting.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import CONNECT_ARGS, build_sqlalchemy_url

engine: Engine = create_engine(
    build_sqlalchemy_url(),
    pool_pre_ping=True,
    connect_args=CONNECT_ARGS,
    future=True,
    hide_parameters=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)
