"""Small immutable publication wrapper around the existing no-clobber writer."""
from pathlib import Path

from astock.data.raw_writer import atomic_new_file
from astock.research.core import require


def publish_bytes(path: Path, body: bytes) -> None:
    require(not any(p.is_symlink() for p in (path, *path.parents)), "PUBLICATION_SYMLINK")
    if path.exists():
        require(path.is_file() and path.read_bytes() == body, "IMMUTABLE_OBJECT_CHANGED")
        return

    def write(temporary: Path) -> None:
        temporary.write_bytes(body)
        require(temporary.read_bytes() == body, "PUBLICATION_WRITE_CHANGED")

    try:
        atomic_new_file(path, write)
    except FileExistsError:
        # A concurrent writer can win only with the same complete bytes.
        require(not path.is_symlink() and path.read_bytes() == body, "IMMUTABLE_OBJECT_CHANGED")
