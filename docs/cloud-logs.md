# Cloud Logs Integration

Complete guide to querying and streaming IBM Cloud Logs using the Zeus toolkit.

## 📝 Overview

Zeus provides **direct API integration** with IBM Cloud Logs, bypassing the CLI for 10x faster queries. The toolkit includes:

1. **MCP API Server** - Direct REST API queries (fastest)
2. **Watson Orchestrate Tools** - Natural language log queries
3. **Log Streaming** - Real-time log transmission from applications
4. **DataPrime Query Language** - Powerful log filtering and analysis

## 🚀 Quick Start

### Query Logs (Watson Orchestrate)

```
"Get logs for mcpfaildemo from the last 4 hours"
```

The `get_app_logs` tool returns up to 100 log entries with:
- Timestamps
- Severity levels
- App names (deployment IDs)
- Log messages

### Query Logs (Python API)

```python
from src.cloud_toolkit.mcp_api_server import CloudAPIServer

server = CloudAPIServer()
logs = server.get_app_logs("mcpfaildemo", hours=4, limit=100)

for log in logs['logs']:
    print(f"[{log['timestamp']}] {log['severity']}")
    print(f"  App: {log['app']}")
    print(f"  {log['message']}")
```

### Query Logs (CLI)

```bash
# Using the toolkit
python src/cloud-toolkit/ibmcloud_toolkit.py plugin logs \
  "query --query 'source logs | limit 100' --since 4h"
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
IBMCLOUD_API_KEY=your_api_key_here

# Cloud Logs instance
CLOUD_LOGS_INSTANCE_GUID=175a2e16-a792-4f66-be4a-189a3b89e9fe

# Region (optional, default: us-south)
CLOUD_LOGS_REGION=us-south

# Custom endpoint (optional)
CLOUD_LOGS_ENDPOINT=https://175a2e16....api.us-south.logs.cloud.ibm.com
```

### Finding Your Instance GUID

```bash
# List Cloud Logs instances
ibmcloud resource service-instances --service-name logs

# Get instance details
ibmcloud resource service-instance mcp-test-logs --output json | jq -r '.guid'
```

## 📊 Log Structure

### Log Entry Format

```json
{
  "timestamp": "2025-11-15T10:40:35.115457773",
  "severity": "3",
  "app": "mcpfaildemo-00001-deployment-65884fb69b-dpp6p",
  "message": "127.0.0.1 - - [15/Nov/2025 10:40:35] \"GET / HTTP/1.1\" 200 -",
  "metadata": [...],
  "labels": [...],
  "user_data": "{\"app\":\"codeengine\",\"message\":{...}}"
}
```

### Severity Levels

| Level | Name | Description |
|-------|------|-------------|
| 1 | DEBUG | Debug messages |
| 2 | VERBOSE | Verbose logging |
| 3 | INFO | Informational messages |
| 4 | WARNING | Warning messages |
| 5 | ERROR | Error conditions |
| 6 | CRITICAL | Critical failures |

### App Name Field

Code Engine logs include the full deployment pod name in the `app` field:
```
mcpfaildemo-00001-deployment-65884fb69b-dpp6p
  ^^^^^^^^^^                                    # App name
             ^^^^^                              # Revision
                   ^^^^^^^^^^                   # Deployment
                              ^^^^^^^^^^^^^^^^^  # Pod ID
```

## 🔍 DataPrime Query Language

### Basic Syntax

```
source logs | filter <condition> | limit N
```

### Query All Logs

```
source logs | limit 100
```

Returns up to 100 log entries from all sources.

### Filter by Time

Handled by query metadata:
```python
server.get_app_logs("app", hours=4)  # Last 4 hours
server.get_app_logs("app", hours=1)  # Last 1 hour
```

### Filter by Severity

```
source logs | filter $d.severity == '6' | limit 50
```

Get critical errors only.

### Filter by Application

**Note**: Code Engine logs use `ibm-platform-logs` as the application name. Actual app names are in the `user_data.message._app` field.

Current approach: Query all logs and filter app name in results:
```python
# Get all logs
logs = server.get_app_logs("mcpfaildemo", hours=4, limit=100)

# App name is already included in each log entry
for log in logs['logs']:
    if 'mcpfaildemo' in log['app']:
        print(log['message'])
```

### Complex Queries

DataPrime supports complex filtering, but due to nested JSON structure in Code Engine logs, the toolkit currently:
1. Queries all logs from a time range
2. Parses the full SSE stream response
3. Extracts app names from `user_data.message._app`
4. Returns formatted results with app names

## 🎯 Common Query Patterns

### Get Recent Logs for App

```python
logs = server.get_app_logs("mcpfaildemo", hours=1, limit=50)
```

Returns last 50 log entries from the past hour, showing all apps.

### Find Crashes and Errors

```python
logs = server.get_app_logs("mcpfaildemo", hours=4, limit=100)

for log in logs['logs']:
    # Look for crash indicators
    if any(keyword in log['message'].lower() for keyword in ['crash', 'oom', '💥', 'error']):
        print(f"[{log['severity']}] {log['timestamp']}")
        print(f"  {log['message']}")
```

### Monitor Specific App

```python
logs = server.get_app_logs("saminc", hours=2, limit=100)

# Filter by app name
for log in logs['logs']:
    if log['app'] and 'saminc' in log['app']:
        print(f"{log['timestamp']}: {log['message'][:100]}")
```

## 🔌 API Details

### Direct API Query

The `get_app_logs` tool uses the Cloud Logs REST API directly:

**Endpoint**:
```
POST https://{instance-guid}.api.{region}.logs.cloud.ibm.com/v1/query
```

**Headers**:
```
Authorization: Bearer {iam_token}
Content-Type: application/json
Accept: text/event-stream
```

**Request Body**:
```json
{
  "query": "source logs | limit 100",
  "metadata": {
    "start_date": "2025-11-15T09:00:00.000Z",
    "end_date": "2025-11-15T13:00:00.000Z",
    "tier": "frequent_search",
    "syntax": "dataprime",
    "limit": 100
  }
}
```

**Response**: Server-Sent Events (SSE) stream
```
: success
data: {"query_id":{"query_id":"..."}}

: success
data: {"result":{"results":[...]}}
```

### SSE Stream Parsing

The API returns results as a Server-Sent Events stream with two events:

1. **Query ID event**: Contains the query execution ID
2. **Result event**: Contains the actual log data

The toolkit:
1. Reads the complete `response.text` (not line-by-line)
2. Splits by SSE event boundaries (`\n\n`)
3. Parses JSON from `data:` lines
4. Extracts logs from `result.results[]`
5. Formats with timestamp, severity, app name, message

**Why not `iter_lines()`?**: The JSON in SSE streams can be very large (10KB+) and `iter_lines()` splits it incorrectly, causing parsing errors.

## 📝 Log Streaming from Apps

### From Memory Test App

The memory test app automatically logs all events to Cloud Logs:

```python
# In your application
import requests

def send_log(message, severity=3, **metadata):
    token = get_iam_token()
    
    log_entry = [{
        "applicationName": "my-app",
        "subsystemName": "backend",
        "text": message,
        "severity": severity,
        "timestamp": int(time.time() * 1000),
        "json": metadata
    }]
    
    response = requests.post(
        f"https://{instance_guid}.ingress.{region}.logs.cloud.ibm.com/logs/v1/singles",
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        },
        json=log_entry
    )
    
    return response.status_code in [200, 201, 204]
```

### Using Log Streamer

```python
from src.app_toolkit.log_streamer import CloudLogsStreamer

streamer = CloudLogsStreamer(
    instance_guid="175a2e16-a792-4f66-be4a-189a3b89e9fe",
    region="us-south"
)

# Send log
streamer.send_log("Application started", severity=3, version="1.0.0")

# Send error
streamer.send_log("Connection failed", severity=5, error_code=500)
```

## 🎭 Watson Orchestrate Integration

### Available Tool

**Tool**: `get_app_logs`

**Parameters**:
- `app_name` (string): Application name (currently ignored - returns all logs)
- `limit` (integer): Max log entries (1-500, default: 100)

**Returns**:
```json
{
  "success": true,
  "query_id": "8fb55ca5-1a53-47df-a7fd-b2145e0c0f22",
  "log_count": 100,
  "logs": [...],
  "time_range": "Last 4 hours: 2025-11-15T09:07:22 to 2025-11-15T13:07:22"
}
```

### Example Queries

Natural language queries in Watson Orchestrate:

```
"Show me logs from the last hour"
→ Returns 100 most recent log entries

"Get logs for mcpfaildemo"
→ Returns logs (all apps shown with app field)

"Find errors in the logs"
→ Returns logs (you'll need to filter severity in results)

"What happened in the last 4 hours?"
→ Returns 100 log entries from last 4 hours
```

## 🔧 Troubleshooting

### No Logs Returned

**Problem**: Query returns "No logs found"

**Solutions**:
1. **Wait longer**: Logs take 1-2 minutes to propagate
2. **Check time range**: Expand hours parameter
3. **Verify instance**: `echo $CLOUD_LOGS_INSTANCE_GUID`
4. **Check app is logging**: Query all logs first

### IAM Token Errors

**Problem**: "Failed to get IAM token"

**Solutions**:
1. Check API key: `echo $IBMCLOUD_API_KEY`
2. Verify API key has access: `ibmcloud iam api-keys`
3. Check token manually:
   ```bash
   curl -X POST https://iam.cloud.ibm.com/identity/token \
     -d "grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey=$IBMCLOUD_API_KEY"
   ```

### JSON Parse Errors

**Problem**: "JSON Parse Error" in logs

**Solutions**:
1. **Already fixed**: The current implementation reads `response.text` instead of `iter_lines()`
2. If still occurring, check toolkit version
3. The fix handles multi-line JSON in SSE streams

### Slow Queries

**Problem**: Queries take >10 seconds

**Solutions**:
1. **Using API**: The MCP server uses direct API (fast)
2. **Using CLI**: The CLI wrapper is slower (10-30s)
3. **Reduce limit**: Query fewer logs (limit=50 vs 100)
4. **Narrow time**: Query 1 hour instead of 4 hours

## 📚 Related Documentation

- [Memory Testing](memory-testing.md) - Test crash scenarios and validate logs
- [Tool Reference](tool-reference.md) - Complete API documentation
- [API Integration](api-integration.md) - Direct API usage patterns
- [Architecture](architecture.md) - How the log query system works

## 🔗 External Resources

- [IBM Cloud Logs API](https://cloud.ibm.com/apidocs/logs-service-api)
- [DataPrime Query Language](https://cloud.ibm.com/docs/cloud-logs?topic=cloud-logs-dataprime-query-language)
- [Cloud Logs Documentation](https://cloud.ibm.com/docs/cloud-logs)

---

**Next**: [Memory Testing Guide](memory-testing.md) →
