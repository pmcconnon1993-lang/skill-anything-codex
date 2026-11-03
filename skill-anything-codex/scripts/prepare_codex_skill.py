#!/usr/bin/env python3
"""Normalize an upstream Skill-Anything export for Codex, retaining a backup."""

import argparse
import re
import shutil
from pathlib import Path

import yaml


def skill_file(skill_directory: Path) -> Path:
    given = skill_directory.expanduser().absolute()
    root = given.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Skill directory is not a directory: {given}")
    path = root / "SKILL.md"
    if path.is_symlink():
        raise ValueError(f"SKILL.md must not be a symlink: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"SKILL.md escapes the skill directory or is not a file: {path}")
    return resolved


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("skill_directory", type=Path)
    args = ap.parse_args()
    try:
        path = skill_file(args.skill_directory)
        original = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", original, re.S)
        if not match:
            raise ValueError("Missing YAML frontmatter")
        front = yaml.safe_load(match.group(1))
        if not isinstance(front, dict) or not front.get("name") or not front.get("description"):
            raise ValueError("Frontmatter must contain name and description")
        allowed = {"name", "description", "license", "allowed-tools", "metadata", "version"}
        unknown = set(front) - allowed
        if unknown:
            raise ValueError(f"Review unsupported fields manually: {sorted(unknown)}")
        if "version" in front:
            metadata = front.setdefault("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be a mapping")
            version = str(front["version"])
            if "version" in metadata and str(metadata["version"]) != version:
                raise ValueError("Conflicting versions; review manually")
            metadata["version"] = version
            del front["version"]
        body = original[match.end() :].replace(
            "python ${CLAUDE_SKILL_DIR}/scripts/quiz.py",
            "# Run from this skill's directory with Python and PyYAML available:\npython3 scripts/quiz.py",
        )
        normalized = (
            "---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + "---\n" + body
        )
        if normalized == original:
            print(f"Already normalized: {path}")
            return
        backup = path.with_name("SKILL.md.upstream-backup")
        with backup.open("xb") as handle:
            handle.write(original.encode("utf-8"))
        staged = path.with_name("SKILL.md.codex-pending")
        with staged.open("x", encoding="utf-8") as handle:
            handle.write(normalized)
        shutil.copymode(path, staged)
        staged.replace(path)
        print(f"Normalized {path}; preserved {backup.name}. Run the Codex validator next.")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        ap.exit(1, f"Normalization failed: {exc}\n")


if __name__ == "__main__":
    main()
