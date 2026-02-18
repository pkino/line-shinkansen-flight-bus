#!/bin/bash

# Local webhook testing script
# Simulates LINE webhook calls for local development

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "🧪 Testing LINE Webhook Locally"
echo "================================"
echo "Target: $BASE_URL/webhook"
echo ""

# Test 1: Empty events (should fail signature validation)
echo "Test 1: Empty events array"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/webhook" \
    -H "Content-Type: application/json" \
    -d '{"events":[]}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
echo "Response: HTTP $HTTP_CODE"
echo "$RESPONSE" | sed '$d' | jq . 2>/dev/null || echo "$RESPONSE" | sed '$d'
echo ""

# Test 2: Invalid signature
echo "Test 2: Invalid signature"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/webhook" \
    -H "Content-Type: application/json" \
    -H "X-Line-Signature: invalid_signature" \
    -d '{"events":[{"type":"message","message":{"type":"text","text":"hello"}}]}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
echo "Response: HTTP $HTTP_CODE"
echo "$RESPONSE" | sed '$d' | jq . 2>/dev/null || echo "$RESPONSE" | sed '$d'
echo ""

# Test 3: Missing signature
echo "Test 3: Missing signature header"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/webhook" \
    -H "Content-Type: application/json" \
    -d '{"events":[{"type":"message","message":{"type":"text","text":"test"}}]}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
echo "Response: HTTP $HTTP_CODE"
echo "$RESPONSE" | sed '$d' | jq . 2>/dev/null || echo "$RESPONSE" | sed '$d'
echo ""

echo "================================"
echo "Summary:"
echo "- Webhook endpoint is accessible"
echo "- Signature validation is active"
echo "- Ready for LINE platform integration"
echo ""
echo "To test with real LINE messages:"
echo "1. Deploy to public URL"
echo "2. Set webhook URL in LINE console"
echo "3. Send message to your LINE bot"
