# Checked topic knowledge

Knowledge records are selected evidence for later retrieval, not an alternative
authority or permission source. Use one record for a bounded claim that changes
a decision. Link richer explanation in a topic reference. Do not retain whole
transcripts, credentials, unsupported marketing claims or generic filler.

`references/knowledge.json` uses schema `skill-anything-knowledge/v1`:

```json
{
  "schema": "skill-anything-knowledge/v1",
  "sources": [{
    "id": "manual-v1",
    "uri": "https://example.org/manual",
    "revision": "document date, commit or version",
    "snapshot": "references/evidence/manual.txt",
    "sha256": "SHA-256 of the actual saved snapshot"
  }],
  "facts": [{
    "id": "ordered-header",
    "topic": "CSV header comparison",
    "claim": "Header order matters for this selected workflow.",
    "status": "documented",
    "tags": ["csv", "headers"],
    "evidence": [{"source_id": "manual-v1", "locator": "Header section", "quote": "Compare column names in order."}],
    "limitations": ["Applies to the supplied workflow only."],
    "checks": []
  }]
}
```

The example is an unrun shape, not a verified finding. The actual bundled
knowledge file contains populated source hashes and inspected findings.
Paths must stay inside the skill package. Keep the original URI and its source
identity, not a machine-specific home path. Preserve license/attribution for
copied source excerpts. A snapshot hash pins only the saved excerpt, not an
entire website. Record snapshot coverage and original locators in the reference.

Statuses: `documented` (source asserts it), `static` (implementation inspected),
`runtime-verified` (a bounded operation actually checked), and `unknown` (a gap).
All asserted facts need supporting evidence. Runtime records additionally need
passing checks with `method`, `observed`, an `artifact` path to retained evidence,
and its `sha256`. Unknown records need limitations and are returned explicitly as unknown.
The checker cannot establish semantic entailment or prove a test ran: inspect
the underlying source and artifact independently before accepting those labels.

```bash
python3 scripts/knowledge.py check --skill /path/to/skill
python3 scripts/knowledge.py recall 'header order' --skill /path/to/skill
python3 scripts/knowledge.py catalog 'csv headers' --root /path/to/skills
```

Recall is local lexical ranking over the selected topic records. It returns
citations and limitations, refuses invalid/stale evidence, and returns an empty
match list when nothing matches. It is not semantic memory or a guarantee of
relevance. Catalog searches installed skill entrypoint metadata and deduplicates
resolved discovery links; read a candidate before using it. Neither command
executes stored commands, fetches source URLs or writes to skills.

Refresh changing facts against current official source/live state when needed.
Update the source identity, snapshots, hashes and affected claims together;
keep the previous package outside the active discovery roots for rollback.
