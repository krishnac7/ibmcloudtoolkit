#!/usr/bin/env python3
"""
IBM Container Registry (ICR) Toolkit - API-based version
Uses IBM Cloud REST APIs instead of CLI for Watson Orchestrate compatibility
"""

import os
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class ICRToolkitAPI:
    """API-based toolkit for IBM Container Registry operations"""
    
    def __init__(self, api_key: str = None, region: str = None):
        self.api_key = api_key or os.getenv('IBMCLOUD_API_KEY')
        self.region = region or os.getenv('CLOUD_LOGS_REGION', 'us-south')
        # Map full region names to short codes for ICR
        region_map = {
            'us-south': 'us',
            'us-east': 'us',
            'eu-de': 'de',
            'eu-gb': 'uk',
            'jp-tok': 'jp',
            'au-syd': 'au',
            'jp-osa': 'jp2',
            'ca-tor': 'ca',
            'br-sao': 'br'
        }
        short_region = region_map.get(self.region, 'us')
        # IBM Container Registry API endpoint
        self.api_endpoint = f'https://{short_region}.icr.io/api'
        self.registry_endpoint = f'https://{short_region}.icr.io'
        self.account_id = None
        self.iam_token = None
        self.token_expiry = None
    
    def _get_iam_token(self) -> str:
        """Get IBM Cloud IAM token and account ID"""
        if self.iam_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.iam_token
        
        if not self.api_key:
            raise Exception("IBM Cloud API key not configured")
        
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
            response.raise_for_status()
            data = response.json()
            self.iam_token = data['access_token']
            self.token_expiry = datetime.now() + timedelta(minutes=50)
            
            # Get account ID from IAM API if not already set
            if not self.account_id:
                try:
                    account_response = requests.get(
                        'https://iam.cloud.ibm.com/v1/apikeys/details',
                        headers={'Authorization': f'Bearer {self.iam_token}', 'IAM-Apikey': self.api_key},
                        timeout=30
                    )
                    if account_response.status_code == 200:
                        account_data = account_response.json()
                        self.account_id = account_data.get('account_id')
                except:
                    # Fallback: placeholder replaced by deploy script
                    self.account_id = '__IBMCLOUD_ACCOUNT_ID__'
            
            return self.iam_token
            
        except Exception as e:
            raise Exception(f"Failed to get IAM token: {str(e)}")
    
    def _call_icr_api(self, endpoint: str, method: str = 'GET', data: dict = None) -> Dict[str, Any]:
        """Call IBM Container Registry API"""
        token = self._get_iam_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Account': self.account_id or ''
        }
        
        if data:
            headers['Content-Type'] = 'application/json'
        
        url = f'{self.api_endpoint}{endpoint}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, json=data, timeout=10)
            else:
                raise Exception(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.text else {}
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Connection timeout - Watson Orchestrate environment may have network restrictions. ICR API endpoint (us.icr.io) is not accessible from this environment. Contact IBM Cloud support to whitelist us.icr.io or use this toolkit locally via CLI.'
            }
        except requests.exceptions.HTTPError as e:
            return {
                'success': False,
                'error': f'HTTP {e.response.status_code}: {e.response.text[:200]}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_namespaces(self) -> Dict[str, Any]:
        """List all namespaces in the account"""
        try:
            result = self._call_icr_api('/v1/namespaces')
            
            if isinstance(result, list):
                return {
                    'success': True,
                    'namespaces': result,
                    'count': len(result)
                }
            elif 'success' in result and not result['success']:
                return result
            else:
                return {
                    'success': True,
                    'namespaces': [result] if result else [],
                    'count': 1 if result else 0
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'namespaces': []
            }
    
    def list_images(self, namespace: str = None) -> Dict[str, Any]:
        """List images in ICR, optionally filtered by namespace"""
        try:
            endpoint = '/v1/images'
            if namespace:
                endpoint += f'?namespace={namespace}'
            
            result = self._call_icr_api(endpoint)
            
            if isinstance(result, list):
                return {
                    'success': True,
                    'images': result,
                    'count': len(result)
                }
            elif 'success' in result and not result['success']:
                return result
            else:
                return {
                    'success': True,
                    'images': [result] if result else [],
                    'count': 1 if result else 0
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'images': []
            }
    
    def delete_image(self, image: str) -> Dict[str, Any]:
        """Delete an image from ICR"""
        try:
            # Parse image path: us.icr.io/namespace/image:tag or namespace/image:tag
            parts = image.replace(f'{self.region}.icr.io/', '').split('/')
            if len(parts) != 2:
                return {
                    'success': False,
                    'error': f'Invalid image format. Expected: namespace/image:tag, got: {image}'
                }
            
            namespace = parts[0]
            image_name = parts[1]
            
            endpoint = f'/v1/images/{namespace}/{image_name}'
            result = self._call_icr_api(endpoint, method='DELETE')
            
            if 'success' in result:
                return result
            
            return {
                'success': True,
                'message': f'Image {image} deleted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_quota(self) -> Dict[str, Any]:
        """Get ICR storage and traffic quota information"""
        try:
            result = self._call_icr_api('/v1/quotas')
            
            if 'success' in result and not result['success']:
                return result
            
            return {
                'success': True,
                'quota': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
