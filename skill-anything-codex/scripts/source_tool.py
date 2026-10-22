#!/usr/bin/env python3
"""Codex adapter: source extraction, offline CLI and staged export adaptation."""

from __future__ import annotations

import argparse
import importlib
import json
import shlex
import shutil
import sys
from dataclasses import asdict
from pathlib import Path


def offline_cli(arguments: list[str]) -> None:
    # Patch before importing generators, which can bind chat at import time.
    from skill_anything import llm

    llm._env_loaded = True
    llm.chat = lambda *args, **kwargs: None
    llm.generate_image = lambda *args, **kwargs: None
    llm.is_available = lambda: False
    from skill_anything.cli import app

    print(
        "Codex adapter: generation APIs disabled; generation uses extractive fallback.",
        file=sys.stderr,
    )
    app(args=arguments, prog_name="skill-anything-codex cli")


def extract(args: argparse.Namespace) -> None:
    from skill_anything.engine import Engine

    source = args.source
    if args.inline:
        if args.type not in {"auto", "text"}:
            raise ValueError("--inline requires auto or text type")
        kind = "text"
    else:
        if not source.startswith(("https://", "http://")):
            path = Path(source).expanduser().resolve(strict=True)
            source = str(path)
        kind = Engine._detect_source_type(source).value if args.type == "auto" else args.type
    kind = "web" if kind == "webpage" else kind
    parsers = {
        "text": ("text_parser", "TextParser"),
        "pdf": ("pdf_parser", "PDFParser"),
        "web": ("web_parser", "WebParser"),
        "video": ("video_parser", "VideoParser"),
        "repo": ("repo_parser", "RepoParser"),
        "skill": ("skill_parser", "SkillParser"),
    }
    if kind not in parsers:
        raise ValueError(
            f"Type {kind!r} needs an existing transcription/OCR route; supply extracted text"
        )
    module, class_name = parsers[kind]
    parser = getattr(importlib.import_module(f"skill_anything.parsers.{module}"), class_name)()
    if kind == "video" and not source.startswith(("https://", "http://")):
        path = Path(source)
        if path.suffix.lower() not in {".srt", ".vtt", ".txt"}:
            sidecar = next(
                (
                    path.with_suffix(ext)
                    for ext in (".srt", ".vtt")
                    if path.with_suffix(ext).is_file()
                ),
                None,
            )
            if sidecar is None:
                raise ValueError(
                    "Local video requires subtitles or an existing transcription route"
                )
            source = str(sidecar)
            path = sidecar
        if path.suffix.lower() in {".srt", ".vtt"}:
            from extract_source import subtitle_segments

            sections = parser._build_sections(subtitle_segments(path), source)
        else:
            sections = parser.parse_sections(source)
    else:
        sections = parser.parse_sections(source)
    if not sections or not any(
        chunk.content.strip() for section in sections for chunk in section.chunks
    ):
        raise ValueError("No readable content extracted; check source access, captions or OCR")
    data = {
        "source": "<inline>" if args.inline else source,
        "source_type": kind,
        "sections": [asdict(section) for section in sections],
        "coverage": getattr(parser, "stats", {}),
        "generation": "none; source extraction only",
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        json.dumps({"output": str(output), "sections": len(sections), "coverage": data["coverage"]})
    )


def adapt_export(args: argparse.Namespace) -> None:
    import yaml

    given = Path(args.source).expanduser().absolute()
    if given.is_symlink():
        raise ValueError("Source package must not be a symlink")
    source = given.resolve(strict=True)
    destination = Path(args.output).expanduser().resolve()
    if (
        destination.exists()
        or destination == source
        or source in destination.parents
        or destination in source.parents
    ):
        raise ValueError("Choose a fresh destination outside the source package")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Resolve source-package symlinks explicitly before adaptation")
    original = (source / "SKILL.md").read_text(encoding="utf-8")
    if not original.startswith("---\n"):
        raise ValueError("Missing SKILL.md frontmatter")
    header, delimiter, body = original[4:].partition("\n---\n")
    if not delimiter:
        raise ValueError("Missing frontmatter closing delimiter")
    frontmatter = yaml.safe_load(header)
    if not isinstance(frontmatter, dict) or not all(
        frontmatter.get(key) for key in ("name", "description")
    ):
        raise ValueError("Missing skill name or description")
    if "version" in frontmatter:
        frontmatter.setdefault("metadata", {})["version"] = str(frontmatter.pop("version"))
    body = body.replace(
        "python ${CLAUDE_SKILL_DIR}/scripts/quiz.py",
        "python " + shlex.quote(str(destination / "scripts/quiz.py")),
    )
    if "${CLAUDE_SKILL_DIR}" in body:
        raise ValueError("Unrecognized Claude-specific path; adapt it manually")
    rewritten = (
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n" + body
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    (destination / "SKILL.md").write_text(rewritten, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(destination),
                "status": "format adapted; semantic and behavior review required",
            }
        )
    )


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"check", "recall", "catalog"}:
        from knowledge import main as knowledge_main

        knowledge_main(sys.argv[1:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        offline_cli(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("extract", help="Extract source sections without an LLM")
    read.add_argument("source")
    read.add_argument(
        "--type", choices=["auto", "text", "pdf", "web", "video", "repo", "skill"], default="auto"
    )
    read.add_argument("--inline", action="store_true")
    read.add_argument("--output", required=True)
    read.set_defaults(run=extract)
    adapt = commands.add_parser(
        "adapt-export", help="Copy and adapt an upstream Skill-Anything export"
    )
    adapt.add_argument("source")
    adapt.add_argument("--output", required=True)
    adapt.set_defaults(run=adapt_export)
    commands.add_parser("cli", help="Run upstream CLI without generation APIs")
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
