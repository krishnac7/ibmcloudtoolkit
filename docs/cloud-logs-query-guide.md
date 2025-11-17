# Cloud Logs Query Guide

This guide explains how to query IBM Cloud Logs using the Cloud Logs API directly with curl.

## Prerequisites

- IBM Cloud API Key
- Cloud Logs instance ID
- Cloud Logs region

## Configuration

```bash
# IBM Cloud credentials
API_KEY="your-api-key-here"
CLOUD_LOGS_INSTANCE_ID="175a2e16-a792-4f66-be4a-189a3b89e9fe"
CLOUD_LOGS_REGION="us-south"
CLOUD_LOGS_ENDPOINT="https://${CLOUD_LOGS_INSTANCE_ID}.api.${CLOUD_LOGS_REGION}.logs.cloud.ibm.com"
```

## Step 1: Get IAM Token

First, obtain an IAM access token:

```bash
curl -X POST 'https://iam.cloud.ibm.com/identity/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=urn:ibm:params:oauth:grant-type:apikey' \
  -d "apikey=${API_KEY}" \
  -o /tmp/token.json

# Extract the token
TOKEN=$(cat /tmp/token.json | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

## Step 2: Query Logs

Query logs using the Cloud Logs Query API with DataPrime syntax:

```bash
curl -s -X POST "${CLOUD_LOGS_ENDPOINT}/v1/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "source logs | limit 300",
    "metadata": {
      "start_date": "2025-11-15T19:00:00.000Z",
      "end_date": "2025-11-15T21:00:00.000Z",
      "tier": "frequent_search",
      "syntax": "dataprime",
      "limit": 300
    }
  }'
```

### Response Format

The API returns data in Server-Sent Events (SSE) format:

```
: success
data: {"query_id":{"query_id":"..."}}

: success
data: {"result":{"results":[...]}}
```

## Step 3: Parse SSE Response

### Option 1: Save to File and Parse

```bash
# Save response to file
curl -s -X POST "${CLOUD_LOGS_ENDPOINT}/v1/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "source logs | limit 300",
    "metadata": {
      "start_date": "2025-11-15T19:00:00.000Z",
      "end_date": "2025-11-15T21:00:00.000Z",
      "tier": "frequent_search",
      "syntax": "dataprime",
      "limit": 300
    }
  }' > /tmp/logs_response.txt

# Parse with Python
python3 << 'EOF'
import json

with open('/tmp/logs_response.txt') as f:
    for line in f:
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])  # Skip "data: " prefix
                if 'result' in data and 'results' in data['result']:
                    for log in data['result']['results']:
                        # Parse log entry
                        user_data = json.loads(log['user_data'])
                        msg = user_data.get('message', {}).get('message', '')
                        app = user_data.get('message', {}).get('_app', '')
                        
                        # Extract metadata
                        ts = next((m['value'] for m in log['metadata'] if m['key'] == 'timestamp'), '')
                        sev = next((m['value'] for m in log['metadata'] if m['key'] == 'severity'), '')
                        
                        print(f"{ts[:19]} [sev {sev}] {app}: {msg[:150]}")
            except Exception as e:
                pass
EOF
```

### Option 2: Filter Specific Apps

```bash
python3 << 'EOF'
import json

with open('/tmp/logs_response.txt') as f:
    for line in f:
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if 'result' in data and 'results' in data['result']:
                    for log in data['result']['results']:
                        user_data = json.loads(log['user_data'])
                        app = user_data.get('message', {}).get('_app', '')
                        
                        # Filter for specific app
                        if 'mcpfaildemo' in app:
                            msg = user_data.get('message', {}).get('message', '')
                            ts = next((m['value'] for m in log['metadata'] if m['key'] == 'timestamp'), '')
                            sev = next((m['value'] for m in log['metadata'] if m['key'] == 'severity'), '')
                            print(f"{ts[:19]} [sev {sev}] {msg[:200]}")
            except: pass
EOF
```

### Option 3: Search for Keywords

```bash
python3 << 'EOF'
import json

keywords = ['threshold', '60%', '80%', '90%', 'PAUSED', 'gradual', 'crash']

with open('/tmp/logs_response.txt') as f:
    for line in f:
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if 'result' in data and 'results' in data['result']:
                    for log in data['result']['results']:
                        user_data = json.loads(log['user_data'])
                        msg = user_data.get('message', {}).get('message', '')
                        
                        # Check if any keyword appears in message
                        if any(keyword in msg for keyword in keywords):
                            app = user_data.get('message', {}).get('_app', '')
                            ts = next((m['value'] for m in log['metadata'] if m['key'] == 'timestamp'), '')
                            sev = next((m['value'] for m in log['metadata'] if m['key'] == 'severity'), '')
                            print(f"{ts[:19]} [sev {sev}] {msg[:180]}")
            except: pass
EOF
```

## Complete Example Script

Here's a complete script to query and parse Cloud Logs:

```bash
#!/bin/bash

# Configuration
API_KEY="your-api-key-here"
CLOUD_LOGS_INSTANCE_ID="175a2e16-a792-4f66-be4a-189a3b89e9fe"
CLOUD_LOGS_REGION="us-south"
CLOUD_LOGS_ENDPOINT="https://${CLOUD_LOGS_INSTANCE_ID}.api.${CLOUD_LOGS_REGION}.logs.cloud.ibm.com"

# Get IAM token
echo "Getting IAM token..."
curl -s -X POST 'https://iam.cloud.ibm.com/identity/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=urn:ibm:params:oauth:grant-type:apikey' \
  -d "apikey=${API_KEY}" > /tmp/token.json

TOKEN=$(cat /tmp/token.json | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# Query logs
echo "Querying logs..."
curl -s -X POST "${CLOUD_LOGS_ENDPOINT}/v1/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "source logs | limit 300",
    "metadata": {
      "start_date": "2025-11-15T19:00:00.000Z",
      "end_date": "2025-11-15T21:00:00.000Z",
      "tier": "frequent_search",
      "syntax": "dataprime",
      "limit": 300
    }
  }' > /tmp/logs_response.txt

# Parse and display
echo "Parsing logs..."
python3 << 'EOF'
import json

with open('/tmp/logs_response.txt') as f:
    count = 0
    for line in f:
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if 'result' in data and 'results' in data['result']:
                    for log in data['result']['results']:
                        user_data = json.loads(log['user_data'])
                        app = user_data.get('message', {}).get('_app', '')
                        
                        if 'mcpfaildemo' in app:
                            msg = user_data.get('message', {}).get('message', '')
                            ts = next((m['value'] for m in log['metadata'] if m['key'] == 'timestamp'), '')
                            sev = next((m['value'] for m in log['metadata'] if m['key'] == 'severity'), '')
                            print(f"{ts[:19]} [sev {sev}] {msg[:150]}")
                            count += 1
            except: pass
    
    print(f"\nTotal logs found: {count}")
EOF
```

## Log Structure

Each log entry contains:

```json
{
  "metadata": [
    {"key": "timestamp", "value": "2025-11-15T19:44:29..."},
    {"key": "severity", "value": "3"},
    {"key": "logid", "value": "..."},
    {"key": "branchid", "value": "..."}
  ],
  "labels": [
    {"key": "applicationname", "value": "ibm-platform-logs"},
    {"key": "subsystemname", "value": "codeengine:..."}
  ],
  "user_data": "{\"app\":\"codeengine\",\"message\":{\"message\":\"...\",\"_app\":\"mcpfaildemo-00013-...\"}}"
}
```

## Severity Levels

- `1` - DEBUG
- `3` - INFO
- `4` - WARNING
- `5` - ERROR
- `6` - CRITICAL

## Time Range Formats

Use ISO 8601 format for timestamps:

```bash
# Last hour
start_date=$(date -u -v-1H '+%Y-%m-%dT%H:%M:%S.000Z')
end_date=$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')

# Specific range
start_date="2025-11-15T19:00:00.000Z"
end_date="2025-11-15T21:00:00.000Z"
```

## DataPrime Query Syntax

Basic query patterns:

```dataprime
# Get all logs
source logs | limit 100

# Filter by app (when supported)
source logs | filter $d.message._app =~ /mcpfaildemo/ | limit 100

# Note: Complex filtering may require client-side parsing
# due to the nested JSON structure in user_data field
```

## Troubleshooting

### Empty Results

If you get no logs:
1. Check the time range - logs may be outside the specified window
2. Verify the Cloud Logs instance ID and region
3. Ensure the IAM token is valid (tokens expire after 1 hour)
4. Check that logs are being sent to the Cloud Logs instance

### Token Expired

IAM tokens expire after 1 hour. Re-run the token request:

```bash
curl -s -X POST 'https://iam.cloud.ibm.com/identity/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=urn:ibm:params:oauth:grant-type:apikey' \
  -d "apikey=${API_KEY}" > /tmp/token.json

TOKEN=$(cat /tmp/token.json | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

### SSE Parsing Issues

The response is in Server-Sent Events format. Each data line starts with `data: `. Make sure to:
1. Strip the `data: ` prefix before JSON parsing
2. Handle the nested JSON in the `user_data` field
3. Extract metadata values using key lookups

## References

- [IBM Cloud Logs API Documentation](https://cloud.ibm.com/apidocs/logs-service-api)
- [DataPrime Query Language](https://cloud.ibm.com/docs/cloud-logs?topic=cloud-logs-dataprime-reference)
- [IAM Token API](https://cloud.ibm.com/apidocs/iam-identity-token-api)
