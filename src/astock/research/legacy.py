"""Read-only adapter of retained market samples; no old acquisition/build workflow."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import UUID

from astock.data.raw_validation import sha256, validate_raw_run
from astock.data.warehouse_lock import warehouse_connection
from astock.phase1 import acquisition
from astock.research.core import day, encoded, read_json, require


def make_bundle(root: Path, output: Path, start: date, end: date, codes: list[str]) -> dict:
    require(start <= end and codes and len(codes) == len(set(codes)), "LEGACY_SCOPE")
    require(not output.exists(), "BUNDLE_OUTPUT_EXISTS")
    files = []
    with warehouse_connection(root / "data/warehouse/astock.duckdb", read_only=True) as db:
        for dataset in ("stock_basic", "daily", "adj_factor"):
            parents = sorted((root / "data/raw/tushare" / dataset).glob("run_id=*"))
            for parent in parents:
                side = read_json(parent / "manifest.json")
                # Only select windows actually present; do not manufacture dates.
                if dataset != "stock_basic":
                    sample = side["objects"][0]
                    observed = day(sample["request_params"]["trade_date"])
                    if not start <= observed <= end:
                        continue
                checked = validate_raw_run(root, db, UUID(side["run_id"]))
                for item in checked:
                    m, table = item["manifest"], item["arrow"]
                    if dataset == "stock_basic" and not (set(table["ts_code"].to_pylist()) & set(codes)):
                        continue
                    proof = [parent / "manifest.json"]
                    contract = parent / "capture-contract.json"
                    if contract.is_file():
                        proof.append(contract)
                    files.append(dict(path=str(item["path"]), sha256=m["sha256"],
                                      dataset="instruments" if dataset == "stock_basic" else dataset,
                                      format="parquet", source=f"retained:TUSHARE/{dataset}/{side['run_id']}",
                                      retrieved_at=m["retrieved_at"].isoformat(), available_at=m["retrieved_at"].isoformat(),
                                      adapter="tushare-v1", evidence=[dict(path=str(p), sha256=sha256(p)) for p in proof],
                                      **(dict(volume_unit="lots100", amount_unit="thousand_CNY") if dataset == "daily" else {})))
    destination = root / "data/private/phase1-integrated-v1"
    exchanges = set()
    with acquisition.store(root, destination, read_only=True) as db:
        members = db.execute("SELECT logical_id,object_id FROM p1_receipt ORDER BY logical_id").fetchall()
        for mid, oid in members:
            directory = destination / "objects" / oid
            source = read_json(directory / "http-source.json")
            member = source["request"]
            if member["dataset"] != "trade_cal":
                continue
            params = member["params"]
            if not day(params["start_date"]) <= start <= end <= day(params["end_date"]):
                continue
            exchange = params["exchange"]
            require(exchange not in exchanges, "LEGACY_CALENDAR_DUPLICATE")
            acquisition.physical_validate(root, destination, db, mid)
            exchanges.add(exchange)
            path = directory / "typed.parquet"
            files.append(dict(path=str(path), sha256=sha256(path), dataset="calendar", format="parquet",
                              source=f"retained:TUSHARE/trade_cal/{oid}; CURRENT_OBSERVATION only, not Phase1 fact admission",
                              retrieved_at=source["retrieved_at"], available_at=source["retrieved_at"], adapter="tushare-v1",
                              evidence=[dict(path=str(directory/name), sha256=sha256(directory/name))
                                        for name in ("response.body", "http-source.json", "manifest.json", "sidecar.json")]))
    bundle = dict(protocol="RESEARCH_INPUT_V1", purpose="CURRENT_OBSERVATION", window_start=start.isoformat(),
                  window_end=end.isoformat(), universe=codes, benchmarks=[], universe_scope="WATCHLIST", files=files)
    # Existing validators establish identity, calendar coverage, units and duplicates.
    # Store import decides current-purpose eligibility; no p1_fact is written.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(encoded(bundle) + b"\n")
    return bundle
