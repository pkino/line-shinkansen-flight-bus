#!/bin/bash

# Production Deployment Verification Script
# This script tests all critical functionality of the LINE AI Bot

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
LOG_FILE="deployment_verification_$(date +%Y%m%d_%H%M%S).log"
FAILURE_COUNT=0
TEST_COUNT=0

echo "========================================" | tee -a "$LOG_FILE"
echo "LINE AI Bot Deployment Verification" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Base URL: $BASE_URL" | tee -a "$LOG_FILE"
echo "Timestamp: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Helper functions
log_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1" | tee -a "$LOG_FILE"
}

run_test() {
    TEST_COUNT=$((TEST_COUNT + 1))
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}[Test $TEST_COUNT]${NC} $1" | tee -a "$LOG_FILE"
    echo "-------------------" | tee -a "$LOG_FILE"
}

# Test 1: Check if service is running
run_test "Service Availability"
if curl -s -f "$BASE_URL/" > /dev/null 2>&1; then
    log_success "Service is responding"
    RESPONSE=$(curl -s "$BASE_URL/")
    echo "$RESPONSE" | jq . 2>&1 | tee -a "$LOG_FILE"
else
    log_error "Service is not responding at $BASE_URL"
    log_error "Cannot proceed with further tests"
    exit 1
fi

# Test 2: Basic health check
run_test "Basic Health Check"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Health check returned 200 OK"
    echo "$BODY" | jq . 2>&1 | tee -a "$LOG_FILE"
else
    log_error "Health check failed with HTTP $HTTP_CODE"
    echo "$BODY" | tee -a "$LOG_FILE"
fi

# Test 3: Detailed health check
run_test "Detailed Health Check"
DETAILED_HEALTH=$(curl -s -w "\n%{http_code}" "$BASE_URL/health/detailed")
HTTP_CODE=$(echo "$DETAILED_HEALTH" | tail -n1)
BODY=$(echo "$DETAILED_HEALTH" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "503" ]; then
    log_info "Detailed health check returned HTTP $HTTP_CODE"
    echo "$BODY" | jq . 2>&1 | tee -a "$LOG_FILE"
    
    # Parse component statuses
    ENV_STATUS=$(echo "$BODY" | jq -r '.components.environment.status' 2>/dev/null)
    LINE_STATUS=$(echo "$BODY" | jq -r '.components.line_bot.status' 2>/dev/null)
    CLAUDE_STATUS=$(echo "$BODY" | jq -r '.components.claude_api.status' 2>/dev/null)
    
    echo "" | tee -a "$LOG_FILE"
    log_info "Component Status Summary:"
    
    if [ "$ENV_STATUS" = "healthy" ]; then
        log_success "Environment: $ENV_STATUS"
    else
        log_error "Environment: $ENV_STATUS"
        echo "$BODY" | jq '.components.environment.details' 2>&1 | tee -a "$LOG_FILE"
    fi
    
    if [ "$LINE_STATUS" = "healthy" ]; then
        log_success "LINE Bot API: $LINE_STATUS"
    else
        log_error "LINE Bot API: $LINE_STATUS"
        echo "$BODY" | jq '.components.line_bot.details' 2>&1 | tee -a "$LOG_FILE"
    fi
    
    if [ "$CLAUDE_STATUS" = "healthy" ]; then
        log_success "Claude API: $CLAUDE_STATUS"
    else
        log_error "Claude API: $CLAUDE_STATUS"
        echo "$BODY" | jq '.components.claude_api.details' 2>&1 | tee -a "$LOG_FILE"
    fi
else
    log_error "Detailed health check failed with HTTP $HTTP_CODE"
    echo "$BODY" | tee -a "$LOG_FILE"
fi

# Test 4: Webhook endpoint availability
run_test "Webhook Endpoint Availability"
WEBHOOK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/webhook" \
    -H "Content-Type: application/json" \
    -d '{"events":[]}')
HTTP_CODE=$(echo "$WEBHOOK_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "400" ]; then
    log_success "Webhook endpoint is accessible (400 expected for invalid signature)"
elif [ "$HTTP_CODE" = "500" ]; then
    log_warning "Webhook endpoint returned 500 (may need configuration)"
    echo "$WEBHOOK_RESPONSE" | sed '$d' | tee -a "$LOG_FILE"
else
    log_info "Webhook endpoint returned HTTP $HTTP_CODE"
    echo "$WEBHOOK_RESPONSE" | sed '$d' | tee -a "$LOG_FILE"
fi

# Test 5: Simulated LINE webhook (if signature can be generated)
run_test "Simulated LINE Webhook"
log_info "Testing webhook with mock LINE message..."

# Create a simple mock webhook payload
MOCK_PAYLOAD='{
  "events": [
    {
      "type": "message",
      "message": {
        "type": "text",
        "text": "test"
      },
      "replyToken": "test_token",
      "source": {
        "type": "user",
        "userId": "test_user"
      },
      "timestamp": '$(date +%s000)'
    }
  ]
}'

WEBHOOK_TEST=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/webhook" \
    -H "Content-Type: application/json" \
    -H "X-Line-Signature: invalid_signature_for_testing" \
    -d "$MOCK_PAYLOAD")
HTTP_CODE=$(echo "$WEBHOOK_TEST" | tail -n1)

if [ "$HTTP_CODE" = "400" ]; then
    log_success "Webhook correctly validates signatures (400 for invalid)"
elif [ "$HTTP_CODE" = "200" ]; then
    log_warning "Webhook accepted request without valid signature"
else
    log_error "Unexpected webhook response: HTTP $HTTP_CODE"
    echo "$WEBHOOK_TEST" | sed '$d' | tee -a "$LOG_FILE"
fi

# Test 6: API Documentation
run_test "API Documentation"
if curl -s -f "$BASE_URL/docs" > /dev/null 2>&1; then
    log_success "API documentation is accessible at $BASE_URL/docs"
else
    log_warning "API documentation not accessible"
fi

# Test 7: Check environment readiness
run_test "Environment Configuration Check"
log_info "Checking required environment variables..."

if [ -z "${LINE_CHANNEL_SECRET}" ]; then
    log_error "LINE_CHANNEL_SECRET not set in environment"
else
    log_success "LINE_CHANNEL_SECRET is configured"
fi

if [ -z "${LINE_CHANNEL_ACCESS_TOKEN}" ]; then
    log_error "LINE_CHANNEL_ACCESS_TOKEN not set in environment"
else
    log_success "LINE_CHANNEL_ACCESS_TOKEN is configured"
fi

if [ -z "${CLAUDE_API_KEY}" ]; then
    log_error "CLAUDE_API_KEY not set in environment"
else
    log_success "CLAUDE_API_KEY is configured"
fi

# Test 8: Performance test
run_test "Basic Performance Test"
log_info "Measuring response times..."

for i in {1..5}; do
    START_TIME=$(date +%s%N)
    curl -s "$BASE_URL/health" > /dev/null
    END_TIME=$(date +%s%N)
    DURATION=$(( (END_TIME - START_TIME) / 1000000 ))
    echo "Request $i: ${DURATION}ms" | tee -a "$LOG_FILE"
done

# Final Summary
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "VERIFICATION SUMMARY" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Total Tests: $TEST_COUNT" | tee -a "$LOG_FILE"
echo "Failures: $FAILURE_COUNT" | tee -a "$LOG_FILE"
echo "Log File: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ $FAILURE_COUNT -eq 0 ]; then
    log_success "All critical tests passed!"
    echo "" | tee -a "$LOG_FILE"
    log_info "Next steps:"
    echo "  1. Verify LINE webhook URL is set to: ${BASE_URL}/webhook" | tee -a "$LOG_FILE"
    echo "  2. Test with actual LINE app by sending a message" | tee -a "$LOG_FILE"
    echo "  3. Monitor logs for incoming requests" | tee -a "$LOG_FILE"
    echo "  4. Check detailed health at: ${BASE_URL}/health/detailed" | tee -a "$LOG_FILE"
    exit 0
else
    log_error "$FAILURE_COUNT test(s) failed!"
    echo "" | tee -a "$LOG_FILE"
    log_info "Troubleshooting:"
    echo "  1. Check environment variables are set correctly" | tee -a "$LOG_FILE"
    echo "  2. Verify LINE channel configuration" | tee -a "$LOG_FILE"
    echo "  3. Confirm Claude API key is valid" | tee -a "$LOG_FILE"
    echo "  4. Review detailed health check output above" | tee -a "$LOG_FILE"
    echo "  5. Check application logs for errors" | tee -a "$LOG_FILE"
    exit 1
fi
