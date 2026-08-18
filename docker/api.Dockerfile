FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system tokenledger \
    && useradd --system --gid tokenledger --home-dir /nonexistent \
       --shell /usr/sbin/nologin tokenledger

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --chown=tokenledger:tokenledger backend/ ./backend/
COPY --chown=tokenledger:tokenledger db/ ./db/
COPY --chown=tokenledger:tokenledger scripts/copy_to_postgres.py ./scripts/copy_to_postgres.py
COPY --chown=tokenledger:tokenledger scripts/audit_db.py ./scripts/audit_db.py

USER tokenledger
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
