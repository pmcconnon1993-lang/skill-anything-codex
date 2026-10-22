"""Behavior checks for evidence validation and local retrieval; no network/model."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "knowledge", ROOT / "skill-anything-codex/scripts/knowledge.py"
)
knowledge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge)


class KnowledgeChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "skill"
        (self.root / "references").mkdir(parents=True)
        self.text = "Header names are case-sensitive and compared in order.\n"
        (self.root / "references/source.txt").write_text(self.text)
        self.data = {
            "schema": "skill-anything-knowledge/v1",
            "sources": [
                {
                    "id": "manual",
                    "uri": "https://example.invalid/manual",
                    "revision": "fixture-1",
                    "snapshot": "references/source.txt",
                    "sha256": hashlib.sha256(self.text.encode()).hexdigest(),
                }
            ],
            "facts": [
                {
                    "id": "headers",
                    "topic": "CSV header order",
                    "claim": "The selected workflow compares header names in order.",
                    "status": "documented",
                    "tags": ["csv"],
                    "limitations": ["Owned fixture only."],
                    "evidence": [
                        {"source_id": "manual", "locator": "Headers", "quote": "compared in order"}
                    ],
                    "checks": [],
                }
            ],
        }
        self.save()

    def save(self):
        (self.root / "references/knowledge.json").write_text(json.dumps(self.data))

    def test_recall_cites_selected_source(self):
        result = knowledge.recall(self.root, "header order", 5)
        self.assertEqual(result["matches"][0]["id"], "headers")
        self.assertEqual(result["matches"][0]["evidence"][0]["revision"], "fixture-1")

    def test_unknown_query_has_no_invented_answer(self):
        self.assertEqual(knowledge.recall(self.root, "photosynthesis", 5)["matches"], [])

    def test_changed_source_refuses_recall(self):
        (self.root / "references/source.txt").write_text("Different version")
        with self.assertRaisesRegex(ValueError, "Stale"):
            knowledge.recall(self.root, "header", 5)

    def test_invented_quote_rejected(self):
        self.data["facts"][0]["evidence"][0]["quote"] = "Case-insensitive comparison"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unsupported source quote"):
            knowledge.checked_knowledge(self.root)

    def test_unattributed_claim_rejected(self):
        self.data["facts"][0]["evidence"] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "needs evidence"):
            knowledge.checked_knowledge(self.root)

    def test_duplicate_keys_rejected(self):
        (self.root / "references/knowledge.json").write_text('{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            knowledge.checked_knowledge(self.root)

    def test_duplicate_fact_rejected(self):
        self.data["facts"].append(copy.deepcopy(self.data["facts"][0]))
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate fact"):
            knowledge.checked_knowledge(self.root)

    def test_evidence_cannot_escape_package(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text(self.text)
        (self.root / "references/escape.txt").symlink_to(outside)
        self.data["sources"][0]["snapshot"] = "references/escape.txt"
        self.save()
        with self.assertRaisesRegex(ValueError, "escapes package"):
            knowledge.checked_knowledge(self.root)

    def test_runtime_claim_requires_observed_checks(self):
        self.data["facts"][0]["status"] = "runtime-verified"
        self.save()
        with self.assertRaisesRegex(ValueError, "needs checks"):
            knowledge.checked_knowledge(self.root)

    def test_runtime_artifact_hash_checked(self):
        artifact = self.root / "references/check.json"
        artifact.write_text('{"result":"pass"}')
        self.data["facts"][0]["status"] = "runtime-verified"
        self.data["facts"][0]["checks"] = [
            {
                "result": "pass",
                "method": "Owned fixture probe",
                "observed": "Expected response observed",
                "artifact": "references/check.json",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        ]
        self.save()
        knowledge.checked_knowledge(self.root)
        artifact.write_text('{"result":"fail"}')
        with self.assertRaisesRegex(ValueError, "Runtime evidence changed"):
            knowledge.checked_knowledge(self.root)

    def test_catalog_deduplicates_discovery_links(self):
        (self.root / "SKILL.md").write_text(
            "---\nname: csv-check\ndescription: Check CSV header order\n---\n"
        )
        links = Path(self.temp.name) / "links"
        links.mkdir()
        (links / "csv-check").symlink_to(self.root)
        result = knowledge.catalog([self.root.parent, links], "header", 5)
        self.assertEqual(len(result["matches"]), 1)

    def test_unknown_record_stays_labelled(self):
        fact = self.data["facts"][0]
        fact.update(status="unknown", evidence=[], claim="Remote header behavior remains unknown.")
        self.save()
        self.assertEqual(
            knowledge.recall(self.root, "header", 5)["matches"][0]["status"], "unknown"
        )

    def test_final_adapter_preserves_subtitle_time(self):
        subtitle = self.root / "talk.srt"
        subtitle.write_text("1\n01:06:01,000 --> 01:06:05,000\nVerify the complete timestamp.\n")
        output = self.root / "extracted.json"
        result = subprocess.run([sys.executable, str(ROOT / "skill-anything-codex/scripts/source_tool.py"),
                                 "extract", str(subtitle), "--output", str(output)],
                                cwd=self.temp.name, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        extracted = json.loads(output.read_text())
        self.assertEqual(extracted["sections"][0]["chunks"][0]["source_time"], "01:06:01")


if __name__ == "__main__":
    unittest.main()
