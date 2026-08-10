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
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl gnupg apt-transport-https ca-certificates gcc g++ \
    && curl -fsSL -o /tmp/ms.asc https://packages.microsoft.com/keys/microsoft.asc \
    && gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg /tmp/ms.asc \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
    && sed -i 's|deb |deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] |' /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev

WORKDIR /app
COPY backend/requirements.txt backend/requirements-mssql.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-mssql.txt

# Build tools/keys were only needed to get here — drop them to keep the
# runtime image smaller and reduce attack surface.
RUN apt-get purge -y curl gnupg apt-transport-https gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/ms.asc

COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist/ ./app/static_frontend/

ENV FLASK_APP=wsgi.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE 8000
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
