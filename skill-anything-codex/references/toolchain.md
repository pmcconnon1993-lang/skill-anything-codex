# Optional source-extraction toolchain

The skill's core authoring/recall workflow uses Codex and the Python standard
library. Its retained source extraction adapter additionally uses
SYuan03/Skill-Anything v0.4.1, inspected at
`3cdc1c1f11dc8e0fc8d816b99d7ca0728b0ab098`.

Use an existing environment where `import skill_anything` succeeds. The companion
source application is retained in this repository's `skill_anything/` directory.
If setup is needed, use a project environment and install only required extras
within the user's requested setup scope. Core supports text; `pdf`, `web`,
and `video` extras provide PDF, webpage and YouTube-caption dependencies. Raw
audio/uncaptioned media needs an existing transcription route; image-only PDFs
need OCR. Installing this skill does not install Whisper, weights or a service.

```bash
python3 scripts/source_tool.py extract '/path/to/notes.md' --output '/work/source.json'
python3 scripts/source_tool.py extract '/path/to/repository' --type repo --output '/work/repo.json'
python3 scripts/source_tool.py extract 'https://example.org/docs' --type web --output '/work/web.json'
python3 scripts/source_tool.py extract 'Pasted material' --inline --output '/work/inline.json'
```

Choose a fresh output file. Extraction retains sections, chunk metadata and
available page/time locators, plus repository selection statistics. It invokes
no generation model and executes no target code. Remote inputs still require
network access. Inspect selected paths and omissions; repository extraction
uses upstream selection limits. Prepare selected snapshots for private material.
Local SRT/VTT extraction uses the retained subtitle parser to preserve complete
cue times; upstream v0.4.1 slices those locators incorrectly. Local video needs
a subtitle sidecar or a prior transcription route, rather than an implicit
Whisper download. The compatible `extract_source.py` and
`prepare_codex_skill.py` helpers from the repository's prior Codex integration
are also preserved; the latter adapts a selected export in place with a backup.

Optional upstream generation remains a conservative seed:

```bash
python3 scripts/source_tool.py cli text '/path/to/notes.md' --format all --concurrency 1 --output '/work/seed'
python3 scripts/source_tool.py cli lint '/work/seed/original-export'
python3 scripts/source_tool.py adapt-export '/work/seed/original-export' --output '/work/fresh-codex-package'
```

The adapter disables generation APIs, image calls and `.env` loading in `cli`;
fallback content needs Codex review and operational authoring. The original
application's `sa` command retains upstream provider behavior; do not silently
use inherited provider keys or enable external generation. Never call seed
material finished solely because export succeeded.

Adaptation preserves the original and changes top-level `version` to
`metadata.version`, replacing the Claude quiz path. The generated absolute quiz
path must be updated if relocating the package, or rewritten as an explicit
run-from-package-root instruction. Use the full claude-to-codex workflow for
arbitrary Claude skills; this helper only adapts the known study-pack format.
Upstream lint requires top-level `version`; Codex validation rejects it. Lint
the original with upstream lint and the adapted package with skill-creator's
current validator. Check knowledge separately with `knowledge.py check`.

On the user's original Mac, the existing `skill-anything-codex` launcher selects
the already installed external-drive environment. Host paths belong in the
local launcher/setup receipt, not this distributable package. If that drive is
unavailable, report it; do not silently reinstall onto a full internal SSD.
