"""Observable checks for the Codex helpers; no LLM backend or network required."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1] / "skill-anything"


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def extract(self, source):
        result = subprocess.run(
            [sys.executable, str(SKILL / "scripts/extract_source.py"), str(source)],
            capture_output=True, text=True, check=True, timeout=30,
        )
        return json.loads(result.stdout)

    def test_text_includes_last_section(self):
        source = self.work / "notes.md"
        source.write_text("# First\n\nStage the copy.\n\n# Last\n\nCompare checksums before replacement.\n")
        parsed = self.extract(source)
        self.assertIn("Compare checksums", json.dumps(parsed))
        self.assertEqual(parsed["source_type"], "text")

    def test_srt_preserves_hours_minutes_seconds(self):
        source = self.work / "talk.srt"
        source.write_text("1\n00:00:01,000 --> 00:00:04,000\nStage the copy.\n\n2\n01:06:01,000 --> 01:06:04,000\nVerify integrity.\n")
        sections = self.extract(source)["sections"]
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[1]["chunks"][0]["source_time"], "01:06:01")

    def test_vtt_preserves_minutes_seconds(self):
        source = self.work / "talk.vtt"
        source.write_text("WEBVTT\n\n00:01.000 --> 00:04.000\nStage the copy.\n\n06:01.000 --> 06:04.000\nVerify integrity.\n")
        sections = self.extract(source)["sections"]
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[1]["chunks"][0]["source_time"], "06:01")

    def test_normalization_keeps_backup_and_is_idempotent(self):
        path = self.work / "SKILL.md"
        original = "---\nname: demo\ndescription: Verify a copied file.\nversion: 1.0.0\n---\n# Demo\n\n```sh\npython ${CLAUDE_SKILL_DIR}/scripts/quiz.py\n```\n"
        path.write_text(original)
        command = [sys.executable, str(SKILL / "scripts/prepare_codex_skill.py"), str(self.work)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        normalized = path.read_text()
        front = yaml.safe_load(normalized.split("---", 2)[1])
        self.assertNotIn("version", front)
        self.assertEqual(front["metadata"]["version"], "1.0.0")
        self.assertNotIn("CLAUDE_SKILL_DIR", normalized)
        self.assertEqual((self.work / "SKILL.md.upstream-backup").read_text(), original)
        subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertEqual(path.read_text(), normalized)

    def test_full_subtitle_parser_is_available_without_backend(self):
        spec = importlib.util.spec_from_file_location("extract_source", SKILL / "scripts/extract_source.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = self.work / "short.srt"
        source.write_text("1\n00:06:01,000 --> 00:06:04,000\nCheck the hash.\n")
        self.assertEqual(module.subtitle_segments(source), [("00:06:01", "Check the hash.")])


if __name__ == "__main__":
    unittest.main()
