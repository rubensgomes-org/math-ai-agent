# Demo

This file provides commands to be used during the demo of this project
running in Azure Container Apps.

## AZ Commands

1. Find out if there is an active replica:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp replica list \
  --name "ca-mathmcp-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --output table
az containerapp replica list \
  --name "ca-nettools-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --output table
az containerapp replica list \
  --name "ca-mathagent-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --output table
```

2. List revisions:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp revision list \
  --name "ca-mathmcp-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --output table
az containerapp revision list \
  --name "ca-nettools-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --output table
az containerapp revision list \
  --name "ca-mathagent-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --output json
```

3. Ensure at least 1 (one) replica running:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp update \
  -n "ca-mathmcp-${ENV}" \
  -g "rg-rgomesapp-${ENV}" \
  --min-replicas 1
az containerapp update \
  -n "ca-nettools-${ENV}" \
  -g "rg-rgomesapp-${ENV}" \
  --min-replicas 1
az containerapp update \
  -n "ca-mathagent-${ENV}" \
  -g "rg-rgomesapp-${ENV}" \
  --min-replicas 1
```

4. Restart container app

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp revision restart \
  -g rg-rgomesapp-${ENV} \
  -n ca-mathmcp-${ENV} \
  --revision "$( \
    az containerapp show \
      -g rg-rgomesapp-${ENV} \
      -n ca-mathmcp-${ENV} \
      --query properties.latestRevisionName -o tsv \
  )"

az containerapp revision restart \
  -g rg-rgomesapp-${ENV} \
  -n ca-nettools-${ENV} \
  --revision "$( \
    az containerapp show \
      -g rg-rgomesapp-${ENV} \
      -n ca-nettools-${ENV} \
      --query properties.latestRevisionName -o tsv \
  )"

az containerapp revision restart \
  -g rg-rgomesapp-${ENV} \
  -n ca-mathagent-${ENV} \
  --revision "$( \
    az containerapp show \
      -g rg-rgomesapp-${ENV} \
      -n ca-mathagent-${ENV} \
      --query properties.latestRevisionName -o tsv \
  )"
```

5. Show image deployed to the container app:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp show \
  --name "ca-mathmcp-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --query "properties.template.containers[0].image" \
  --output tsv
az containerapp show \
  --name "ca-nettools-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --query "properties.template.containers[0].image" \
  --output tsv
az containerapp show \
  --name "ca-mathagent-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --query "properties.template.containers[0].image" \
  --output tsv
# If it is mcr.microsoft.com/k8se/quickstart:latest, then the calculator-mcp
# image has not been deployed yet.
```

5. Show the container FQDN:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

# ATTENTION: this FQDN is the FQDN of the proxy server for the ACA. It is
# only resolvable and reachable from within the same CAE (Container App
# Environment) because the ACA ingresses are INTERNAL.
#
# Also, within the same CAE, the app name alone is enough to reach an ACA.
# For example, given:
#
# ca-mathmcp-dev.internal.proudpond-e9d3985a.centralus.azurecontainerapps.io
#
# another ACA in the same CAE can reach it as ca-mathmcp-dev.

az containerapp show \
  --name "ca-mathmcp-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
az containerapp show \
  --name "ca-nettools-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
az containerapp show \
  --name "ca-mathagent-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
```

6. Connect to the debug containers:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp debug \
  -n "ca-mathmcp-${ENV}" \
  -g "rg-rgomesapp-${ENV}"
az containerapp debug \
  -n "ca-mathagent-${ENV}" \
  -g "rg-rgomesapp-${ENV}"
```

## From the `nettools` container

**NOTE:** after leaving the nettools CLI, type `stty sane` to clear up any
terminal issues.

1. Connect to the `nettools` console:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp exec \
  --name "ca-nettools-${ENV}" \
  --resource-group "rg-rgomesapp-${ENV}" \
  --command /bin/bash
```

### Testing `math-ai-agent`

1. Health check:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account
#HOST="localhost:9090"
HOST="ca-mathagent-${ENV}"

curl -v "http://${HOST}/health"
```

2. Submit prompts to `math-ai-agent`

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account
#HOST="localhost:9090"
HOST="ca-mathagent-${ENV}"

# Simple prompt:
curl -s -X POST http://${HOST}/prompt/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "What is 12 times 37 plus 5?"}'

# Answer only, without the reasoning, printed as plain text with jq:
curl -s -X POST http://${HOST}/prompt/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "What is the square of 144 divided by 3?", "display_reasoning": false}' \
  | jq -r .answer

# Multi-step word problem, showing the HTTP status and total time:
curl -s -w '\nHTTP %{http_code} in %{time_total}s\n' \
  -X POST http://${HOST}/prompt/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "A rectangle is 15.5 m by 8.2 m. What are its area and perimeter?"}'

# Error case: dividing by zero shows how calculator errors come back.
curl -s -X POST http://${HOST}/prompt/ \
  -H 'Content-Type: application/json' \
  -d '{"text": "What is 10 divided by 0?"}'
```

### Testing `caculator-mcp`

1. Health check:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

curl -v "http://ca-mathmcp-${ENV}/health"

telnet "ca-mathmcp-${ENV}" 80
# Then type the request below (use ca-mathmcp-lab for lab) and press Enter
# twice:
GET /health HTTP/1.1
Host: ca-mathmcp-dev
```

2. Run `testcalcmcp.sh` to test the Calculator MCP server.

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

# REMEMBER the port for the ACA is 80 because we are hitting the ACA proxy,
# which delegates the call to the real port internal to the container.
testcalcmcp.sh --host "ca-mathmcp-${ENV}" --port 80
```

4. Show the MCP server name and other information:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

# Modern MCP protocol - Stateless
curl -sS "http://ca-mathmcp-${ENV}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: server/discover" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "server/discover",
    "params": {
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {
          "name": "curl", "version": "1.0"
        },
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  }' | jq .

# Modern MCP protocol - Stateless (debug/verbose/trace)
curl -v --trace-ascii trace.log "http://ca-mathmcp-${ENV}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: server/discover" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "server/discover",
    "params": {
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {
          "name": "curl", "version": "1.0"
        },
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  }' | jq .

# Legacy MCP protocol - Stateful
curl -s "http://ca-mathmcp-${ENV}/mcp" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {"name": "curl", "version": "1.0"}
    }
  }' | sed -n 's/^data://p' | jq .
```

5. List the MCP tools:

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

# Modern MCP protocol
curl -sS "http://ca-mathmcp-${ENV}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/list" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {
          "name": "curl", "version": "1.0"
        },
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  }' | jq .

# Legacy MCP protocol - requires a session from initialize
SID="$(
  curl -sS -i "http://ca-mathmcp-${ENV}/mcp" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "initialize",
      "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "curl", "version": "1.0"}
      }
    }' | awk -F': ' 'tolower($1)=="mcp-session-id" {print $2}' | tr -d '\r'
)"
curl -s "http://ca-mathmcp-${ENV}/mcp" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: ${SID}" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
curl -s "http://ca-mathmcp-${ENV}/mcp" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: ${SID}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | sed -n 's/^data://p' | jq .
```

## Don't forget to bring replicas down to 0 (zero)

```bash
ENV=dev # rubens azure account
#ENV=lab # 3cloud azure account

az containerapp update \
  -n "ca-mathmcp-${ENV}" \
  -g "rg-rgomesapp-${ENV}" \
  --min-replicas 0
az containerapp update \
  -n "ca-nettools-${ENV}" \
  -g "rg-rgomesapp-${ENV}" \
  --min-replicas 0
az containerapp update \
  -n "ca-mathagent-${ENV}" \
  -g "rg-rgomesapp-${ENV}" \
  --min-replicas 0
```
