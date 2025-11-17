# Memory Testing & Crash Scenarios

Complete guide to testing application crashes, out-of-memory scenarios, and log capture validation.

## 📝 Overview

The Zeus toolkit includes a purpose-built **Memory Test Application** deployed as `mcpfaildemo` that provides controlled crash scenarios for testing:

- **Immediate OOM crashes** - Allocate huge memory instantly
- **Gradual memory consumption** - Slowly fill memory until crash
- **Configurable delays** - Control when crashes occur
- **Full Cloud Logs integration** - All events logged to Cloud Logs
- **Request logging** - Every HTTP request logged automatically
- **80% memory warnings** - Proactive threshold monitoring

**Deployed App**: https://mcpfaildemo.1w7gl8ju83cj.us-east.codeengine.appdomain.cloud/

## 🆕 Recent Updates (November 2025)

### Request Logging
Every HTTP request is automatically logged to Cloud Logs:
- 📥 **Incoming request**: method, path, client IP, User-Agent, memory usage
- 📤 **Response**: status code, duration (ms), response size, memory after
- 🆔 **Request IDs**: Unique IDs for request correlation
- ⚖️ **Automatic severity**: INFO (2xx), WARNING (4xx), ERROR (5xx)

### 80% Memory Warning System  
Proactive memory monitoring with automatic warnings:
- ⚠️ **WARNING log** at 80% memory threshold
- 🚨 **CRITICAL log** at 90% memory threshold
- ✅ Auto-resets when memory drops below thresholds
- 📊 Includes `process_percent` and `threshold_status` in all responses

### Enhanced Error Logging
Comprehensive exception handling:
- Catches `MemoryError`, `OSError`, and generic exceptions
- Logs error type, message, and errno (for OSError)
- Includes full memory stats in all error logs
- Handles cases where logging itself fails during OOM

## 🎯 Use Cases

1. **Validate logging** - Ensure crashes are captured in Cloud Logs
2. **Test auto-scaling** - Trigger OOM to test scaling policies
3. **Monitor alerting** - Verify alerts fire on crashes
4. **Test recovery** - Validate Code Engine restarts apps
5. **Load testing** - Simulate memory pressure

## 🔧 Memory Test App Endpoints

### Health Check
```bash
GET /
```

Returns app status and available endpoints:
```json
{
  "status": "running",
  "app": "memory-test-app",
  "memory_test_active": false,
  "memory_stats": {
    "process_rss_mb": 45.2,
    "system_total_mb": 4096,
    "system_used_percent": 65.3
  },
  "endpoints": {
    "/crash": "POST - Initiate memory crash",
    "/start-memory-test": "Start gradual consumption",
    "/trigger-oom": "Immediate OOM"
  }
}
```

### Crash Endpoint (Primary)
```bash
POST /crash
Content-Type: application/json

{
  "type": "oom",       # "oom" or "gradual"
  "delay": 5           # seconds to wait
}
```

**Response**:
```json
{
  "status": "crash_initiated",
  "type": "immediate_oom",
  "message": "OOM will occur in 5 seconds",
  "delay_seconds": 5,
  "current_memory": {...}
}
```

### Gradual Memory Test
```bash
GET /start-memory-test
```

Starts consuming memory in 50MB chunks every 2 seconds until OOM.

**Response**:
```json
{
  "status": "started",
  "message": "Memory test initiated",
  "current_memory": {...}
}
```

**Stop it**:
```bash
GET /stop-memory-test
```

### Immediate OOM
```bash
GET /trigger-oom
```

Attempts to allocate 10GB immediately (deprecated - use `/crash` instead).

## 🚀 Usage Examples

### Example 1: Test Immediate Crash

Using curl:
```bash
curl -X POST https://mcpfaildemo.1w7gl8ju83cj.us-east.codeengine.appdomain.cloud/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "oom", "delay": 10}'
```

Using Watson Orchestrate:
```
"Trigger a crash on mcpfaildemo with 10 second delay"
```

Using Python:
```python
from src.app-toolkit.memory_app_toolkit import MemoryTestAppToolkit

toolkit = MemoryTestAppToolkit()
result = toolkit.trigger_crash(
    crash_type="oom",
    delay_seconds=10
)
print(result)
```

**What happens**:
1. App logs crash initiation to Cloud Logs
2. Waits 10 seconds
3. Attempts to allocate 10GB of memory
4. Container crashes with OOM error
5. Code Engine restarts the container
6. All events are logged

### Example 2: Gradual Memory Consumption

```bash
# Start gradual test
curl https://mcpfaildemo.1w7gl8ju83cj.us-east.codeengine.appdomain.cloud/start-memory-test

# Monitor logs
ibmcloud logs query --query "source logs | filter \$d.applicationname == 'mcpfaildemo'" --since 5m

# Stop test (if needed)
curl https://mcpfaildemo.1w7gl8ju83cj.us-east.codeengine.appdomain.cloud/stop-memory-test
```

Using Watson Orchestrate:
```
"Start a gradual memory test on mcpfaildemo"
```

**What happens**:
1. Allocates 50MB every 2 seconds
2. Logs every 5 iterations or when memory > 80%
3. Warning logs at 80%
4. Error logs at 90%
5. Critical logs at 95%
6. Eventually crashes with OOM
7. Container restarts automatically

### Example 3: Verify Logs Captured Crash

```python
from src.cloud-toolkit.mcp_api_server import CloudAPIServer

# Wait 2 minutes after crash for logs to propagate
import time
time.sleep(120)

# Query logs
server = CloudAPIServer()
result = server.get_app_logs("mcpfaildemo", hours=1, limit=100)

# Look for crash indicators
print(result)
```

Expected log entries:
```
[2025-11-15T10:40:00] WARNING
  🔥 Crash initiated via /crash endpoint - type: oom

[2025-11-15T10:40:05] ERROR
  Allocating 10GB chunk...

[2025-11-15T10:40:06] CRITICAL
  💥 OOM triggered successfully!

[2025-11-15T10:40:10] INFO
  Memory test application started  # <- Container restarted
```

## 📊 Log Severity Levels

The memory test app uses standard severity levels:

| Severity | Name | Use Case |
|----------|------|----------|
| 1 | DEBUG | Debug mode messages |
| 3 | INFO | Normal operations, startup |
| 4 | WARNING | Memory > 80%, crash initiated |
| 5 | ERROR | Memory > 90%, errors occurred |
| 6 | CRITICAL | Memory > 95%, OOM events |

## 🔍 Monitoring Crash Events

### Using Watson Orchestrate

```
"Get logs for mcpfaildemo from the last hour"
```

The `get_app_logs` tool will return all logs including crash events.

### Using MCP Server

If you have the MCP server running in Claude Desktop:
```
> Query Cloud Logs for mcpfaildemo errors in the last hour
```

### Using Python API

```python
from src.cloud-toolkit.mcp_api_server import CloudAPIServer

server = CloudAPIServer()

# Get recent logs
logs = server.get_app_logs("mcpfaildemo", hours=1, limit=100)

# Parse for crashes
for log in logs['logs']:
    if '💥' in log['message'] or 'OOM' in log['message']:
        print(f"[CRASH] {log['timestamp']}: {log['message']}")
```

## 📈 Memory Stats Endpoint

Query current memory usage without triggering crashes:

```bash
curl https://mcpfaildemo.1w7gl8ju83cj.us-east.codeengine.appdomain.cloud/memory-stats
```

Response:
```json
{
  "process_rss_mb": 52.3,
  "process_vms_mb": 102.5,
  "system_total_mb": 4096,
  "system_available_mb": 2048,
  "system_used_percent": 50.0
}
```

## ⚠️ Important Notes

### Crash Recovery
- **Automatic restart**: Code Engine automatically restarts crashed containers
- **Restart delay**: ~10-30 seconds for container to be ready
- **State loss**: All in-memory data is lost (allocated_memory array cleared)
- **No downtime**: Code Engine routes traffic to healthy instances

### Log Propagation
- **Delay**: Logs may take 1-2 minutes to appear in Cloud Logs
- **Buffering**: Cloud Logs ingestion has a buffer period
- **Ordering**: Log order is preserved but timestamps may vary slightly

### Memory Limits
- **Code Engine default**: 4GB RAM per instance
- **OOM threshold**: Crash occurs when attempting allocation beyond limit
- **Kubernetes OOM**: Container killed by kernel OOM killer

### Best Practices
1. **Wait for logs**: Allow 2-3 minutes after crash before querying logs
2. **Use delays**: Add 5-10 second delays to see pre-crash logs
3. **Monitor health**: Check `/` endpoint before and after crashes
4. **Test in non-prod**: Crashes will disrupt service temporarily

## 🧪 Testing Scenarios

### Scenario 1: Validate Cloud Logs Capture

**Goal**: Ensure crashes are logged to Cloud Logs

```bash
# 1. Trigger crash with delay
curl -X POST https://mcpfaildemo.../crash \
  -H "Content-Type: application/json" \
  -d '{"type": "oom", "delay": 10}'

# 2. Wait 3 minutes for logs to propagate
sleep 180

# 3. Query logs
python -c "
from src.cloud_toolkit.mcp_api_server import CloudAPIServer
server = CloudAPIServer()
print(server.get_app_logs('mcpfaildemo', hours=1, limit=50))
"

# 4. Verify crash logs present
# Look for: "Crash initiated", "OOM triggered", "application started" (restart)
```

### Scenario 2: Test Auto-Scaling Response

**Goal**: Trigger crashes to test if auto-scaler responds

```bash
# 1. Get current scale
ibmcloud ce app get --name mcpfaildemo

# 2. Trigger multiple crashes
for i in {1..5}; do
  curl -X POST https://mcpfaildemo.../crash \
    -H "Content-Type: application/json" \
    -d '{"type": "oom", "delay": 5}'
  sleep 30
done

# 3. Check if auto-scaler increased instances
python src/cloud-toolkit/auto_scaler_agent_v2.py \
  --app mcpfaildemo \
  --project-name zeus-project
```

### Scenario 3: Gradual Memory Exhaustion

**Goal**: Simulate slow memory leak

```bash
# 1. Start gradual test
curl https://mcpfaildemo.../start-memory-test

# 2. Monitor memory stats
watch -n 5 'curl -s https://mcpfaildemo.../memory-stats | jq'

# 3. Query logs every minute
while true; do
  ibmcloud logs query \
    --query "source logs | filter \$d.applicationname == 'mcpfaildemo' | limit 10" \
    --since 1m
  sleep 60
done
```

## 🔧 Troubleshooting

### Crash Not Logged

**Problem**: Triggered crash but no logs in Cloud Logs

**Solutions**:
1. Wait longer - logs can take 2-3 minutes
2. Check Cloud Logs instance configured: `echo $CLOUD_LOGS_ENDPOINT`
3. Verify IAM token valid: Check app logs for "IAM token" errors
4. Query wider time range: Last 10 minutes instead of 5

### App Won't Restart

**Problem**: Container stays in crashed state

**Solutions**:
1. Check Code Engine app status: `ibmcloud ce app get --name mcpfaildemo`
2. Look for configuration issues: `ibmcloud ce app events --name mcpfaildemo`
3. Redeploy if needed: `ibmcloud ce app update --name mcpfaildemo --min-scale 1`

### Can't Trigger Crash

**Problem**: `/crash` endpoint returns error

**Solutions**:
1. Check request format: Must be POST with JSON body
2. Verify app reachable: `curl https://mcpfaildemo.../`
3. Check if test already running: Stop with `/stop-memory-test`

## 📚 Related Documentation

- [Cloud Logs Integration](cloud-logs.md) - How to query logs
- [Code Engine Management](code-engine.md) - Managing apps
- [Auto Scaling](auto-scaling.md) - Automatic scaling based on logs
- [Tool Reference](tool-reference.md) - App toolkit API reference

---

**Next**: [Auto Scaling Guide](auto-scaling.md) →
