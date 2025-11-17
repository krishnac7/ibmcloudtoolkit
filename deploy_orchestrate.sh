#!/bin/bash
# Deploy IBM Cloud Toolkit to Watson Orchestrate using orchestrate CLI

set -e

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "Deploying IBM Cloud Toolkit to Watson Orchestrate..."

# Activate orchestrate environment
echo "0. Activating orchestrate environment..."
if [ -z "$IBMCLOUD_API_KEY" ]; then
    echo "Error: IBMCLOUD_API_KEY not found in .env file"
    exit 1
fi

ORCHESTRATE_ENV=${ORCHESTRATE_ENV:-ibmcloud}
orchestrate env activate "$ORCHESTRATE_ENV" --api-key "$IBMCLOUD_API_KEY"
echo "Environment activated"
echo ""

# Inject credentials into mcp_api_server.py before deployment
echo "1. Injecting credentials into server..."
# Make backups first
cp src/cloud-toolkit/mcp_api_server.py src/cloud-toolkit/mcp_api_server.py.bak
cp src/cloud-toolkit/icr_toolkit_api.py src/cloud-toolkit/icr_toolkit_api.py.bak

# Inject all credentials (no .bak to avoid multiple backups)
sed -i '' "s|'__IBMCLOUD_API_KEY__'|'$IBMCLOUD_API_KEY'|g" src/cloud-toolkit/mcp_api_server.py
sed -i '' "s|'__IBMCLOUD_ACCOUNT_ID__'|'$IBMCLOUD_ACCOUNT_ID'|g" src/cloud-toolkit/mcp_api_server.py src/cloud-toolkit/icr_toolkit_api.py
sed -i '' "s|'__IBMCLOUD_REGION__'|'$IBMCLOUD_REGION'|g" src/cloud-toolkit/mcp_api_server.py
sed -i '' "s|'__CODE_ENGINE_PROJECT_ID__'|'$CODE_ENGINE_PROJECT_ID'|g" src/cloud-toolkit/mcp_api_server.py
sed -i '' "s|'__CLOUD_LOGS_INSTANCE_ID__'|'$CLOUD_LOGS_INSTANCE_ID'|g" src/cloud-toolkit/mcp_api_server.py
sed -i '' "s|'__CLOUD_LOGS_INSTANCE_GUID__'|'$CLOUD_LOGS_INSTANCE_GUID'|g" src/cloud-toolkit/mcp_api_server.py
sed -i '' "s|'__CLOUD_LOGS_REGION__'|'$CLOUD_LOGS_REGION'|g" src/cloud-toolkit/mcp_api_server.py
echo "Credentials injected"
echo ""

# Deploy Cloud Toolkit (Code Engine, Cloud Logs, ICR)
echo "2. Removing existing toolkit (if exists)..."
orchestrate toolkits remove --name ibm-cloud-toolkit 2>/dev/null || echo "No existing toolkit to remove"
echo ""

echo "3. Deploying Cloud Toolkit..."
orchestrate toolkits import \
    --kind mcp \
    --name ibm-cloud-toolkit \
    --description "IBM Cloud Code Engine, Cloud Logs, and Container Registry API toolkit" \
    --package-root src/cloud-toolkit \
    --command "python mcp_api_server.py" \
    --tools "*"

echo "Cloud Toolkit deployed successfully"

# Restore original file (remove injected credentials)
echo ""
echo "4. Cleaning up..."
mv src/cloud-toolkit/mcp_api_server.py.bak src/cloud-toolkit/mcp_api_server.py 2>/dev/null || true
mv src/cloud-toolkit/icr_toolkit_api.py.bak src/cloud-toolkit/icr_toolkit_api.py 2>/dev/null || true
echo ""

echo "Deployed tools:"
echo "  - Cloud Logs: get_app_logs, query_cloud_logs"
echo "  - Code Engine: get_app_status, scale_app, update_app_memory, restart_app, rebuild_app"
echo "  - Container Registry: list_icr_images, list_icr_namespaces, delete_icr_image, get_icr_quota"
echo "  - Services: list_services, create_service, bind_service"
echo "  - Resources: list_resource_groups, target_resource_group"
echo ""
echo "To use with connections, add: --app-id ibmcloud_connection"
