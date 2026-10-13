FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Psycopg 3 is installed from the binary wheel (psycopg[binary]), which bundles libpq. No
# Microsoft ODBC driver, unixODBC or compiler toolchain is required since ADR-028 moved the
# database to PostgreSQL.

# pytest reads its configuration from pyproject.toml. Without this the container has no config
# file and falls back to default collection, while CI -- which runs pytest against a plain
# checkout -- honours [tool.pytest.ini_options]. Copying it keeps local Compose runs and hosted
# CI on the same configuration.
COPY pyproject.toml ./pyproject.toml

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests
COPY tooling ./tooling

EXPOSE 8000

CMD ["python", "-m", "app.startup"]
