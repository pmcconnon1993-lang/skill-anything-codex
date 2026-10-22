"""Bounded source-contract probes; no Claude/model calls or live accounts."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import yaml

upstream = Path(sys.argv[1]).expanduser().resolve(strict=True)
sys.path.insert(0, str(upstream))
work = Path(tempfile.mkdtemp(prefix='source-probes-', dir=upstream.parent))


def load(name):
    spec = importlib.util.spec_from_file_location(name, upstream / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


packager = load('package_multiplatform')
fixture = work / 'fixture-skill'
fixture.mkdir()
(fixture / 'SKILL.md').write_text('---\nname: fixture-skill\ndescription: >\n  Check ordered CSV headers with a selected fixture.\n---\n\n# CSV\n\nCompare a supplied header list in order.\n')
parsed, _ = packager._read_skill_md(fixture)
assert parsed['description'] == '>'
packager.package(str(fixture), ['codex'], str(work / 'dist'))
companion = yaml.safe_load((work / 'dist/codex/fixture-skill/agents/openai.yaml').read_text())
assert companion['interface']['short_description'] == '>'
assert companion['dependencies']['tools'] == ['bash', 'file_read', 'file_write']
tests = load('generate_tests')
cases = tests._generate_functional_cases({'target_name': 'csv', 'target_type': 'cli', 'capabilities': [{'name': 'check'}]}, 1)
assert [a['type'] for a in cases[0]['assertions']] == ['contains_keyword', 'no_error']
benchmark = load('run_benchmark')
commands = []
benchmark.subprocess = SimpleNamespace(run=lambda argv, **kwargs: commands.append((argv, kwargs)) or SimpleNamespace(stdout='{}', stderr=''), TimeoutExpired=subprocess.TimeoutExpired)
benchmark._grade_response = lambda **kwargs: {'probe': 'stubbed; not a quality evaluation'}
benchmark._run_single_benchmark({'query': 'Check CSV'}, fixture, work, 'with')
with_call = commands[-1]
benchmark._run_single_benchmark({'query': 'Check CSV'}, None, work, 'without')
assert with_call == commands[-1]
result = {'identity': '0f7d527492ca84b28148600880a4854374df8c24', 'probes': [
    {'name': 'folded-description', 'observed': 'description collapses to literal >; Codex short_description becomes >', 'result': 'confirmed'},
    {'name': 'codex-dependencies', 'observed': 'tools are strings bash/file_read/file_write, not documented Codex tool dependency objects', 'result': 'confirmed'},
    {'name': 'generated-assertions', 'observed': 'contains_keyword plus no_error; no backend-output check supplied', 'result': 'confirmed'},
    {'name': 'benchmark-skill-loading', 'observed': 'captured subprocess argv and kwargs identical with and without skill_path', 'result': 'confirmed; subprocess and grader stubbed, no model benchmark run'}],
    'limits': 'Bounded source-contract probes do not measure model quality or prove every upstream path is broken.'}
(work / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'result': result, 'evidence': str(work / 'results.json')}, indent=2))
