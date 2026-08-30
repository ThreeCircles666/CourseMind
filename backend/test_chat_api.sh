#!/bin/bash
# Test script for Qwen chat stream endpoint

API_BASE="http://127.0.0.1:8000"

echo "=== CourseMind Qwen Integration Test ==="
echo ""

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s "${API_BASE}/api/v1/health" | python3 -m json.tool
echo ""

# Test 2: Chat stream (requires running backend)
echo "2. Testing chat stream endpoint..."
echo "   Message: 你好，请用一句话介绍你自己"
echo ""
echo "   Response:"
echo "   ---"

curl -N -X POST "${API_BASE}/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message":"你好，请用一句话介绍你自己"}' 2>&1

echo ""
echo "   ---"
echo ""
echo "=== Test Complete ==="
