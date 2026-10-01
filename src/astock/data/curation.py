"""Typed specifications and reproducibility helpers; no market curation runner."""

import hashlib
from pathlib import Path
from typing import Literal
from uuid import UUID

import pyarrow as pa
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from astock.data.contracts import load_contracts
from astock.data.probe_audit import canonical_json
from astock.data.raw_writer import atomic_new_file

USAGES = {
    'daily': 'SIGNAL_ELIGIBLE_NEXT_SESSION',
    'daily_basic': 'CURRENT_RECONSTRUCTION',
    'adj_factor': 'AUDIT_RECONSTRUCTION_ONLY',
    'stk_limit': 'EXECUTION_CONSTRAINT_ONLY',
    'suspend_d': 'EXECUTION_FACT_ONLY',
    'stock_st': 'UNIVERSE_RISK_STATE_ONLY',
}
TYPES = {'string': pa.string(), 'float64': pa.float64(), 'int64': pa.int64(), 'date32': pa.date32()}


class CurationField(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, hide_input_in_errors=True)
    source_column: str = Field(pattern=r'^[a-z][a-z0-9_]*$')
    target_column: str = Field(pattern=r'^[a-z][a-z0-9_]*$')
    logical_type: Literal['string', 'float64', 'int64', 'date32']
    nullable_policy: Literal['FORBID', 'PRESERVE_NULL']
    unit: str = Field(min_length=1)
    identity_requirement: Literal['RESOLVED_AS_OF_EVENT', 'NONE']
    research_usage: str


class CurationSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, hide_input_in_errors=True)
    spec_version: Literal['1.0', '2.0']
    dataset: str
    source_catalog_version: Literal['v2']
    research_usage: str
    fields: list[CurationField] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_semantics(self):
        if USAGES.get(self.dataset) != self.research_usage:
            raise ValueError('Dataset usage restriction differs')
        for attribute in ('source_column', 'target_column'):
            values = [getattr(f, attribute) for f in self.fields]
            if len(set(values)) != len(values):
                raise ValueError('Duplicate curation column')
        if any(f.research_usage != self.research_usage for f in self.fields):
            raise ValueError('Field usage differs')
        identity = [f for f in self.fields if f.source_column == 'ts_code']
        if len(identity) != 1 or identity[0].identity_requirement != 'RESOLVED_AS_OF_EVENT':
            raise ValueError('Explicit identity resolution required')
        return self

    def arrow_schema(self) -> pa.Schema:
        return pa.schema([pa.field(f.target_column, TYPES[f.logical_type],
                                   nullable=f.nullable_policy != 'FORBID',
                                   metadata={'unit': f.unit, 'research_usage': f.research_usage})
                          for f in self.fields])

    def empty_table(self) -> pa.Table:
        return pa.Table.from_batches([], schema=self.arrow_schema())


def load_curation_specs(root: Path, *, spec_version: str='v1') -> tuple[CurationSpec, ...]:
    if spec_version not in ('v1','v2'):
        raise ValueError('Unknown curation version')
    contracts = {c.dataset: c for c in load_contracts(root, catalog_version='v2')}
    specs = tuple(CurationSpec.model_validate(yaml.safe_load(p.read_text()))
                  for p in sorted((root/f'config/curation/{spec_version}').glob('*.yaml')))
    if len(specs) != len(USAGES) or {s.dataset for s in specs} != set(USAGES):
        raise ValueError('Curation specification set differs')
    for s in specs:
        if s.spec_version != {'v1':'1.0','v2':'2.0'}[spec_version]:
            raise ValueError('Specification version differs')
        if not (root/f'config/curation/{spec_version}/{s.dataset}.yaml').is_file():
            raise ValueError('Curation filename must match dataset')
        if [f.source_column for f in s.fields] != contracts[s.dataset].required_fields:
            raise ValueError('Curation source columns differ from pinned catalog')
    return specs


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def configuration_hash(root: Path) -> str:
    paths = sorted([*(root/'config/contracts/v2').glob('*.yaml'),
                    *(root/'config/curation/v1').glob('*.yaml')])
    return digest([(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths])


def publish_curated_bytes(root: Path, *, dataset: str, run_id: UUID, part: int, content: bytes) -> Path:
    """No-clobber storage primitive only; callers must validate rows and register lineage."""
    if dataset not in USAGES or not isinstance(run_id, UUID) or not 0 <= part <= 999:
        raise ValueError('Invalid curated object destination')
    directory = root.resolve()/'data/curated'/dataset/f'curation_run_id={run_id}'
    path = directory/f'part-{part:03}.parquet'
    if not path.resolve().is_relative_to(root.resolve()/'data/curated'):
        raise ValueError('Curated destination escapes storage')
    atomic_new_file(path, lambda temporary: temporary.write_bytes(content))
    return path


def input_manifest_hash(objects: list[dict]) -> str:
    paths = [o['relative_path'] for o in objects]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate input manifest object path')
    return digest(sorted(objects, key=lambda o: o['relative_path']))
