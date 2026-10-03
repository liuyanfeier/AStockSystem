"""Scoped provider representations; official codes and legacy identities stay separate."""

from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from astock.data.identity import _aware, is_native_identifier, is_normalized_ashare_identifier
from astock.data.receipt_integrity import digest

DATASETS = ('daily', 'daily_basic', 'adj_factor', 'stk_limit', 'stock_st', 'suspend_d')
RESOLVER_PROTOCOL = 'R2_RESOLVER_UTC_INSTANT_V2'


class ImmutableModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, hide_input_in_errors=True, revalidate_instances='always')


class ListingEpisode(ImmutableModel):
    episode_id: UUID
    security_id: str = Field(min_length=1)
    venue: Literal['SSE', 'SZSE', 'BSE', 'OTHER']
    asset_type: Literal['STK', 'CDR', 'BOND', 'OTHER', 'UNKNOWN']
    valid_from: date
    valid_to: date | None = None
    last_trading_date: date | None = None
    provider_delist_date: date | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime
    available_at: AwareDatetime
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    approval_ref: str = Field(min_length=1)

    @model_validator(mode='after')
    def intervals(self):
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError('Episode requires a nonempty half-open interval')
        if self.available_at < self.retrieved_at or (self.published_at and self.available_at < self.published_at):
            raise ValueError('Episode availability precedes its evidence')
        return self

    def contains(self, event: date) -> bool:
        return self.valid_from <= event and (self.valid_to is None or event < self.valid_to)


class ExchangeCode(ImmutableModel):
    code_id: UUID
    episode_id: UUID
    identifier_type: Literal['EXCHANGE_CODE'] = 'EXCHANGE_CODE'
    identifier: str
    valid_from: date
    valid_to: date | None = None
    available_at: AwareDatetime
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    approval_ref: str = Field(min_length=1)

    @model_validator(mode='after')
    def interval(self):
        if not is_normalized_ashare_identifier(self.identifier):
            raise ValueError('Official code requires independently normalized identity')
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError('Official code requires a half-open interval')
        return self


class SourceObservation(ImmutableModel):
    raw_object_id: UUID
    raw_row_number: int = Field(ge=0, strict=True)
    event_date: date


class ProviderBinding(ImmutableModel):
    binding_id: UUID
    binding_version: int = Field(ge=1)
    provider: Literal['tushare'] = 'tushare'
    dataset: Literal['daily', 'daily_basic', 'adj_factor', 'stk_limit', 'stock_st', 'suspend_d']
    native_identifier: str
    episode_id: UUID
    representation_kind: Literal['EVENT_NATIVE', 'RETROSPECTIVE', 'UNKNOWN']
    observations: tuple[SourceObservation, ...] = Field(min_length=1)
    first_observed_at: AwareDatetime
    decision_at: AwareDatetime
    available_at: AwareDatetime
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    decision_status: Literal['PROPOSED', 'APPROVED', 'EVIDENCE_REQUIRED', 'CONFLICT', 'OUT_OF_SCOPE']
    approval_ref: str | None = None
    supersedes_binding_id: UUID | None = None
    knowledge_basis: Literal['CURRENT_RECONSTRUCTION'] = 'CURRENT_RECONSTRUCTION'

    @model_validator(mode='after')
    def exact_scope(self):
        if not is_native_identifier(self.native_identifier):
            raise ValueError('Native value must be retained nonblank text')
        if not self.first_observed_at <= self.decision_at <= self.available_at:
            raise ValueError('Decision knowledge cannot precede observation')
        if len(set((o.raw_object_id, o.raw_row_number, o.event_date) for o in self.observations)) != len(self.observations):
            raise ValueError('Duplicate observed source scope')
        if self.decision_status == 'APPROVED' and (not self.approval_ref or self.representation_kind == 'UNKNOWN'):
            raise ValueError('An active binding needs explicit approval and representation')
        return self


class Resolution(ImmutableModel):
    native_identifier: str | None
    reason: str | None
    security_id: str | None = None
    episode_id: UUID | None = None
    venue: str | None = None
    exchange_code_at_event: str | None = None
    binding_id: UUID | None = None
    binding_available_at: AwareDatetime | None = None
    representation_kind: str | None = None
    evidence_ids: tuple[str, ...] = ()
    basis: Literal['CURRENT_RECONSTRUCTION'] = 'CURRENT_RECONSTRUCTION'


def canonical_resolver_member(member: ListingEpisode | ExchangeCode | ProviderBinding) -> dict:
    """V2: explicit resolver instants only; retain dates and all other semantics."""
    fields = {
        ListingEpisode: ('published_at', 'retrieved_at', 'available_at'),
        ExchangeCode: ('available_at',),
        ProviderBinding: ('first_observed_at', 'decision_at', 'available_at'),
    }
    payload = member.model_dump(mode='json')
    for field in fields[type(member)]:
        value = getattr(member, field)
        if value is not None:
            _aware(value)
            payload[field] = value.astimezone(timezone.utc).isoformat(timespec='microseconds').removesuffix('+00:00') + 'Z'
    return payload


def canonical_resolver_payload(resolver) -> dict:
    """One membership/serialization rule for hashing, storage and validation."""
    return {
        key: sorted((canonical_resolver_member(member) for member in members), key=lambda row: row[id_field])
        for key, members, id_field in (
            ('episodes', resolver.episodes, 'episode_id'),
            ('official_codes', resolver.codes, 'code_id'),
            ('provider_bindings', resolver.bindings, 'binding_id'),
        )
    }


class ProviderResolver:
    def __init__(self, episodes, codes, bindings):
        self.episodes = tuple(ListingEpisode.model_validate(e) for e in episodes)
        self.codes = tuple(ExchangeCode.model_validate(c) for c in codes)
        self.bindings = tuple(ProviderBinding.model_validate(b) for b in bindings)
        if len({e.episode_id for e in self.episodes}) != len(self.episodes):
            raise ValueError('Duplicate episode version; append a new episode ID')
        if len({b.binding_id for b in self.bindings}) != len(self.bindings):
            raise ValueError('Duplicate binding version')
        if len({c.code_id for c in self.codes}) != len(self.codes):
            raise ValueError('Duplicate official code record')
        self._episodes = {e.episode_id: e for e in self.episodes}
        def unique_intervals(rows, key, message):
            groups = {}
            for row in rows: groups.setdefault(key(row), []).append(row)
            for group in groups.values():
                ordered = sorted(group, key=lambda r: r.valid_from)
                for left, right in zip(ordered, ordered[1:]):
                    if left.valid_to is None or right.valid_from < left.valid_to:
                        raise ValueError(message)
        unique_intervals(self.episodes, lambda e:e.security_id, 'Overlapping listing episodes; identity conflict')
        unique_intervals(self.codes, lambda c:c.episode_id, 'Ambiguous official code/episode interval')
        unique_intervals(self.codes, lambda c:c.identifier, 'Ambiguous official code/episode interval')
        self._codes = {}
        for c in self.codes:self._codes.setdefault(c.episode_id, []).append(c)
        self._resolution_indices = {}
        by_id = {b.binding_id: b for b in self.bindings}
        episode_ids = {e.episode_id for e in self.episodes}
        for c in self.codes:
            if c.episode_id not in episode_ids:
                raise ValueError('Official code has no episode')
            episode = self._episodes[c.episode_id]
            if c.valid_from < episode.valid_from or (episode.valid_to is not None and (c.valid_to is None or c.valid_to > episode.valid_to)):
                raise ValueError('Official interval cannot extend listing episode')
        successors = set()
        for b in self.bindings:
            if b.episode_id not in episode_ids:
                raise ValueError('Binding has no episode')
            if b.supersedes_binding_id:
                old = by_id.get(b.supersedes_binding_id)
                if not old or b.supersedes_binding_id in successors:
                    raise ValueError('Missing or forked supersession')
                if (old.provider, old.dataset, old.native_identifier) != (b.provider, b.dataset, b.native_identifier):
                    raise ValueError('Supersession cannot cross provider scope')
                if b.available_at <= old.available_at or b.binding_version <= old.binding_version:
                    raise ValueError('Supersession requires later version/knowledge')
                successors.add(b.supersedes_binding_id)
        # Each exact source scope has an independent knowledge interval. A
        # proposed successor cannot end an approved interval. This avoids scanning
        # every source row at every knowledge boundary in a real126-output batch.
        approved = [b for b in self.bindings if b.decision_status == 'APPROVED']
        ends = {b.supersedes_binding_id:b.available_at for b in approved if b.supersedes_binding_id}
        scopes = {}
        for b in approved:
            for o in b.observations:
                key = b.provider,b.dataset,b.native_identifier,o.raw_object_id,o.raw_row_number,o.event_date
                scopes.setdefault(key, []).append((b.available_at,ends.get(b.binding_id)))
        for intervals in scopes.values():
            ordered = sorted(intervals)
            for left,right in zip(ordered,ordered[1:]):
                if left[1] is None or right[0] < left[1]:
                    raise ValueError('Overlapping provider mapping; quarantine conflict')

    def _known(self, as_of):
        known = [b for b in self.bindings if b.available_at <= as_of and b.decision_status == 'APPROVED']
        superseded = {b.supersedes_binding_id for b in known}
        return [b for b in known if b.binding_id not in superseded and b.decision_status == 'APPROVED']

    @property
    def snapshot_hash(self):
        return digest(canonical_resolver_payload(self))

    def resolve(self, *, provider, dataset, native_identifier, event_date: date,
                raw_object_id: UUID, raw_row_number: int, knowledge_as_of: datetime,
                provider_exchange=None, provider_asset_type=None):
        _aware(knowledge_as_of)
        if not isinstance(raw_object_id, UUID) or type(raw_row_number) is not int or raw_row_number < 0:
            raise ValueError('Explicit capture source and zero-based row required')
        def reject(reason):
            return Resolution(native_identifier=native_identifier, reason=reason)
        if not is_native_identifier(native_identifier):
            return reject('MISSING_NATIVE_IDENTIFIER')
        if not is_normalized_ashare_identifier(native_identifier):
            return reject('NON_NORMALIZED_IDENTIFIER')
        if knowledge_as_of not in self._resolution_indices:
            index = {}
            for binding in self._known(knowledge_as_of):
                for observation in binding.observations:
                    key = (binding.provider,binding.dataset,binding.native_identifier,
                           observation.raw_object_id,observation.raw_row_number,observation.event_date)
                    index.setdefault(key, []).append(binding)
            self._resolution_indices[knowledge_as_of] = index
        matches = self._resolution_indices[knowledge_as_of].get(
            (provider,dataset,native_identifier,raw_object_id,raw_row_number,event_date), [])
        if len(matches) != 1:
            return reject('AMBIGUOUS_PROVIDER_BINDING' if matches else 'NO_SCOPED_PROVIDER_BINDING')
        b = matches[0]
        e = self._episodes[b.episode_id]
        if e.available_at > knowledge_as_of:
            return reject('EPISODE_KNOWLEDGE_UNAVAILABLE')
        if e.venue == 'BSE' and event_date < date(2021,11,15):
            return reject('PRE_BSE_LEGACY')
        if not e.contains(event_date):
            return reject('OUTSIDE_LISTING_EPISODE')
        if provider_exchange is not None and provider_exchange != e.venue:
            return reject('PROVIDER_EXCHANGE_CONFLICT')
        if provider_asset_type is not None and provider_asset_type != e.asset_type:
            return reject('PROVIDER_ASSET_CONFLICT')
        if e.asset_type == 'UNKNOWN' or (dataset == 'stk_limit' and provider_asset_type is None):
            return reject('ASSET_EVIDENCE_REQUIRED')
        if e.asset_type != 'STK' or e.venue not in ('SSE','SZSE','BSE'):
            return reject('ASSET_OUT_OF_SCOPE')
        codes = [c for c in self._codes.get(e.episode_id, []) if c.available_at <= knowledge_as_of
                 and c.valid_from <= event_date and (c.valid_to is None or event_date < c.valid_to)]
        if len(codes) != 1:
            return reject('OFFICIAL_CODE_EVIDENCE_REQUIRED' if not codes else 'OFFICIAL_CODE_CONFLICT')
        if b.representation_kind == 'EVENT_NATIVE' and native_identifier != codes[0].identifier:
            return reject('EVENT_NATIVE_OFFICIAL_CODE_CONFLICT')
        return Resolution(native_identifier=native_identifier, reason=None,security_id=e.security_id,
                          episode_id=e.episode_id,venue=e.venue,exchange_code_at_event=codes[0].identifier,
                          binding_id=b.binding_id,binding_available_at=b.available_at,
                          representation_kind=b.representation_kind,
                          evidence_ids=tuple(sorted(set((*e.evidence_ids,*b.evidence_ids,*codes[0].evidence_ids)))))
