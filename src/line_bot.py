from typing import List, Union

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhook import MessageEvent, TextMessageContent
from linebot.v3.webhooks import MessageEvent as WebhookMessageEvent

from src.claude_service import ClaudeService
from src.config import settings
from src.logging_config import get_logger
from src.message_formatter import MessageFormatter
from src.models import ParsedIntent
from src.session_manager import SessionManager
from src.transport_service import TransportService

logger = get_logger(__name__)


class LineBotHandler:
    """Main handler for LINE bot webhook events."""

    def __init__(self) -> None:
        configuration = Configuration(
            access_token=settings.line_channel_access_token,
        )
        self.api_client = ApiClient(configuration)
        self.messaging_api = MessagingApi(self.api_client)

        self.claude_service = ClaudeService()
        self.transport_service = TransportService()
        self.session_manager = SessionManager()
        self.message_formatter = MessageFormatter()

    async def handle_text_message(
        self,
        event: MessageEvent,
    ) -> None:
        """Handle incoming text message from user.

        Args:
            event: LINE webhook message event
        """
        try:
            if not isinstance(event.message, TextMessageContent):
                logger.warning("non_text_message_received", event_type=type(event.message))
                return

            user_id = event.source.user_id
            message_text = event.message.text
            reply_token = event.reply_token

            logger.info(
                "processing_message",
                user_id=user_id,
                message=message_text,
            )

            # Get user session
            session = self.session_manager.get_session(user_id)

            # Parse message with Claude
            intent = await self.claude_service.parse_user_message(
                user_message=message_text,
                context=session.context,
            )

            # Update session with parsed intent
            session.last_intent = intent
            self._update_session_from_intent(user_id, intent)

            # Generate response
            response_messages = await self._generate_response(intent)

            # Send reply
            await self._send_reply(reply_token, response_messages)

            logger.info(
                "message_processed_successfully",
                user_id=user_id,
                is_ambiguous=intent.is_ambiguous,
            )

        except Exception as e:
            logger.error(
                "error_processing_message",
                error=str(e),
                exc_info=True,
            )
            # Send error message
            error_msg = self.message_formatter.format_error_message(
                "メッセージの処理中にエラーが発生しました。"
            )
            await self._send_reply(reply_token, [error_msg])

    async def _generate_response(
        self,
        intent: ParsedIntent,
    ) -> List[Union[TextMessage, object]]:
        """Generate response messages based on parsed intent.

        Args:
            intent: Parsed user intent

        Returns:
            List of LINE message objects
        """
        # If ambiguous, request clarification
        if intent.is_ambiguous:
            return [self.message_formatter.format_clarification(intent)]

        # Check if we have enough information
        if not intent.departure or not intent.destination:
            clarification_intent = ParsedIntent(
                is_ambiguous=True,
                clarification_needed="出発地と目的地を教えてください。\n\n例: 東京から博多",
                confidence=0.0,
            )
            return [self.message_formatter.format_clarification(clarification_intent)]

        # Search for transport options
        options = await self.transport_service.search_transport(intent)

        # Format results
        results_message = self.message_formatter.format_transport_options(
            options=options,
            intent=intent,
        )

        return [results_message]

    async def _send_reply(
        self,
        reply_token: str,
        messages: List[Union[TextMessage, object]],
    ) -> None:
        """Send reply to LINE user.

        Args:
            reply_token: Reply token from webhook event
            messages: List of messages to send
        """
        try:
            self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=messages,
                )
            )
            logger.info("reply_sent", message_count=len(messages))
        except Exception as e:
            logger.error(
                "error_sending_reply",
                error=str(e),
                exc_info=True,
            )
            raise

    def _update_session_from_intent(
        self,
        user_id: str,
        intent: ParsedIntent,
    ) -> None:
        """Update session context from parsed intent."""
        if intent.departure:
            self.session_manager.update_session_context(
                user_id, "departure", intent.departure
            )
        if intent.destination:
            self.session_manager.update_session_context(
                user_id, "destination", intent.destination
            )
        if intent.date:
            self.session_manager.update_session_context(user_id, "date", intent.date)
        if intent.time:
            self.session_manager.update_session_context(user_id, "time", intent.time)
