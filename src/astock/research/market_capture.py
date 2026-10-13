"""Fixed market partitions and day batches using the existing capture runner."""
from typing import Literal
from pydantic import Field, model_validator
from astock.research.acquisition import CapturePlan
from astock.research.core import require


class MarketCapturePlan(CapturePlan):
    protocol: Literal['RESEARCH_CAPTURE_V2']
    universe: list[str] = Field(default_factory=list, max_length=0)
    universe_scope: Literal['CURRENT_A_SHARE_L'] = 'CURRENT_A_SHARE_L'
    markets: list[Literal['SSE', 'SZSE', 'BSE']]
    bse_calendar_reference: Literal['SSE_AGREES_SZSE_DOCUMENTED'] = 'SSE_AGREES_SZSE_DOCUMENTED'
    industry_version: Literal['SW2021_L1'] = 'SW2021_L1'
    industry_codes: list[str] = Field(min_length=1, max_length=100)
    expected_min_sessions: int = Field(ge=1, le=250)
    members: list[dict] = Field(min_length=1, max_length=1024)
    maximum_requests: int = Field(ge=1, le=1024)
    maximum_attempts: int = Field(ge=1, le=1024)
    max_total_body_bytes: int = Field(ge=1024, le=1024**3)
    max_added_disk_bytes: int = Field(ge=1024**2, le=4 * 1024**3)

    @model_validator(mode='after')
    def market_scope(self):
        require(set(self.markets) == {'SSE', 'SZSE', 'BSE'} and len(self.markets) == 3, 'MARKET_PLAN_EXCHANGES')
        require(len(set(self.industry_codes)) == len(self.industry_codes), 'MARKET_PLAN_INDUSTRIES')
        require(all(m.get('contract_version') == 'RESEARCH_PROVIDER_V2' for m in self.members), 'MARKET_PLAN_CONTRACT')
        basics = [m['params'] for m in self.members if m['api'] == 'stock_basic']
        require(basics == [dict(exchange=e, list_status='L') for e in self.markets], 'MARKET_PLAN_IDENTITIES')
        industry = [m['params']['l1_code'] for m in self.members if m['api'] == 'index_member_all']
        require(industry == self.industry_codes, 'MARKET_PLAN_INDUSTRY_PARTITIONS')
        require([m['params'] for m in self.members if m['api'] == 'index_classify'] == [dict(level='L1', src='SW2021')], 'MARKET_PLAN_CLASSIFICATION')
        calendar = [m['params'] for m in self.members if m['api']=='trade_cal']
        require(calendar == [dict(exchange=e,start_date=self.window_start.strftime('%Y%m%d'),end_date=self.window_end.strftime('%Y%m%d')) for e in ('SSE','SZSE')], 'MARKET_PLAN_CALENDARS')
        days = {api: [m['params']['trade_date'] for m in self.members if m['api']==api] for api in ('daily','adj_factor')}
        require(days['daily'] == days['adj_factor'] and len(days['daily']) >= self.expected_min_sessions, 'MARKET_PLAN_DAY_PARTITIONS')
        return self


def parse_plan(value: dict) -> CapturePlan:
    return (MarketCapturePlan if value.get('protocol') == 'RESEARCH_CAPTURE_V2' else CapturePlan).model_validate(value)
