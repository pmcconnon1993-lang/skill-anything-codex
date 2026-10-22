#!/usr/bin/env python3
"""Extract source sections through Skill-Anything without generative API calls."""

import argparse
import json
import re
import sys
from dataclasses import asdict
from importlib import import_module
from pathlib import Path

PARSERS = {
    "text": ("text_parser", "TextParser"),
    "pdf": ("pdf_parser", "PDFParser"),
    "webpage": ("web_parser", "WebParser"),
    "video": ("video_parser", "VideoParser"),
    "repo": ("repo_parser", "RepoParser"),
    "skill": ("skill_parser", "SkillParser"),
}


def subtitle_segments(path):
    """Preserve full SRT/VTT cue times; upstream v0.4.1 slices hours/minutes."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    segments = []
    index = 0
    while index < len(lines):
        cue = re.match(r"\s*((?:\d{2,}:)?\d{2}:\d{2})[,.]\d+\s+-->", lines[index])
        index += 1
        if not cue:
            continue
        content = []
        while index < len(lines) and lines[index].strip():
            content.append(re.sub(r"<[^>]+>", "", lines[index]).strip())
            index += 1
        text = " ".join(content).strip()
        if text:
            segments.append((cue.group(1), text))
    return segments


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("--type", choices=["auto", *PARSERS], default="auto")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        kind = args.type
        if kind == "auto":
            from skill_anything.engine import Engine
            kind = Engine._detect_source_type(args.source).value
        if kind not in PARSERS:
            raise ValueError("Raw audio requires a transcript; use an existing transcription workflow.")
        if kind == "video" and not args.source.startswith(("https://", "http://")):
            path = Path(args.source)
            if path.suffix.lower() not in {".srt", ".vtt", ".txt"}:
                sidecar = next((path.with_suffix(ext) for ext in (".srt", ".vtt")
                                if path.with_suffix(ext).is_file()), None)
                if sidecar is None:
                    raise ValueError("Local video requires .srt/.vtt subtitles or prior transcription.")
                args.source = str(sidecar)
        module, cls = PARSERS[kind]
        parser = getattr(import_module(f"skill_anything.parsers.{module}"), cls)()
        if kind == "video" and not args.source.startswith(("https://", "http://")) and Path(args.source).suffix.lower() in {".srt", ".vtt"}:
            sections = parser._build_sections(subtitle_segments(Path(args.source)), args.source)
        else:
            sections = parser.parse_sections(args.source)
        if not sections or not any(s.content.strip() for s in sections):
            raise ValueError("No readable content extracted; check source or use OCR/transcription.")
        data = {
            "source": args.source,
            "source_type": kind,
            "sections": [asdict(section) for section in sections],
            "parser_stats": getattr(parser, "stats", {}),
        }
        result = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(result)
            print(f"Extracted {len(sections)} sections to {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(result)
    except (OSError, ValueError, ImportError, RuntimeError) as exc:
        ap.exit(1, f"Extraction failed: {exc}\n")


if __name__ == "__main__":
    main()
