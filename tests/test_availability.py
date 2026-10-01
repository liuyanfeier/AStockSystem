from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from astock.data.availability import AvailabilityBasis, RecordTimes, TimePrecision


NOW = datetime(2024, 1, 3, 8, tzinfo=timezone.utc)


def test_unknown_availability_preserves_uncertainty():
    record = RecordTimes(event_date=NOW.date(), retrieved_at=NOW)
    assert record.available_at is None
    assert record.availability_basis == AvailabilityBasis.UNKNOWN
    assert record.time_precision == TimePrecision.UNKNOWN


@pytest.mark.parametrize('basis', list(AvailabilityBasis))
def test_every_supported_basis_can_be_represented(basis):
    record = RecordTimes(event_at=NOW, retrieved_at=NOW, availability_basis=basis,
                         available_at=None if basis == AvailabilityBasis.UNKNOWN else NOW,
                         time_precision='SECOND')
    assert record.availability_basis == basis


@pytest.mark.parametrize('change', [
    {'availability_basis': 'INVENTED'}, {'time_precision': 'INVENTED'},
    {'available_at': NOW}, {'retrieved_at': NOW.replace(tzinfo=None)},
    {'availability_basis': 'SOURCE_PUBLICATION'},
    {'availability_basis': 'SOURCE_PUBLICATION', 'available_at': NOW,
     'published_at': NOW + timedelta(seconds=1)},
    {'availability_basis': 'OBSERVED_CAPTURE', 'available_at': NOW - timedelta(seconds=1)},
    {'event_date': None},
])
def test_invalid_or_future_leaking_availability_is_rejected(change):
    payload = {'event_date': NOW.date(), 'retrieved_at': NOW} | change
    with pytest.raises(ValidationError):
        RecordTimes(**payload)
