---
name: skillinstall
description: Install or update a reusable Codex skill from a supplied URL or source. Use when the user says skillinstall, skill install, or asks skill-installer to turn a website into an installed skill with reusable findings.
---

# Skill Install

Interpret `skillinstall <URL>` as a request to inspect the source, install or create the relevant skill globally, and verify it. Use the requested scope; do not merely save a bookmark or summarize the homepage.

- If the source contains an existing SKILL.md package, use installed `skill-installer` guidance and its installer helper. Inspect the package and its dependencies, preserve existing work, and validate the installed result.
- If the source is a website, document, repository, or tutorial without a skill package, use installed `skill-anything` and `skill-creator` guidance to extract operational procedures and produce a usable skill. Read relevant pages and source files; a landing page alone may be insufficient.
- Default to `$CODEX_HOME/skills/<name>`, or `~/.codex/skills/<name>` when CODEX_HOME is unset. Update a matching existing skill when appropriate; preserve unrelated content. Resolve installed skills from the active skill catalog rather than assuming a fixed machine path.
- Store reusable findings in the resulting skill's references with source URLs, retrieval date, version when relevant, verification, and limitations. Keep SKILL.md focused on activation, decisions, procedures, and success checks. Follow the user's standing Harness² routing policy where present.
- When explicitly asked to remember findings or a preference, save a concise memory entry or pointer through the environment's permitted memory mechanism. Full source-backed detail belongs in the skill references. On recall, read those files and refresh facts likely to have changed. Installation does not train the underlying model or guarantee perfect recall.
- Test structural validity and representative behavior before calling the installation usable. Report missing access, transcripts, dependencies, or source material honestly. Preserve existing provider/model choices; installation alone does not authorize downloads of models or unrelated software.
- Publish or update GitHub only when requested or otherwise explicitly authorized. Keep credentials, private memory, and machine-specific configuration out of published packages.

Examples: `skillinstall https://example.com/tool/docs` creates or updates an operational skill from that documentation. `Use skill-installer on https://github.com/owner/repo/tree/main/skills/tool` installs the existing package. `Recall the findings from <skill-name>` reads its references and checks any time-sensitive claims.
