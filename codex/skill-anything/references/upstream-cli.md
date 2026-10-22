# Upstream CLI

Source: https://github.com/SYuan03/Skill-Anything
Version: 0.4.1; revision: 3cdc1c1f11dc8e0fc8d816b99d7ca0728b0ab098.
The local Codex wrapper and helpers are additions; upstream does not ship this SKILL.md.

Use `~/.local/bin/skill-anything` instead of the README's `sa`, which conflicts with `/usr/sbin/sa`. The isolated environment is `~/.local/share/skill-anything/venv`.

```sh
skill-anything --help
skill-anything version
skill-anything text /absolute/notes.md --format skill --output /absolute/output
skill-anything pdf /absolute/book.pdf --format all --output /absolute/output
skill-anything web https://example.com/guide --format study --output /absolute/output
skill-anything repo /absolute/repository --format skill --output /absolute/output
skill-anything video /absolute/transcript.srt --format skill --output /absolute/output
skill-anything export /absolute/pack.yaml --format skill --output /absolute/output
skill-anything import-skill /absolute/skill-directory --format study --output /absolute/output
skill-anything lint /absolute/upstream-skill-directory
skill-anything audit /absolute/pack.yaml --strict
```

The exported directory is `<output>/<slugified-title>/`. `--format all` also creates study, web, and Anki outputs. CLI study/skill/all exports may attempt an image API request when credentials are configured.

## Backend and input limits

Upstream reads `SKILL_ANYTHING_API_KEY` (or `OPENAI_API_KEY`), `SKILL_ANYTHING_API_BASE`, and `SKILL_ANYTHING_MODEL`; FAST/SMART variants select map/reduce models. It also loads `.env` from the working directory. Do not print credentials or treat their presence as inference readiness. No API key/provider configuration was installed. Use Codex-native drafting without a suitable backend. Do not silently adopt upstream's default model or change the user's chosen local model. Check generation diagnostics for fallback/failures.

The optional runtime setup installs PDF text, webpage, text/Markdown, repository, and YouTube/subtitle dependencies; verify their presence on the current machine. Live access may fail due to permissions, unavailable transcripts, or network restrictions. Whisper dependencies/models were not installed. For raw audio/video use an existing authorized transcription workflow or supplied transcript. EPUB/DOCX/scans/images need an appropriate extraction tool first.

## Codex compatibility

Upstream exports unsupported top-level `version` and `${CLAUDE_SKILL_DIR}`. The local preparation helper repairs these packaging issues and retains a backup; semantic adaptation is still needed. Upstream lint expects version: run it before normalization, then use Codex quick_validate.py afterward.

Keep the upstream checkout unchanged. Inspect local source for implementation details; do not upgrade the pinned installation merely to generate a new skill.

Upstream v0.4.1 slices SRT/VTT cue timestamps incorrectly. The local extraction helper preserves full cue times before using upstream section bucketing. Use this helper for subtitle sources when accurate time locators matter; the unmodified CLI still has that upstream limitation.

## Optional runtime setup

Codex-native skill creation works through available source-reading tools without this CLI or a separate API key. For the upstream parser/CLI backend, use an existing Python 3.10+ interpreter (3.13 is tested). Check for an existing working environment before creating one:

```sh
python3.13 -m venv ~/.local/share/skill-anything/venv
~/.local/share/skill-anything/venv/bin/python -m pip install 'skill-anything[pdf,web,video] @ git+https://github.com/SYuan03/Skill-Anything.git@3cdc1c1f11dc8e0fc8d816b99d7ca0728b0ab098'
~/.local/share/skill-anything/venv/bin/skill-anything version
```

Use the venv command directly if no global skill-anything command exists. Do not replace an existing venv or command. No audio extra or model download is required.
