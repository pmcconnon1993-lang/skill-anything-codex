# Codex installation and recall

This directory adds installable Codex skills around the upstream Skill-Anything CLI.

- `skillinstall`: routes a URL to an existing skill installation or source-to-skill creation.
- `skill-anything-codex`: extracts source material and helps Codex create operational agent skills; also supports upstream learning packs and exports.

## Install globally

With Codex's bundled skill-installer:

```sh
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo pmcconnon1993-lang/skill-anything-codex \
  --path skill-anything-codex codex/skillinstall
```

The installer defaults to `$CODEX_HOME/skills`, or `~/.codex/skills`. Adjust the installer script path if CODEX_HOME differs. The skills become available on the next turn. Existing destinations cause a refusal: inspect and back up an existing package before an intentional update.

The instructions can use Codex's existing source-reading tools without a separate API key. The extraction scripts need the optional Python runtime described in [upstream-cli.md](../skill-anything-codex/references/toolchain.md); a skill installation does not itself install that backend. Standalone CLI generation needs a configured backend for useful LLM output and may otherwise use heuristics. No credentials, model weights, or personal memory are included.

## Use

Say `skillinstall https://example.com/tool/docs`, or invoke `$skillinstall` with your URL. The expected result is an installed or updated skill containing operational procedures, source-backed references, and verification results. A summary or bookmark alone is insufficient.

Existing GitHub SKILL.md packages use skill-installer. Websites and repositories without one use skill-anything-codex plus skill-creator. The routing skills depend on Codex's bundled skill-installer and skill-creator; install both packages above together.

## Durable findings

Reusable findings live in the resulting skill's references with source URL, retrieval date, relevant version, and verification limits. Ask `Recall the findings from <skill-name>` to revisit those references. Ask `Remember this long-term` to additionally save a concise preference or pointer using the host environment's permitted memory mechanism.

This is persistent instruction and reference storage, not model training or a guarantee of perfect recall. Skills and memory must be available in the current environment; installing on one computer does not automatically sync another. Refresh facts that may have changed. Publication of this integration does not authorize publishing future private findings.

## Verification

The helpers repair the upstream v0.4.1 Codex export metadata/quiz path and preserve SRT/VTT timestamps during extraction. The upstream CLI remains unchanged. With the optional runtime installed, run `python -m unittest discover -s codex/tests -v` using that environment's Python.
