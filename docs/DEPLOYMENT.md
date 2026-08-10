# Deploying to Azure

Everything here is designed so **your Azure credentials never touch this
Claude session or GitHub Actions as a stored secret**: you run the
provisioning commands yourself from your own machine (or Cloud Shell), and
GitHub Actions authenticates via OIDC federation — a short-lived token
exchange, not a password or client secret sitting in repo settings.

## Architecture

One Azure App Service, running as a Linux container (not the built-in code
runtime — see "Why a container?" below), serving both the API and the built
React app from a single origin. Azure SQL Database for data, Azure Container
Registry for the image, an Azure Files share mounted into the container for
uploaded documents (V5s, generated Letters of Authority) so they survive
restarts and redeploys.

```
GitHub push to main
  → GitHub Actions (OIDC login, no stored secret)
    → az acr build            (builds the Docker image in the cloud)
    → az webapp config container set   (points the Web App at the new image)
    → az webapp restart
        ↓
  Azure App Service (container)  ←→  Azure SQL Database
        ↓ mounted Azure Files share
  Uploaded documents / Letters of Authority
```

### Why a container, not App Service's built-in Python runtime?

`pyodbc` (needed for Azure SQL) requires the `msodbcsql18` native driver.
Azure App Service's built-in Linux Python image doesn't ship it, and
anything installed via a startup script doesn't survive the platform's
periodic image refreshes — Microsoft's own guidance for this exact situation
is a custom container. The `Dockerfile` at the repo root installs the driver
once, at build time, so it's baked into the image instead of reinstalled
(unreliably) on every cold start.

## One-time setup (you run this — I never see your credentials)

Prerequisites: [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
installed and logged in (`az login`), an Azure subscription, and either the
[GitHub CLI](https://cli.github.com/) (`gh`) or access to the repo's Settings
→ Secrets page.

### 1. Pick names and create the resource group

```bash
export APP_NAME=wgtkportal          # 3-15 lowercase alphanumeric chars, must be globally unique-ish (used in the ACR + storage account names)
export RESOURCE_GROUP=wgtk-portal-rg
export LOCATION=uksouth

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
```

### 2. Deploy the infrastructure

Leave `sqlAdminPassword` and `secretKey` off the command line — Azure CLI
will prompt for them interactively (masked input), so they never land in
your shell history:

```bash
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters appName="$APP_NAME"
```

This creates: Container Registry, App Service Plan + Web App (container,
pulls via its own managed identity — no ACR admin password anywhere), Azure
SQL Server + Database, a storage account with a mounted file share for
uploads, and the RBAC role letting the Web App pull from the registry.

Capture the outputs:

```bash
az deployment group show -g "$RESOURCE_GROUP" -n main \
  --query properties.outputs
```

You'll get `webAppName`, `webAppUrl`, and `acrLoginServer` — you'll need
`webAppName` for the GitHub secrets below.

### 3. Set up GitHub OIDC (no client secret, ever)

Create an app registration and let GitHub's OIDC tokens authenticate as it —
no password/secret is generated or stored anywhere:

```bash
export REPO="KingMajoring/ClientPortal"   # owner/repo
export BRANCH="main"                       # branch the workflow deploys from

APP_ID=$(az ad app create --display-name "wgtk-portal-deploy" --query appId -o tsv)
az ad sp create --id "$APP_ID"

az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-'"$BRANCH"'",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:'"$REPO"':ref:refs/heads/'"$BRANCH"'",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

If you also want to trigger the deploy manually via `workflow_dispatch` from
a different branch while testing, add another federated credential with that
branch's ref in `subject`.

Grant it Contributor on just this resource group (not the whole
subscription):

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
```

### 4. Add GitHub repo secrets

```bash
TENANT_ID=$(az account show --query tenantId -o tsv)
WEBAPP_NAME=$(az deployment group show -g "$RESOURCE_GROUP" -n main --query properties.outputs.webAppName.value -o tsv)

gh secret set AZURE_CLIENT_ID -b"$APP_ID" -R "$REPO"
gh secret set AZURE_TENANT_ID -b"$TENANT_ID" -R "$REPO"
gh secret set AZURE_SUBSCRIPTION_ID -b"$SUBSCRIPTION_ID" -R "$REPO"
gh secret set AZURE_RESOURCE_GROUP -b"$RESOURCE_GROUP" -R "$REPO"
gh secret set AZURE_WEBAPP_NAME -b"$WEBAPP_NAME" -R "$REPO"
gh secret set AZURE_ACR_NAME -b"${APP_NAME}acr" -R "$REPO"
```

(No `gh`? Add the same six as repo secrets manually under Settings → Secrets
and variables → Actions.)

### 5. Deploy

Merge this branch to `main` (the workflow triggers on push to `main`), or
run it manually right now from the Actions tab → "Deploy to Azure" →
"Run workflow" (needs the `workflow_dispatch` federated credential from step
3 if you're running from a non-`main` branch).

### 6. Create the first WGTK Admin user

`seed.py` **drops every table** — never run it against this database.
Instead, temporarily open the SQL firewall to your own IP, run the
production-safe bootstrap script from your machine, then close it again:

```bash
MY_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --server "${APP_NAME}-sql" \
  --name TemporaryAdminBootstrap \
  --start-ip-address "$MY_IP" --end-ip-address "$MY_IP"

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-mssql.txt   # needs the ODBC Driver 18 installed locally too
export DATABASE_URL="mssql+pyodbc://wgtkadmin:<the password you set in step 2>@${APP_NAME}-sql.database.windows.net:1433/${APP_NAME}db?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
python create_admin.py admin@wgtk.co.uk Wendy Admin

az sql server firewall-rule delete \
  --resource-group "$RESOURCE_GROUP" --server "${APP_NAME}-sql" --name TemporaryAdminBootstrap
```

From then on, log in as that Admin and onboard client companies and further
staff through the app itself (Clients / Users pages) — no more scripts
needed.

## Known limitations of this phase-1 deploy

- **Single instance.** `alwaysOn` is set but there's no autoscale or
  multi-region failover configured — fine for a demo/early-access rollout,
  not yet sized for real production load.
- **SQL auth, not Azure AD auth.** The database connection uses a SQL
  login/password app setting rather than the Web App's managed identity.
  Azure AD-only auth to SQL is the natural next hardening step.
- **ETA-expiry is manually triggered.** `POST /api/staff/enquiries/check-eta-expiry`
  still needs something to call it on a schedule — an Azure Function on a
  timer trigger, or a cron-triggered Logic App, would close this.
- **Email is still the console stub.** `MAIL_BACKEND=console` ships as the
  default app setting — switch it to a real provider when ready (see
  `app/services/email_service.py`).
