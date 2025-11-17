# Memory Test App - Code Engine Deployment

Quick deployment guide for the memory test application.

## Deploy to Code Engine

```bash
# 1. Navigate to app directory
cd memory-test-app

# 2. Build and push Docker image (replace with your registry)
docker build -t <your-registry>/memory-test-app:latest .
docker push <your-registry>/memory-test-app:latest

# 3. Deploy to Code Engine
ibmcloud target -r us-east
ibmcloud ce project select --name krbalaga

ibmcloud ce app create \
  --name memory-test-app \
  --image <your-registry>/memory-test-app:latest \
  --memory 512M \
  --cpu 0.5 \
  --min-scale 0 \
  --max-scale 2 \
  --port 8080 \
  --env IBMCLOUD_API_KEY=<your-api-key> \
  --env CLOUD_LOGS_INSTANCE_GUID=<your-logs-instance-guid> \
  --env CLOUD_LOGS_REGION=us-south
```

## Test the App

```bash
# Get app URL
APP_URL=$(ibmcloud ce app get --name memory-test-app --output json | jq -r '.url')

# Check health
curl $APP_URL

# Trigger memory crash (immediate OOM after 5 seconds)
curl -X POST $APP_URL/crash -H "Content-Type: application/json" -d '{"type": "oom", "delay": 5}'

# Trigger gradual memory crash
curl -X POST $APP_URL/crash -H "Content-Type: application/json" -d '{"type": "gradual"}'

# Start memory test (gradual OOM) - legacy method
curl $APP_URL/start-memory-test

# Check memory stats
curl $APP_URL/memory-stats
```

## Monitor with Watson Orchestrate Agent

```bash
# Check logs for issues
python3 ../auto_scaler_agent.py check-logs

# Get app status
python3 ../auto_scaler_agent.py get-status

# Auto-scale based on logs
python3 ../auto_scaler_agent.py auto-scale

# Manual scaling
python3 ../auto_scaler_agent.py scale-memory 1024
```

## Endpoints

- `GET /` - Health check and status
- `POST /crash` - **Initiate memory crash** (main endpoint)
  - Request body: `{"type": "oom"|"gradual", "delay": seconds}`
  - `type`: `"oom"` for immediate crash, `"gradual"` for slow build-up
  - `delay`: seconds before crash starts (default: 5, only for "oom" type)
- `GET /start-memory-test` - Start gradual memory consumption (legacy)
- `GET /stop-memory-test` - Stop memory test
- `GET /memory-stats` - Get current memory statistics
- `GET /trigger-oom` - Immediately trigger OOM (legacy)

## Environment Variables

**Required for Cloud Logs Streaming:**
- `IBMCLOUD_API_KEY` - IBM Cloud API key for IAM authentication (recommended)
- `CLOUD_LOGS_INSTANCE_GUID` - Cloud Logs instance GUID
- `CLOUD_LOGS_REGION` - Cloud Logs region (default: us-south)

**Alternative (custom endpoint):**
- `CLOUD_LOGS_ENDPOINT` - Full Cloud Logs ingress endpoint URL
  - Example: `https://your-guid.ingress.us-south.logs.cloud.ibm.com/logs/v1/singles`

**Optional:**
- `PORT` - Server port (default: 8080)

**Note:** If `IBMCLOUD_API_KEY` is not set, the app will try to use IBM Cloud CLI authentication (for local development only).
