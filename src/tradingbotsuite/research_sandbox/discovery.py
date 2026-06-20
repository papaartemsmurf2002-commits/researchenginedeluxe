from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path


def _path_sort_key(path: Path) -> tuple[str, str]:
    name = path.name
    return name.lower(), name


def _walk_files(root: Path, *, accepted_names: frozenset[str] | None = None) -> Iterator[Path]:
    stack = [root]
    while stack:
        directory = stack.pop()
        entries = sorted(directory.iterdir(), key=_path_sort_key)
        child_dirs: list[Path] = []
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                child_dirs.append(entry)
                continue
            if entry.is_file() and (accepted_names is None or entry.name in accepted_names):
                yield entry
        stack.extend(reversed(child_dirs))


def bounded_discover_files(
    roots: Iterable[Path],
    *,
    max_files: int,
    missing_root_message: str,
    accepted_names: Iterable[str] | None = None,
) -> tuple[list[Path], bool]:
    if max_files <= 0:
        raise ValueError("max_files must be positive")

    accepted = frozenset(accepted_names) if accepted_names is not None else None
    files: list[Path] = []
    truncated = False
    for root in roots:
        if not root.exists():
            raise FileNotFoundError(f"{missing_root_message}: {root}")
        candidates: Iterable[Path]
        if root.is_file():
            candidates = [root] if accepted is None or root.name in accepted else []
        else:
            candidates = _walk_files(root, accepted_names=accepted)
        for path in candidates:
            if len(files) >= max_files:
                truncated = True
                break
            files.append(path)
        if truncated:
            break
    return files, truncated
