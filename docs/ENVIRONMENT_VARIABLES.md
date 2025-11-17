# Environment Variables Configuration

This document describes all environment variables used in the IBM Cloud Toolkit project.

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your values in `.env`

3. The `.env` file is gitignored to protect your credentials

## Required Variables

### IBM Cloud Authentication

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `IBMCLOUD_API_KEY` | IBM Cloud API key for authentication | `abc123...` | ✅ Yes |
| `IBMCLOUD_REGION` | IBM Cloud region | `us-east` | No (default: us-east) |

**How to get your API key:**
```bash
ibmcloud iam api-key-create my-toolkit-key -d "Key for IBM Cloud Toolkit"
```

### Code Engine Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `CODE_ENGINE_PROJECT_ID` | Code Engine project ID | `e46a65b4-9d5b-4cf2-8ca1-d31c7af31759` | No (has default) |

**How to get project ID:**
```bash
ibmcloud ce project current --output json | jq -r '.guid'
```

### Cloud Logs Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `CLOUD_LOGS_INSTANCE_ID` | Cloud Logs instance ID (for queries) | `175a2e16-a792-4f66-be4a-189a3b89e9fe` | No (has default) |
| `CLOUD_LOGS_INSTANCE_GUID` | Cloud Logs instance GUID (for ingestion) | `29c3fa55-a31e-4b04-964c-b4bbdac84ca2` | No |
| `CLOUD_LOGS_REGION` | Cloud Logs region | `us-south` | No (default: us-south) |

**How to get Cloud Logs instance IDs:**
```bash
# List all Cloud Logs instances
ibmcloud resource service-instances --service-name logs --output json | jq -r '.[] | "\(.name): \(.guid)"'
```

### Memory Test Application

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `MEMORY_TEST_APP_URL` | Deployed memory test app URL | `https://mcpfaildemo.1w7gl8ju83cj.us-east.codeengine.appdomain.cloud` | No (has default) |

**How to get app URL:**
```bash
ibmcloud ce app get --name mcpfaildemo --output url
```

### Watson Orchestrate Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `WO_WORKSPACE_ID` | Watson Orchestrate workspace ID | `ws-abc123...` | No (for deployment only) |
| `WO_API_KEY` | Watson Orchestrate API key | `wo-key-123...` | No (for deployment only) |
| `WO_ENVIRONMENT` | Deployment environment | `dev` or `prod` | No (default: dev) |

## Using Environment Variables

### In Python Code

All Python modules automatically load from `.env`:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env file

api_key = os.getenv('IBMCLOUD_API_KEY')
region = os.getenv('IBMCLOUD_REGION', 'us-east')  # with default
```

### In Shell Scripts

Source the .env file:

```bash
# Load variables
set -a
source .env
set +a

# Use variables
echo $IBMCLOUD_API_KEY
ibmcloud login --apikey "$IBMCLOUD_API_KEY"
```

### In Docker

Pass environment variables to containers:

```bash
# Using docker run
docker run --env-file .env my-image

# Using docker-compose (automatically reads .env)
docker-compose up
```

## Security Best Practices

1. ✅ **Never commit `.env` to git** - it's already in `.gitignore`
2. ✅ **Use `.env.example`** as a template with placeholder values
3. ✅ **Rotate API keys regularly** - create new keys periodically
4. ✅ **Use IAM access groups** - limit API key permissions
5. ✅ **Different keys per environment** - separate dev/staging/prod keys

## Troubleshooting

### API Key Issues

```bash
# Test if API key works
ibmcloud login --apikey "$IBMCLOUD_API_KEY"

# Check key details
ibmcloud iam api-keys | grep my-toolkit-key
```

### Loading Issues

```bash
# Check if .env exists
ls -la .env

# Verify variable is set
echo $IBMCLOUD_API_KEY

# Check if variable is loaded in Python
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('IBMCLOUD_API_KEY'))"
```

### Missing Variables

If a required variable is missing:

1. Check `.env.example` for the correct variable name
2. Add it to your `.env` file
3. Restart your application/script

## Migration from Hardcoded Values

Previous versions had hardcoded values in the code. They have been replaced with environment variables:

| Old (Hardcoded) | New (Environment Variable) |
|-----------------|----------------------------|
| API key in code | `IBMCLOUD_API_KEY` |
| Project ID in code | `CODE_ENGINE_PROJECT_ID` |
| Instance IDs in code | `CLOUD_LOGS_INSTANCE_ID`, `CLOUD_LOGS_INSTANCE_GUID` |

All existing configurations will use the default values in `.env`, but you should update them with your own values.
