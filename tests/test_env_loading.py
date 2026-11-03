"""Security regression tests for dotenv loading boundaries."""

from __future__ import annotations

import os

import pytest

import skill_anything.llm as llm
from skill_anything.parsers.audio_parser import AudioParser


def _clear_llm_routing(monkeypatch) -> None:
    monkeypatch.setattr(llm, "_env_loaded", False)
    for name in (
        "SKILL_ANYTHING_API_KEY",
        "OPENAI_API_KEY",
        "SKILL_ANYTHING_API_BASE",
        "OPENAI_API_BASE",
        "SKILL_ANYTHING_PROXY",
        "SKILL_ANYTHING_ENV_FILE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_llm_ignores_dotenv_from_untrusted_working_and_package_directories(
    monkeypatch, tmp_path
) -> None:
    """Removing the trust-boundary guard must expose the hostile endpoint again."""
    untrusted_cwd = tmp_path / "working-copy"
    untrusted_cwd.mkdir()
    (untrusted_cwd / ".env").write_text(
        "SKILL_ANYTHING_API_BASE=https://attacker.invalid\n",
        encoding="utf-8",
    )

    untrusted_package = tmp_path / "package-root"
    (untrusted_package / "skill_anything").mkdir(parents=True)
    (untrusted_package / ".env").write_text(
        "SKILL_ANYTHING_PROXY=https://proxy.attacker.invalid\n",
        encoding="utf-8",
    )

    _clear_llm_routing(monkeypatch)
    monkeypatch.chdir(untrusted_cwd)
    monkeypatch.setattr(llm, "__file__", str(untrusted_package / "skill_anything" / "llm.py"))

    llm._ensure_env()

    assert "SKILL_ANYTHING_API_BASE" not in os.environ
    assert "SKILL_ANYTHING_PROXY" not in os.environ


def test_audio_api_fallback_ignores_working_directory_dotenv(monkeypatch, tmp_path) -> None:
    """Audio fallback must not reintroduce the working-directory dotenv path."""
    untrusted_cwd = tmp_path / "working-copy"
    untrusted_cwd.mkdir()
    (untrusted_cwd / ".env").write_text(
        "SKILL_ANYTHING_API_BASE=https://attacker.invalid\n",
        encoding="utf-8",
    )

    _clear_llm_routing(monkeypatch)
    monkeypatch.chdir(untrusted_cwd)

    assert AudioParser._try_openai_whisper_api(str(tmp_path / "missing.wav")) is None
    assert "SKILL_ANYTHING_API_BASE" not in os.environ


def test_llm_loads_only_an_explicit_absolute_env_file(monkeypatch, tmp_path) -> None:
    """Operators retain dotenv convenience through an explicit trusted path."""
    selected_env = tmp_path / "selected.env"
    selected_env.write_text("SKILL_ANYTHING_MODEL=trusted-model\n", encoding="utf-8")

    monkeypatch.setattr(llm, "_env_loaded", False)
    monkeypatch.delenv("SKILL_ANYTHING_MODEL", raising=False)
    monkeypatch.setenv("SKILL_ANYTHING_ENV_FILE", str(selected_env))

    llm._ensure_env()

    assert os.environ["SKILL_ANYTHING_MODEL"] == "trusted-model"


def test_llm_rejects_relative_explicit_env_file(monkeypatch) -> None:
    """An explicit config path must not silently regain working-directory trust."""
    monkeypatch.setattr(llm, "_env_loaded", False)
    monkeypatch.setenv("SKILL_ANYTHING_ENV_FILE", ".env")

    with pytest.raises(ValueError, match="absolute path"):
        llm._ensure_env()
