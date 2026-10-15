"""Native computation contract; public report serialization is an output adapter."""
from typing import Literal
from astock.company.models import Strict
from astock.features.lineage import intern_feature_sources
from astock.research.core import digest


class MarketSnapshot(Strict):
    protocol: Literal['MARKET_SNAPSHOT_V1'] = "MARKET_SNAPSHOT_V1"
    bundle_id: str
    as_of: str
    window_start: str
    window_end: str
    code_hash: str
    parameters: dict
    parameters_hash: str
    market: dict
    radar: dict
    features: list[dict]
    source_hash_sets: dict[str, list[str]]
    source_manifest_hash: str
    limitations: list[str]

    @classmethod
    def from_analysis(cls, value: dict) -> "MarketSnapshot":
        features, hashes = intern_feature_sources(value["features"])
        return cls(**{key: value[key] for key in (
            "bundle_id", "as_of", "window_start", "window_end", "code_hash",
            "parameters", "parameters_hash", "market", "radar", "limitations")},
                   features=features, source_hash_sets=hashes,
                   source_manifest_hash=digest(value["sources"]))
