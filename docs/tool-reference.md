# Cloud Toolkit - Tool Reference

Complete reference for all 27 tools in the IBM Cloud API toolkit.

## Tool Overview

| Category | Tools | Description |
|----------|-------|-------------|
| Cloud Logs | 2 | Query and stream logs from Cloud Logs |
| Code Engine | 7 | Manage Code Engine applications |
| Services | 8 | IBM Cloud service management |
| Resources | 5 | Resource group and account management |
| Configuration | 3 | IBM Cloud CLI configuration |
| Generic CLI | 2 | Execute arbitrary IBM Cloud CLI commands |

## Cloud Logs Tools

### get_app_logs
Query logs for a specific application from Cloud Logs.

**Parameters:**
- `app_name` (string, required): Application name
- `limit` (integer, optional): Max logs to return (default: 100, max: 500)

**Returns:**
```json
{
  "success": true,
  "query_id": "uuid",
  "log_count": 100,
  "logs": [...],
  "time_range": "Last 4 hours"
}
```

**Example:**
```bash
get_app_logs(app_name="mcpfaildemo", limit=50)
```

### query_cloud_logs
Execute arbitrary DataPrime query against Cloud Logs.

**Parameters:**
- `query` (string, required): DataPrime query
- `hours` (integer, optional): Time range in hours (default: 4)
- `limit` (integer, optional): Max results (default: 100)

**Returns:**
```json
{
  "success": true,
  "query_id": "uuid",
  "result_count": 50,
  "results": [...]
}
```

**Example:**
```bash
query_cloud_logs(
  query="source logs | filter severity >= 5 | limit 50",
  hours=1
)
```

## Code Engine Tools

### get_app_status
Get detailed status of a Code Engine application.

**Parameters:**
- `app_name` (string, required): Application name
- `project_id` (string, optional): Project ID (uses default if not provided)

**Returns:**
```json
{
  "success": true,
  "app": {
    "name": "mcpfaildemo",
    "status": "Ready",
    "url": "https://...",
    "scale_memory_limit": "2G",
    "scale_cpu_limit": "1",
    "scale_min_instances": 0,
    "scale_max_instances": 10,
    "image_reference": "..."
  }
}
```

### scale_app
Scale a Code Engine application instances.

**Parameters:**
- `app_name` (string, required): Application name
- `min_instances` (integer, optional): Minimum instances
- `max_instances` (integer, optional): Maximum instances

**Example:**
```bash
scale_app(app_name="mcpfaildemo", min_instances=1, max_instances=5)
```

### update_app_memory
Update memory allocation for a Code Engine application.

**Parameters:**
- `app_name` (string, required): Application name
- `memory` (string, required): Memory limit (Valid: 1G, 2G, 4G, 8G, 16G, 32G)

**Returns:**
```json
{
  "success": true,
  "message": "Updated mcpfaildemo memory to 4G",
  "app": {...}
}
```

**Note:** Code Engine only accepts memory values in gigabytes. Values like 256M or 512M are not supported.

### update_app_cpu
Update CPU allocation for a Code Engine application.

**Parameters:**
- `app_name` (string, required): Application name
- `cpu` (string, required): CPU limit (e.g., "0.5", "1", "2")

### restart_app
Restart a Code Engine application by updating a dummy environment variable.

**Parameters:**
- `app_name` (string, required): Application name

**Returns:**
```json
{
  "success": true,
  "message": "Restart initiated for mcpfaildemo"
}
```

### delete_app
Delete a Code Engine application.

**Parameters:**
- `app_name` (string, required): Application name

### rebuild_app ⭐ NEW
Rebuild a Code Engine application from source code without redeployment.

**Parameters:**
- `app_name` (string, required): Application name to rebuild
- `wait` (boolean, optional): Wait for rebuild to complete (default: false)
- `project_id` (string, optional): Project ID (uses default if not provided)

**Requirements:**
- App must be created with `--build-source`
- Source code must be in a Git repository or container registry

**Returns:**
```json
{
  "success": true,
  "message": "Rebuild initiated for mcpfaildemo",
  "app_name": "mcpfaildemo",
  "build_run": "rebuild-1731679234",
  "build_source": "https://github.com/user/repo",
  "build_strategy": "dockerfile",
  "status": "Ready",
  "waiting": false
}
```

**Use Cases:**
- Deploy code changes without full redeploy
- Force rebuild after source code updates
- Refresh container image from latest source
- Automated CI/CD pipelines

**Error Cases:**
```json
{
  "success": false,
  "error": "App has no build configuration",
  "suggestion": "App must be created with --build-source to support rebuilding"
}
```

**Example:**
```bash
# Basic rebuild
rebuild_app(app_name="mcpfaildemo")

# Rebuild and wait for completion
rebuild_app(app_name="mcpfaildemo", wait=true)
```

## Services Tools

### list_services
List all service instances in the current resource group.

### create_service
Create a new IBM Cloud service instance.

**Parameters:**
- `service_name` (string, required): Name for the instance
- `service_type` (string, required): Service type (e.g., "logs")
- `plan` (string, required): Service plan
- `location` (string, required): Region

### delete_service
Delete a service instance.

### bind_service
Bind a service to a Code Engine application.

### unbind_service  
Unbind a service from a Code Engine application.

### get_service_keys
List service keys for a service instance.

### create_service_key
Create a new service key.

### delete_service_key
Delete a service key.

## Resource Management Tools

### list_resource_groups
List all resource groups in the account.

### target_resource_group
Switch to a different resource group.

**Parameters:**
- `resource_group` (string, required): Resource group name

### list_regions
List available IBM Cloud regions.

### get_account_info
Get current IBM Cloud account information.

### list_projects
List all Code Engine projects.

## Configuration Tools

### get_cli_config
Get current IBM Cloud CLI configuration.

### target_region
Switch to a different region.

**Parameters:**
- `region` (string, required): Region name (e.g., "us-east", "us-south")

### login_status
Check IBM Cloud CLI login status.

## Generic CLI Tools

### execute_cli_command
Execute arbitrary IBM Cloud CLI command.

**Parameters:**
- `command` (string, required): CLI command to execute

**Example:**
```bash
execute_cli_command(command="ce project list")
```

### get_cli_help
Get help for IBM Cloud CLI commands.

**Parameters:**
- `command` (string, optional): Command to get help for

## Memory Test App Tools

See [Memory Testing Guide](memory-testing.md) for complete documentation.

### trigger_crash
Trigger a controlled application crash.

### start_memory_test
Start gradual memory consumption test.

### stop_memory_test
Stop memory consumption test.

### get_memory_stats
Get current memory statistics with threshold warnings.

**Returns:**
```json
{
  "process_rss_mb": 67.66,
  "process_percent": 1.14,
  "system_total_mb": 5924.56,
  "system_used_percent": 32.9,
  "threshold_status": {
    "level": "normal",
    "percent": 32.9,
    "warning_80": false,
    "warning_90": false
  }
}
```

### check_app_health
Check application health status.

### trigger_oom
Immediately trigger out-of-memory crash.

## Tool Usage Patterns

### Sequential Operations
```bash
# 1. Check app status
get_app_status(app_name="myapp")

# 2. Scale up for load
scale_app(app_name="myapp", min_instances=2, max_instances=10)

# 3. Update memory
update_app_memory(app_name="myapp", memory="4G")

# 4. Rebuild with latest code
rebuild_app(app_name="myapp")

# 5. Check logs after rebuild
get_app_logs(app_name="myapp", limit=50)
```

### Error Recovery
```bash
# 1. Check if app crashed
get_app_status(app_name="myapp")

# 2. Get recent logs
get_app_logs(app_name="myapp", limit=100)

# 3. Restart app
restart_app(app_name="myapp")

# 4. Scale up memory if OOM
update_app_memory(app_name="myapp", memory="4G")
```

### Deployment Pipeline
```bash
# 1. Trigger rebuild from git
rebuild_app(app_name="myapp", wait=true)

# 2. Verify deployment
get_app_status(app_name="myapp")

# 3. Check logs for errors
get_app_logs(app_name="myapp", limit=20)

# 4. Scale if needed
scale_app(app_name="myapp", min_instances=1, max_instances=5)
```

## Watson Orchestrate Usage

All tools are available in Watson Orchestrate via natural language:

```
User: "Show me the status of mcpfaildemo"
→ Calls: get_app_status(app_name="mcpfaildemo")

User: "Scale mcpfaildemo to max 5 instances"
→ Calls: scale_app(app_name="mcpfaildemo", max_instances=5)

User: "Get logs for mcpfaildemo from last hour"
→ Calls: get_app_logs(app_name="mcpfaildemo", limit=100)

User: "Rebuild mcpfaildemo from source"
→ Calls: rebuild_app(app_name="mcpfaildemo")

User: "Update mcpfaildemo memory to 4GB"
→ Calls: update_app_memory(app_name="mcpfaildemo", memory="4G")
```

## API vs CLI Performance

| Operation | CLI Time | API Time | Speedup |
|-----------|----------|----------|---------|
| Query 100 logs | ~12s | ~1.2s | 10x |
| Get app status | ~3s | ~0.5s | 6x |
| Update memory | ~4s | ~0.8s | 5x |
| Rebuild app | ~5s | ~1s | 5x |

The toolkit uses direct API calls for maximum performance, bypassing the IBM Cloud CLI where possible.

---

**Next**: See [Deployment Guide](toolkit-deployment.md) for deployment instructions
