from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from alembic.util import CommandError

from app.core.database import CONNECT_ARGS, build_sqlalchemy_url
from app.models_metadata import target_metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

alembic_url = build_sqlalchemy_url().render_as_string(hide_password=False).replace("%", "%%")
config.set_main_option("sqlalchemy.url", alembic_url)

AUTOGENERATE_REFUSED = (
    "`alembic revision --autogenerate` and `alembic check` are refused in this project. The models describe "
    "only some of the tables, so Alembic would propose dropping the rest. Write the migration by hand: "
    "db/notes/migration-rules.md, 'Migrations are written by hand'."
)


def refuse_autogenerate(migration_context, revision, directives) -> None:
    """Refuse every comparison of the models with the database (TB-1 TB1-400).

    Alembic calls this only for `alembic revision --autogenerate` and `alembic check`: a plain
    `alembic revision` runs this file only when alembic.ini sets `revision_environment`, which it
    does not. It raises before any revision file is written.
    """
    raise CommandError(AUTOGENERATE_REFUSED)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=refuse_autogenerate,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Apply migrations on a UTC session, matching the application engine.
        connect_args=CONNECT_ARGS,
        # A failed migration's bound values stay out of the start-up log, as the application
        # engine's do (TB-1 TB1-503).
        hide_parameters=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=refuse_autogenerate,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()