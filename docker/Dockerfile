FROM python:3.12-slim

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
