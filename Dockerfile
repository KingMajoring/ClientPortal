# syntax=docker/dockerfile:1

# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend runtime ----
# Pinned to bookworm explicitly: "python:3.11-slim" floats to whatever Debian
# release is currently "slim" upstream, which moved to trixie (13) while
# Microsoft's ODBC driver repo below is still bookworm (12)-only. Floating
# tags + a hardcoded distro-versioned URL don't mix — pin both sides.
FROM python:3.11-slim-bookworm AS backend

# msodbcsql18 + unixodbc: Azure App Service's built-in Python runtime does
# NOT ship these (confirmed not baked in as of this image), and anything
# installed via a startup script doesn't survive a redeploy. A custom
# container is the reliable way to get pyodbc talking to Azure SQL — see
# docs/DEPLOYMENT.md for why this is a container deploy rather than a plain
# code-based App Service.
# NOTE: Microsoft's prod.list already ships its own bracketed options,
# including "signed-by=/usr/share/keyrings/microsoft-prod.gpg" — an earlier
# revision also `sed`-inserted a *second* [signed-by=...] group in front of
# that, producing two adjacent bracket groups on one line, which is invalid
# apt syntax ("Malformed entry ... URI parse", caught on the first real
# build). The fix is to do less: just write the key to the exact path the
# file already names, and leave prod.list untouched.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl gnupg apt-transport-https ca-certificates gcc g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev

WORKDIR /app
COPY backend/requirements.txt backend/requirements-mssql.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-mssql.txt

# Build tools/keys were only needed to get here — drop them to keep the
# runtime image smaller and reduce attack surface.
RUN apt-get purge -y curl gnupg apt-transport-https gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist/ ./app/static_frontend/

ENV FLASK_APP=wsgi.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE 8000
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
