FROM python:3.12-slim

# PostgreSQL 16 client (pg_dump matching the db container) from PGDG
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/eudamed

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eudamed_tool ./eudamed_tool
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY xsd ./xsd
COPY templates ./templates

EXPOSE 8000

# Run migrations, then serve
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
