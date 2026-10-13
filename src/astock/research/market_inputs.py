"""V2 input contracts; V1 dumps and historical source hashes remain unchanged."""
from typing import Literal
from pydantic import Field
from astock.research.inputs import Bundle, SourceFile


class MarketSourceFile(SourceFile):
    dataset: Literal['instruments', 'calendar', 'daily', 'index_daily', 'adj_factor', 'status',
                     'industry_classification', 'industry_membership']
    calendar_exchange: Literal['SSE', 'SZSE', 'BSE'] | None = None


class MarketBundle(Bundle):
    protocol: Literal['RESEARCH_INPUT_V2']
    universe_scope: Literal['CURRENT_A_SHARE_L', 'PROVIDER_SAMPLE', 'WATCHLIST']
    files: list[MarketSourceFile] = Field(min_length=1)
    # A declared documentary proxy, not a fabricated BSE calendar response.
    bse_calendar_reference: Literal['SSE_AGREES_SZSE_DOCUMENTED', 'INDEPENDENT', 'UNKNOWN'] = 'UNKNOWN'


def parse_bundle(value: dict) -> Bundle:
    model = MarketBundle if value.get('protocol') == 'RESEARCH_INPUT_V2' else Bundle
    return model.model_validate(value)


def parse_source(value: dict) -> SourceFile:
    model = MarketSourceFile if value.get('dataset') in {'industry_classification', 'industry_membership'} else SourceFile
    return model.model_validate(value)
