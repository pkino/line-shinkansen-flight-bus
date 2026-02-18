#!/bin/bash

# Deployment readiness check
# Run this before deploying to production

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERROR_COUNT=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
    else
        echo -e "${RED}✗${NC} $1 missing"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
}

check_env_var() {
    if [ -n "${!1}" ]; then
        echo -e "${GREEN}✓${NC} $1 is set"
    else
        echo -e "${RED}✗${NC} $1 is not set"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
}

echo "========================================"
echo "Deployment Readiness Check"
echo "========================================"
echo ""

echo "1. Checking required files..."
check_file "src/main.py"
check_file "requirements.txt"
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file ".env"
echo ""

echo "2. Checking environment variables..."
source .env 2>/dev/null || true
check_env_var "LINE_CHANNEL_SECRET"
check_env_var "LINE_CHANNEL_ACCESS_TOKEN"
check_env_var "CLAUDE_API_KEY"
echo ""

echo "3. Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker is installed"
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker daemon is running"
    else
        echo -e "${RED}✗${NC} Docker daemon is not running"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
else
    echo -e "${RED}✗${NC} Docker is not installed"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi
echo ""

echo "4. Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} requirements.txt found"
    echo "   Dependencies:"
    cat requirements.txt | grep -v '^#' | grep -v '^$' | sed 's/^/   - /'
fi
echo ""

echo "========================================"
if [ $ERROR_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ Ready for deployment!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Build: docker-compose build"
    echo "  2. Start: docker-compose up -d"
    echo "  3. Verify: ./scripts/verify_deployment.sh"
    exit 0
else
    echo -e "${RED}✗ $ERROR_COUNT issue(s) found${NC}"
    echo ""
    echo "Fix the issues above before deploying."
    exit 1
fi
