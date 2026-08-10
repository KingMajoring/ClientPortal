// WGTK Client Portal — Azure infrastructure for the single-App-Service
// deployment (Flask serves the built React app; container-based so pyodbc
// can talk to Azure SQL — see docs/DEPLOYMENT.md for why).
//
// Deploy with: az deployment group create -g <rg> -f infra/main.bicep \
//   -p appName=<name> sqlAdminPassword=<secret> secretKey=<secret>
// sqlAdminPassword / secretKey are never written to this file — you supply
// them at deploy time and Azure stores them as encrypted app settings /
// SQL server properties, not source-controlled anywhere.

@description('Base name used to derive all resource names (lowercase, alphanumeric, 3-15 chars).')
@minLength(3)
@maxLength(15)
param appName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('SQL admin login name.')
param sqlAdminUsername string = 'wgtkadmin'

@description('SQL admin password. Supply at deploy time — never stored in this file.')
@secure()
param sqlAdminPassword string

@description('Flask SECRET_KEY. Supply at deploy time — never stored in this file.')
@secure()
param secretKey string

@description('App Service Plan SKU. B1 is the smallest tier that supports Always On.')
param appServicePlanSku string = 'B1'

var acrName = '${appName}acr'
var planName = '${appName}-plan'
var webAppName = '${appName}-web'
var sqlServerName = '${appName}-sql'
var sqlDbName = '${appName}db'
var storageAccountName = '${appName}uploads'
var fileShareName = 'uploads'
var uploadsMountPath = '/home/uploads'
// Bootstrap image so the Web App has something to pull on first create,
// before the GitHub Actions workflow has pushed a real image to the ACR.
var bootstrapImage = 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'

resource acr 'Microsoft.ContainerRegistry/registries@2021-09-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false // pulls happen via the Web App's managed identity, not a shared admin password
  }
}

resource plan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: planName
  location: location
  sku: { name: appServicePlanSku }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource sqlServer 'Microsoft.Sql/servers@2021-11-01' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlAdminUsername
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
  }
}

resource sqlFirewallAllowAzure 'Microsoft.Sql/servers/firewallRules@2021-11-01' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2021-11-01' = {
  parent: sqlServer
  name: sqlDbName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    maxSizeBytes: 2147483648
  }
}

// Uploaded documents (V5s, generated Letters of Authority) must survive
// container restarts and redeploys, which the container filesystem does
// not — mounted as an Azure Files share below so storage_service.py's
// "local filesystem" path works unmodified against durable storage.
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource fileShareService 'Microsoft.Storage/storageAccounts/fileServices@2022-09-01' = {
  parent: storageAccount
  name: 'default'
}

resource uploadsShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2022-09-01' = {
  parent: fileShareService
  name: fileShareName
}

resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: webAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${bootstrapImage}'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      appSettings: [
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: 'https://${acr.properties.loginServer}' }
        { name: 'FLASK_ENV', value: 'production' }
        { name: 'SECRET_KEY', value: secretKey }
        {
          name: 'DATABASE_URL'
          value: 'mssql+pyodbc://${sqlAdminUsername}:${sqlAdminPassword}@${sqlServer.properties.fullyQualifiedDomainName}:1433/${sqlDbName}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'
        }
        { name: 'MAIL_BACKEND', value: 'console' }
        { name: 'ETA_EXPIRY_GRACE_HOURS', value: '2' }
        { name: 'UPLOAD_ROOT', value: uploadsMountPath }
      ]
    }
  }
}

resource webAppStorageMount 'Microsoft.Web/sites/config@2022-09-01' = {
  parent: webApp
  name: 'azurestorageaccounts'
  properties: {
    uploads: {
      type: 'AzureFiles'
      accountName: storageAccount.name
      shareName: fileShareName
      mountPath: uploadsMountPath
      accessKey: storageAccount.listKeys().keys[0].value
    }
  }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, webApp.id, 'AcrPull')
  scope: acr
  properties: {
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
  }
}

output webAppName string = webApp.name
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output acrLoginServer string = acr.properties.loginServer
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
