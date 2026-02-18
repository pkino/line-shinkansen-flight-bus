import json
from typing import Optional

import anthropic
from anthropic import AsyncAnthropic

from src.config import settings
from src.logging_config import get_logger
from src.models import ParsedIntent, TransportType

logger = get_logger(__name__)


class ClaudeService:
    """Service for interacting with Claude API for natural language understanding."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    async def parse_user_message(
        self,
        user_message: str,
        context: Optional[dict[str, str]] = None,
    ) -> ParsedIntent:
        """Parse user message to extract travel intent.

        Args:
            user_message: The user's natural language message
            context: Previous conversation context for multi-turn conversations

        Returns:
            ParsedIntent object with extracted information
        """
        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(user_message, context)

            logger.info(
                "calling_claude_api",
                message=user_message,
                model=self.model,
            )

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
            )

            # Extract text from response
            response_text = response.content[0].text
            logger.info("claude_response_received", response=response_text)

            # Parse JSON response
            parsed_data = json.loads(response_text)
            intent = ParsedIntent(**parsed_data)

            logger.info(
                "intent_parsed_successfully",
                intent=intent.model_dump(),
            )

            return intent

        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), response=response_text)
            return self._create_fallback_intent(user_message)

        except anthropic.APIError as e:
            logger.error("claude_api_error", error=str(e))
            return self._create_fallback_intent(user_message)

        except Exception as e:
            logger.error("unexpected_error", error=str(e), exc_info=True)
            return self._create_fallback_intent(user_message)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Claude."""
        return """You are a travel assistant for Japanese domestic transport search.
Your job is to extract travel information from natural language queries.

Extract the following information:
- departure: departure location (Japanese city/station name)
- destination: destination location (Japanese city/station name)
- date: travel date (convert to ISO format YYYY-MM-DD if possible)
- time: preferred time (convert to HH:MM format if possible)
- transport_type: one of [shinkansen, flight, bus, unknown]
- is_ambiguous: true if critical information is missing or unclear
- clarification_needed: what specific information needs to be clarified
- confidence: float 0-1 indicating parsing confidence

IMPORTANT RULES:
1. For relative dates like "金曜" (Friday), "来週" (next week), set is_ambiguous=true and ask for clarification
2. Common Japanese cities: 東京, 大阪, 福岡, 博多, 京都, 名古屋, 札幌, 仙台, etc.
3. If only one location is mentioned, ask which is departure vs destination
4. Default transport_type is "unknown" unless explicitly mentioned
5. Return ONLY valid JSON, no other text

JSON Schema:
{
  "departure": "string or null",
  "destination": "string or null",
  "date": "string or null",
  "time": "string or null",
  "transport_type": "shinkansen|flight|bus|unknown",
  "is_ambiguous": boolean,
  "clarification_needed": "string or null",
  "confidence": float
}"""

    def _build_user_prompt(self, message: str, context: Optional[dict[str, str]]) -> str:
        """Build the user prompt with optional context."""
        prompt = f"User message: {message}\n\n"

        if context:
            prompt += "Previous context:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        prompt += "Extract travel information and return as JSON:"
        return prompt

    def _create_fallback_intent(self, user_message: str) -> ParsedIntent:
        """Create a fallback intent when parsing fails."""
        return ParsedIntent(
            is_ambiguous=True,
            clarification_needed="申し訳ございません。メッセージを理解できませんでした。\n\n出発地、目的地、日時を教えていただけますか？",
            confidence=0.0,
        )
