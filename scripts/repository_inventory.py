"""Read-only capacity inventory; never open a database or follow a symlink.

Full file paths and optional data hashes belong in an ignored private output.
Byte totals use file stat blocks, deduplicated by inode. APFS shared extents are
not observable here, so these totals are not a promise of deletion savings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def inventory(root: Path, *, hash_data: bool = False, excluded: Path | None = None) -> dict:
    root = root.resolve()
    excluded = excluded.resolve() if excluded is not None else None
    groups: dict = defaultdict(lambda: dict(files=0, logical_bytes=0, allocated_bytes=0))
    extensions: dict = defaultdict(lambda: dict(files=0, logical_bytes=0))
    databases, fingerprints, symlinks = [], {}, []
    seen: set = set()
    unique_blocks = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        symlinks.extend(str((base / name).relative_to(root))
                        for name in dirs if (base / name).is_symlink())
        dirs[:] = sorted(d for d in dirs if not (base / d).is_symlink()
                         and (excluded is None or base / d != excluded))
        for name in sorted(files):
            path = base / name
            rel = path.relative_to(root)
            if path.is_symlink():
                symlinks.append(str(rel))
                continue
            stat = path.stat()
            keys = [rel.parts[0]]
            if rel.parts[0] == "data":
                keys.append("/".join(rel.parts[:3]))
            for key in set(keys):
                group = groups[key]
                group["files"] += 1
                group["logical_bytes"] += stat.st_size
                group["allocated_bytes"] += stat.st_blocks * 512
            inode = (stat.st_dev, stat.st_ino)
            if inode not in seen:
                unique_blocks += stat.st_blocks * 512
                seen.add(inode)
            if rel.parts[0] == "data":
                ext = extensions[path.suffix or "<none>"]
                ext["files"] += 1
                ext["logical_bytes"] += stat.st_size
                record = dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns)
                if hash_data:
                    digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                    after = path.stat()
                    if (after.st_size, after.st_mtime_ns, after.st_ino) != (
                            stat.st_size, stat.st_mtime_ns, stat.st_ino):
                        raise RuntimeError("File changed during inventory")
                    record["sha256"] = digest.hexdigest()
                fingerprints[str(rel)] = record
                if path.suffix in {".duckdb", ".db", ".sqlite", ".sqlite3"}:
                    databases.append(dict(path=str(rel), **record))
    duplicate_dbs: dict = defaultdict(list)
    for db in databases:
        if "sha256" in db:
            duplicate_dbs[db["sha256"]].append(db["path"])
    return dict(observed_at=datetime.now(timezone.utc).isoformat(), root=str(root),
                hash_data=hash_data, groups=dict(sorted(groups.items())),
                data_extensions=dict(sorted(extensions.items())), databases=databases,
                duplicate_database_hashes={k: v for k, v in duplicate_dbs.items() if len(v) > 1},
                data_files=fingerprints, symlink_paths=sorted(symlinks),
                unique_file_allocated_bytes=unique_blocks,
                limitation="File blocks only; excludes directory blocks and cannot resolve APFS shared extents")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hash-data", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    private = root / "data/private/repository-governance"
    if not output.is_relative_to(private):
        parser.error("Output must be inside data/private/repository-governance")
    if output.exists():
        parser.error("Output already exists; choose a new snapshot name")
    result = inventory(root, hash_data=args.hash_data, excluded=private)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(dict(output=str(output), data=result["groups"].get("data"),
                         databases=len(result["databases"]), hash_data=args.hash_data)))


if __name__ == "__main__":
    main()
