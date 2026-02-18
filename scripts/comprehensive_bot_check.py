#!/usr/bin/env python3
"""Comprehensive bot deployment verification."""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Load environment
load_dotenv()

class BotDeploymentChecker:
    def __init__(self):
        self.line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
        self.line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.prod_url = os.getenv('RAILWAY_PUBLIC_URL') or os.getenv('RENDER_EXTERNAL_URL')
        
        self.checks_passed = 0
        self.checks_failed = 0
        self.issues = []
        self.recommendations = []
    
    def print_header(self, text: str):
        print(f"\n{'='*60}")
        print(f"{BLUE}{text}{NC}")
        print(f"{'='*60}\n")
    
    def print_success(self, text: str):
        print(f"{GREEN}✓ {text}{NC}")
        self.checks_passed += 1
    
    def print_error(self, text: str, issue: str = None):
        print(f"{RED}✗ {text}{NC}")
        self.checks_failed += 1
        if issue:
            self.issues.append(issue)
    
    def print_warning(self, text: str):
        print(f"{YELLOW}⚠ {text}{NC}")
    
    def check_environment_variables(self) -> bool:
        """Check if all required environment variables are set."""
        self.print_header("1. Environment Variables Check")
        
        all_present = True
        
        if self.line_channel_secret:
            self.print_success("LINE_CHANNEL_SECRET is set")
        else:
            self.print_error("LINE_CHANNEL_SECRET is missing", 
                           "Set LINE_CHANNEL_SECRET in .env file")
            all_present = False
        
        if self.line_access_token:
            self.print_success("LINE_CHANNEL_ACCESS_TOKEN is set")
        else:
            self.print_error("LINE_CHANNEL_ACCESS_TOKEN is missing",
                           "Set LINE_CHANNEL_ACCESS_TOKEN in .env file")
            all_present = False
        
        if self.anthropic_key:
            self.print_success("ANTHROPIC_API_KEY is set")
        else:
            self.print_error("ANTHROPIC_API_KEY is missing",
                           "Set ANTHROPIC_API_KEY in .env file")
            all_present = False
        
        return all_present
    
    def check_line_credentials(self) -> Tuple[bool, Optional[Dict]]:
        """Validate LINE credentials and get bot info."""
        self.print_header("2. LINE Credentials Validation")
        
        if not self.line_access_token:
            self.print_error("Cannot validate - access token missing")
            return False, None
        
        try:
            headers = {'Authorization': f'Bearer {self.line_access_token}'}
            response = requests.get('https://api.line.me/v2/bot/info', 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                self.print_success("LINE Access Token is VALID")
                print(f"  Bot Name: {bot_info.get('displayName', 'N/A')}")
                print(f"  Bot ID: {bot_info.get('basicId', 'N/A')}")
                print(f"  User ID: {bot_info.get('userId', 'N/A')}")
                return True, bot_info
            elif response.status_code == 401:
                self.print_error("LINE Access Token is INVALID or EXPIRED",
                               "Generate new token in LINE Developers Console")
                return False, None
            else:
                self.print_error(f"Unexpected response: {response.status_code}")
                return False, None
                
        except requests.exceptions.RequestException as e:
            self.print_error(f"Network error: {str(e)}")
            return False, None
    
    def check_webhook_configuration(self) -> Tuple[bool, Optional[str]]:
        """Check LINE webhook configuration."""
        self.print_header("3. Webhook Configuration Check")
        
        if not self.line_access_token:
            self.print_error("Cannot check - access token missing")
            return False, None
        
        try:
            headers = {'Authorization': f'Bearer {self.line_access_token}'}
            response = requests.get(
                'https://api.line.me/v2/bot/channel/webhook/endpoint',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                webhook_url = data.get('endpoint')
                
                if webhook_url:
                    self.print_success(f"Webhook is configured")
                    print(f"  URL: {webhook_url}")
                    
                    # Check if webhook is active
                    if data.get('active'):
                        self.print_success("Webhook is ACTIVE")
                    else:
                        self.print_warning("Webhook is configured but NOT ACTIVE")
                        self.recommendations.append(
                            "Enable webhook in LINE Developers Console > Messaging API > Webhook settings"
                        )
                    
                    return True, webhook_url
                else:
                    self.print_error("Webhook URL is not set",
                                   "Configure webhook URL in LINE Developers Console")
                    return False, None
            else:
                self.print_error(f"Failed to fetch webhook config: {response.status_code}")
                return False, None
                
        except requests.exceptions.RequestException as e:
            self.print_error(f"Network error: {str(e)}")
            return False, None
    
    def check_server_deployment(self) -> Tuple[bool, Optional[str]]:
        """Check if server is deployed and accessible."""
        self.print_header("4. Server Deployment Check")
        
        # Check local server
        local_url = 'http://localhost:8000'
        try:
            response = requests.get(f'{local_url}/health', timeout=3)
            if response.status_code == 200:
                self.print_success("Local server is running on port 8000")
                print(f"  Health check: {response.json()}")
        except:
            self.print_warning("Local server not detected (this is OK if deployed to production)")
        
        # Check production server
        if self.prod_url:
            self.print_success(f"Production URL found: {self.prod_url}")
            try:
                response = requests.get(f'{self.prod_url}/health', timeout=10)
                if response.status_code == 200:
                    self.print_success("Production server is ACCESSIBLE")
                    print(f"  Health check: {response.json()}")
                    return True, self.prod_url
                else:
                    self.print_error(f"Production server returned {response.status_code}",
                                   "Check deployment logs for errors")
                    return False, self.prod_url
            except requests.exceptions.RequestException as e:
                self.print_error(f"Cannot reach production server: {str(e)}",
                               "Verify deployment is running and URL is correct")
                return False, self.prod_url
        else:
            self.print_error("No production URL configured",
                           "Set RAILWAY_PUBLIC_URL or RENDER_EXTERNAL_URL")
            return False, None
    
    def check_webhook_endpoint_match(self, webhook_url: Optional[str], 
                                    server_url: Optional[str]) -> bool:
        """Check if webhook URL matches deployed server."""
        self.print_header("5. Webhook-Server URL Match")
        
        if not webhook_url or not server_url:
            self.print_warning("Cannot verify - missing URLs")
            return False
        
        # Extract domain from both URLs
        webhook_domain = webhook_url.replace('https://', '').replace('http://', '').split('/')[0]
        server_domain = server_url.replace('https://', '').replace('http://', '').split('/')[0]
        
        if webhook_domain == server_domain:
            self.print_success("Webhook URL matches production server")
            return True
        else:
            self.print_error(
                f"Webhook URL ({webhook_domain}) does NOT match server ({server_domain})",
                f"Update webhook URL to: {server_url}/webhook"
            )
            self.recommendations.append(
                f"Go to LINE Developers Console > Messaging API > Webhook settings\n"
                f"  Set webhook URL to: {server_url}/webhook"
            )
            return False
    
    def check_anthropic_api(self) -> bool:
        """Check if Anthropic API key is valid."""
        self.print_header("6. Anthropic API Check")
        
        if not self.anthropic_key:
            self.print_error("Anthropic API key not set")
            return False
        
        # We can't easily validate without making a real API call,
        # but we can check format
        if self.anthropic_key.startswith('sk-ant-'):
            self.print_success("Anthropic API key format looks valid")
            self.print_warning("Full validation requires making an API call")
            return True
        else:
            self.print_error("Anthropic API key format appears invalid",
                           "Key should start with 'sk-ant-'")
            return False
    
    def generate_summary_report(self, bot_info: Optional[Dict], 
                              webhook_url: Optional[str],
                              server_url: Optional[str]):
        """Generate final summary and recommendations."""
        self.print_header("DEPLOYMENT STATUS SUMMARY")
        
        total_checks = self.checks_passed + self.checks_failed
        
        print(f"Total Checks: {total_checks}")
        print(f"{GREEN}Passed: {self.checks_passed}{NC}")
        print(f"{RED}Failed: {self.checks_failed}{NC}")
        print()
        
        # Determine overall status
        if self.checks_failed == 0:
            print(f"{GREEN}{'='*60}")
            print(f"STATUS: ✅ BOT IS LIVE AND ACCESSIBLE")
            print(f"{'='*60}{NC}\n")
            
            if bot_info:
                print("📱 Users can add the bot:")
                print(f"   LINE ID: {bot_info.get('basicId', 'N/A')}")
                print(f"   Bot Name: {bot_info.get('displayName', 'N/A')}")
                if bot_info.get('userId'):
                    print(f"   Add Friend URL: https://line.me/R/ti/p/{bot_info['userId']}")
            
            print("\n📝 Next steps:")
            print("   1. Run: python scripts/generate_bot_access.py")
            print("   2. Share the QR code with test users")
            print("   3. Test with message: '金曜18時 博多'")
            
        elif self.checks_failed <= 2:
            print(f"{YELLOW}{'='*60}")
            print(f"STATUS: ⚠️  BOT HAS MINOR ISSUES")
            print(f"{'='*60}{NC}\n")
            print("The bot may work but needs attention.\n")
            
        else:
            print(f"{RED}{'='*60}")
            print(f"STATUS: ❌ BOT IS NOT ACCESSIBLE")
            print(f"{'='*60}{NC}\n")
            print("Multiple critical issues detected.\n")
        
        # Print issues
        if self.issues:
            print(f"{RED}🔧 Issues to fix:{NC}")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
            print()
        
        # Print recommendations
        if self.recommendations:
            print(f"{YELLOW}💡 Recommendations:{NC}")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"   {i}. {rec}")
            print()
        
        # Return overall status
        return self.checks_failed == 0
    
    def run_all_checks(self) -> bool:
        """Run all deployment checks."""
        print(f"\n{BLUE}╔═══════════════════════════════════════════════════════════╗")
        print(f"║  LINE Bot Comprehensive Deployment Verification           ║")
        print(f"╚═══════════════════════════════════════════════════════════╝{NC}\n")
        
        # Run checks
        env_ok = self.check_environment_variables()
        
        credentials_ok, bot_info = self.check_line_credentials()
        
        webhook_ok, webhook_url = self.check_webhook_configuration()
        
        server_ok, server_url = self.check_server_deployment()
        
        if webhook_url and server_url:
            self.check_webhook_endpoint_match(webhook_url, server_url)
        
        self.check_anthropic_api()
        
        # Generate summary
        is_live = self.generate_summary_report(bot_info, webhook_url, server_url)
        
        return is_live

def main():
    checker = BotDeploymentChecker()
    is_live = checker.run_all_checks()
    
    sys.exit(0 if is_live else 1)

if __name__ == '__main__':
    main()
