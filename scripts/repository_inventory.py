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



def inventory_many(roots: list[Path]) -> dict:
    """Count explicit project roots, aliases/nested roots once and global hardlinks once.

    No credential/file contents or database connections are needed. Missing roots,
    permission errors and symlinks remain visible, never reported as zero usage.
    """
    requested = sorted({p.resolve() for p in roots}, key=lambda p: (len(p.parts), str(p)))
    selected: list[Path] = []
    for path in requested:
        if not path.is_dir():
            raise ValueError("Capacity root missing or not a directory")
        if not any(path.is_relative_to(parent) for parent in selected):
            selected.append(path)
    seen: set = set()
    result, errors = [], []
    unique_allocated = 0
    for root in selected:
        summary = dict(root=str(root), files=0, logical_bytes=0, allocated_bytes=0,
                       databases=0, symlinks=0, groups={})
        def failure(error):
            errors.append(dict(root=str(root), error=type(error).__name__))
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=failure):
            base = Path(directory)
            summary["symlinks"] += sum((base / d).is_symlink() for d in dirs)
            dirs[:] = [d for d in dirs if not (base / d).is_symlink()]
            for name in files:
                path = base / name
                if path.is_symlink():
                    summary["symlinks"] += 1
                    continue
                try:
                    st = path.stat()
                except OSError as error:
                    failure(error)
                    continue
                if not path.is_file():
                    continue
                summary["files"] += 1
                summary["logical_bytes"] += st.st_size
                summary["allocated_bytes"] += st.st_blocks * 512
                summary["databases"] += int(path.suffix in {".duckdb", ".db", ".sqlite", ".sqlite3"})
                rel = path.relative_to(root)
                group = "/".join(rel.parts[:2]) if len(rel.parts) > 2 else rel.parts[0]
                counts = summary["groups"].setdefault(group, dict(files=0, logical_bytes=0, allocated_bytes=0))
                for key, value in (("files", 1), ("logical_bytes", st.st_size), ("allocated_bytes", st.st_blocks * 512)):
                    counts[key] += value
                inode = (st.st_dev, st.st_ino)
                if inode not in seen:
                    unique_allocated += st.st_blocks * 512
                    seen.add(inode)
        result.append(summary)
    return dict(roots=result, logical_bytes=sum(r["logical_bytes"] for r in result),
                unique_file_allocated_bytes=unique_allocated, complete=not errors, errors=errors,
                requested_roots=len(requested), counted_roots=len(selected),
                target_bytes=50_000_000_000, ceiling_bytes=100_000_000_000,
                limitation="Explicit verified project roots only; file blocks exclude directory blocks/APFS clone sharing; symlinks not followed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hash-data", action="store_true")
    parser.add_argument("--additional-root", type=Path, action="append", default=[],
                        help="Explicit historical project workspace; read-only capacity accounting")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    private = root / "data/private/repository-governance"
    if not output.is_relative_to(private):
        parser.error("Output must be inside data/private/repository-governance")
    if output.exists():
        parser.error("Output already exists; choose a new snapshot name")
    result = inventory(root, hash_data=args.hash_data, excluded=private)
    if args.additional_root:
        result["project_capacity"] = inventory_many([root, *args.additional_root])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(dict(output=str(output), data=result["groups"].get("data"),
                         databases=len(result["databases"]), hash_data=args.hash_data)))


if __name__ == "__main__":
    main()
