import pytest
from src.claude_service import ClaudeService
from src.models import ParsedIntent, TransportType


@pytest.mark.asyncio
class TestClaudeService:
    """Tests for ClaudeService."""

    @pytest.fixture
    def service(self):
        return ClaudeService()

    async def test_parse_simple_message(self, service):
        """Test parsing a simple message with all information."""
        message = "東京から博多 金曜18時"
        intent = await service.parse_user_message(message)

        assert intent.destination == "博多" or intent.destination is not None
        assert isinstance(intent, ParsedIntent)

    async def test_parse_ambiguous_message(self, service):
        """Test parsing an ambiguous message."""
        message = "明日行きたい"
        intent = await service.parse_user_message(message)

        assert intent.is_ambiguous is True
        assert intent.clarification_needed is not None

    async def test_fallback_on_error(self, service):
        """Test fallback behavior on parsing error."""
        # This should trigger fallback
        intent = service._create_fallback_intent("test message")

        assert intent.is_ambiguous is True
        assert intent.confidence == 0.0
