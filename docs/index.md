# Zeus - IBM Cloud Toolkit Documentation

Complete documentation for the Zeus IBM Cloud automation toolkit with Watson Orchestrate integration.

## 📚 Documentation Index

### Getting Started
- **[Quick Start Guide](quickstart.md)** - Get up and running in 5 minutes
- **[Installation](installation.md)** - Detailed installation instructions
- **[Configuration](configuration.md)** - Environment setup and configuration

### Core Components
- **[Cloud Toolkit](cloud-toolkit.md)** - 26 IBM Cloud management tools
- **[App Toolkit](app-toolkit.md)** - 6 memory test application control tools
- **[MCP Servers](mcp-servers.md)** - Model Context Protocol integration

### Features
- **[Cloud Logs Integration](cloud-logs.md)** - Query and stream logs
- **[Code Engine Management](code-engine.md)** - Application lifecycle management
- **[Auto Scaling](auto-scaling.md)** - Log-based automatic scaling
- **[Memory Testing](memory-testing.md)** - Crash testing and OOM scenarios

### Watson Orchestrate
- **[Deployment Guide](watson-orchestrate.md)** - Deploy toolkits to Watson Orchestrate
- **[Tool Reference](tool-reference.md)** - Complete tool API reference
- **[Toolkit Deployment](toolkit-deployment.md)** - Local MCP toolkit deployment methods

### Advanced Topics
- **[Architecture](architecture.md)** - System design and components
- **[API Integration](api-integration.md)** - Direct API usage without CLI
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

### Examples
- **[Usage Examples](examples.md)** - Real-world use cases
- **[Testing Scenarios](testing.md)** - How to test crashes and failures

## 🎯 What is Zeus?

Zeus is a comprehensive IBM Cloud automation toolkit that provides:

1. **32 Watson Orchestrate Tools** - Direct integration with Watson Orchestrate for natural language cloud operations
2. **Direct API Access** - Bypass CLI for faster operations (Cloud Logs query tool)
3. **MCP Integration** - Model Context Protocol servers for AI agent integration
4. **Memory Test App** - Purpose-built application for testing crash scenarios and logging

## 🏗️ Project Structure

```
zeus/
├── docs/                    # 📖 You are here
│   ├── index.md            # This file
│   ├── quickstart.md
│   ├── cloud-toolkit.md
│   └── ...
│
├── src/
│   ├── cloud-toolkit/      # IBM Cloud operations (26 tools)
│   │   ├── mcp_api_server.py      # MCP server with direct API access
│   │   ├── ibmcloud_toolkit.py    # Watson Orchestrate toolkit
│   │   └── auto_scaler_agent_v2.py
│   │
│   └── app-toolkit/        # Memory test app control (6 tools)
│       ├── memory_app_toolkit.py
│       └── memory-test-app/
│           └── app.py      # Flask app with /crash endpoint
│
├── config/                 # MCP server configurations
├── .env.toolkit           # Environment template
└── README.md              # Project overview
```

## 🚀 Quick Links

### Common Tasks
- [Deploy to Watson Orchestrate →](watson-orchestrate.md#deployment)
- [Query Cloud Logs →](cloud-logs.md#querying-logs)
- [Test Application Crashes →](memory-testing.md#crash-scenarios)
- [Scale Code Engine Apps →](code-engine.md#scaling)

### Tool Categories
- [Cloud Logs Tools (2) →](tool-reference.md#cloud-logs)
- [Code Engine Tools (6) →](tool-reference.md#code-engine)
- [Service Management Tools (8) →](tool-reference.md#services)
- [Resource Management Tools (5) →](tool-reference.md#resources)
- [Generic CLI Tools (5) →](tool-reference.md#cli)
- [Memory Test Tools (6) →](tool-reference.md#memory-test)

## 💡 Key Features

### 1. Direct API Integration
The Cloud Logs query tool bypasses the CLI entirely, using direct REST API calls for 10x faster queries:

```python
# Traditional CLI approach (slow)
ibmcloud logs query --query "source logs" --since 1h

# Zeus API approach (fast)
toolkit.query_cloud_logs("source logs", hours=1)
```

### 2. Watson Orchestrate Integration
All 32 tools are available in Watson Orchestrate for natural language cloud operations:

```
User: "Show me the logs for mcpfaildemo from the last 4 hours"
Orchestrate: Uses get_app_logs tool → Returns 100 log entries
```

### 3. Memory Test Application
Purpose-built app with multiple crash endpoints:

- `/crash` - POST endpoint to trigger crashes on demand
- `/start-memory-test` - Gradual memory consumption
- `/trigger-oom` - Immediate out-of-memory crash
- All crashes are logged to Cloud Logs for testing

### 4. MCP Server Support
Model Context Protocol servers for AI agents like Claude Desktop:

```bash
# Query logs directly from Claude
> Query my Cloud Logs for errors in the last hour

# Get app status
> What's the status of my Code Engine apps?
```

## 📊 Tool Statistics

| Toolkit | Tools | Category |
|---------|-------|----------|
| Cloud Toolkit | 27 | IBM Cloud Operations |
| App Toolkit | 6 | Memory Test Control |
| **Total** | **33** | **Watson Orchestrate** |

### Cloud Toolkit Breakdown
- Cloud Logs: 2 tools
- Code Engine: 7 tools (includes **rebuild_app**)
- Service Management: 8 tools
- Resource Management: 5 tools
- Configuration: 3 tools
- Generic CLI: 2 tools

## 🎓 Learning Path

### Beginner
1. [Installation](installation.md) - Set up your environment
2. [Quick Start](quickstart.md) - Run your first commands
3. [Cloud Logs](cloud-logs.md) - Query your logs

### Intermediate
4. [Code Engine](code-engine.md) - Manage applications
5. [Watson Orchestrate](watson-orchestrate.md) - Deploy toolkits
6. [Memory Testing](memory-testing.md) - Test crash scenarios

### Advanced
7. [Architecture](architecture.md) - Understand the system
8. [API Integration](api-integration.md) - Direct API usage
9. [Auto Scaling](auto-scaling.md) - Implement auto-scaling

## 🔗 External Resources

- [IBM Cloud Docs](https://cloud.ibm.com/docs)
- [Watson Orchestrate ADK](https://developer.watson-orchestrate.ibm.com/)
- [Cloud Logs API](https://cloud.ibm.com/apidocs/logs-service-api)
- [Code Engine Docs](https://cloud.ibm.com/docs/codeengine)

## 🆘 Getting Help

- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)
- **Examples**: Check [examples.md](examples.md)
- **Tool Reference**: Full API docs in [tool-reference.md](tool-reference.md)

---

**Next Steps**: Start with the [Quick Start Guide](quickstart.md) →
