#!/usr/bin/env python3
"""
IBM Cloud Logs MCP Server - API-based (no CLI required)
Uses IBM Cloud REST APIs directly
"""

import os
import sys
import json
import requests
from typing import Dict, Any
from datetime import datetime, timedelta
from icr_toolkit_api import ICRToolkitAPI

class CloudLogsAPIMCPServer:
    def __init__(self):
        # Credentials injected by deploy script from .env file
        self.api_key = '__IBMCLOUD_API_KEY__'
        self.account_id = '__IBMCLOUD_ACCOUNT_ID__'
        self.region = '__IBMCLOUD_REGION__'
        self.project_id = '__CODE_ENGINE_PROJECT_ID__'
        self.cloud_logs_instance_id = '__CLOUD_LOGS_INSTANCE_ID__'
        self.cloud_logs_instance_guid = '__CLOUD_LOGS_INSTANCE_GUID__'
        self.cloud_logs_region = '__CLOUD_LOGS_REGION__'
        self.cloud_logs_endpoint = f'https://{self.cloud_logs_instance_id}.api.{self.cloud_logs_region}.logs.cloud.ibm.com'
        self.iam_token = None
        self.token_expiry = None
        self._icr_toolkit = None
    
    @property
    def icr_toolkit(self):
        """Lazy initialization of ICR toolkit"""
        if self._icr_toolkit is None:
            self._icr_toolkit = ICRToolkitAPI(api_key=self.api_key, region=self.cloud_logs_region)
        return self._icr_toolkit
    
    def _get_iam_token(self) -> str:
        """Get IBM Cloud IAM token"""
        if self.iam_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.iam_token
        
        if not self.api_key:
            return None
        
        try:
            response = requests.post(
                'https://iam.cloud.ibm.com/identity/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
                    'apikey': self.api_key
                },
                timeout=30
            )
            
            if response.status_code != 200:
                import sys
                print(f"IAM token error: {response.status_code} - {response.text[:200]}", file=sys.stderr)
                return None
            
            response.raise_for_status()
            data = response.json()
            self.iam_token = data['access_token']
            self.token_expiry = datetime.now() + timedelta(minutes=50)
            return self.iam_token
        except requests.Timeout:
            import sys
            print("IAM token request timed out", file=sys.stderr)
            return None
        except Exception as e:
            import sys
            print(f"IAM token error: {type(e).__name__} - {str(e)[:200]}", file=sys.stderr)
            return None
    
    def _call_code_engine_api(self, endpoint: str, project_id: str, method: str = 'GET', data: dict = None, etag: str = None) -> Dict[str, Any]:
        """Call Code Engine API with support for GET, POST, PATCH, DELETE"""
        try:
            token = self._get_iam_token()
            if not token:
                return {'success': False, 'error': 'Failed to get IAM token. Check API key configuration.', 'details': 'IBMCLOUD_API_KEY not configured or invalid'}
            
            url = f"https://api.{self.region}.codeengine.cloud.ibm.com/v2/projects/{project_id}/{endpoint}"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            if method in ['POST', 'PATCH', 'PUT'] and data:
                headers['Content-Type'] = 'application/json'
            
            if method in ['PATCH', 'PUT'] and etag:
                headers['If-Match'] = etag
            
            timeout = 30
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return {'success': False, 'error': f'Unsupported HTTP method: {method}'}
            
            if response.status_code in [200, 201, 202]:
                return {'success': True, 'data': response.json()}
            else:
                error_detail = response.text[:500] if response.text else 'No error details'
                return {
                    'success': False, 
                    'error': f"API returned {response.status_code}",
                    'details': error_detail,
                    'url': url,
                    'method': method
                }
        except requests.Timeout:
            return {
                'success': False, 
                'error': 'API request timed out after 30 seconds',
                'details': f'Endpoint: {endpoint}',
                'suggestion': 'Check network connectivity or try again'
            }
        except requests.ConnectionError as e:
            return {
                'success': False,
                'error': 'Connection error',
                'details': str(e)[:200],
                'suggestion': 'Check internet connectivity'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"API error: {type(e).__name__}",
                'details': str(e)[:300]
            }
    
    def get_tools_list(self):
        """List available tools"""
        return {
            "tools": [
                {
                    "name": "get_code_engine_apps",
                    "description": "List Code Engine applications in a project",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "get_app_status",
                    "description": "Get status of a Code Engine application",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name (e.g., mcpfaildemo)"
                            }
                        },
                        "required": ["app_name"]
                    }
                },
                {
                    "name": "rebuild_app",
                    "description": "Rebuild a Code Engine application from source code. Forces a new build from the configured source repository.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {
                                "type": "string",
                                "description": "Code Engine project ID (optional, uses default if not provided)"
                            },
                            "app_name": {
                                "type": "string",
                                "description": "Name of the application to rebuild"
                            },
                            "wait": {
                                "type": "boolean",
                                "description": "Wait for rebuild to complete (default: false)",
                                "default": False
                            }
                        },
                        "required": ["app_name"]
                    }
                },
                {
                    "name": "update_app_memory",
                    "description": "Update memory allocation for a Code Engine app",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name (e.g., mcpfaildemo)"
                            },
                            "memory": {
                                "type": "string",
                                "description": "Memory limit - Valid values: 250M, 500M, 1G, 2G, 4G, 8G, 16G, 32G"
                            }
                        },
                        "required": ["app_name", "memory"]
                    }
                },
                {
                    "name": "update_app_cpu",
                    "description": "Update CPU allocation for a Code Engine app",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name (e.g., mcpfaildemo)"
                            },
                            "cpu": {
                                "type": "string",
                                "description": "CPU limit (e.g., 0.125, 0.25, 0.5, 1, 2)"
                            }
                        },
                        "required": ["app_name", "cpu"]
                    }
                },
                {
                    "name": "scale_app_instances",
                    "description": "Update min/max instance scaling for a Code Engine app",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name (e.g., mcpfaildemo)"
                            },
                            "min_instances": {
                                "type": "integer",
                                "description": "Minimum instances (0 or more)"
                            },
                            "max_instances": {
                                "type": "integer",
                                "description": "Maximum instances (1 or more)"
                            }
                        },
                        "required": ["app_name"]
                    }
                },
                {
                    "name": "update_app_config",
                    "description": "Update multiple configuration settings for a Code Engine app at once",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name (e.g., mcpfaildemo)"
                            },
                            "memory": {
                                "type": "string",
                                "description": "Memory limit - Valid values: 250M, 500M, 1G, 2G, 4G, 8G, 16G, 32G"
                            },
                            "cpu": {
                                "type": "string",
                                "description": "CPU limit (e.g., 0.125, 0.25, 0.5, 1)"
                            },
                            "min_instances": {
                                "type": "integer",
                                "description": "Minimum instances"
                            },
                            "max_instances": {
                                "type": "integer",
                                "description": "Maximum instances"
                            }
                        },
                        "required": ["app_name"]
                    }
                },
                {
                    "name": "restart_app",
                    "description": "Force restart a Code Engine app by creating a new revision",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name (e.g., mcpfaildemo)"
                            }
                        },
                        "required": ["app_name"]
                    }
                },
                {
                    "name": "get_app_logs",
                    "description": "Get recent logs for a Code Engine application. Returns logs from today by default (since midnight UTC), filtered by app name (default: mcpfaildemo)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Application name to filter logs (default: mcpfaildemo)",
                                "default": "mcpfaildemo"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of log lines to retrieve (default: 100, max: 500)"
                            },
                            "hours": {
                                "type": "integer",
                                "description": "Number of hours to look back (default: today since midnight UTC, max: 168 for 7 days)"
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "list_resource_instances",
                    "description": "List IBM Cloud resource instances (services) in the account",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "resource_group": {
                                "type": "string",
                                "description": "Filter by resource group name (optional)"
                            },
                            "service_name": {
                                "type": "string",
                                "description": "Filter by service name like 'logs', 'code-engine', etc. (optional)"
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "list_icr_images",
                    "description": "List container images in IBM Container Registry",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "description": "Filter by namespace (e.g., testdeploy)"
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "list_icr_namespaces",
                    "description": "List all ICR namespaces in the account",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "delete_icr_image",
                    "description": "Delete an image from IBM Container Registry",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "image": {
                                "type": "string",
                                "description": "Full image path (e.g., us.icr.io/testdeploy/myimage:latest)"
                            }
                        },
                        "required": ["image"]
                    }
                },
                {
                    "name": "get_icr_quota",
                    "description": "Get ICR storage and traffic quota information",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]
        }
    
    def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool"""
        
        if tool_name == "get_code_engine_apps":
            project_id = arguments.get('project_id', self.project_id)
            # Correct endpoint: apps with optional query parameters
            result = self._call_code_engine_api('apps?limit=100', project_id)
            
            if result['success']:
                apps = result['data'].get('apps', [])
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "project_id": project_id,
                            "apps": apps,
                            "count": len(apps)
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to get apps')
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "get_app_status":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            
            result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            
            if result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "app": result['data']
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to get app status')
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "rebuild_app":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            wait = arguments.get('wait', False)
            
            # Get current app to retrieve build configuration and etag
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            if not get_result['success']:
                error_msg = get_result.get('error', 'Unknown error')
                error_details = get_result.get('details', '')
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Failed to get app configuration: {error_msg}",
                            "details": error_details,
                            "app_name": app_name,
                            "suggestion": "Check that app exists and has build configuration"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            app_data = get_result['data']
            etag = app_data.get('entity_tag')
            
            # Check if app has build configuration
            if 'build' not in app_data or not app_data['build']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "App has no build configuration",
                            "app_name": app_name,
                            "suggestion": "App must be created with --build-source to support rebuilding",
                            "current_image": app_data.get('image_reference')
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            # Trigger rebuild by updating build run name (forces new build)
            import time
            patch_data = {
                "build_run": f"rebuild-{int(time.time())}"
            }
            
            result = self._call_code_engine_api(
                f'apps/{app_name}',
                project_id,
                method='PATCH',
                data=patch_data,
                etag=etag
            )
            
            if result['success']:
                app_result = result['data']
                build_info = app_result.get('build', {})
                
                response_data = {
                    "success": True,
                    "message": f"Rebuild initiated for {app_name}",
                    "app_name": app_name,
                    "build_run": patch_data['build_run'],
                    "build_source": build_info.get('source_url'),
                    "build_strategy": build_info.get('strategy_type'),
                    "status": app_result.get('status'),
                    "waiting": wait
                }
                
                if wait:
                    response_data['note'] = "Build is in progress. Use get_app_status to check build completion."
                
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(response_data, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to trigger rebuild'),
                            "details": result.get('details', 'No additional details available'),
                            "url": result.get('url'),
                            "method": result.get('method'),
                            "app_name": app_name
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "rebuild_app":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            wait = arguments.get('wait', False)
            
            # Get current app to retrieve build configuration and etag
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            if not get_result['success']:
                error_msg = get_result.get('error', 'Unknown error')
                error_details = get_result.get('details', '')
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Failed to get app configuration: {error_msg}",
                            "details": error_details,
                            "app_name": app_name,
                            "suggestion": "Check that app exists and has build configuration"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            app_data = get_result['data']
            etag = app_data.get('entity_tag')
            
            # Check if app has build configuration
            if 'build' not in app_data or not app_data['build']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "App has no build configuration",
                            "app_name": app_name,
                            "suggestion": "App must be created with --build-source to support rebuilding",
                            "current_image": app_data.get('image_reference')
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            # Trigger rebuild by updating build run name (forces new build)
            import time
            patch_data = {
                "build_run": f"rebuild-{int(time.time())}"
            }
            
            result = self._call_code_engine_api(
                f'apps/{app_name}',
                project_id,
                method='PATCH',
                data=patch_data,
                etag=etag
            )
            
            if result['success']:
                app_result = result['data']
                build_info = app_result.get('build', {})
                
                response_data = {
                    "success": True,
                    "message": f"Rebuild initiated for {app_name}",
                    "app_name": app_name,
                    "build_run": patch_data['build_run'],
                    "build_source": build_info.get('source_url'),
                    "build_strategy": build_info.get('strategy_type'),
                    "status": app_result.get('status'),
                    "waiting": wait
                }
                
                if wait:
                    response_data['note'] = "Build is in progress. Use get_app_status to check build completion."
                
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(response_data, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to trigger rebuild'),
                            "details": result.get('details', 'No additional details available'),
                            "url": result.get('url'),
                            "method": result.get('method'),
                            "app_name": app_name
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "update_app_memory":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            memory = arguments.get('memory')
            
            # Validate memory format - Code Engine only accepts G (gigabyte) values
            valid_memory_values = ['1G', '2G', '4G', '8G', '16G', '32G']
            if memory not in valid_memory_values:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Invalid memory value: {memory}",
                            "valid_values": valid_memory_values,
                            "note": "Code Engine only accepts memory values in gigabytes (G), not megabytes (M)",
                            "requested_memory": memory,
                            "suggestion": f"Use one of these values: {', '.join(valid_memory_values)}"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            # Get current app to retrieve etag
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            if not get_result['success']:
                error_msg = get_result.get('error', 'Unknown error')
                error_details = get_result.get('details', '')
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Failed to get current app configuration: {error_msg}",
                            "details": error_details,
                            "app_name": app_name,
                            "suggestion": "Check that app exists and API key is valid"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            etag = get_result['data'].get('entity_tag')
            
            # PATCH request to update memory
            patch_data = {
                "scale_memory_limit": memory
            }
            
            result = self._call_code_engine_api(f'apps/{app_name}', project_id, method='PATCH', data=patch_data, etag=etag)
            
            if result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "message": f"Updated {app_name} memory to {memory}",
                            "app": result['data']
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to update memory'),
                            "details": result.get('details', 'No additional details available'),
                            "url": result.get('url'),
                            "method": result.get('method'),
                            "app_name": app_name,
                            "requested_memory": memory
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "update_app_cpu":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            cpu = arguments.get('cpu')
            
            # Get current app to retrieve etag
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            if not get_result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "Failed to get current app configuration"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            etag = get_result['data'].get('entity_tag')
            
            # PATCH request to update CPU
            patch_data = {
                "scale_cpu_limit": cpu
            }
            
            result = self._call_code_engine_api(f'apps/{app_name}', project_id, method='PATCH', data=patch_data, etag=etag)
            
            if result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "message": f"Updated {app_name} CPU to {cpu}",
                            "app": result['data']
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to update CPU')
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "scale_app_instances":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            min_instances = arguments.get('min_instances')
            max_instances = arguments.get('max_instances')
            
            # Build PATCH data with only provided values
            patch_data = {}
            if min_instances is not None:
                patch_data['scale_min_instances'] = min_instances
            if max_instances is not None:
                patch_data['scale_max_instances'] = max_instances
            
            if not patch_data:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "Must provide at least min_instances or max_instances"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            # Get current app to retrieve etag
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            if not get_result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "Failed to get current app configuration"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            etag = get_result['data'].get('entity_tag')
            
            result = self._call_code_engine_api(f'apps/{app_name}', project_id, method='PATCH', data=patch_data, etag=etag)
            
            if result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "message": f"Updated {app_name} instance scaling",
                            "app": result['data']
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to update instance scaling')
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "update_app_config":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            
            # Build PATCH data with all provided values
            patch_data = {}
            if arguments.get('memory'):
                patch_data['scale_memory_limit'] = arguments['memory']
            if arguments.get('cpu'):
                patch_data['scale_cpu_limit'] = arguments['cpu']
            if arguments.get('min_instances') is not None:
                patch_data['scale_min_instances'] = arguments['min_instances']
            if arguments.get('max_instances') is not None:
                patch_data['scale_max_instances'] = arguments['max_instances']
            
            if not patch_data:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "Must provide at least one configuration value to update"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            # Get current app to retrieve etag
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            if not get_result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "Failed to get current app configuration"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            etag = get_result['data'].get('entity_tag')
            
            result = self._call_code_engine_api(f'apps/{app_name}', project_id, method='PATCH', data=patch_data, etag=etag)
            
            if result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "message": f"Updated {app_name} configuration",
                            "updates": patch_data,
                            "app": result['data']
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to update configuration')
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "restart_app":
            project_id = arguments.get('project_id', self.project_id)
            app_name = arguments.get('app_name')
            
            # Get current app config first
            get_result = self._call_code_engine_api(f'apps/{app_name}', project_id)
            
            if not get_result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": "Failed to get current app configuration"
                        }, indent=2)
                    }],
                    "isError": True
                }
            
            etag = get_result['data'].get('entity_tag')
            
            # Force a new revision by patching with a dummy environment variable
            import time
            patch_data = {
                "run_env_variables": get_result['data'].get('run_env_variables', []) + [
                    {
                        "type": "literal",
                        "name": "RESTART_TRIGGER",
                        "value": str(int(time.time()))
                    }
                ]
            }
            
            result = self._call_code_engine_api(f'apps/{app_name}', project_id, method='PATCH', data=patch_data, etag=etag)
            
            if result['success']:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "message": f"Restarted {app_name} (new revision created)",
                            "app": result['data']
                        }, indent=2)
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": result.get('error', 'Failed to restart app')
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "get_app_logs":
            app_name = arguments.get('app_name', 'mcpfaildemo')  # Default to mcpfaildemo
            limit = arguments.get('limit', 100)
            hours = arguments.get('hours')  # None = default to "today"
            
            # Limit to max 500 lines
            if limit > 500:
                limit = 500
            
            # Use Cloud Logs query API - results come in SSE stream
            from datetime import datetime, timedelta
            
            # Calculate time range
            end_time = datetime.utcnow()
            
            if hours is None:
                # Default: logs from today (since midnight UTC)
                start_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Limit to max 7 days (168 hours)
                if hours > 168:
                    hours = 168
                start_time = end_time - timedelta(hours=hours)
            
            try:
                token = self._get_iam_token()
                if not token:
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": "Failed to get IAM token for Cloud Logs query"
                            }, indent=2)
                        }],
                        "isError": True
                    }
                
                query_url = f"{self.cloud_logs_endpoint}/v1/query"
                query_payload = {
                    "query": f"source logs | limit {limit}",
                    "metadata": {
                        "start_date": start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "end_date": end_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "tier": "frequent_search",
                        "syntax": "dataprime",
                        "limit": limit
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
                
                # Submit query and read SSE stream for results
                response = requests.post(query_url, headers=headers, json=query_payload, timeout=120, stream=True)
                
                if response.status_code != 200:
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": f"Query submission failed: {response.status_code}",
                                "details": response.text,
                                "app_name": app_name
                            }, indent=2)
                        }],
                        "isError": True
                    }
                
                # Parse SSE stream - query_id comes first, then results
                # Read the entire response text since JSON can span multiple iter_lines
                query_id = None
                logs_data = None
                
                response_text = response.text
                
                # Split by SSE event boundaries (empty lines between events)
                for event in response_text.split('\n\n'):
                    if 'data: ' in event:
                        # Extract the data portion
                        for line in event.split('\n'):
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])
                                    if 'query_id' in data:
                                        query_id = data['query_id']['query_id']
                                    elif 'result' in data:
                                        logs_data = data['result']
                                        break
                                except json.JSONDecodeError:
                                    pass
                    if logs_data:
                        break
                
                if not logs_data:
                    time_desc = "today" if hours is None else f"the last {hours} hours"
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": "No logs found or query timeout",
                                "query_id": query_id,
                                "time_range": time_desc,
                                "suggestion": f"No logs found for {time_desc}. Try increasing the time range with the 'hours' parameter."
                            }, indent=2)
                        }],
                        "isError": False
                    }
                
                # Format the logs nicely
                results = logs_data.get('results', [])
                formatted_logs = []
                
                for log_entry in results:
                    # Extract key fields
                    timestamp = None
                    message = None
                    severity = None
                    app_name_from_log = None
                    
                    for meta in log_entry.get('metadata', []):
                        if meta['key'] == 'timestamp':
                            timestamp = meta['value']
                        elif meta['key'] == 'severity':
                            severity = meta['value']
                    
                    user_data = log_entry.get('user_data', '')
                    if user_data:
                        try:
                            user_json = json.loads(user_data)
                            message = user_json.get('message', {}).get('message', user_data[:200])
                            app_name_from_log = user_json.get('message', {}).get('_app', 'unknown')
                        except:
                            message = user_data[:200]
                    
                    # Filter by app name if specified (case-insensitive partial match)
                    if app_name and app_name_from_log:
                        if app_name.lower() not in app_name_from_log.lower():
                            continue
                    
                    formatted_logs.append({
                        "timestamp": timestamp,
                        "severity": severity,
                        "app": app_name_from_log,
                        "message": message
                    })
                
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "query_id": query_id,
                            "log_count": len(formatted_logs),
                            "logs": formatted_logs,
                            "app_filter": app_name if app_name else "none",
                            "time_range": f"Last {hours} hours: {start_time.isoformat()} to {end_time.isoformat()}",
                            "hours": hours
                        }, indent=2)
                    }],
                    "isError": False
                }
                
            except Exception as e:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Exception during log retrieval: {str(e)}"
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "list_resource_instances":
            resource_group = arguments.get('resource_group')
            service_name = arguments.get('service_name')
            
            try:
                token = self._get_iam_token()
                if not token:
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": "Failed to get IAM token"
                            }, indent=2)
                        }],
                        "isError": True
                    }
                
                # Use IBM Cloud Resource Controller API
                resource_url = "https://resource-controller.cloud.ibm.com/v2/resource_instances"
                
                # Build query parameters
                params = {}
                if resource_group:
                    params['resource_group_id'] = resource_group
                if service_name:
                    params['name'] = service_name
                
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json'
                }
                
                response = requests.get(resource_url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    resources = data.get('resources', [])
                    
                    # Format resource list
                    formatted_resources = []
                    for resource in resources:
                        formatted_resources.append({
                            'name': resource.get('name'),
                            'id': resource.get('id'),
                            'type': resource.get('resource_id'),
                            'state': resource.get('state'),
                            'region': resource.get('region_id'),
                            'resource_group': resource.get('resource_group_id'),
                            'crn': resource.get('crn')
                        })
                    
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "count": len(formatted_resources),
                                "resources": formatted_resources
                            }, indent=2)
                        }]
                    }
                else:
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": f"Resource Controller API returned {response.status_code}",
                                "details": response.text[:500]
                            }, indent=2)
                        }],
                        "isError": True
                    }
                    
            except Exception as e:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"Failed to list resources: {str(e)}"
                        }, indent=2)
                    }],
                    "isError": True
                }
        
        elif tool_name == "list_icr_images":
            namespace = arguments.get('namespace')
            result = self.icr_toolkit.list_images(namespace)
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        elif tool_name == "list_icr_namespaces":
            result = self.icr_toolkit.list_namespaces()
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        elif tool_name == "delete_icr_image":
            image = arguments.get('image')
            result = self.icr_toolkit.delete_image(image)
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        elif tool_name == "get_icr_quota":
            result = self.icr_toolkit.get_quota()
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        else:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": f"Unknown tool: {tool_name}"
                    }, indent=2)
                }],
                "isError": True
            }
    
    def handle_request(self, request: dict):
        """Handle MCP protocol request"""
        method = request.get('method')
        
        if method == 'tools/list':
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": self.get_tools_list()
            }
        
        elif method == 'tools/call':
            params = request.get('params', {})
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            result = self.call_tool(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": result
            }
        
        elif method == 'initialize':
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "ibm-cloud-api-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def run(self):
        """Run the MCP server (stdio mode)"""
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    server = CloudLogsAPIMCPServer()
    server.run()
