"""Independent five-table store: source bundles, observations, reports and manual journal."""
from __future__ import annotations

import hashlib
from pathlib import Path

from astock.data.warehouse_lock import warehouse_connection, warehouse_lock
from astock.research.core import code_fingerprint, digest, encoded, instant, read_json, require
from astock.research.inputs import Bundle, SourceFile, load_bundle, records
from astock.research.publication import publish_bytes

SCHEMA = """
CREATE TABLE research_meta(version INTEGER PRIMARY KEY);
INSERT INTO research_meta VALUES (1);
CREATE TABLE research_bundle(id VARCHAR PRIMARY KEY, manifest JSON NOT NULL);
CREATE TABLE research_observation(bundle_id VARCHAR, dataset VARCHAR, record_key VARCHAR,
    available_at TIMESTAMPTZ, source_hash VARCHAR, payload JSON,
    PRIMARY KEY(bundle_id,dataset,record_key));
CREATE TABLE research_report(id VARCHAR PRIMARY KEY, bundle_id VARCHAR, snapshot JSON NOT NULL);
CREATE TABLE research_journal(id VARCHAR PRIMARY KEY, event_at TIMESTAMPTZ, available_at TIMESTAMPTZ,
    payload JSON NOT NULL);
"""


def observation_key(spec: SourceFile, row: dict) -> str:
    values = [row.get("code"), row.get("exchange"), row.get("date")]
    if spec.dataset == "status" and spec.adapter == "tushare-response-v1":
        values.append(spec.sha256)
        if row.get("event_key"):
            values.append(row["event_key"])
    if spec.dataset in {'industry_classification', 'industry_membership'}:
        values.append(row['industry_code'])
    return digest(values)


class ResearchStore:
    def __init__(self, path: Path):
        self.path = path.absolute()
        self._derived_cache = None
        require(not self.path.is_symlink(), "STORE_SYMLINK")

    def _check(self, db) -> None:
        tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
        require(tables == {"research_meta", "research_bundle", "research_observation", "research_report", "research_journal"},
                "NOT_A_RESEARCH_STORE")
        require(db.execute("SELECT version FROM research_meta").fetchall() == [(1,)], "STORE_VERSION")

    def initialize(self) -> None:
        # Never open/migrate an original database under a new schema.
        with warehouse_lock(self.path):
            existed = self.path.exists()
            with warehouse_connection(self.path) as db:
                if existed:
                    self._check(db)
                else:
                    db.execute("BEGIN")
                    try:
                        db.execute(SCHEMA)
                        db.execute("COMMIT")
                    except Exception:
                        db.execute("ROLLBACK")
                        raise

    def import_bundle(self, path: Path) -> str:
        bundle, inputs = load_bundle(path)  # validate ALL files before any SQL write
        manifest = bundle.model_dump(mode="json")
        bundle_id = digest(manifest)
        self.initialize()
        with warehouse_connection(self.path) as db:
            self._check(db)
            existing = db.execute("SELECT manifest FROM research_bundle WHERE id=?", [bundle_id]).fetchone()
            if existing:
                require(existing[0] == encoded(manifest).decode(), "BUNDLE_CONFLICT")
                self._verify_sources(manifest)
                return bundle_id
            # Immutable retained input bytes; SQL rollback may leave an unreferenced
            # content-addressed object, never partially admitted observations.
            raw = self.path.parent / "raw"
            require(not raw.is_symlink(), "RAW_DIRECTORY_SYMLINK")
            raw.mkdir(exist_ok=True)
            objects = {}
            for spec, body, _ in inputs:
                objects[spec.sha256] = body
                for evidence in spec.evidence:
                    proof = Path(evidence.path)
                    proof = proof if proof.is_absolute() else path.parent / proof
                    value = proof.read_bytes()
                    require(hashlib.sha256(value).hexdigest() == evidence.sha256, "SOURCE_EVIDENCE_CHANGED")
                    objects[evidence.sha256] = value
            for checksum, body in objects.items():
                target = raw / checksum
                require(not target.is_symlink(), "RAW_SYMLINK")
                if target.exists():
                    require(hashlib.sha256(target.read_bytes()).hexdigest() == checksum, "RAW_CORRUPTED")
                else:
                    publish_bytes(target, body)
            db.execute("BEGIN")
            try:
                db.execute("INSERT INTO research_bundle VALUES (?,?)", [bundle_id, encoded(manifest).decode()])
                values = []
                for spec, _, rows in inputs:
                    for row in rows:
                        key = observation_key(spec, row)
                        values.append([bundle_id, spec.dataset, key, spec.available_at, spec.sha256, encoded(row).decode()])
                if values:
                    db.executemany("INSERT INTO research_observation VALUES (?,?,?,?,?,?)", values)
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        return bundle_id

    def _verify_sources(self, manifest: dict) -> None:
        require(not (self.path.parent / "raw").is_symlink(), "RAW_DIRECTORY_SYMLINK")
        hashes = {item["sha256"] for file in manifest["files"] for item in [file, *file.get("evidence", [])]}
        for checksum in hashes:
            p = self.path.parent / "raw" / checksum
            require(p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest() == checksum,
                    "RETAINED_SOURCE_CHANGED")

    def snapshot(self, bundle_id: str, as_of: str) -> tuple[dict, dict]:
        import json
        with warehouse_connection(self.path, read_only=True) as db:
            self._check(db)
            item = db.execute("SELECT manifest FROM research_bundle WHERE id=?", [bundle_id]).fetchone()
            require(item is not None, "BUNDLE_UNKNOWN")
            manifest = json.loads(item[0])
            require(digest(manifest) == bundle_id, "STORED_MANIFEST_CHANGED")
            self._verify_sources(manifest)
            rows = db.execute("SELECT dataset,record_key,source_hash,payload FROM research_observation WHERE bundle_id=? AND available_at<=? ORDER BY dataset,record_key",
                              [bundle_id, instant(as_of)]).fetchall()
        signature = (bundle_id, instant(as_of).isoformat(), code_fingerprint())
        if self._derived_cache and self._derived_cache[0] == signature:
            expected = self._derived_cache[1]
        else:
            # Re-derive normalized observations from retained source bytes. This also
            # supplies an independent rebuild path without touching original stores.
            from astock.research.market_inputs import parse_bundle, parse_source
            bundle = parse_bundle(manifest)
            verified_inputs = []
            expected = []
            for item in manifest["files"]:
                spec = parse_source(item)
                body = (self.path.parent / "raw" / spec.sha256).read_bytes()
                proofs = {p.sha256: (self.path.parent / "raw" / p.sha256).read_bytes() for p in spec.evidence}
                # Verify even sources later than as_of; invalid grades cannot hide in
                # a retained manifest. Original capture paths need not still exist.
                normalized = records(spec, body, bundle, evidence_bodies=proofs)
                verified_inputs.append((spec, body, normalized))
                if instant(spec.available_at) <= instant(as_of):
                    expected.extend((spec.dataset, observation_key(spec, r), spec.sha256, encoded(r).decode())
                                    for r in normalized)
            if bundle.protocol == 'RESEARCH_INPUT_V2':
                from astock.research.inputs import validate_market_inputs
                validate_market_inputs(bundle, verified_inputs)
            expected = tuple(sorted(expected))
            # Bounded to one 256MiB encoded expectation; larger snapshots remain uncached.
            self._derived_cache = (signature, expected) if sum(len(r[3].encode())+128 for r in expected) <= 256*1024**2 else None
        require(sorted(rows) == sorted(expected), "STORED_OBSERVATIONS_CHANGED")
        result: dict[str, list] = {}
        for dataset, _, source_hash, payload in rows:
            result.setdefault(dataset, []).append({**json.loads(payload), "source_hash": source_hash})
        return manifest, result

    def save_report(self, snapshot: dict) -> str:
        run_id = digest(snapshot)
        with warehouse_connection(self.path) as db:
            self._check(db)
            old = db.execute("SELECT snapshot FROM research_report WHERE id=?", [run_id]).fetchone()
            if old:
                require(old[0] == encoded(snapshot).decode(), "REPORT_CONFLICT")
            else:
                db.execute("INSERT INTO research_report VALUES (?,?,?)",
                           [run_id, snapshot["bundle_id"], encoded(snapshot).decode()])
        return run_id
