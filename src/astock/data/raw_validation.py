"""Read-only exact raw/sidecar proof, also usable for generic multipart runs."""

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import UUID

import pyarrow.parquet as pq

from astock.data.audit import RawObjectManifest, RequestParams
from astock.data.probe_audit import canonical_json
from astock.data.slice_errors import ReceiptIntegrityError


def require(condition: bool, code: str, **counts) -> None:
    if not condition:
        raise ReceiptIntegrityError(code, **counts)


def strict_json(value: str | bytes) -> object:
    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, 'JSON_DUPLICATE_KEY')
            result[key] = item
        return result

    def invalid_constant(_):
        raise ReceiptIntegrityError('JSON_INVALID')

    try:
        return json.loads(value, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except ReceiptIntegrityError:
        raise
    except (ValueError, TypeError, UnicodeError):
        raise ReceiptIntegrityError('JSON_INVALID') from None


def typed_params(value: str | bytes | dict) -> dict:
    params = strict_json(value) if isinstance(value, (str, bytes)) else value
    require(type(params) is dict, 'PARAMS_TYPE')
    require(not (params.keys() - RequestParams.model_fields.keys()), 'PARAMS_UNKNOWN_FIELD')
    for key, item in params.items():
        require(item is None or type(item) is str, 'PARAMS_TYPE')
        if item is not None and key in ('trade_date', 'start_date', 'end_date'):
            try:
                require(date.fromisoformat(item).isoformat() == item, 'PARAMS_DATE')
            except ValueError:
                raise ReceiptIntegrityError('PARAMS_DATE') from None
    try:
        RequestParams.model_validate(params)
    except ValueError:
        raise ReceiptIntegrityError('PARAMS_INVALID') from None
    return params


def same_json(left: object, right: object) -> bool:
    # Canonical bytes preserve bool/number/string/null distinctions that == loses.
    return canonical_json(left) == canonical_json(right)


def safe_file(root: Path, relative: str, *, under: str) -> Path:
    require(type(relative) is str, 'UNSAFE_PATH')
    parts = PurePosixPath(relative).parts
    require(bool(parts) and not relative.startswith('/') and '\\' not in relative,
            'UNSAFE_PATH')
    require(all(p not in ('', '.', '..') for p in relative.split('/')), 'UNSAFE_PATH')
    base = root.resolve()
    candidate = base
    for part in parts:
        candidate = candidate / part
        require(not candidate.is_symlink(), 'UNSAFE_PATH')
    require(candidate.resolve().is_relative_to(base / under), 'UNSAFE_PATH')
    require(candidate.is_file(), 'EVIDENCE_MISSING')
    return candidate


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def instant(value: object) -> datetime:
    require(type(value) is str, 'METADATA_TIME')
    try:
        result = datetime.fromisoformat(value)
        require(result.tzinfo is not None and result.utcoffset() is not None, 'METADATA_TIME')
        return result.astimezone(timezone.utc)
    except ValueError:
        raise ReceiptIntegrityError('METADATA_TIME') from None


def rows_dict(db, sql: str, params: list) -> list[dict]:
    result = db.execute(sql, params)
    columns = [c[0] for c in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def validate_raw_run(root: Path, db, run_id: UUID) -> list[dict]:
    """Exactly match every registered part and sidecar; no terminal-run assumption."""
    from astock.data.raw_writer import schema_digest

    runs = rows_dict(db, 'SELECT * FROM ingestion_run WHERE run_id=?', [str(run_id)])
    require(len(runs) == 1, 'RUN_CARDINALITY', expected=1, observed=len(runs))
    manifests = rows_dict(db, 'SELECT * FROM raw_object_manifest WHERE run_id=? ORDER BY relative_path',
                          [str(run_id)])
    require(bool(manifests), 'RAW_CARDINALITY', expected=1, observed=0)
    dataset = runs[0]['dataset']
    side_path = safe_file(root, f'data/raw/tushare/{dataset}/run_id={run_id}/manifest.json',
                          under='data/raw')
    side = strict_json(side_path.read_bytes())
    require(type(side) is dict and set(side) == {'run_id', 'dataset', 'objects'}, 'SIDECAR_FIELDS')
    require(side['run_id'] == str(run_id) and side['dataset'] == dataset, 'SIDECAR_IDENTITY')
    require(type(side['objects']) is list and len(side['objects']) == len(manifests),
            'SIDECAR_CARDINALITY', expected=len(manifests),
            observed=len(side['objects']) if type(side['objects']) is list else 0)
    seen = set()
    checked = []
    for manifest in manifests:
        params = typed_params(manifest['request_params'])
        try:
            RawObjectManifest.model_validate({**manifest, 'request_params': params})
        except ValueError:
            raise ReceiptIntegrityError('RAW_METADATA') from None
        require(manifest['dataset'] == dataset, 'RAW_DATASET')
        path = safe_file(root, manifest['relative_path'], under='data/raw')
        require(sha256(path) == manifest['sha256'], 'FILE_CHECKSUM')
        arrow = pq.ParquetFile(path).read()
        require(arrow.num_rows == manifest['row_count'], 'FILE_ROW_COUNT')
        require(schema_digest(arrow) == manifest['schema_hash'], 'FILE_SCHEMA')
        dates = []
        for column in ('trade_date', 'cal_date'):
            if column in arrow.column_names:
                for item in arrow[column].to_pylist():
                    if isinstance(item, str) and re.fullmatch(r'[0-9]{8}', item):
                        try:
                            dates.append(date.fromisoformat(f'{item[:4]}-{item[4:6]}-{item[6:]}'))
                        except ValueError:
                            pass  # Same event-bound derivation as the immutable writer.
        require((min(dates) if dates else None) == manifest['min_event_date']
                and (max(dates) if dates else None) == manifest['max_event_date'], 'FILE_EVENT_BOUNDS')
        expected = dict(object_id=str(manifest['object_id']), relative_path=manifest['relative_path'],
                        sha256=manifest['sha256'], row_count=manifest['row_count'],
                        schema_hash=manifest['schema_hash'], request_params=params,
                        min_event_date=manifest['min_event_date'].isoformat() if manifest['min_event_date'] else None,
                        max_event_date=manifest['max_event_date'].isoformat() if manifest['max_event_date'] else None,
                        availability_basis='OBSERVED_CAPTURE')
        matches = [item for item in side['objects'] if type(item) is dict
                   and item.get('object_id') == expected['object_id']]
        require(len(matches) == 1 and expected['object_id'] not in seen, 'SIDECAR_OBJECT_SET')
        item = matches[0]
        require(set(item) == set(expected) | {'retrieved_at', 'available_at'}, 'SIDECAR_FIELDS')
        require(same_json({k: item[k] for k in expected}, expected), 'SIDECAR_CONTENT')
        require(instant(item['retrieved_at']) == manifest['retrieved_at']
                and instant(item['available_at']) == manifest['retrieved_at'], 'SIDECAR_TIME')
        seen.add(expected['object_id'])
        checked.append(dict(manifest=manifest, arrow=arrow, path=path,
                            sidecar_sha256=sha256(side_path)))
    require(len(seen) == len(side['objects']), 'SIDECAR_OBJECT_SET')
    return checked
