# Source findings and adopted techniques

Inspected on 2026-10-22:

- [AgentSkillOS/SkillAnything](https://github.com/AgentSkillOS/SkillAnything/tree/0f7d527492ca84b28148600880a4854374df8c24), commit `0f7d527492ca84b28148600880a4854374df8c24`.
- [SYuan03/Skill-Anything](https://github.com/SYuan03/Skill-Anything/tree/3cdc1c1f11dc8e0fc8d816b99d7ca0728b0ab098), v0.4.1, commit `3cdc1c1f11dc8e0fc8d816b99d7ca0728b0ab098`.

These are different projects. The second supplies the existing study-pack and
source extraction application. The first supplies a software-to-skill pipeline
inspired by CLI-Anything. This package combines selected techniques with the
user's existing Codex authoring and source-verification workflows; it does not
claim that the complete upstream pipelines are runtime-ready on this host.

## Adopted, with changes

| Technique | Codex implementation |
| --- | --- |
| Analyze → design → implement → test → evaluate → refine → package | Evidence-led stages proportional to the actual task, without mandatory model benchmarking for every small skill |
| Target routes for CLI/API/library/workflow/service | Distinguish documented interfaces, actual implementation and observed execution; retain existing working integrations |
| Capability-to-architecture mapping | Focused entrypoint, conditional topic references, exact operational contracts and only useful helpers |
| Functional and trigger cases | Test output/source invariants and boundary requests; do not score word mentions as working operations |
| With-skill/baseline evaluation | Require the skill to actually enter the tested agent context; keep tasks, model and tools fixed and report unrun comparisons |
| Platform packaging | Native Codex frontmatter and companion metadata, verified resources, citations and installation hashes |
| Retained learning | Checked topic records and read-only lexical recall with cited evidence; changing source requires review |

## Verified limits

1. **Target analysis is bounded.** API input is capped, library discovery selects
   the first 50 Python files and at most 100 discovered symbols. Symbol names,
   help and a homepage are leads, not complete operational contracts.
2. **Generated functional cases are weak starting points.** The inspected
   generator emits `contains_keyword` and `no_error` assertions. A response can
   mention an operation without performing it correctly.
3. **Trigger evaluation is Claude-specific.** `run_eval.py` writes temporary
   `.claude/commands` content and invokes `claude -p`. It was not executed here;
   those writes and results are unnecessary for Codex adaptation.
4. **Benchmark loading needs repair.** `_run_single_benchmark` accepts
   `skill_path` but does not use it to construct the subprocess call or context.
   A stubbed contract probe captured identical argv/kwargs with and without a
   skill path. This is a code-contract check, not a real model benchmark.
5. **Packaging is not complete Codex validation.** A real disposable packaging
   probe converted folded `description` into the literal `>` and generated
   dependency strings `bash`, `file_read`, `file_write`. Native Codex expects
   supported dependency objects, not invented tool registration. The output
   also retained a multiline template comment before frontmatter and the tool
   reported a validation warning while completing. This package therefore
   authors Codex files directly instead of installing that generated output.

Selected supporting source excerpts and hashes are in `knowledge.json` and
`evidence/`. They cover the described paths only. The recorded claims are
static findings; separate probes support the particular behaviors above.
No upstream advertised model benchmark score was adopted.

The current skill is a semantic rebuild of the selected methods, not a blind
copy of the converted upstream entrypoint. The converter was run in isolated
staging; Claude evaluators, optimization loops, obfuscation and other-platform
configuration were excluded from the installed workflow.

## Attribution

Existing source-extraction adapter and new Codex knowledge helpers are retained
as editable code. AgentSkillOS source excerpts retain its
[MIT license](licenses/AgentSkillOS-MIT.txt),
[NOTICE](licenses/AgentSkillOS-NOTICE.txt), and the
[Apache 2.0 text](licenses/Apache-2.0.txt) for attributed evaluation excerpts.
No upstream evaluator or benchmark executable is installed by this package.
The original SYuan03 application and license remain intact in the repository.
