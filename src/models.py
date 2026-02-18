from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Transport type enumeration."""

    SHINKANSEN = "shinkansen"
    FLIGHT = "flight"
    BUS = "bus"
    UNKNOWN = "unknown"


class ParsedIntent(BaseModel):
    """Parsed user intent from natural language."""

    departure: Optional[str] = Field(None, description="Departure location")
    destination: Optional[str] = Field(None, description="Destination location")
    date: Optional[str] = Field(None, description="Travel date (ISO format or natural)")
    time: Optional[str] = Field(None, description="Preferred time")
    transport_type: TransportType = Field(
        default=TransportType.UNKNOWN,
        description="Preferred transport type",
    )
    is_ambiguous: bool = Field(
        default=False,
        description="Whether the query needs clarification",
    )
    clarification_needed: Optional[str] = Field(
        None,
        description="What clarification is needed",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of the parsing",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "departure": "東京",
                "destination": "博多",
                "date": "2024-01-26",
                "time": "18:00",
                "transport_type": "shinkansen",
                "is_ambiguous": False,
                "confidence": 0.95,
            }
        }


class TransportOption(BaseModel):
    """A single transport option (mock data for MVP)."""

    transport_type: TransportType
    departure_time: str
    arrival_time: str
    duration: str
    price: int
    departure_station: str
    arrival_station: str
    train_name: Optional[str] = None
    seat_availability: str = Field(default="Available")

    class Config:
        json_schema_extra = {
            "example": {
                "transport_type": "shinkansen",
                "departure_time": "18:03",
                "arrival_time": "23:14",
                "duration": "5h 11min",
                "price": 22950,
                "departure_station": "東京",
                "arrival_station": "博多",
                "train_name": "のぞみ57号",
                "seat_availability": "◯",
            }
        }


class ConversationSession(BaseModel):
    """User conversation session state."""

    user_id: str
    last_intent: Optional[ParsedIntent] = None
    context: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update(self) -> None:
        """Update the session timestamp."""
        self.updated_at = datetime.utcnow()
