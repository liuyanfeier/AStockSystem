"""Read-only global consumption and approved identity facts from retained stores."""
from __future__ import annotations

import json
from pathlib import Path

from astock.data.warehouse_lock import warehouse_connection
from astock.phase1.core import day, digest, encoded, file_hash, logical_id, overlapping, require

ORIGINALS = {
    "warehouse": "data/warehouse/astock.duckdb",
    "metadata": "data/private/phase1c1-admission-metadata-live-v1/metadata.duckdb",
    "capture": "data/private/full-backfill-v1/capture.duckdb",
}


def normalized_params(params: dict) -> dict:
    return {k: day(v).strftime("%Y%m%d") if isinstance(v, str) and
            (k.endswith("_date") or k == "period") else v for k, v in params.items()}


def snapshot(root: Path, *, paths: dict | None = None) -> dict:
    paths = paths or {k: root / v for k, v in ORIGINALS.items()}
    records, hashes, rowsets = [], {}, {}
    for name, p in paths.items():
        require(not p.with_suffix(".duckdb.wal").exists(), "LEGACY_WAL_PRESENT")
        with warehouse_connection(p, read_only=True) as db:
            hashes[name] = file_hash(p)
            if name == "warehouse":
                for rid, dataset, params, state, attempts in db.execute(
                        'SELECT request_id,dataset,request_params,status,attempts FROM slice_request ORDER BY ordinal').fetchall():
                    req = dict(dataset=dataset, params=normalized_params(json.loads(params)))
                    records.append(dict(store=name, origin_id=str(rid), request=req,
                                        logical_id=logical_id(req), state=state, consumed=attempts > 0))
                rowsets[name] = digest(records)
            elif name == "metadata":
                for rid, payload in db.execute('SELECT request_id,request_json FROM metadata_member ORDER BY request_id').fetchall():
                    wire = json.loads(payload)["wire"]
                    req = dict(dataset=wire["api_name"], params=normalized_params(wire["params"]))
                    history = db.execute('SELECT state FROM metadata_event WHERE request_id=? ORDER BY ordinal', [rid]).fetchall()
                    records.append(dict(store=name, origin_id=str(rid), request=req,
                                        logical_id=logical_id(req), state=history[-1][0] if history else "PENDING", consumed=bool(history)))
                rowsets[name] = digest([r for r in records if r["store"] == name])
            else:
                names = {n for n, in db.execute('SHOW TABLES').fetchall()}
                from astock.data.receipt_integrity import serial
                rowsets[name] = digest({n: serial(db.execute('SELECT * FROM "' + n + '" ORDER BY ALL').fetchall()) for n in sorted(names)})
                for mid, obj, origin, payload in db.execute('SELECT member_id,object_id,origin_plan,payload FROM backfill_member ORDER BY member_id').fetchall():
                    member = json.loads(payload)
                    req = dict(dataset=member["dataset"], params=normalized_params(member["params"]))
                    history = db.execute('SELECT state FROM backfill_event WHERE member_id=? ORDER BY ordinal', [mid]).fetchall()
                    if "continuation_event" in names:
                        newer = db.execute('SELECT state FROM continuation_event WHERE member_id=? ORDER BY ordinal', [mid]).fetchall()
                        require(not (history and newer), "CROSS_VERSION_DOUBLE_CONSUMPTION")
                        history = history or newer
                    records.append(dict(store=name, origin_id=mid, object_id=str(obj), origin_plan=origin,
                                        request=req, logical_id=logical_id(req), state=history[-1][0] if history else "PENDING", consumed=bool(history)))
            require(hashes[name] == file_hash(p), "LEGACY_CHANGED_DURING_SNAPSHOT")
    return dict(protocol="PHASE1_GLOBAL_CONSUMPTION_V1", root=str(root.resolve()),
                original_paths={k: str(v.resolve()) for k, v in paths.items()}, original_hashes=hashes,
                rowset_hashes=rowsets, records=records)


def check_unconsumed(member: dict, legacy: dict, *, allow_known_complete_overlap=True) -> None:
    mid = logical_id(member)
    for r in legacy["records"]:
        if not r["consumed"]:
            continue
        require(r["logical_id"] != mid, "ALREADY_CONSUMED_GLOBAL_REQUEST")
        if overlapping(member, r["request"]):
            require(allow_known_complete_overlap and r["state"] in ("COMPLETE", "RAW_RETAINED")
                    and member["dataset"] == "trade_cal", "OVERLAPPING_HISTORICAL_SCOPE_HOLD")


def check_snapshot(legacy: dict) -> None:
    # Locked stable bytes; timestamps and directory names do not stand in for hashes.
    for name, rel in legacy["original_paths"].items():
        p = Path(rel)
        require(not p.with_suffix(".duckdb.wal").exists(), "LEGACY_WAL_PRESENT")
        with warehouse_connection(p, read_only=True):
            require(file_hash(p) == legacy["original_hashes"][name], "LEGACY_CONSUMPTION_CHANGED")


def approved_identity_export(root: Path) -> dict:
    """Export finite approved facts with their actual scope; never infer wider aliases."""
    from astock.data.receipt_integrity import serial
    p = root / ORIGINALS["warehouse"]
    with warehouse_connection(p, read_only=True) as db:
        tables = {}
        for n in ("listing_episode", "official_exchange_code", "provider_native_binding", "provider_binding_observation"):
            q = db.execute('SELECT * FROM "' + n + '" ORDER BY ALL')
            names = [c[0] for c in q.description]
            tables[n] = [dict(zip(names, serial(row), strict=True)) for row in q.fetchall()]
        return dict(warehouse_hash=file_hash(p), tables=tables, scope="EXACT_EXISTING_APPROVED_FACTS_ONLY",
                    grants_new_mapping=False, resolver_rows_not_global_security_master=True)
