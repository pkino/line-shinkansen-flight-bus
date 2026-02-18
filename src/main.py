import os
import httpx
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import anthropic
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

if not all([LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, CLAUDE_API_KEY]):
    logger.error("Missing required environment variables")
    logger.error(f"LINE_CHANNEL_SECRET: {'SET' if LINE_CHANNEL_SECRET else 'MISSING'}")
    logger.error(f"LINE_CHANNEL_ACCESS_TOKEN: {'SET' if LINE_CHANNEL_ACCESS_TOKEN else 'MISSING'}")
    logger.error(f"CLAUDE_API_KEY: {'SET' if CLAUDE_API_KEY else 'MISSING'}")

app = FastAPI(
    title="LINE AI Bot",
    description="AI-powered LINE bot using Claude",
    version="1.0.0"
)

# Initialize LINE Bot
try:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN) if LINE_CHANNEL_ACCESS_TOKEN else None
    handler = WebhookHandler(LINE_CHANNEL_SECRET) if LINE_CHANNEL_SECRET else None
except Exception as e:
    logger.error(f"Failed to initialize LINE Bot: {e}")
    line_bot_api = None
    handler = None

# Initialize Claude client
try:
    claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None
except Exception as e:
    logger.error(f"Failed to initialize Claude client: {e}")
    claude_client = None

# Store deployment info
DEPLOYMENT_TIME = datetime.utcnow().isoformat()
REQUEST_COUNT = 0
LAST_WEBHOOK_TIME = None
HEALTH_CHECK_COUNT = 0


@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "LINE AI Bot",
        "status": "running",
        "version": "1.0.0",
        "deployed_at": DEPLOYMENT_TIME,
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "webhook": "/webhook",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint for load balancers"""
    global HEALTH_CHECK_COUNT
    HEALTH_CHECK_COUNT += 1
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all service status"""
    global HEALTH_CHECK_COUNT
    HEALTH_CHECK_COUNT += 1
    
    health_status = {
        "service": "LINE AI Bot",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "deployment_time": DEPLOYMENT_TIME,
        "metrics": {
            "total_requests": REQUEST_COUNT,
            "health_checks": HEALTH_CHECK_COUNT,
            "last_webhook": LAST_WEBHOOK_TIME
        },
        "components": {}
    }
    
    # Check environment variables
    env_status = "healthy"
    env_details = {
        "LINE_CHANNEL_SECRET": "configured" if LINE_CHANNEL_SECRET else "missing",
        "LINE_CHANNEL_ACCESS_TOKEN": "configured" if LINE_CHANNEL_ACCESS_TOKEN else "missing",
        "CLAUDE_API_KEY": "configured" if CLAUDE_API_KEY else "missing"
    }
    if not all([LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, CLAUDE_API_KEY]):
        env_status = "degraded"
    
    health_status["components"]["environment"] = {
        "status": env_status,
        "details": env_details
    }
    
    # Check LINE Bot API
    line_status = "unknown"
    line_details = {}
    
    if line_bot_api:
        try:
            # Test LINE API with a simple API call
            quota = line_bot_api.get_message_quota()
            line_status = "healthy"
            line_details = {
                "api": "connected",
                "quota_type": quota.type,
                "quota_value": quota.value
            }
        except LineBotApiError as e:
            line_status = "unhealthy"
            line_details = {
                "error": str(e),
                "status_code": e.status_code if hasattr(e, 'status_code') else None
            }
        except Exception as e:
            line_status = "unhealthy"
            line_details = {"error": str(e)}
    else:
        line_status = "not_initialized"
        line_details = {"error": "LINE Bot API not initialized"}
    
    health_status["components"]["line_bot"] = {
        "status": line_status,
        "details": line_details
    }
    
    # Check Claude API
    claude_status = "unknown"
    claude_details = {}
    
    if claude_client:
        try:
            # Test Claude API with a minimal request
            response = claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            claude_status = "healthy"
            claude_details = {
                "api": "connected",
                "model": "claude-sonnet-4-5-20250929"
            }
        except anthropic.APIError as e:
            claude_status = "unhealthy"
            claude_details = {"error": str(e)}
        except Exception as e:
            claude_status = "unhealthy"
            claude_details = {"error": str(e)}
    else:
        claude_status = "not_initialized"
        claude_details = {"error": "Claude client not initialized"}
    
    health_status["components"]["claude_api"] = {
        "status": claude_status,
        "details": claude_details
    }
    
    # Determine overall status
    component_statuses = [comp["status"] for comp in health_status["components"].values()]
    if all(status == "healthy" for status in component_statuses):
        health_status["status"] = "operational"
    elif any(status == "unhealthy" for status in component_statuses):
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "unknown"
    
    # Return appropriate HTTP status code
    status_code = 200 if health_status["status"] in ["operational", "degraded"] else 503
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.post("/webhook")
async def webhook(request: Request):
    """LINE webhook endpoint"""
    global REQUEST_COUNT, LAST_WEBHOOK_TIME
    REQUEST_COUNT += 1
    LAST_WEBHOOK_TIME = datetime.utcnow().isoformat()
    
    if not handler:
        logger.error("Webhook handler not initialized")
        raise HTTPException(status_code=500, detail="Webhook handler not initialized")
    
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    body_str = body.decode('utf-8')
    
    logger.info(f"Received webhook request. Signature present: {bool(signature)}")
    
    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"status": "ok"}


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """Handle text messages from LINE"""
    if not claude_client or not line_bot_api:
        logger.error("Claude client or LINE Bot API not initialized")
        return
    
    user_message = event.message.text
    logger.info(f"Received message: {user_message}")
    
    try:
        # Call Claude API
        response = claude_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        
        ai_response = response.content[0].text
        logger.info(f"Claude response: {ai_response[:100]}...")
        
        # Send reply via LINE
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="申し訳ございません。AIサービスに接続できませんでした。")
        )
    except LineBotApiError as e:
        logger.error(f"LINE Bot API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
