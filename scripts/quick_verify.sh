#!/bin/bash

# Quick verification script for immediate deployment checks
# Usage: ./scripts/quick_verify.sh [BASE_URL]

BASE_URL="${1:-http://localhost:8000}"

echo "🔍 Quick Deployment Check"
echo "========================="
echo "Target: $BASE_URL"
echo ""

# Check if service is up
echo "1. Checking service availability..."
if curl -s -f "$BASE_URL/" > /dev/null 2>&1; then
    echo "✓ Service is UP"
else
    echo "✗ Service is DOWN"
    exit 1
fi

# Check health
echo ""
echo "2. Checking health endpoint..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    echo "✓ Health check passed"
else
    echo "⚠ Health check returned unexpected status"
    echo "$HEALTH" | jq .
fi

# Check detailed health
echo ""
echo "3. Checking component health..."
DETAILED=$(curl -s "$BASE_URL/health/detailed")

LINE_STATUS=$(echo "$DETAILED" | jq -r '.components.line_bot.status')
CLAUDE_STATUS=$(echo "$DETAILED" | jq -r '.components.claude_api.status')
ENV_STATUS=$(echo "$DETAILED" | jq -r '.components.environment.status')

echo "   Environment: $ENV_STATUS"
echo "   LINE Bot: $LINE_STATUS"
echo "   Claude API: $CLAUDE_STATUS"

# Summary
echo ""
echo "========================="
if [ "$LINE_STATUS" = "healthy" ] && [ "$CLAUDE_STATUS" = "healthy" ] && [ "$ENV_STATUS" = "healthy" ]; then
    echo "✓ All systems operational!"
    echo ""
    echo "Next: Configure LINE webhook to: ${BASE_URL}/webhook"
    exit 0
else
    echo "⚠ Some components need attention"
    echo ""
    echo "Run full verification: ./scripts/verify_deployment.sh"
    exit 1
fi
