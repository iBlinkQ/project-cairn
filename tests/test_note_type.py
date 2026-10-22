"""Fixed new identities and safe historical updates with isolated provider stubs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SKILL = ROOT
SCRIPTS = SKILL / 'scripts'
SPEC = importlib.util.spec_from_file_location('fixed_notion_batch', SCRIPTS / 'notion-graduate-batch.py')
BATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BATCH)
HISTORICAL = ['knowledge_note', '项目经验', '培训经验', 'a: b #c "quoted" \\path', 'true', 'null', '2026-10-14', '[a].*+$']


@pytest.fixture
def provider_env(tmp_path):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    vault = tmp_path / 'vault'
    vault.mkdir()
    stub = f'#!{sys.executable}\n' + r'''import json, os, pathlib, sys
a=sys.argv[1:]; root=pathlib.Path(os.environ['CAPTURE_ROOT'])
name=pathlib.Path(sys.argv[0]).name
with (root/'calls.jsonl').open('a') as f: f.write(json.dumps([name,a])+'\n')
if name=='obsidian':
    if a==['vault=Test Vault','vault','info=path']: print(os.environ['FAKE_VAULT'])
    else: raise SystemExit('unexpected obsidian call')
elif name=='lark-cli':
    if a[:3]==['wiki','nodes','create']:
        print(json.dumps({'data':{'node':{'node_token':'node','obj_token':'doc','url':'https://fake.test/wiki/node'}}}))
    elif a[:2]==['docs','+update']:
        (root/'lark.md').write_text(sys.stdin.read()); print('{"ok":true}')
    elif a[:2]==['docs','+fetch']: print((root/'lark.md').read_text())
    else: raise SystemExit('unexpected lark call: '+str(a))
elif name=='curl':
    method=a[a.index('-X')+1] if '-X' in a else 'GET'
    url=next(x for x in a if x.startswith('https://'))
    payload=json.loads(pathlib.Path(a[a.index('--data')+1][1:]).read_text()) if '--data' in a else None
    with (root/'requests.jsonl').open('a') as f: f.write(json.dumps({'method':method,'url':url,'payload':payload})+'\n')
    if payload is not None: (root/'payload.json').write_text(json.dumps(payload))
    statefile=root/'notion.json'
    state=json.loads(statefile.read_text()) if statefile.exists() else {'properties':{}}
    if method=='POST' and url.endswith('/databases'):
        print(json.dumps({'object':'database','id':'db','url':'https://fake.test/db'}))
    elif method in ('POST','PATCH') and ('/pages' in url):
        state['properties'].update(payload['properties']); statefile.write_text(json.dumps(state))
        print(json.dumps({'object':'page','id':'page','url':'https://fake.test/page'}))
    elif method=='GET' and '/pages/' in url:
        state['properties']['Name']={'type':'title','title':[{'plain_text':'Sample'}]}
        print(json.dumps({'object':'page',**state}))
    elif '/blocks/' in url: print('{"results":[],"has_more":false}')
    else: raise SystemExit('unexpected curl call')
'''
    for name in ['obsidian', 'lark-cli', 'curl']:
        path = bin_dir / name
        path.write_text(stub)
        path.chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
               CAPTURE_ROOT=str(tmp_path), FAKE_VAULT=str(vault), NOTION_API_TOKEN='fake-test-token')
    return tmp_path, vault, env


def run_adapter(name, args, env):
    return subprocess.run(['/bin/bash', str(SCRIPTS / name), *args], env=env,
                          cwd=env['CAPTURE_ROOT'], text=True, capture_output=True, timeout=20)


def fm(path):
    return yaml.safe_load(path.read_text().split('---', 2)[1])


def requests(temp):
    return [json.loads(line) for line in (temp / 'requests.jsonl').read_text().splitlines()]


def test_fixed_topic_template_and_configs_ignore_identity_selector():
    topic = yaml.safe_load((SKILL / 'assets/templates/topic.md').read_text().split('---', 2)[1])
    assert topic['type'] == 'project_topic'
    for name in ['config.yaml', 'user-config.yaml']:
        values = yaml.safe_load((SKILL / 'assets/templates' / name).read_text())
        assert 'note_type' not in values.get('cairn', {})
        assert 'note_type' not in values.get('defaults', {})
    assert not (SCRIPTS / 'resolve-note-type.py').exists()


def test_new_notes_and_database_use_fixed_identity(provider_env):
    temp, vault, env = provider_env
    # Old, contradictory config is intentionally present. Adapters must not
    # consume it, rewrite it, or freeze its value in new output.
    project = temp / '.cairn'
    project.mkdir()
    cfg = project / 'config.yaml'
    cfg.write_text('cairn:\n  note_type: old-project-choice\n')
    saved = cfg.read_bytes()
    common = ['--title', 'Sample', '--graduated-by', 'Alice']
    for name, args in [
        ('obsidian-graduate.sh', ['--vault', 'Test Vault', '--target', 'kb', '--graduated-from', 'Demo|cairn/topic.md']),
        ('lark-wiki-graduate.sh', ['--space-id', 'space', '--identity', 'bot', '--graduated-from', 'Demo|cairn/topic.md']),
        ('notion-graduate.sh', ['--db', 'db', '--graduated-from', 'Demo: cairn/topic.md']),
    ]:
        result = run_adapter(name, common + args, env)
        assert result.returncode == 0, (name, result.stderr)
        assert 'mismatch' not in result.stderr
    assert fm(vault / 'kb/Sample.md')['type'] == 'project_insight'
    assert fm(temp / 'lark.md')['type'] == 'project_insight'
    assert json.loads((temp / 'notion.json').read_text())['properties']['type']['select']['name'] == 'project_insight'
    result = run_adapter('notion-init-db.sh', ['--parent-page-id', 'parent', '--title', 'Knowledge'], env)
    assert result.returncode == 0, result.stderr
    names = [x['name'] for x in json.loads((temp / 'payload.json').read_text())['properties']['type']['select']['options']]
    assert names == ['project_insight', 'knowledge_note', 'playbook', 'reference']
    assert cfg.read_bytes() == saved


@pytest.mark.parametrize('note_type', HISTORICAL)
def test_regraduation_preserves_confirmed_old_type_and_literal_strings(provider_env, note_type):
    temp, vault, env = provider_env
    folder = vault / 'kb'
    folder.mkdir()
    target = folder / 'Sample.md'
    target.write_text('---\n' + yaml.safe_dump({'type': note_type}, allow_unicode=True) + '---\nOld body\n')
    common = ['--title', 'Sample', '--type', note_type, '--graduated-by', 'Alice', '--graduated-by', 'Bob']
    result = run_adapter('obsidian-graduate.sh', common + ['--vault', 'Test Vault', '--target', 'kb', '--graduated-from', 'Demo|cairn/topic.md', '--force'], env)
    assert result.returncode == 0, result.stderr
    assert fm(target)['type'] == note_type
    assert fm(target)['graduated_by'] == ['Alice', 'Bob']
    result = run_adapter('lark-wiki-graduate.sh', common + ['--space-id', 'space', '--identity', 'bot', '--update-node-token', 'node', '--update-obj-token', 'doc', '--update-url', 'https://fake.test/wiki/node'], env)
    assert result.returncode == 0, result.stderr
    assert fm(temp / 'lark.md')['type'] == note_type
    (temp / 'notion.json').write_text(json.dumps({'properties': {'type': {'select': {'name': note_type}}}}))
    result = run_adapter('notion-graduate.sh', ['--title', 'Sample', '--db', 'db', '--page-id', 'page', '--graduated-by', 'Bob'], env)
    assert result.returncode == 0, result.stderr
    assert 'type' not in requests(temp)[0]['payload']['properties']
    assert json.loads((temp / 'notion.json').read_text())['properties']['type']['select']['name'] == note_type
    result = run_adapter('notion-graduate.sh', common + ['--db', 'db', '--page-id', 'page'], env)
    assert result.returncode == 0, result.stderr
    assert json.loads((temp / 'notion.json').read_text())['properties']['type']['select']['name'] == note_type


def test_overwrite_cannot_silently_apply_new_default(provider_env):
    temp, vault, env = provider_env
    target = vault / 'kb/Sample.md'
    target.parent.mkdir()
    target.write_text('---\ntype: knowledge_note\n---\nOld content\n')
    before = target.read_bytes()
    result = run_adapter('obsidian-graduate.sh', ['--vault', 'Test Vault', '--title', 'Sample', '--target', 'kb', '--graduated-from', 'Demo|cairn/topic.md', '--force'], env)
    assert result.returncode != 0 and '--type' in result.stderr
    assert target.read_bytes() == before
    (temp / 'calls.jsonl').unlink()
    result = run_adapter('lark-wiki-graduate.sh', ['--title', 'Sample', '--identity', 'bot', '--graduated-by', 'Bob', '--update-node-token', 'node', '--update-obj-token', 'doc', '--update-url', 'https://fake.test/wiki/node'], env)
    assert result.returncode != 0
    assert not (temp / 'calls.jsonl').exists()


def test_explicitly_confirmed_type_change_can_update_historical_targets(provider_env):
    temp, vault, env = provider_env
    target = vault / 'kb/Sample.md'
    target.parent.mkdir()
    target.write_text('---\ntype: knowledge_note\n---\nOld body\n')
    common = ['--title', 'Sample', '--type', 'project_insight', '--graduated-by', 'Alice']
    result = run_adapter('obsidian-graduate.sh', common + ['--vault', 'Test Vault', '--target', 'kb', '--graduated-from', 'Demo|cairn/topic.md', '--force'], env)
    assert result.returncode == 0, result.stderr
    assert fm(target)['type'] == 'project_insight'
    (temp / 'lark.md').write_text('---\ntype: knowledge_note\n---\nOld body\n')
    result = run_adapter('lark-wiki-graduate.sh', common + ['--space-id', 'space', '--identity', 'bot', '--update-node-token', 'node', '--update-obj-token', 'doc', '--update-url', 'https://fake.test/wiki/node'], env)
    assert result.returncode == 0, result.stderr
    assert fm(temp / 'lark.md')['type'] == 'project_insight'
    (temp / 'notion.json').write_text(json.dumps({'properties': {'type': {'select': {'name': 'knowledge_note'}}}}))
    result = run_adapter('notion-graduate.sh', common + ['--db', 'db', '--page-id', 'page'], env)
    assert result.returncode == 0, result.stderr
    assert json.loads((temp / 'notion.json').read_text())['properties']['type']['select']['name'] == 'project_insight'


@pytest.mark.parametrize('note_type', ['', ' ', 'a\nb', 'a\rb', 'a\u2028b'])
def test_invalid_type_stops_before_any_provider_call(provider_env, note_type):
    temp, _, env = provider_env
    for name, args in [
        ('obsidian-graduate.sh', ['--vault', 'Test Vault', '--title', 'Sample', '--target', 'kb', '--graduated-from', 'Demo|cairn/topic.md']),
        ('lark-wiki-graduate.sh', ['--title', 'Sample', '--space-id', 'space']),
        ('notion-graduate.sh', ['--db', 'db', '--title', 'Sample']),
        ('notion-init-db.sh', ['--parent-page-id', 'parent', '--title', 'Sample']),
    ]:
        result = run_adapter(name, args + ['--type', note_type], env)
        assert result.returncode != 0, (name, result.stderr)
    assert not (temp / 'calls.jsonl').exists()


def test_notion_complete_properties_obey_new_and_preserved_types(provider_env):
    temp, _, env = provider_env
    props = temp / 'props.json'
    props.write_text(json.dumps({'Name': {'title': [{'text': {'content': 'Sample'}}]}}))
    common = ['--title', 'Sample', '--db', 'db', '--props-json', str(props)]
    result = run_adapter('notion-graduate.sh', common, env)
    assert result.returncode == 0, result.stderr
    assert requests(temp)[0]['payload']['properties']['type']['select']['name'] == 'project_insight'
    props.write_text(json.dumps({'type': {'select': {'name': 'knowledge_note'}}}))
    before = len(requests(temp))
    result = run_adapter('notion-graduate.sh', common, env)
    assert result.returncode != 0
    result = run_adapter('notion-graduate.sh', common + ['--page-id', 'page'], env)
    assert result.returncode != 0
    assert len(requests(temp)) == before
    result = run_adapter('notion-graduate.sh', common + ['--page-id', 'page', '--type', 'knowledge_note'], env)
    assert result.returncode == 0, result.stderr
    assert json.loads((temp / 'notion.json').read_text())['properties']['type']['select']['name'] == 'knowledge_note'


def write_note(path, note_type, **fields):
    metadata = {'type': note_type, 'graduated_from': [{'project': 'Demo', 'path': 'cairn/topic.md'}], 'graduated_by': ['Alice'], **fields}
    path.write_text('---\n' + yaml.safe_dump(metadata, allow_unicode=True) + '---\n## Background\nOrigin\n## Conclusion\nClaim\n')
    return path


def batch_calls(monkeypatch, files, *extra, existing=()):
    calls = []
    def api(method, path, body=None, **kwargs):
        calls.append((method, path, body))
        if path.startswith('databases/'):
            return {'results': [{'id': 'old-' + title, 'properties': {'Name': {'title': [{'plain_text': title}]}}} for title in existing], 'has_more': False}
        if path.startswith('blocks/'): return {'results': [], 'has_more': False}
        return {'id': 'new-' + str(len(calls))}
    monkeypatch.setattr(BATCH, 'api', api)
    monkeypatch.setenv('NOTION_API_TOKEN', 'fake-test-token')
    monkeypatch.setattr(sys, 'argv', ['batch', '--db', 'db', *extra, *map(str, files)])
    return calls


def test_batch_new_and_historical_material_can_share_one_batch(tmp_path, monkeypatch):
    notes = [write_note(tmp_path / (name + '.md'), kind) for name, kind in [('New', 'project_insight'), ('Old', 'knowledge_note')]]
    calls = batch_calls(monkeypatch, notes)
    BATCH.main()
    created = [body for method, path, body in calls if method == 'POST' and path == 'pages']
    assert [body['properties']['type']['select']['name'] for body in created] == ['project_insight', 'knowledge_note']


@pytest.mark.parametrize('migrate', [False, True])
def test_batch_declined_migration_preserves_target_while_updating_content(tmp_path, monkeypatch, migrate):
    note = write_note(tmp_path / 'Existing.md', 'project_insight')
    calls = batch_calls(monkeypatch, [note], *(['--migrate-types'] if migrate else []), existing=['Existing'])
    BATCH.main()
    patched = next(body for method, path, body in calls if method == 'PATCH' and path == 'pages/old-Existing')
    assert ('type' in patched['properties']) == migrate
    if migrate: assert patched['properties']['type']['select']['name'] == 'project_insight'
    assert any(method == 'PATCH' and path == 'blocks/old-Existing/children' for method, path, body in calls)
    assert not any(method == 'POST' and path == 'pages' for method, path, body in calls)


@pytest.mark.parametrize('note_type', HISTORICAL[1:])
def test_custom_historical_import_requires_explicit_allowlist(tmp_path, monkeypatch, note_type):
    note = write_note(tmp_path / 'Historical.md', note_type)
    calls = batch_calls(monkeypatch, [note])
    with pytest.raises(SystemExit): BATCH.main()
    assert calls == []
    calls = batch_calls(monkeypatch, [note], '--legacy-type', note_type)
    BATCH.main()
    payload = next(body for method, path, body in calls if method == 'POST' and path == 'pages')
    assert payload['properties']['type']['select']['name'] == note_type


@pytest.mark.parametrize('fields', [
    {'type': 'project_topic'}, {'graduated_by': None}, {'graduated_by': ['']},
    {'graduated_from': None}, {'graduated_from': [{'project': 'Demo'}]},
    {'graduated_from': {'project': 'Demo', 'path': 'cairn/topic.md'}},
])
def test_invalid_batch_material_is_rejected_before_first_request(tmp_path, monkeypatch, fields):
    good = write_note(tmp_path / 'Good.md', 'project_insight')
    metadata = {'type': 'project_insight', 'graduated_from': [{'project': 'Demo', 'path': 'cairn/topic.md'}], 'graduated_by': ['Alice'], **fields}
    bad = tmp_path / 'Bad.md'
    bad.write_text('---\n' + yaml.safe_dump(metadata) + '---\nNot prepared\n')
    calls = batch_calls(monkeypatch, [good, bad])
    with pytest.raises(SystemExit): BATCH.main()
    assert calls == []


def test_project_topic_cannot_be_allowlisted(tmp_path, monkeypatch):
    note = write_note(tmp_path / 'Topic.md', 'project_topic')
    calls = batch_calls(monkeypatch, [note], '--legacy-type', 'project_topic')
    with pytest.raises(SystemExit): BATCH.main()
    assert calls == []
