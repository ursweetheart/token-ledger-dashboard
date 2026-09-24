# Reuse the installed toolchain; application sources are mounted at /app for tests.
FROM token-ledger-tools:local
RUN pip3 install --no-cache-dir --break-system-packages 'PyYAML>=6.0,<7' pytest httpx
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
ENTRYPOINT ["python3"]
