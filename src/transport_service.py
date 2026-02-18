from datetime import datetime, timedelta
from typing import List

from src.logging_config import get_logger
from src.models import ParsedIntent, TransportOption, TransportType

logger = get_logger(__name__)


class TransportService:
    """Service for searching transport options (mock implementation for MVP)."""

    async def search_transport(
        self,
        intent: ParsedIntent,
    ) -> List[TransportOption]:
        """Search for transport options based on parsed intent.

        Args:
            intent: Parsed user intent

        Returns:
            List of transport options (mock data for MVP)
        """
        logger.info(
            "searching_transport",
            departure=intent.departure,
            destination=intent.destination,
            date=intent.date,
        )

        # Return mock data for MVP
        return self._generate_mock_options(intent)

    def _generate_mock_options(self, intent: ParsedIntent) -> List[TransportOption]:
        """Generate mock transport options for testing."""

        # Determine base transport type
        if intent.transport_type == TransportType.UNKNOWN:
            # Default to shinkansen for common routes
            transport_type = TransportType.SHINKANSEN
        else:
            transport_type = intent.transport_type

        departure = intent.departure or "東京"
        destination = intent.destination or "博多"

        if transport_type == TransportType.SHINKANSEN:
            return self._generate_shinkansen_options(departure, destination, intent.time)
        elif transport_type == TransportType.FLIGHT:
            return self._generate_flight_options(departure, destination, intent.time)
        else:
            return self._generate_shinkansen_options(departure, destination, intent.time)

    def _generate_shinkansen_options(
        self,
        departure: str,
        destination: str,
        preferred_time: str | None,
    ) -> List[TransportOption]:
        """Generate mock shinkansen options."""

        base_time = preferred_time or "18:00"
        hour, minute = map(int, base_time.split(":"))

        options = [
            TransportOption(
                transport_type=TransportType.SHINKANSEN,
                departure_time=f"{hour:02d}:{minute:02d}",
                arrival_time=f"{(hour+5) % 24:02d}:{(minute+11) % 60:02d}",
                duration="5時間11分",
                price=22950,
                departure_station=departure,
                arrival_station=destination,
                train_name="のぞみ57号",
                seat_availability="◯",
            ),
            TransportOption(
                transport_type=TransportType.SHINKANSEN,
                departure_time=f"{(hour+1) % 24:02d}:{minute:02d}",
                arrival_time=f"{(hour+6) % 24:02d}:{(minute+23) % 60:02d}",
                duration="5時間23分",
                price=22950,
                departure_station=departure,
                arrival_station=destination,
                train_name="のぞみ63号",
                seat_availability="△",
            ),
            TransportOption(
                transport_type=TransportType.SHINKANSEN,
                departure_time=f"{(hour+2) % 24:02d}:{minute:02d}",
                arrival_time=f"{(hour+7) % 24:02d}:{(minute+15) % 60:02d}",
                duration="5時間15分",
                price=22950,
                departure_station=departure,
                arrival_station=destination,
                train_name="ひかり537号",
                seat_availability="◯",
            ),
        ]

        return options

    def _generate_flight_options(
        self,
        departure: str,
        destination: str,
        preferred_time: str | None,
    ) -> List[TransportOption]:
        """Generate mock flight options."""

        base_time = preferred_time or "18:00"
        hour, minute = map(int, base_time.split(":"))

        # Convert city names to airport codes (simplified)
        dep_airport = f"{departure}空港"
        arr_airport = f"{destination}空港"

        options = [
            TransportOption(
                transport_type=TransportType.FLIGHT,
                departure_time=f"{hour:02d}:{minute:02d}",
                arrival_time=f"{(hour+2) % 24:02d}:{minute:02d}",
                duration="2時間",
                price=18500,
                departure_station=dep_airport,
                arrival_station=arr_airport,
                train_name="ANA453",
                seat_availability="◯",
            ),
            TransportOption(
                transport_type=TransportType.FLIGHT,
                departure_time=f"{(hour+1) % 24:02d}:{(minute+30) % 60:02d}",
                arrival_time=f"{(hour+3) % 24:02d}:{(minute+30) % 60:02d}",
                duration="2時間",
                price=16800,
                departure_station=dep_airport,
                arrival_station=arr_airport,
                train_name="JAL321",
                seat_availability="△",
            ),
        ]

        return options
