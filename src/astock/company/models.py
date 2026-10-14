"""Explicit evidence classes, financial units and publication/knowledge boundaries."""
from datetime import date
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator
from astock.research.core import instant, require


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Source(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    code: str = Field(pattern=r'^\d{6}\.(SH|SZ|BJ)$')
    title: str
    url: str
    published_on: date | None
    retrieved_at: str
    sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    hosting: Literal['DISCLOSURE_PLATFORM', 'ISSUER', 'DOCUMENT_MIRROR']
    state: Literal['RETRIEVED', 'UNAVAILABLE']
    # End of publication day conservatively avoids inventing an intraday release time.
    available_at: str | None
    publication_basis: Literal['DISCLOSURE_PLATFORM_DAY', 'MIRROR_ANNOUNCEMENT_DAY'] = 'DISCLOSURE_PLATFORM_DAY'
    audit: Literal['AUDITED', 'REVIEWED_NOT_AUDITED', 'UNAUDITED', 'UNKNOWN']

    @model_validator(mode='after')
    def source_boundary(self):
        u = urlsplit(self.url)
        require(u.scheme == 'https' and not u.username and not u.password and not u.query
                and not u.fragment, 'COMPANY_SOURCE_URL')
        platform = {'static.cninfo.com.cn', 'static.sse.com.cn', 'disc.static.szse.cn',
                    'www.bse.cn', 'www.hkexnews.hk', 'www1.hkexnews.hk'}
        mirrors = {'file.finance.sina.com.cn'}
        require(u.hostname in platform | mirrors, 'COMPANY_SOURCE_HOST')
        require(self.hosting == ('DOCUMENT_MIRROR' if u.hostname in mirrors else 'DISCLOSURE_PLATFORM'),
                'COMPANY_SOURCE_HOSTING')
        require((self.hosting == 'DOCUMENT_MIRROR') == (self.publication_basis == 'MIRROR_ANNOUNCEMENT_DAY'), 'COMPANY_PUBLICATION_BASIS')
        instant(self.retrieved_at)
        require((self.state == 'RETRIEVED') == (self.sha256 is not None), 'COMPANY_SOURCE_STATE')
        if self.state == 'RETRIEVED':
            require(self.published_on is not None and self.available_at is not None, 'COMPANY_SOURCE_TIME')
        if self.available_at:
            from datetime import datetime, time
            from zoneinfo import ZoneInfo
            require(self.published_on is not None, 'COMPANY_PUBLICATION_UNKNOWN')
            end = datetime.combine(self.published_on, time.max, ZoneInfo('Asia/Shanghai'))
            require(instant(self.available_at) >= max(instant(end), instant(self.retrieved_at)), 'COMPANY_PUBLICATION_DAY_BOUNDARY')
        return self


class Reference(Strict):
    source_id: str
    locator: str = Field(min_length=1)  # PDF page and table/paragraph, not a private path.


class Statement(Strict):
    id: str
    kind: Literal['FACT', 'INFERENCE', 'HYPOTHESIS', 'UNKNOWN']
    text: str = Field(min_length=1)
    references: list[Reference] = Field(default_factory=list)
    supports: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def evidence_class(self):
        require(self.kind != 'FACT' or bool(self.references), 'COMPANY_FACT_WITHOUT_SOURCE')
        require(self.kind not in ('INFERENCE', 'HYPOTHESIS') or bool(self.supports), 'COMPANY_REASON_WITHOUT_FACT')
        require(self.kind != 'UNKNOWN' or not self.supports, 'COMPANY_UNKNOWN_PROMOTED')
        return self


class Financial(Strict):
    id: str
    name: str
    value: Decimal | None
    unit: Literal['CNY', 'CNY_MILLION', 'PERCENT', 'CNY_PER_SHARE', 'SHARES']
    currency: Literal['CNY'] = 'CNY'
    period_start: date | None = None
    period_end: date
    accounting_basis: Literal['ASBE_CONSOLIDATED', 'ASBE_PARENT'] = 'ASBE_CONSOLIDATED'
    reference: Reference | None = None
    # Ratios derived elsewhere only compare identical metric/unit/period lengths.
    comparison_value: Decimal | None = None
    comparison_period_start: date | None = None
    comparison_period_end: date | None = None
    reported_change_percent: Decimal | None = None

    @model_validator(mode='after')
    def financial_boundary(self):
        require(self.value is None or self.value.is_finite(), 'COMPANY_FINANCIAL_NONFINITE')
        require(self.comparison_value is None or self.comparison_value.is_finite(), 'COMPANY_FINANCIAL_NONFINITE')
        require(self.value is None or self.reference is not None, 'COMPANY_NUMBER_WITHOUT_SOURCE')
        require(self.reported_change_percent is None or self.reported_change_percent.is_finite(), 'COMPANY_FINANCIAL_NONFINITE')
        require(self.comparison_period_start is None or self.comparison_period_end is not None and self.comparison_period_start <= self.comparison_period_end, 'COMPANY_COMPARISON_PERIOD')
        require(self.period_start is None or self.period_start <= self.period_end, 'COMPANY_PERIOD')
        require(self.comparison_value is None or self.comparison_period_end is not None, 'COMPANY_COMPARISON_PERIOD')
        require(self.value is not None or self.comparison_value is None, 'COMPANY_UNKNOWN_COMPARISON')
        if self.comparison_period_end:
            require(self.comparison_period_end < self.period_end, 'COMPANY_COMPARISON_FUTURE')
        return self


class Company(Strict):
    code: str = Field(pattern=r'^\d{6}\.(SH|SZ|BJ)$')
    profile: list[Statement]
    financials: list[Financial]
    events: list[Statement]
    support: list[Statement]
    counter: list[Statement]
    unknowns: list[Statement]
    status: Literal['继续重点研究', '普通跟踪', '暂不研究', '风险观察']
    priority_reason: str
    next_checks: list[str] = Field(min_length=1)
    thesis_invalidations: list[str] = Field(min_length=1)


class ResearchCatalog(Strict):
    protocol: Literal['COMPANY_RESEARCH_V1']
    as_of: str
    sources: list[Source]
    companies: list[Company]

    @model_validator(mode='after')
    def research_time_and_dependencies(self):
        cutoff = instant(self.as_of)
        sources = {s.id: s for s in self.sources}
        require(len(sources) == len(self.sources), 'COMPANY_DUPLICATE_SOURCE')
        require(len({c.code for c in self.companies}) == len(self.companies), 'COMPANY_DUPLICATE_CODE')
        for source in self.sources:
            require(instant(source.retrieved_at) <= cutoff, 'COMPANY_RETRIEVED_AFTER_ASOF')
        for company in self.companies:
            require(all(s.kind == 'UNKNOWN' for s in company.unknowns), 'COMPANY_UNKNOWN_CLASS')
            require(len({f.id for f in company.financials}) == len(company.financials), 'COMPANY_DUPLICATE_FINANCIAL')
            statements = [*company.profile, *company.events, *company.support, *company.counter, *company.unknowns]
            facts = {s.id for s in statements if s.kind == 'FACT'}
            require(len({s.id for s in statements}) == len(statements), 'COMPANY_DUPLICATE_STATEMENT')
            for statement in statements:
                require(set(statement.supports) <= facts, 'COMPANY_SUPPORT_NOT_FACT')
                for reference in statement.references:
                    self._reference(reference, company.code, sources, cutoff)
            for figure in company.financials:
                require(figure.period_end <= cutoff.date(), 'COMPANY_FUTURE_FINANCIAL_PERIOD')
                if figure.reference:
                    source = self._reference(figure.reference, company.code, sources, cutoff)
                    require(source.published_on >= figure.period_end, 'COMPANY_REPORT_BEFORE_PERIOD')
        return self

    @staticmethod
    def _reference(reference, code, sources, cutoff):
        require(reference.source_id in sources, 'COMPANY_SOURCE_UNKNOWN')
        source = sources[reference.source_id]
        require(source.code == code, 'COMPANY_CROSS_ENTITY_SOURCE')
        require(source.state == 'RETRIEVED' and source.available_at is not None
                and instant(source.available_at) <= cutoff, 'COMPANY_EVIDENCE_UNAVAILABLE')
        return source
