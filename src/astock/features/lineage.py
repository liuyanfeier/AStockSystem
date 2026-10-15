"""Compact repeated feature provenance without coupling computation to publication."""
from copy import deepcopy

from astock.research.core import digest


def intern_feature_sources(features: list[dict]) -> tuple[list[dict], dict[str, list[str]]]:
    compact = deepcopy(features)
    sources: dict[str, list[str]] = {}
    for feature in compact:
        hashes = sorted(set(feature.pop("source_hashes", [])))
        key = digest(hashes)
        sources[key] = hashes
        feature["source_hash_set_id"] = key
    return compact, sources
