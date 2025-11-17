# Watson Orchestrate Toolkit Deployment

Guide for deploying local MCP toolkits to Watson Orchestrate.

## Overview

Watson Orchestrate supports importing local Python MCP servers as toolkits. This allows you to develop and test toolkits locally before deployment.

## Deployment Methods

### 1. Local Python MCP Server

For Python-based MCP servers with custom logic:

```bash
orchestrate toolkits import \
    --kind mcp \
    --name ibm-cloud-api \
    --description "IBM Cloud Code Engine and Cloud Logs API toolkit" \
    --package-root ./src/cloud-toolkit \
    --command "python mcp_api_server.py" \
    --tools "*"
```

#### Required Structure
```
src/cloud-toolkit/
├── mcp_api_server.py      # MCP server entry point
├── requirements.txt       # Python dependencies
└── ...other files
```

#### Key Parameters
- `--kind mcp`: Specifies MCP toolkit type
- `--name`: Toolkit identifier (must be unique)
- `--description`: Human-readable description
- `--package-root`: Root folder containing server code
- `--command`: Command to start the MCP server
- `--tools "*"`: Import all tools (or specify comma-separated list)

### 2. PyPI Package

For published Python packages:

```bash
orchestrate toolkits import \
    --kind mcp \
    --name tavily \
    --description "Search the internet" \
    --command "pipx run mcp-tavily@0.1.10" \
    --tools "*" \
    --app-id tavily
```

### 3. NPM Package

For Node.js packages:

```bash
orchestrate toolkits import \
    --kind mcp \
    --name filesystem \
    --description "File system operations" \
    --command "npx -y @modelcontextprotocol/server-filesystem@0.5.1 /tmp" \
    --tools "*"
```

### 4. Local Node.js Server

For local Node.js MCP servers:

```bash
orchestrate toolkits import \
    --kind mcp \
    --name my-nodejs-toolkit \
    --description "Custom Node.js toolkit" \
    --package-root ./mcp_server \
    --command "node server.js" \
    --tools "*"
```

Required structure:
```
mcp_server/
├── server.js
├── package.json
└── node_modules/
```

### 5. Remote Gateway

For remote MCP servers:

```bash
orchestrate toolkits import \
    --kind mcp \
    --name remote-toolkit \
    --description "Remote MCP server" \
    --gateway-url "https://api.example.com/mcp" \
    --tools "*"
```

## Connection Management

If your toolkit requires API keys or credentials:

### Add Connection
```bash
orchestrate connections add -a my_connection
```

### Configure for Environments
```bash
for env in draft live; do
    orchestrate connections configure \
        -a my_connection \
        --env $env \
        --type team \
        --kind key_value
    
    orchestrate connections set-credentials \
        -a my_connection \
        --env $env \
        -e "API_KEY=$MY_API_KEY" \
        -e "SECRET=$MY_SECRET"
done
```

### Link to Toolkit
Add `--app-id my_connection` when importing:

```bash
orchestrate toolkits import \
    --kind mcp \
    --name ibm-cloud-api \
    --app-id my_connection \
    ...
```

## IBM Cloud Toolkit Deployment

### Prerequisites

1. **Environment Variables** (set via connections):
   ```bash
   IBMCLOUD_API_KEY=<your-api-key>
   CLOUD_LOGS_INSTANCE_GUID=<instance-id>
   CLOUD_LOGS_REGION=us-south
   ```

2. **Dependencies** (requirements.txt):
   ```
   requests>=2.31.0
   mcp>=1.0.0
   ```

### Deploy Cloud Toolkit

```bash
# Navigate to cloud-toolkit directory
cd src/cloud-toolkit

# Import the toolkit
orchestrate toolkits import \
    --kind mcp \
    --name ibm-cloud-api \
    --description "IBM Cloud Code Engine and Cloud Logs API toolkit" \
    --package-root . \
    --command "python mcp_api_server.py" \
    --tools "*"
```

This deploys 27 tools:
- **Cloud Logs**: get_app_logs, query_cloud_logs
- **Code Engine**: get_app_status, scale_app, update_app_memory, update_app_cpu, restart_app, delete_app, **rebuild_app**
- **Services**: list_services, create_service, delete_service, bind_service, etc.
- **Resources**: list_resource_groups, target_resource_group, etc.

### Deploy App Toolkit

```bash
# Navigate to app-toolkit directory  
cd src/app-toolkit

# Import the toolkit
orchestrate toolkits import \
    --kind mcp \
    --name memory-test-app \
    --description "Memory test application control toolkit" \
    --package-root . \
    --command "python memory_app_toolkit.py" \
    --tools "*"
```

This deploys 6 tools:
- trigger_crash, start_memory_test, stop_memory_test
- get_memory_stats, check_app_health, trigger_oom

## Management Commands

### List Toolkits
```bash
orchestrate toolkits list
```

### Remove Toolkit
```bash
orchestrate toolkits remove --name ibm-cloud-api
```

### Update Toolkit
```bash
# Remove old version
orchestrate toolkits remove --name ibm-cloud-api

# Import new version
orchestrate toolkits import --kind mcp --name ibm-cloud-api ...
```

### View Toolkit Details
```bash
orchestrate toolkits describe --name ibm-cloud-api
```

## Troubleshooting

### Import Fails with "Missing requirements.txt"

Ensure `requirements.txt` is at the root of `--package-root`:
```bash
ls src/cloud-toolkit/requirements.txt  # Should exist
```

### Tools Not Appearing

1. Check toolkit was imported:
   ```bash
   orchestrate toolkits list | grep ibm-cloud-api
   ```

2. Verify tools are exported from MCP server:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python mcp_api_server.py
   ```

3. Try importing specific tools:
   ```bash
   --tools "get_app_logs,get_app_status"
   ```

### Connection Errors

1. Verify connection exists:
   ```bash
   orchestrate connections list
   ```

2. Check credentials are set:
   ```bash
   orchestrate connections get-credentials -a my_connection --env draft
   ```

3. Ensure `--app-id` matches connection name

### MCP Server Crashes

1. Test server locally:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python mcp_api_server.py
   ```

2. Check for syntax errors:
   ```bash
   python -m py_compile mcp_api_server.py
   ```

3. Verify dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

## Best Practices

### 1. Version Control
Include version in toolkit name for easier rollback:
```bash
--name ibm-cloud-api-v2
```

### 2. Selective Tool Import
Import only needed tools for faster loading:
```bash
--tools "get_app_logs,get_app_status,scale_app"
```

### 3. Development Workflow
1. Test locally with MCP inspector
2. Deploy to draft environment
3. Test in Watson Orchestrate draft
4. Promote to live environment

### 4. Environment Separation
Use different connection names for dev/prod:
```bash
orchestrate connections add -a ibm-cloud-dev
orchestrate connections add -a ibm-cloud-prod
```

### 5. Documentation
Include clear descriptions for discoverability:
```bash
--description "IBM Cloud Code Engine management - scale, restart, monitor apps"
```

## Resources

- [Watson Orchestrate ADK](https://developer.watson-orchestrate.ibm.com/)
- [Local MCP Toolkits](https://developer.watson-orchestrate.ibm.com/tools/toolkits/local_mcp_toolkits)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Zeus Documentation](index.md)

## Example: Complete Deployment

```bash
#!/bin/bash

# 1. Set up connection
orchestrate connections add -a ibm-cloud

for env in draft live; do
    orchestrate connections configure \
        -a ibm-cloud \
        --env $env \
        --type team \
        --kind key_value
    
    orchestrate connections set-credentials \
        -a ibm-cloud \
        --env $env \
        -e "IBMCLOUD_API_KEY=$IBMCLOUD_API_KEY" \
        -e "CLOUD_LOGS_INSTANCE_GUID=$CLOUD_LOGS_INSTANCE_GUID" \
        -e "CLOUD_LOGS_REGION=us-south"
done

# 2. Deploy cloud toolkit
cd src/cloud-toolkit
orchestrate toolkits import \
    --kind mcp \
    --name ibm-cloud-api \
    --description "IBM Cloud Code Engine and Cloud Logs API toolkit (27 tools)" \
    --package-root . \
    --command "python mcp_api_server.py" \
    --tools "*" \
    --app-id ibm-cloud

# 3. Deploy app toolkit
cd ../app-toolkit
orchestrate toolkits import \
    --kind mcp \
    --name memory-test-app \
    --description "Memory test application control toolkit (6 tools)" \
    --package-root . \
    --command "python memory_app_toolkit.py" \
    --tools "*" \
    --app-id ibm-cloud

# 4. Verify deployment
orchestrate toolkits list

echo "✅ Deployment complete - 33 tools available in Watson Orchestrate"
```

---

**Next**: See [Tool Reference](tool-reference.md) for complete API documentation
