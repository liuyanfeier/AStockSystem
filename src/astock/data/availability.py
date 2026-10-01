"""Knowledge-time representation only; does not reconstruct production timestamps."""

from datetime import date
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator


class AvailabilityBasis(StrEnum):
    MARKET_CLOSE_RECONSTRUCTED = "MARKET_CLOSE_RECONSTRUCTED"
    PROVIDER_DOCUMENTED_SCHEDULE = "PROVIDER_DOCUMENTED_SCHEDULE"
    SOURCE_PUBLICATION = "SOURCE_PUBLICATION"
    CONSERVATIVE_NEXT_SESSION = "CONSERVATIVE_NEXT_SESSION"
    OBSERVED_CAPTURE = "OBSERVED_CAPTURE"
    EXECUTION_FACT = "EXECUTION_FACT"
    UNKNOWN = "UNKNOWN"


class TimePrecision(StrEnum):
    DATE = "DATE"
    MINUTE = "MINUTE"
    SECOND = "SECOND"
    MICROSECOND = "MICROSECOND"
    UNKNOWN = "UNKNOWN"


class RecordTimes(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    event_date: date | None = None
    event_at: AwareDatetime | None = None
    published_at: AwareDatetime | None = None
    available_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime
    availability_basis: AvailabilityBasis = AvailabilityBasis.UNKNOWN
    time_precision: TimePrecision = TimePrecision.UNKNOWN

    @model_validator(mode="after")
    def check_times(self):
        if self.event_date is None and self.event_at is None:
            raise ValueError("An event date or time is required")
        if self.availability_basis == AvailabilityBasis.UNKNOWN and self.available_at is not None:
            raise ValueError("Unknown availability must not invent an available_at")
        if self.availability_basis != AvailabilityBasis.UNKNOWN and self.available_at is None:
            raise ValueError("An evidenced basis requires available_at")
        if self.published_at and self.available_at and self.available_at < self.published_at:
            raise ValueError("Availability cannot precede publication")
        if (self.availability_basis == AvailabilityBasis.OBSERVED_CAPTURE
                and self.available_at < self.retrieved_at):
            raise ValueError("Observed capture cannot establish earlier availability")
        return self
