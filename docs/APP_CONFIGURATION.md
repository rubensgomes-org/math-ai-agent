# Azure App Configuration

This file describes information about the Azure App Configuration used to store this project configuration.

## System Managed Identity

The app configuration resource is assigned a system-managed identity which is granted permision to read secrets in KeyVault





## Data-Plane Role

You need an Entra ID data-plane role on the store. Being Owner or Contributor of the subscription only covers the control plane, so it doesn't let you read key-values.

```bash
APPCS_ID=$(az appconfig show --name appcs-rgomes-dev --query id -o tsv)
USER_ID=$(az ad signed-in-user show --query id -o tsv)


az role assignment create \
  --role "App Configuration Data Owner" \
  --assignee-object-id "$USER_ID" \
  --assignee-principal-type User \
  --scope "$APPCS_ID"
```