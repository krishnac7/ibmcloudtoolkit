#!/usr/bin/env python3
"""
Memory Test Application for Code Engine
Gradually increases memory usage until OOM, logging everything to Cloud Logs
"""

import os
import sys
import time
import psutil
import requests
import json
from flask import Flask, jsonify, request
from datetime import datetime
import subprocess
import logging

# Configure unbuffered output for reliable log capture
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Configure Python logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Suppress Flask/Werkzeug debug and development server logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # Only show errors from Flask dev server

app = Flask(__name__)
app.logger.setLevel(logging.WARNING)  # Suppress Flask info logs

# Request counter for tracking
request_counter = 0

# Cloud Logs Configuration from environment variables
CLOUD_LOGS_INSTANCE = os.getenv('CLOUD_LOGS_INSTANCE_GUID')
CLOUD_LOGS_REGION = os.getenv('CLOUD_LOGS_REGION', 'us-south')
IBMCLOUD_API_KEY = os.getenv('IBMCLOUD_API_KEY')

# Build endpoint from instance GUID or use custom endpoint
if os.getenv('CLOUD_LOGS_ENDPOINT'):
    CLOUD_LOGS_ENDPOINT = os.getenv('CLOUD_LOGS_ENDPOINT')
elif CLOUD_LOGS_INSTANCE:
    CLOUD_LOGS_ENDPOINT = f"https://{CLOUD_LOGS_INSTANCE}.ingress.{CLOUD_LOGS_REGION}.logs.cloud.ibm.com/logs/v1/singles"
else:
    CLOUD_LOGS_ENDPOINT = None
    logger.warning("Cloud Logs not configured - logs will only print to console")
    logger.info("Set CLOUD_LOGS_INSTANCE_GUID or CLOUD_LOGS_ENDPOINT")
    sys.stdout.flush()

# Global state
memory_test_running = False
allocated_memory = []
iam_token_cache = None
iam_token_expiry = 0
memory_warning_60_sent = False
memory_warning_80_sent = False
memory_warning_90_sent = False

def get_container_memory_limit():
    """Detect container memory limit from cgroup or environment"""
    try:
        # Try cgroup v2 first (newer systems)
        cgroup_v2_path = '/sys/fs/cgroup/memory.max'
        if os.path.exists(cgroup_v2_path):
            with open(cgroup_v2_path, 'r') as f:
                limit = f.read().strip()
                if limit != 'max':
                    return int(limit) / (1024 * 1024)  # Convert to MB
        
        # Try cgroup v1
        cgroup_v1_path = '/sys/fs/cgroup/memory/memory.limit_in_bytes'
        if os.path.exists(cgroup_v1_path):
            with open(cgroup_v1_path, 'r') as f:
                limit = int(f.read().strip())
                # Ignore very large values (no limit set)
                if limit < 9223372036854771712:  # Not "unlimited"
                    return limit / (1024 * 1024)  # Convert to MB
        
        # Check environment variable (Code Engine sets this)
        if 'CE_MEMORY' in os.environ:
            return float(os.environ['CE_MEMORY'])
        
    except Exception as e:
        logger.warning(f"Could not detect container memory limit: {e}")
    
    # Default to 1GB if detection fails
    return 1024.0

def get_iam_token():
    """Get IAM token from API key or IBM Cloud CLI"""
    global iam_token_cache, iam_token_expiry
    
    # Check cache (tokens valid for 60 minutes, we cache for 50)
    if iam_token_cache and time.time() < iam_token_expiry:
        return iam_token_cache
    
    # Try API key first (preferred for production)
    if IBMCLOUD_API_KEY:
        try:
            response = requests.post(
                'https://iam.cloud.ibm.com/identity/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
                    'apikey': IBMCLOUD_API_KEY
                },
                timeout=10
            )
            if response.status_code == 200:
                token = response.json().get('access_token')
                iam_token_cache = token
                iam_token_expiry = time.time() + (50 * 60)  # Cache for 50 minutes
                return token
        except Exception as e:
            print(f"[WARNING] Failed to get IAM token from API key: {e}")
    
    # Fallback to CLI (for local development)
    try:
        result = subprocess.run(
            ['ibmcloud', 'iam', 'oauth-tokens', '--output', 'json'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            tokens = json.loads(result.stdout)
            token = tokens.get('iam_token', '').replace('Bearer ', '')
            iam_token_cache = token
            iam_token_expiry = time.time() + (50 * 60)
            return token
    except Exception as e:
        print(f"[WARNING] Failed to get IAM token from CLI: {e}")
    
    return None

@app.before_request
def log_request_start():
    """Log the start of each request"""
    global request_counter
    request_counter += 1
    
    request.start_time = time.time()
    request.request_id = f"{int(time.time() * 1000)}-{request_counter}"
    
    stats = get_memory_stats()
    
    send_log(
        f"Incoming request: {request.method} {request.path}",
        severity=3,  # INFO
        request_id=request.request_id,
        method=request.method,
        path=request.path,
        endpoint=request.endpoint,
        remote_addr=request.remote_addr,
        user_agent=request.headers.get('User-Agent', 'unknown'),
        content_type=request.headers.get('Content-Type'),
        content_length=request.headers.get('Content-Length'),
        memory_mb=stats['process_rss_mb'],
        memory_percent=stats['system_used_percent']
    )

@app.after_request
def log_request_end(response):
    """Log the completion of each request"""
    if hasattr(request, 'start_time'):
        duration_ms = round((time.time() - request.start_time) * 1000, 2)
        request_id = getattr(request, 'request_id', 'unknown')
        
        # Determine severity based on status code
        severity = 3  # INFO
        if response.status_code >= 500:
            severity = 5  # ERROR
        elif response.status_code >= 400:
            severity = 4  # WARNING
        
        stats = get_memory_stats()
        
        send_log(
            f"Response: {request.method} {request.path} - {response.status_code}",
            severity=severity,
            request_id=request_id,
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            response_size=response.content_length,
            memory_mb=stats['process_rss_mb'],
            memory_percent=stats['system_used_percent']
        )
    
    return response

@app.errorhandler(Exception)
def log_exception(error):
    """Log unhandled exceptions"""
    request_id = getattr(request, 'request_id', 'unknown')
    
    try:
        stats = get_memory_stats()
        send_log(
            f"Unhandled exception in {request.method} {request.path}: {type(error).__name__}",
            severity=5,  # ERROR
            request_id=request_id,
            method=request.method,
            path=request.path,
            error_type=type(error).__name__,
            error_message=str(error),
            **stats
        )
    except:
        print(f"Exception in {request.path}: {type(error).__name__} - {error}")
    
    # Re-raise the exception to let Flask handle it normally
    raise

def check_memory_thresholds():
    """Check memory usage and send warnings if thresholds exceeded"""
    global memory_warning_60_sent, memory_warning_80_sent, memory_warning_90_sent
    
    stats = get_memory_stats()
    system_memory_percent = stats['system_used_percent']
    process_rss_mb = stats['process_rss_mb']
    
    # Dynamically detect container memory limit
    container_limit_mb = get_container_memory_limit()
    container_memory_percent = (process_rss_mb / container_limit_mb) * 100
    
    # Add container stats to return value
    stats['container_limit_mb'] = round(container_limit_mb, 2)
    stats['container_memory_percent'] = round(container_memory_percent, 2)
    
    # 60% threshold warning (based on container limit)
    if container_memory_percent >= 60 and not memory_warning_60_sent:
        memory_warning_60_sent = True
        send_log(
            "INFO: Container memory reached 60% threshold",
            severity=3,  # INFO
            threshold="60%",
            action="Normal operation - monitoring memory usage",
            **stats
        )
        sys.stdout.flush()
    
    # 80% threshold warning
    if container_memory_percent >= 80 and not memory_warning_80_sent:
        memory_warning_80_sent = True
        send_log(
            "WARNING: Container memory exceeded 80% threshold",
            severity=4,  # WARNING
            threshold="80%",
            action="Monitor closely for potential OOM",
            **stats
        )
        sys.stdout.flush()
    
    # 90% threshold critical warning
    if container_memory_percent >= 90 and not memory_warning_90_sent:
        memory_warning_90_sent = True
        send_log(
            "CRITICAL: Container memory exceeded 90% threshold - OOM risk high!",
            severity=5,  # ERROR
            threshold="90%",
            action="OOM imminent - consider scaling up memory",
            **stats
        )
        sys.stdout.flush()
    
    # Reset warnings if memory drops below thresholds
    if container_memory_percent < 55:
        memory_warning_60_sent = False
        memory_warning_80_sent = False
        memory_warning_90_sent = False
    elif container_memory_percent < 75:
        memory_warning_80_sent = False
        memory_warning_90_sent = False
    elif container_memory_percent < 85:
        memory_warning_90_sent = False
    
    return stats

def send_log(message, severity=3, **metadata):
    """Send log to Cloud Logs and stdout"""
    # Map severity to logging level and always log to stdout
    severity_map = {1: 'DEBUG', 3: 'INFO', 4: 'WARNING', 5: 'ERROR', 6: 'CRITICAL'}
    level_name = severity_map.get(severity, 'INFO')
    
    # Log to stdout with metadata
    log_line = f"[{severity}] {message} | {metadata}"
    if severity >= 5:
        logger.error(log_line)
    elif severity == 4:
        logger.warning(log_line)
    else:
        logger.info(log_line)
    sys.stdout.flush()
    
    # Skip Cloud Logs if not configured
    if not CLOUD_LOGS_ENDPOINT:
        return False
    
    token = get_iam_token()
    if not token:
        logger.warning("No IAM token available, skipping Cloud Logs")
        return False
    
    log_entry = [{
        "applicationName": "memory-test-app",
        "subsystemName": "backend",
        "text": message,
        "severity": severity,
        "timestamp": int(time.time() * 1000),
        "json": metadata
    }]
    
    try:
        response = requests.post(
            CLOUD_LOGS_ENDPOINT,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            },
            json=log_entry,
            timeout=5
        )
        success = response.status_code in [200, 201, 204]
        if not success:
            print(f"[WARNING] Cloud Logs request failed: {response.status_code} - {response.text[:200]}")
        return success
    except Exception as e:
        print(f"[ERROR] Failed to send log to Cloud Logs: {e}")
        return False

def get_memory_stats():
    """Get current memory statistics with container-aware limits"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    system_mem = psutil.virtual_memory()
    
    # Calculate process memory usage percentage
    process_mb = mem_info.rss / 1024 / 1024
    system_total_mb = system_mem.total / 1024 / 1024
    process_percent = (process_mb / system_total_mb) * 100 if system_total_mb > 0 else 0
    
    return {
        "process_rss_mb": round(process_mb, 2),
        "process_vms_mb": round(mem_info.vms / 1024 / 1024, 2),
        "process_percent": round(process_percent, 2),
        "system_total_mb": round(system_total_mb, 2),
        "system_available_mb": round(system_mem.available / 1024 / 1024, 2),
        "system_used_mb": round(system_mem.used / 1024 / 1024, 2),
        "system_used_percent": round(system_mem.percent, 2)
    }

@app.route('/')
def home():
    """Health check endpoint"""
    stats = check_memory_thresholds()
    return jsonify({
        "status": "running",
        "app": "memory-test-app",
        "memory_test_active": memory_test_running,
        "memory_stats": stats,
        "allocated_chunks": len(allocated_memory),
        "endpoints": {
            "/": "Health check",
            "/crash": "POST - Initiate memory crash (type: oom|gradual, delay: seconds)",
            "/start-memory-test": "Start gradual memory consumption test",
            "/stop-memory-test": "Stop memory consumption test",
            "/memory-stats": "Get current memory stats",
            "/trigger-oom": "Immediately trigger OOM (deprecated - use /crash)"
        }
    })

@app.route('/memory-stats')
def memory_stats():
    """Get current memory statistics with threshold checks"""
    stats = check_memory_thresholds()
    
    # Add threshold status
    memory_percent = stats['system_used_percent']
    stats['threshold_status'] = {
        'level': 'normal' if memory_percent < 80 else 'warning' if memory_percent < 90 else 'critical',
        'percent': memory_percent,
        'warning_80': memory_percent >= 80,
        'warning_90': memory_percent >= 90
    }
    
    return jsonify(stats)

@app.route('/start-memory-test')
def start_memory_test():
    """Start gradual memory consumption test"""
    global memory_test_running
    
    if memory_test_running:
        return jsonify({"error": "Memory test already running"}), 400
    
    memory_test_running = True
    stats = get_memory_stats()
    
    send_log(
        "Memory test started - will gradually increase memory usage",
        severity=3,  # INFO
        **stats
    )
    
    # Start memory consumption in background
    import threading
    threading.Thread(target=consume_memory_gradually, daemon=True).start()
    
    return jsonify({
        "status": "started",
        "message": "Memory test initiated",
        "current_memory": stats
    })

@app.route('/stop-memory-test')
def stop_memory_test():
    """Stop memory consumption test"""
    global memory_test_running, allocated_memory
    
    if not memory_test_running:
        return jsonify({"error": "No memory test running"}), 400
    
    memory_test_running = False
    chunks_freed = len(allocated_memory)
    allocated_memory.clear()
    
    stats = get_memory_stats()
    send_log(
        f"Memory test stopped - freed {chunks_freed} chunks",
        severity=3,  # INFO
        chunks_freed=chunks_freed,
        **stats
    )
    
    return jsonify({
        "status": "stopped",
        "chunks_freed": chunks_freed,
        "current_memory": stats
    })

@app.route('/crash', methods=['POST'])
def crash():
    """Endpoint to initiate memory crash on specific request"""
    stats = get_memory_stats()
    
    # Get crash parameters from request
    data = request.get_json() or {}
    delay_seconds = data.get('delay', 5)
    crash_type = data.get('type', 'oom')  # 'oom' or 'gradual'
    
    send_log(
        f"Crash initiated via /crash endpoint - type: {crash_type}",
        severity=4,  # WARNING
        crash_type=crash_type,
        delay_seconds=delay_seconds,
        **stats
    )
    
    if crash_type == 'gradual':
        # Start gradual memory consumption
        global memory_test_running
        if memory_test_running:
            return jsonify({"error": "Memory test already running"}), 400
        
        memory_test_running = True
        import threading
        threading.Thread(target=consume_memory_gradually, daemon=True).start()
        
        return jsonify({
            "status": "crash_initiated",
            "type": "gradual",
            "message": f"Gradual memory consumption started - will crash eventually",
            "current_memory": stats
        })
    else:
        # Immediate OOM crash
        import threading
        
        def delayed_crash():
            time.sleep(delay_seconds)
            send_log(f"💥 Executing immediate crash after {delay_seconds}s delay", severity=6)
            allocate_huge_memory()
        
        threading.Thread(target=delayed_crash, daemon=True).start()
        
        return jsonify({
            "status": "crash_initiated",
            "type": "immediate_oom",
            "message": f"OOM will occur in {delay_seconds} seconds",
            "delay_seconds": delay_seconds,
            "current_memory": stats
        })

@app.route('/trigger-oom')
def trigger_oom():
    """Immediately trigger OOM for testing"""
    stats = get_memory_stats()
    
    send_log(
        "Triggering immediate OOM for testing",
        severity=4,  # WARNING
        **stats
    )
    
    # Allocate huge chunk to trigger OOM
    import threading
    threading.Thread(target=allocate_huge_memory, daemon=True).start()
    
    return jsonify({
        "status": "triggered",
        "message": "OOM will occur in ~5 seconds",
        "current_memory": stats
    })

def consume_memory_gradually():
    """Gradually consume memory until OOM with comprehensive error logging"""
    global memory_test_running, allocated_memory
    
    # Dynamically calculate chunk size based on container memory limit
    container_limit_mb = get_container_memory_limit()
    
    # Use 2% of container memory per chunk (more granular for better threshold detection)
    chunk_size = int((container_limit_mb * 0.02) * 1024 * 1024)  # 2% of limit in bytes
    chunk_size_mb = chunk_size / (1024 * 1024)
    
    iteration = 0
    last_log_iteration = 0
    paused_at_60 = False
    paused_at_80 = False
    
    # Calculate expected iterations to thresholds
    current_stats = get_memory_stats()
    current_mb = current_stats['process_rss_mb']
    mb_to_60 = (container_limit_mb * 0.60) - current_mb
    mb_to_80 = (container_limit_mb * 0.80) - current_mb
    iterations_to_60 = int(mb_to_60 / chunk_size_mb) if mb_to_60 > 0 else 0
    iterations_to_80 = int(mb_to_80 / chunk_size_mb) if mb_to_80 > 0 else 0
    
    send_log(
        "Starting gradual memory consumption test",
        severity=3,
        container_limit_mb=round(container_limit_mb, 2),
        chunk_size_mb=round(chunk_size_mb, 2),
        current_memory_mb=round(current_mb, 2),
        iterations_to_60_percent=iterations_to_60,
        iterations_to_80_percent=iterations_to_80,
        target="Consume memory until OOM"
    )
    sys.stdout.flush()
    
    while memory_test_running:
        iteration += 1
        
        try:
            # Check memory before allocation
            stats = check_memory_thresholds()
            container_limit_mb = stats.get('container_limit_mb', 1024)
            container_memory_percent = stats.get('container_memory_percent', 0)
            process_mb = stats['process_rss_mb']
            
            # PAUSE at 60% threshold - send log and wait for propagation
            if container_memory_percent >= 60 and not paused_at_60:
                paused_at_60 = True
                send_log(
                    "PAUSED: Reached 60% container memory threshold - waiting for log propagation",
                    severity=3,
                    iteration=iteration,
                    chunks_allocated=len(allocated_memory),
                    total_allocated_mb=round((len(allocated_memory) * chunk_size) / 1024 / 1024, 2),
                    **stats
                )
                sys.stdout.flush()
                logger.info("⏸️  Pausing for 10 seconds at 60% to ensure logs reach Cloud Logs...")
                time.sleep(10)  # Wait for log to propagate
                logger.info("▶️  Resuming memory allocation after 60% threshold")
                sys.stdout.flush()
            
            # PAUSE at 80% threshold - send log and wait
            if container_memory_percent >= 80 and not paused_at_80:
                paused_at_80 = True
                send_log(
                    "PAUSED: Reached 80% container memory threshold - waiting for log propagation",
                    severity=4,
                    iteration=iteration,
                    chunks_allocated=len(allocated_memory),
                    total_allocated_mb=round((len(allocated_memory) * chunk_size) / 1024 / 1024, 2),
                    **stats
                )
                sys.stdout.flush()
                logger.warning("⏸️  Pausing for 10 seconds at 80% to ensure logs reach Cloud Logs...")
                time.sleep(10)
                logger.warning("▶️  Resuming memory allocation after 80% threshold - OOM risk increasing")
                sys.stdout.flush()
            
            # Allocate memory chunk with error handling
            try:
                chunk = bytearray(chunk_size)
                allocated_memory.append(chunk)
            except MemoryError as alloc_error:
                # Log allocation failure
                logger.error(f"Memory allocation failed at iteration {iteration}")
                raise
            
            # Get stats after allocation
            stats_after = get_memory_stats()
            container_memory_percent_after = (stats_after['process_rss_mb'] / container_limit_mb) * 100
            
            # Determine log severity based on memory usage
            severity = 3  # INFO
            if container_memory_percent_after >= 95:
                severity = 6  # CRITICAL
            elif container_memory_percent_after >= 90:
                severity = 5  # ERROR
            elif container_memory_percent_after >= 80:
                severity = 4  # WARNING
            
            # Log every 3 iterations (more frequent), or always when above 80%
            should_log = (iteration % 3 == 0) or (container_memory_percent_after >= 80) or (iteration - last_log_iteration >= 5)
            
            if should_log:
                last_log_iteration = iteration
                
                log_message = f"Memory allocation iteration {iteration}"
                if container_memory_percent_after >= 95:
                    log_message = f"CRITICAL iteration {iteration} - OOM imminent!"
                elif container_memory_percent_after >= 90:
                    log_message = f"HIGH RISK iteration {iteration} - approaching OOM"
                elif container_memory_percent_after >= 80:
                    log_message = f"Warning iteration {iteration} - 80% threshold exceeded"
                
                send_log(
                    log_message,
                    severity=severity,
                    iteration=iteration,
                    chunks_allocated=len(allocated_memory),
                    total_allocated_mb=round((len(allocated_memory) * chunk_size) / 1024 / 1024, 2),
                    chunk_size_mb=round(chunk_size / 1024 / 1024, 2),
                    container_memory_percent=round(container_memory_percent_after, 2),
                    **stats_after
                )
                sys.stdout.flush()
            
            # Wait before next allocation (faster when high memory to trigger OOM)
            wait_time = 0.5 if container_memory_percent_after >= 90 else 1 if container_memory_percent_after >= 80 else 2
            time.sleep(wait_time)
            
        except MemoryError as e:
            try:
                stats = get_memory_stats()
                send_log(
                    "💥 MemoryError caught - OOM occurred!",
                    severity=6,  # CRITICAL
                    error_type="MemoryError",
                    error_message=str(e),
                    iteration=iteration,
                    chunks_before_oom=len(allocated_memory),
                    total_mb_allocated=round((len(allocated_memory) * chunk_size) / 1024 / 1024, 2),
                    **stats
                )
            except:
                print(f"💥 MemoryError at iteration {iteration} - unable to log to Cloud Logs")
            memory_test_running = False
            break
            
        except OSError as e:
            try:
                stats = get_memory_stats()
                send_log(
                    "💥 OSError during memory allocation - system limit reached",
                    severity=6,  # CRITICAL
                    error_type="OSError",
                    error_message=str(e),
                    error_errno=e.errno if hasattr(e, 'errno') else None,
                    iteration=iteration,
                    chunks_allocated=len(allocated_memory),
                    **stats
                )
            except:
                print(f"💥 OSError at iteration {iteration}: {e}")
            memory_test_running = False
            break
            
        except Exception as e:
            try:
                stats = get_memory_stats()
                send_log(
                    f"Unexpected error during memory test: {type(e).__name__}",
                    severity=5,  # ERROR
                    error_type=type(e).__name__,
                    error_message=str(e),
                    iteration=iteration,
                    chunks_allocated=len(allocated_memory),
                    **stats
                )
            except:
                print(f"Error at iteration {iteration}: {type(e).__name__} - {e}")
            memory_test_running = False
            break
    
    # Log test completion
    try:
        final_stats = get_memory_stats()
        send_log(
            "Memory test completed or stopped",
            severity=3,
            total_iterations=iteration,
            total_chunks=len(allocated_memory),
            total_mb_allocated=round((len(allocated_memory) * chunk_size) / 1024 / 1024, 2),
            reason="OOM" if not memory_test_running else "Stopped",
            **final_stats
        )
    except:
        print(f"Memory test ended at iteration {iteration}")

def allocate_huge_memory():
    """Allocate huge memory to immediately trigger OOM with detailed error logging"""
    try:
        stats_before = get_memory_stats()
        send_log(
            "Starting immediate OOM trigger - allocating 10GB",
            severity=5,  # ERROR
            allocation_size_gb=10,
            **stats_before
        )
        
        time.sleep(2)
        
        send_log(
            "Allocating 10GB chunk now...",
            severity=6,  # CRITICAL
            action="Triggering OOM"
        )
        
        # This should trigger OOM
        huge = bytearray(10 * 1024 * 1024 * 1024)  # 10GB
        
        # If we get here, allocation somehow succeeded (shouldn't happen)
        send_log(
            "Unexpected: 10GB allocation succeeded without OOM",
            severity=4,
            allocated_size_gb=10
        )
        
    except MemoryError as e:
        try:
            stats = get_memory_stats()
            send_log(
                "OOM triggered successfully via MemoryError",
                severity=6,  # CRITICAL
                error_type="MemoryError",
                error_message=str(e),
                expected_behavior=True,
                **stats
            )
        except:
            print("MemoryError - OOM triggered (unable to send to Cloud Logs)")
            
    except OSError as e:
        try:
            stats = get_memory_stats()
            send_log(
                "OOM triggered via OSError - system limit reached",
                severity=6,  # CRITICAL
                error_type="OSError",
                error_message=str(e),
                error_errno=e.errno if hasattr(e, 'errno') else None,
                **stats
            )
        except:
            print(f"OSError during OOM trigger: {e}")
            
    except Exception as e:
        try:
            stats = get_memory_stats()
            send_log(
                f"Unexpected error during OOM trigger: {type(e).__name__}",
                severity=5,  # ERROR
                error_type=type(e).__name__,
                error_message=str(e),
                expected_behavior=False,
                **stats
            )
        except:
            print(f"OOM trigger failed: {type(e).__name__} - {e}")

if __name__ == '__main__':
    # Send startup log
    stats = get_memory_stats()
    send_log(
        "Memory test application started",
        severity=3,  # INFO
        version="1.0.0",
        **stats
    )
    
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
