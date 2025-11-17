#!/bin/bash

echo "=== Memory Test App - Crash Test ==="
echo ""

# Clean up any existing container
docker stop memory-test 2>/dev/null
docker rm memory-test 2>/dev/null

# Start container
echo "1. Starting container..."
docker run -d -p 8080:8080 --name memory-test --rm krishnac7/csmdemo:zeus
sleep 3

# Health check
echo ""
echo "2. Health check:"
curl -s http://localhost:8080/ | jq -c '{status, memory_test_active}'

# Trigger crash
echo ""
echo "3. Triggering OOM crash (delay=3s)..."
curl -X POST http://localhost:8080/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "oom", "delay": 3}' 2>/dev/null | jq -c '{status, type, delay_seconds}'

# Monitor
echo ""
echo "4. Monitoring container (checking every second)..."
for i in {1..10}; do
  if docker ps | grep -q memory-test; then
    echo "  [$i] Container still running..."
    sleep 1
  else
    echo "  [$ i] 💥 Container crashed!"
    break
  fi
done

# Get final logs
echo ""
echo "5. Final container logs:"
echo "========================================"
docker logs memory-test 2>&1 | grep -E "\[3\]|\[4\]|\[5\]|\[6\]|💥|⚡|🚨" || echo "No severity logs found"
echo "========================================"

echo ""
echo "✅ Test complete"
