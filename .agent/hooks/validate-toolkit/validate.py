#!/usr/bin/env python3
"""Read-only validation for repository toolkit metadata, links and adapters."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASELINE = {
    'build', 'investigate', 'research', 'verify', 'review', 'fix',
    'release', 'deploy', 'publish', 'push', 'pull',
}
CONTRACTS = {
    'core', 'authorization', 'verification', 'git-github',
    'deployment', 'handoff', 'memory', 'scopes',
}
PROVIDERS = ('.codex', '.claude')
# Claude Code loads these adapters only on an explicit /name invocation.
CLAUDE_USER_ONLY = {'release', 'deploy', 'publish'}
CLAUDE_GATE = 'disable-model-invocation: true'


def frontmatter(path: Path, claude_gate: bool = False) -> dict[str, str]:
    """Parse this toolkit's portable two-field YAML/JSON-string subset.

    The Claude release, deploy and publish adapters add one fixed gate line.
    """
    text = path.read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise ValueError('missing or malformed frontmatter')
    lines = match[1].splitlines()
    if claude_gate:
        if lines.count(CLAUDE_GATE) != 1:
            raise ValueError(f'Claude adapter requires {CLAUDE_GATE!r} for explicit-only invocation')
        lines = [line for line in lines if line != CLAUDE_GATE]
    elif any(line.startswith('disable-model-invocation:') for line in lines):
        raise ValueError('disable-model-invocation is reserved for the Claude release, deploy and publish adapters')
    fields: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition(':')
        if not sep or key not in {'name', 'description'} or key in fields:
            raise ValueError('expected unique name and description fields')
        # JSON double-quoted strings are also YAML 1.2 scalars. This deliberate
        # subset avoids a new runtime dependency and rejects ambiguous YAML.
        parsed = json.loads(value.strip())
        if not isinstance(parsed, str) or not parsed.strip():
            raise ValueError(f'{key} must be a nonempty quoted string')
        fields[key] = parsed
    if set(fields) != {'name', 'description'}:
        raise ValueError('name and description are required')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', fields['name']):
        raise ValueError('invalid skill name')
    if len(fields['name']) > 64 or len(fields['description']) > 1024:
        raise ValueError('metadata exceeds skill limits')
    if fields['name'] != path.parent.name:
        raise ValueError('name does not match directory')
    return fields


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    def check(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    required = ['AGENTS.md', 'CLAUDE.md', '.agent/README.md', '.agent/project.yaml',
                '.agent/evals/skill-routing.md', '.agent/integrations/README.md',
                '.agent/workflows/README.md', '.agent/hooks/README.md']
    required += [f'.agent/contracts/{name}.md' for name in sorted(CONTRACTS)]
    for path in required:
        check((root / path).is_file(), f'missing required file: {path}')
    try:
        p = json.loads((root / '.agent/project.yaml').read_text())
        check(p['schema_version'] == 1, 'unsupported metadata schema')
        check(p['project']['id'] == 'github:jikovec/Uncorrupter', 'project identity drift')
        check(p['project']['name'] == 'File Uncorrupter', 'project name drift')
        check(p['project']['type'] == 'application', 'project type drift')
        check(p['repository'] == {'host': 'github', 'owner': 'jikovec',
              'name': 'Uncorrupter', 'default_branch': 'main',
              'canonical_remote': 'origin'}, 'repository identity drift')
        check(p['organization'] == {'id': None, 'name': None}, 'unadopted organization binding')
        check(p['ownership']['class'] == 'user-owned', 'ownership classification drift')
        check(p['mind_seed'] == {'enabled': False, 'binding': None},
              'Mind-Seed activation requires binding reconciliation and validator update')
        for group, keys in [('agent', ('instructions', 'canonical_skills', 'project_specific_skills')),
                            ('integrations', ('directory',)), ('workflows', ('directory',))]:
            for key in keys:
                check((root / p[group][key]).exists(), f'unresolved metadata path: {group}.{key}')
        check(bool(p['environment']['primary_runtime']), 'runtime missing')
        check(isinstance(p['environment']['required_tools'], list), 'required_tools must be a list')
        for path in p['environment']['source_files']:
            check((root / path).is_file(), f'unresolved environment source: {path}')
        def no_runtime(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    check(key not in {'current_commit', 'current_branch', 'test_status',
                          'deployment', 'session_id', 'token', 'secret', 'password'},
                          f'transient or secret metadata key: {key}')
                    no_runtime(child)
            elif isinstance(value, list):
                for child in value:
                    no_runtime(child)
        no_runtime(p)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f'project metadata: {exc}')

    canonical: dict[str, tuple[Path, dict[str, str]]] = {}
    descriptions: set[str] = set()
    for path in sorted((root / 'skills').rglob('SKILL.md')):
        try:
            fields = frontmatter(path)
            name = fields['name']
            check(name not in canonical, f'duplicate canonical skill: {name}')
            check(fields['description'] not in descriptions, f'duplicate description: {name}')
            check(path.relative_to(root).parts in [
                ('skills', name, 'SKILL.md'), ('skills', 'project', name, 'SKILL.md')],
                f'unsupported canonical placement: {path.relative_to(root)}')
            if path.parent.parent.name == 'project':
                check(name not in BASELINE, f'project skill shadows baseline: {name}')
            canonical[name] = (path, fields)
            descriptions.add(fields['description'])
        except (OSError, ValueError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    for name in sorted(BASELINE):
        check((root / f'skills/{name}/SKILL.md').is_file(), f'missing baseline skill: {name}')

    for name in canonical:
        check(not (root / '.agents/skills' / name / 'SKILL.md').exists(),
              f'legacy duplicate discovery: .agents/skills/{name}/SKILL.md; preserve and reconcile before native routing')

    for provider in PROVIDERS:
        paths = list((root / provider / 'skills').glob('*/SKILL.md'))
        check({p.parent.name for p in paths} == set(canonical), f'{provider}: adapter inventory drift')
        for name, (source, fields) in canonical.items():
            adapter = root / provider / 'skills' / name / 'SKILL.md'
            try:
                gated = provider == '.claude' and name in CLAUDE_USER_ONLY
                check(frontmatter(adapter, gated) == fields, f'{provider}/{name}: metadata drift')
                target = source.relative_to(root).as_posix()
                body = adapter.read_text().split('---\n', 2)[-1].strip()
                expected = (f'Read and follow the canonical [{name} workflow](../../../{target}) before acting.\n'
                            'Follow root `AGENTS.md` and applicable scoped instructions. Resolve repository-relative\n'
                            'paths from this checkout. This adapter contains discovery metadata only.')
                check(body == expected, f'{provider}/{name}: adapter must remain a policy-free pointer')
            except (OSError, ValueError) as exc:
                errors.append(f'{provider}/{name}: {exc}')

    try:
        routes = (root / '.agent/evals/skill-routing.md').read_text()
        for name in canonical:
            match = re.search(r'^## ' + re.escape(name) + r'\n(.*?)(?=^## |\Z)', routes, re.M | re.S)
            check(match is not None, f'missing routing cases: {name}')
            if match:
                sections = re.split(r'^### ', match[1], flags=re.M)
                for title, minimum in [('Positive examples', 3), ('Counterexamples', 2)]:
                    section = next((s for s in sections if s.startswith(title + '\n')), '')
                    check(len(re.findall(r'^- ', section, re.M)) >= minimum,
                          f'{name}: insufficient {title.lower()}')
        check('@AGENTS.md' in (root / 'CLAUDE.md').read_text(), 'Claude import missing')
        index = json.loads((root / 'docs/agent-index.json').read_text())
        check(index['important_paths']['agent_project'] == '.agent/project.yaml', 'machine index missing project')
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f'routing/import/index: {exc}')

    documents = list((root / '.agent').rglob('*.md')) + list((root / 'skills').rglob('*.md'))
    documents += [root / 'AGENTS.md', root / 'CLAUDE.md', root / 'docs/agent-workflow.md']
    for doc in documents:
        if not doc.is_file():
            continue
        text = doc.read_text()
        check(text.endswith('\n'), f'{doc.relative_to(root)}: missing final newline')
        check(not any(line.rstrip() != line for line in text.splitlines()),
              f'{doc.relative_to(root)}: trailing whitespace')
        for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', text):
            if urlsplit(target).scheme or target.startswith('#'):
                continue
            local = unquote(target.split('#', 1)[0])
            dest = (doc.parent / local).resolve()
            check(dest.is_relative_to(root), f'{doc.relative_to(root)}: link escapes repository: {target}')
            check(dest.exists(), f'{doc.relative_to(root)}: broken link: {target}')
    return errors


def main() -> int:
    if len(sys.argv) > 2:
        print('Usage: python .agent/hooks/validate-toolkit/validate.py [repository-root]', file=sys.stderr)
        return 2
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[3]
    errors = validate(root)
    if errors:
        print('\n'.join(f'FAIL: {e}' for e in errors), file=sys.stderr)
        return 1
    print('PASS: toolkit identity, contracts, skills, adapter parity, routing coverage and links')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
