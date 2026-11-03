"""Safe local source-file access for repository and skill parsers."""

from __future__ import annotations

from pathlib import Path


def resolve_source_root(root: Path, *, label: str) -> Path:
    """Resolve and validate the source root selected by the caller."""
    given = root.expanduser().absolute()
    resolved = given.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"{label} is not a directory: {given}")
    return resolved


def read_text_within_root(
    root: Path,
    path: Path,
    *,
    encoding: str = "utf-8",
    optional: bool = False,
) -> str | None:
    """Read a regular file only when its entire path is symlink-free and contained."""
    root = root.resolve(strict=True)
    candidate = path.expanduser().absolute()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Source file escapes selected root: {candidate}") from exc

    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Source path contains a symlink: {relative.as_posix()}")

    if not candidate.exists():
        if optional:
            return None
        raise FileNotFoundError(candidate)

    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError(f"Source file escapes selected root: {relative.as_posix()}")
    if not resolved.is_file():
        raise ValueError(f"Source path is not a regular file: {relative.as_posix()}")
    return resolved.read_text(encoding=encoding)
