# Read-only FastAPI backend. The collection pipeline lives in tools.Dockerfile
# because the two need opposite database rights.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system tokenledger \
    && useradd --system --gid tokenledger --home-dir /nonexistent \
       --shell /usr/sbin/nologin tokenledger

# Requirements before source so the install layer stays cached.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --chown=tokenledger:tokenledger backend/ ./backend/
COPY --chown=tokenledger:tokenledger db/ ./db/

USER tokenledger
EXPOSE 8000

# 0.0.0.0, not 127.0.0.1: inside a container that would be unreachable to nginx.
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
