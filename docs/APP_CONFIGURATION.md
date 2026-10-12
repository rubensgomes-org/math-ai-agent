# Azure App Configuration

This file describes information about the Azure App Configuration used to store this project configuration.

## System Managed Identity

The app configuration resource is assigned a system-managed identity which is granted permision to read secrets in KeyVault







## User-Assigned Managed Identiry (UAMI)

A single shared ** User-Assigned
Managed Identity** is provisioned in the `azure-iac` Terraform `managed-identiry` module to used by every ACA container app.  The UAMI is called `id-<workload>app-<env>` (e.g., id-rgomes-dev).

This UAMI has been granted "App Configuration Data Reader" role on the App Configuration store inside the Terraform `azure-iac` `app-configuration` module. Therefore, any ACA container app with the assigned UAMI should be able to load/read app configuration store data using the `DefaultAzureCredential` In a container app, `DefaultAzureCredential` acts as a managed-identity credential.

The following environment variables are set in the container app by Terraform `azure-iac` during provisioning:

- AZURE_CLIENT_ID
- KEY_VAULT_URI
- APP_CONFIG_ENDPOINT


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

## Endpoint and Client Connection

The client reads the store endpoint from the `APP_CONFIG_ENDPOINT`
environment variable (dev: `https://appcs-rgomes-dev.azconfig.io`).
azure-iac sets it on each container app:

1. Module `05-app-configuration` outputs `appcs_endpoint`.
2. Root `12-container-apps` passes it as `app_configuration_endpoint`.
3. Module `container-apps` sets it as `APP_CONFIG_ENDPOINT`.

The client connects with:

```python
load(endpoint=endpoint, credential=DefaultAzureCredential(), ...)
```

- `DefaultAzureCredential` uses the UAMI selected by `AZURE_CLIENT_ID`.
- It gets an Entra ID token from the ACA identity endpoint; no secrets.
- The SDK calls the store over HTTPS with the token as a bearer token.

With `APP_CONFIG_ENDPOINT` set, every setting comes from the
`ca-mathagent/*` keys, labeled with the `CONTAINER_APP_NAME` suffix
(`ca-mathagent-dev` -> `dev`). Only `logging` comes from the YAML file.
The API key comes from the `KEY_VAULT_URI` vault secret
`ca-mathagent--<api_key_env>`, with `_` replaced by `-`.

Locally, `APP_CONFIG_ENDPOINT` is unset and only the YAML file is used.
To test against the store, export it and run `az login`; the data-plane
role above is required.
