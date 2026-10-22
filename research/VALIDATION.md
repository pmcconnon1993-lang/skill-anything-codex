# Skill Anything Codex: implementation and verification

Date: 2026-10-22. The installable Codex package is
[`skill-anything-codex/`](../skill-anything-codex/SKILL.md).

## Result

The former `skill-anything` capability now has an explicit source/name +
“skill install” route, selected topic references, portable evidence records,
local recall, and evidence checks. The core knowledge helper uses the Python
standard library. The existing SYuan03 extraction application is preserved.

The upstream study and adopted/rejected techniques are in
[`source-findings.md`](../skill-anything-codex/references/source-findings.md).
Its five bounded implementation findings are also machine-readable in
[`knowledge.json`](../skill-anything-codex/references/knowledge.json), with
selected source excerpts, hashes, locators and license notices.

Final combined repository verification: **120 tests passed** and Ruff passed.
The local dependency advisory audit reported no known vulnerabilities in audited
dependencies; the local application itself could not be matched to a registry
advisory record.

## Checks actually performed

- **13 helper tests passed:** cited recall, empty result for an
  unsupported question, refusal of changed snapshots, fabricated quotes,
  unsupported claims, duplicate JSON keys/record IDs, escaping symlinks,
  unsupported runtime labels and changed runtime artifacts; catalog link
  deduplication, explicit unknown-state retention, and full subtitle timestamp preservation.
- **Before/after tool comparison:** the old entrypoint rejects `recall`; the new
  entrypoint returns the matching Codex packaging finding and citations. Both
  produced identical extraction JSON for the same selected text from outside
  the source directory. This is an operational extension, not a measured model
  quality improvement or a native trigger benchmark.
- **Independent forward task:** a separate agent used the new skill and an
  owned synthetic HeaderGuard workflow to create a staged operational CSV skill,
  a standard-library CLI, retained source evidence and four knowledge records.
  Its 13 real success/boundary CLI cases passed from outside the source
  directory with input hashes unchanged. The coordinating assistant inspected
  the actual instructions, implementation, evidence and JSON records, and reran
  the valid, reordered-header and empty-file cases.
- **Source-contract probes:** folded-description loss, shallow Codex packaging,
  keyword/no-error generated assertions, and identical with/without-skill
  subprocess calls were reproduced. The benchmark's subprocess and grader were
  stubbed for that contract check; no paid model benchmark was run.
- **Codex checks:** current skill-creator frontmatter validation, native
  `agents/openai.yaml`, linked-resource checks and knowledge evidence validation.
  The Claude-oriented source was separately passed through isolated conversion
  staging; its evaluators/settings were excluded from the final package.

## Reproduce bounded checks

```bash
python3 -m unittest discover -s checks -v
python3 skill-anything-codex/scripts/knowledge.py check
python3 skill-anything-codex/scripts/knowledge.py recall 'Codex packaging'
python3 research/probe_upstream.py /path/to/AgentSkillOS-SkillAnything
```

The final command requires the pinned AgentSkillOS checkout and PyYAML, creates
disposable artifacts alongside it, and performs no model calls. It is a study
probe, not an installed agent evaluator. Review upstream code before executing
it against another revision. Source snapshots and probes cover only the named
paths, not all functionality.

## Boundaries and remaining uncertainty

Checked excerpts do not prove that a model's interpretation is correct; Codex
must assess whether the source supports each claim. Local lexical recall does
not replace semantic memory or guarantee automatic skill selection. A live
service may change without modifying the saved snapshot. Fresh-session skill
activation, arbitrary website coverage and model-quality improvements are not
proven by these checks. Transcription/OCR/access gaps must remain explicit.

The upstream repository's local security scan remained incomplete because its
optional AI triage service was unavailable; its existing two medium URL-handling
candidates were source-reviewed. No high finding was reported. New helper code
was separately scanned with no findings in scope; this is not a full security
certification. Dependency audit excludes the local application itself when no
matching registry advisory record is available. No credentials or host-specific
configuration belong in this publication.
