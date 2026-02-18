from typing import List

from linebot.v3.messaging import (
    FlexBubble,
    FlexBox,
    FlexButton,
    FlexCarousel,
    FlexComponent,
    FlexMessage,
    FlexText,
    TextMessage,
    URIAction,
)

from src.logging_config import get_logger
from src.models import ParsedIntent, TransportOption

logger = get_logger(__name__)


class MessageFormatter:
    """Format responses for LINE messaging."""

    def format_clarification(
        self,
        intent: ParsedIntent,
    ) -> TextMessage:
        """Format a clarification request message."""
        message = intent.clarification_needed or "情報を確認させてください。"
        return TextMessage(text=message)

    def format_transport_options(
        self,
        options: List[TransportOption],
        intent: ParsedIntent,
    ) -> FlexMessage:
        """Format transport options as a Flex Message carousel."""

        if not options:
            return TextMessage(text="申し訳ございません。該当する便が見つかりませんでした。")

        # Create header text
        header = self._create_header(intent)

        # Create bubbles for each option
        bubbles = [self._create_option_bubble(option) for option in options]

        carousel = FlexCarousel(contents=bubbles)

        return FlexMessage(
            alt_text=f"{intent.departure}→{intent.destination}の検索結果",
            contents=carousel,
        )

    def format_error_message(self, error_message: str) -> TextMessage:
        """Format an error message."""
        return TextMessage(
            text=f"エラーが発生しました。\n\n{error_message}\n\nもう一度お試しください。"
        )

    def _create_header(self, intent: ParsedIntent) -> str:
        """Create header text for search results."""
        parts = []
        if intent.departure:
            parts.append(intent.departure)
        if intent.destination:
            parts.append(intent.destination)

        route = "→".join(parts) if parts else "検索結果"

        if intent.date:
            route += f" ({intent.date})"

        return route

    def _create_option_bubble(self, option: TransportOption) -> FlexBubble:
        """Create a Flex Bubble for a single transport option."""

        # Determine color based on transport type
        color_map = {
            "shinkansen": "#0066CC",
            "flight": "#CC0000",
            "bus": "#00AA00",
        }
        header_color = color_map.get(option.transport_type.value, "#666666")

        # Transport type label
        type_label_map = {
            "shinkansen": "新幹線",
            "flight": "飛行機",
            "bus": "バス",
        }
        type_label = type_label_map.get(option.transport_type.value, "その他")

        # Build bubble content
        bubble = FlexBubble(
            size="kilo",
            header=FlexBox(
                layout="vertical",
                contents=[
                    FlexText(
                        text=type_label,
                        color="#FFFFFF",
                        size="sm",
                        weight="bold",
                    )
                ],
                background_color=header_color,
                padding_all="md",
            ),
            body=FlexBox(
                layout="vertical",
                contents=[
                    # Train/Flight name
                    FlexText(
                        text=option.train_name or "N/A",
                        size="xl",
                        weight="bold",
                        margin="none",
                    ),
                    # Time section
                    FlexBox(
                        layout="baseline",
                        contents=[
                            FlexText(
                                text=option.departure_time,
                                size="3xl",
                                weight="bold",
                                flex=0,
                            ),
                            FlexText(
                                text=" → ",
                                size="lg",
                                color="#999999",
                                flex=0,
                                margin="sm",
                            ),
                            FlexText(
                                text=option.arrival_time,
                                size="3xl",
                                weight="bold",
                                flex=0,
                            ),
                        ],
                        margin="lg",
                    ),
                    # Duration
                    FlexText(
                        text=f"所要時間: {option.duration}",
                        size="sm",
                        color="#666666",
                        margin="md",
                    ),
                    # Route
                    FlexBox(
                        layout="baseline",
                        contents=[
                            FlexText(
                                text=option.departure_station,
                                size="sm",
                                flex=1,
                            ),
                            FlexText(
                                text="→",
                                size="sm",
                                color="#999999",
                                flex=0,
                                margin="sm",
                            ),
                            FlexText(
                                text=option.arrival_station,
                                size="sm",
                                flex=1,
                                align="end",
                            ),
                        ],
                        margin="md",
                    ),
                    # Price and availability
                    FlexBox(
                        layout="baseline",
                        contents=[
                            FlexText(
                                text=f"¥{option.price:,}",
                                size="xl",
                                weight="bold",
                                color=header_color,
                            ),
                            FlexText(
                                text=f"空席: {option.seat_availability}",
                                size="sm",
                                color="#666666",
                                align="end",
                            ),
                        ],
                        margin="lg",
                    ),
                ],
                padding_all="xl",
            ),
            footer=FlexBox(
                layout="vertical",
                contents=[
                    FlexButton(
                        style="primary",
                        color=header_color,
                        action=URIAction(
                            label="予約する (準備中)",
                            uri="https://line.me",
                        ),
                    )
                ],
                padding_all="md",
            ),
        )

        return bubble
