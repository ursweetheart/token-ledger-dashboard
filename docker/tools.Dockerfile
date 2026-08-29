# Collection pipeline and database rebuild. Separate from api because api is
# read-only while rebuild_db.py runs DROP SCHEMA.
#
# cloud-sdk base: pull_monitoring.py shells out to `gcloud auth
# print-access-token`. No credential is baked in -- gcloud config is mounted.

FROM google/cloud-sdk:slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

COPY scripts/  ./scripts/
COPY db/       ./db/
COPY backend/  ./backend/

# Runs as root: loaders write to /app/data and gcloud writes to its config dir,
# both mounted volumes. A different UID hits permission errors.
CMD ["python3", "scripts/update_dashboard.py"]
