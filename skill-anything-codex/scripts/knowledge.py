#!/usr/bin/env python3
"""Check source-backed facts and retrieve selected local skill knowledge."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"Invalid JSON number: {value}")
        ),
    )


def local_file(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Evidence paths must be nonempty package-relative paths")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Evidence escapes package or is not a file: {relative}")
    return path


def checked_knowledge(skill):
    root = Path(skill).expanduser().resolve(strict=True)
    data = read_json(root / "references/knowledge.json")
    if not isinstance(data, dict) or data.get("schema") != "skill-anything-knowledge/v1":
        raise ValueError("Unknown knowledge schema")
    if not isinstance(data.get("sources"), list) or not isinstance(data.get("facts"), list):
        raise ValueError("sources and facts must be arrays")
    sources, snapshots = {}, {}
    for source in data["sources"]:
        if not isinstance(source, dict) or not all(
            isinstance(source.get(key), str) and source[key].strip()
            for key in ("id", "uri", "revision", "snapshot", "sha256")
        ):
            raise ValueError("Each source needs id, uri, revision, snapshot and sha256")
        sid = source["id"]
        if sid in sources:
            raise ValueError(f"Duplicate source id: {sid}")
        path = local_file(root, source["snapshot"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(
                f"Stale or changed snapshot: {sid}; refresh source and review affected claims"
            )
        sources[sid], snapshots[sid] = source, path.read_text(encoding="utf-8")
    seen = set()
    for fact in data["facts"]:
        if not isinstance(fact, dict) or not all(
            isinstance(fact.get(key), str) and fact[key].strip()
            for key in ("id", "topic", "claim", "status")
        ):
            raise ValueError("Each fact needs id, topic, claim and status")
        if fact["id"] in seen:
            raise ValueError(f"Duplicate fact id: {fact['id']}")
        seen.add(fact["id"])
        if fact["status"] not in {"documented", "static", "runtime-verified", "unknown"}:
            raise ValueError(f"Invalid evidence status: {fact['id']}")
        for key in ("tags", "limitations"):
            if not isinstance(fact.get(key, []), list) or not all(
                isinstance(item, str) for item in fact.get(key, [])
            ):
                raise ValueError(f"{key} must contain strings: {fact['id']}")
        evidence = fact.get("evidence", [])
        if not isinstance(evidence, list) or (fact["status"] != "unknown" and not evidence):
            raise ValueError(f"Asserted fact needs evidence: {fact['id']}")
        if fact["status"] == "unknown" and not fact.get("limitations"):
            raise ValueError(f"Unknown fact needs limitations: {fact['id']}")
        for citation in evidence:
            if not isinstance(citation, dict):
                raise ValueError("Evidence entry must be an object")
            sid, quote = citation.get("source_id"), citation.get("quote")
            if (
                sid not in sources
                or not isinstance(quote, str)
                or not quote.strip()
                or quote not in snapshots[sid]
            ):
                raise ValueError(f"Unsupported source quote: {fact['id']}")
            if not isinstance(citation.get("locator"), str) or not citation["locator"].strip():
                raise ValueError(f"Missing evidence locator: {fact['id']}")
        checks = fact.get("checks", [])
        if not isinstance(checks, list):
            raise ValueError("checks must be an array")
        if fact["status"] == "runtime-verified":
            if not checks:
                raise ValueError(f"Runtime claim needs checks: {fact['id']}")
            for check in checks:
                if (
                    not isinstance(check, dict)
                    or check.get("result") != "pass"
                    or not all(
                        isinstance(check.get(key), str) and check[key].strip()
                        for key in ("method", "observed", "artifact")
                    )
                ):
                    raise ValueError(f"Runtime check incomplete or failed: {fact['id']}")
                artifact = local_file(root, check["artifact"])
                if hashlib.sha256(artifact.read_bytes()).hexdigest() != check.get("sha256"):
                    raise ValueError(f"Runtime evidence changed or lacks hash: {fact['id']}")
    return root, data, sources


def words(text):
    return set(re.findall(r"\w+", text.casefold()))


def recall(skill, query, limit):
    root, data, sources = checked_knowledge(skill)
    terms = words(query)
    matches = []
    for fact in data["facts"]:
        searchable = " ".join([fact["topic"], fact["claim"], *fact.get("tags", [])])
        score = len(terms & words(searchable))
        if score:
            citations = [
                {
                    **citation,
                    "uri": sources[citation["source_id"]]["uri"],
                    "revision": sources[citation["source_id"]]["revision"],
                    "snapshot": str(root / sources[citation["source_id"]]["snapshot"]),
                }
                for citation in fact.get("evidence", [])
            ]
            matches.append({**fact, "score": score, "evidence": citations})
    matches.sort(key=lambda fact: (-fact["score"], fact["id"]))
    return {
        "skill": str(root),
        "method": "local lexical overlap; evidence files checked, semantic support requires review",
        "query": query,
        "matches": matches[:limit],
    }


def catalog(roots, query, limit):
    terms, seen, matches, errors = words(query), set(), [], []
    for directory in roots:
        parent = Path(directory).expanduser()
        if not parent.exists():
            continue
        for entry in sorted(parent.iterdir()):
            try:
                root = entry.resolve(strict=True)
                if root in seen or not (root / "SKILL.md").is_file():
                    continue
                seen.add(root)
                text = (root / "SKILL.md").read_text(encoding="utf-8")
                header = text[4:].partition("\n---")[0] if text.startswith("---\n") else ""
                score = len(terms & words(root.name + " " + header))
                if score:
                    matches.append(
                        {
                            "name": root.name,
                            "entrypoint": str(root / "SKILL.md"),
                            "score": score,
                            "has_knowledge": (root / "references/knowledge.json").is_file(),
                        }
                    )
            except (OSError, UnicodeError) as exc:
                errors.append({"path": str(entry), "error": str(exc)})
    matches.sort(key=lambda item: (-item["score"], item["name"]))
    return {
        "method": "skill metadata lexical search; read entrypoint before use",
        "matches": matches[:limit],
        "errors": errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    default_skill = str(Path(__file__).resolve().parents[1])
    check = commands.add_parser("check")
    check.add_argument("--skill", default=default_skill)
    find = commands.add_parser("recall")
    find.add_argument("query")
    find.add_argument("--skill", default=default_skill)
    find.add_argument("--limit", type=int, default=5)
    findall = commands.add_parser("catalog")
    findall.add_argument("query")
    findall.add_argument("--root", action="append")
    findall.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if args.command == "check":
        root, data, _ = checked_knowledge(args.skill)
        result = {
            "skill": str(root),
            "status": "evidence structure checked",
            "sources": len(data["sources"]),
            "facts": len(data["facts"]),
            "limit": "Does not prove semantic entailment, live freshness or that recorded tests ran",
        }
    elif args.limit < 1 or args.limit > 100:
        raise ValueError("limit must be between 1 and 100")
    elif args.command == "recall":
        result = recall(args.skill, args.query, args.limit)
    else:
        roots = args.root or [
            str(Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"),
            str(Path.home() / ".agents/skills"),
        ]
        result = catalog(roots, args.query, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(2)
