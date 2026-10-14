"""Observable note identity behavior, using isolated files and local provider stubs."""
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
SCRIPTS = SKILL / "scripts"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESOLVE = load("resolve_note_type", SCRIPTS / "resolve-note-type.py")
BATCH = load("configured_notion_batch", SCRIPTS / "notion-graduate-batch.py")
TYPES = ["project_insight", "项目经验", "培训经验", 'a: b #c "quoted" \\path', "true", "null", "2026-10-14", "[a].*+$"]


def config(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.mark.parametrize("note_type", TYPES)
def test_selection_freezing_and_reuse(tmp_path, note_type):
    user = config(tmp_path / "user.yaml", {"defaults": {"language": "zh"}})
    before = user.read_bytes()
    choice = RESOLVE.init_types(user, selection=note_type)
    assert choice["topic_type"] == choice["knowledge_type"] == note_type
    assert user.read_bytes() == before  # Resolution never persists an unconfirmed choice.
    for rel in ["assets/templates/config.yaml", "assets/templates/user-config.yaml", "assets/templates/topic.md"]:
        rendered = (SKILL / rel).read_text().replace("{{NOTE_TYPE_YAML}}", choice["topic_type_yaml"])
        value = yaml.safe_load(rendered.split("---", 2)[1] if rel.endswith("topic.md") else rendered)
        actual = value["type"] if rel.endswith("topic.md") else value["cairn" if rel.endswith("/config.yaml") else "defaults"]["note_type"]
        assert actual == note_type and isinstance(actual, str)
    config(user, {"defaults": {"language": "zh", "note_type": note_type}})
    assert RESOLVE.init_types(user, reuse=True)["topic_type"] == note_type
    assert RESOLVE.init_types(user, skip=True)["topic_type"] == note_type
    project = config(tmp_path / "project.yaml", {"cairn": {"language": "zh", "note_type": note_type}, "graduation": {"provider": "none"}})
    config(user, {"defaults": {"note_type": "a later personal choice"}})
    assert RESOLVE.project_types(project)["topic_type"] == note_type


def test_skip_unanswered_and_old_user_defaults(tmp_path):
    user = config(tmp_path / "user.yaml", {"defaults": {"language": "zh"}})
    assert RESOLVE.init_types(user, skip=True)["topic_type"] == "project_insight"
    assert RESOLVE.init_types(tmp_path / "missing.yaml", skip=True)["source"] == "explicit_skip_fallback"
    for kwargs in [{}, {"reuse": True}, {"selection": " "}]:
        with pytest.raises(ValueError):
            RESOLVE.init_types(user, **kwargs)


def test_legacy_project_ignores_new_personal_default_and_stays_read_only(tmp_path):
    project = config(tmp_path / "project.yaml", {"cairn": {"language": "zh"}})
    config(tmp_path / "user.yaml", {"defaults": {"note_type": "项目经验"}})
    before = project.read_bytes()
    resolved = RESOLVE.project_types(project)
    assert resolved["legacy"]
    assert (resolved["topic_type"], resolved["knowledge_type"]) == ("project_topic", "knowledge_note")
    assert project.read_bytes() == before
    bad_call = subprocess.run([sys.executable, str(SCRIPTS / "resolve-note-type.py"), "--project-config", str(project), "--user-config", str(tmp_path / "user.yaml")], capture_output=True)
    assert bad_call.returncode != 0


@pytest.mark.parametrize("value", [None, False, 42, [], "", "  ", "a\nb", "a\rb", "a\u2028b", "a\u2029b"])
def test_invalid_config_and_selection_never_fall_back(tmp_path, value):
    project = config(tmp_path / "project.yaml", {"cairn": {"note_type": value}})
    user = config(tmp_path / "user.yaml", {"defaults": {"note_type": value}})
    with pytest.raises(ValueError):
        RESOLVE.project_types(project)
    with pytest.raises(ValueError):
        RESOLVE.init_types(user, skip=True)
    with pytest.raises(ValueError):
        RESOLVE.valid_type(value)


@pytest.fixture
def provider_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    stub = f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
a=sys.argv[1:]; root=pathlib.Path(os.environ["CAPTURE_ROOT"])
name=pathlib.Path(sys.argv[0]).name
with (root/"calls.jsonl").open("a") as f: f.write(json.dumps([name,a])+"\\n")
if name=="obsidian":
    if a==["vault=Test Vault","vault","info=path"]: print(os.environ["FAKE_VAULT"])
    else: raise SystemExit("unexpected obsidian call")
elif name=="lark-cli":
    if a[:3]==["wiki","nodes","create"]:
        print(json.dumps({"data":{"node":{"node_token":"node","obj_token":"doc","url":"https://fake.test/wiki/node"}}}))
    elif a[:2]==["docs","+update"]:
        (root/"lark.md").write_text(sys.stdin.read()); print('{"ok":true}')
    elif a[:2]==["docs","+fetch"]: print((root/"lark.md").read_text())
    else: raise SystemExit("unexpected lark call: "+str(a))
elif name=="curl":
    method=a[a.index("-X")+1] if "-X" in a else "GET"
    url=next(x for x in a if x.startswith("https://"))
    if "--data" in a:
        payload=json.loads(pathlib.Path(a[a.index("--data")+1][1:]).read_text())
        (root/"payload.json").write_text(json.dumps(payload))
    if method=="POST":
        is_db=url.endswith("/databases")
        print(json.dumps({"object":"database" if is_db else "page","id":"id","url":"https://fake.test/id"}))
    elif method=="GET":
        props=json.loads((root/"payload.json").read_text())["properties"]
        props["Name"]={"type":"title","title":[{"plain_text":"Sample"}]}
        print(json.dumps({"object":"page","properties":props}))
    else: raise SystemExit("unexpected curl call")
'''
    for name in ["obsidian", "lark-cli", "curl"]:
        p = bin_dir / name
        p.write_text(stub)
        p.chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], CAPTURE_ROOT=str(tmp_path), FAKE_VAULT=str(vault), NOTION_API_TOKEN="fake-test-token")
    return tmp_path, vault, env


def run_adapter(name, args, env):
    return subprocess.run(["/bin/bash", str(SCRIPTS / name), *args], env=env, text=True, capture_output=True, timeout=20)


@pytest.mark.parametrize("note_type", TYPES)
def test_all_provider_writes_roundtrip_same_literal_identity(provider_env, note_type):
    temp, vault, env = provider_env
    common = ["--title", "Sample", "--type", note_type]
    obsidian = run_adapter("obsidian-graduate.sh", [*common, "--vault", "Test Vault", "--target", "kb", "--graduated-from", "Demo|cairn/topic.md", "--graduated-by", "Alice"], env)
    assert obsidian.returncode == 0, obsidian.stderr
    assert "warn: read-back" not in obsidian.stderr
    fm = yaml.safe_load((vault / "kb/Sample.md").read_text().split("---", 2)[1])
    assert fm["type"] == note_type and isinstance(fm["type"], str)
    lark = run_adapter("lark-wiki-graduate.sh", [*common, "--identity", "bot", "--space-id", "space-test", "--graduated-from", "Demo|cairn/topic.md", "--graduated-by", "Alice"], env)
    assert lark.returncode == 0, lark.stderr
    assert "expected type text" not in lark.stderr
    assert yaml.safe_load((temp / "lark.md").read_text().split("---", 2)[1])["type"] == note_type
    notion = run_adapter("notion-graduate.sh", [*common, "--db", "db-test", "--graduated-from", "Demo: cairn/topic.md", "--graduated-by", "Alice"], env)
    assert notion.returncode == 0, notion.stderr
    assert "type mismatch" not in notion.stderr
    assert json.loads((temp / "payload.json").read_text())["properties"]["type"]["select"]["name"] == note_type
    db = run_adapter("notion-init-db.sh", ["--parent-page-id", "parent", "--title", "Knowledge", "--type", note_type], env)
    assert db.returncode == 0, db.stderr
    options = json.loads((temp / "payload.json").read_text())["properties"]["type"]["select"]["options"]
    names = [x["name"] for x in options]
    assert names[:3] == ["knowledge_note", "playbook", "reference"]
    assert names.count(note_type) == 1


@pytest.mark.parametrize("note_type", ["", " ", "a\nb", "a\rb", "a\u2028b"])
def test_invalid_adapter_identity_stops_before_provider_call(provider_env, note_type):
    temp, _, env = provider_env
    for name, args in [
        ("obsidian-graduate.sh", ["--vault", "Test Vault", "--title", "Sample", "--target", "kb", "--graduated-from", "Demo|cairn/topic.md"]),
        ("lark-wiki-graduate.sh", ["--title", "Sample", "--space-id", "space-test"]),
        ("notion-graduate.sh", ["--db", "db-test", "--title", "Sample"]),
        ("notion-init-db.sh", ["--parent-page-id", "parent", "--title", "Sample"]),
    ]:
        result = run_adapter(name, [*args, "--type", note_type], env)
        assert result.returncode != 0, (name, result.stderr)
    assert not (temp / "calls.jsonl").exists()


def test_legacy_omitted_metadata_and_db_options(provider_env):
    temp, vault, env = provider_env
    result = run_adapter("obsidian-graduate.sh", ["--vault", "Test Vault", "--title", "Sample", "--target", "kb", "--graduated-from", "Demo|cairn/topic.md"], env)
    assert result.returncode == 0
    assert "type: knowledge_note\n" in (vault / "kb/Sample.md").read_text()
    result = run_adapter("notion-graduate.sh", ["--db", "db", "--title", "Sample"], env)
    assert result.returncode == 0
    assert "type" not in json.loads((temp / "payload.json").read_text())["properties"]
    result = run_adapter("notion-init-db.sh", ["--parent-page-id", "parent", "--title", "Sample"], env)
    assert result.returncode == 0
    assert [x["name"] for x in json.loads((temp / "payload.json").read_text())["properties"]["type"]["select"]["options"]] == ["knowledge_note", "playbook", "reference"]
    body = temp / "body.md"
    body.write_text("# Sample\nBody exactly preserved.\n")
    result = run_adapter("lark-wiki-graduate.sh", ["--title", "Sample", "--space-id", "space-test", "--identity", "bot", "--content", str(body)], env)
    assert result.returncode == 0
    assert (temp / "lark.md").read_bytes() == body.read_bytes()


def test_explicit_notion_type_cannot_be_overridden_by_properties(provider_env):
    temp, _, env = provider_env
    props = temp / "props.json"
    props.write_text(json.dumps({"type": {"select": {"name": "other"}}}))
    args = ["--db", "db", "--title", "Sample", "--type", "项目经验", "--props-json", str(props)]
    result = run_adapter("notion-graduate.sh", args, env)
    assert result.returncode != 0
    assert not (temp / "calls.jsonl").exists()
    props.write_text(json.dumps({"type": {"select": {"name": "项目经验"}}}))
    result = run_adapter("notion-graduate.sh", args, env)
    assert result.returncode == 0, result.stderr
    assert json.loads((temp / "payload.json").read_text())["properties"]["type"]["select"]["name"] == "项目经验"


@pytest.mark.parametrize("note_type", TYPES)
def test_batch_configured_identity_and_unprepared_same_type_rejection(tmp_path, monkeypatch, note_type):
    ready = tmp_path / "Ready.md"
    fm = {"type": note_type, "graduated_from": [{"project": "Demo", "path": "cairn/topic.md"}], "graduated_by": ["Alice"]}
    ready.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n## Background\nOrigin\n## Conclusion\nClaim\n")
    calls = []
    def fake_api(method, path, body=None, **kwargs):
        calls.append((method, path, body))
        if path.startswith("databases/") or path.startswith("blocks/"):
            return {"results": [], "has_more": False}
        return {"id": "page"}
    monkeypatch.setattr(BATCH, "api", fake_api)
    monkeypatch.setenv("NOTION_API_TOKEN", "fake-test-token")
    monkeypatch.setattr(sys, "argv", ["batch", "--db", "db", "--expected-type", note_type, str(ready)])
    BATCH.main()
    create = next(body for method, path, body in calls if method == "POST" and path == "pages")
    assert create["properties"]["type"]["select"]["name"] == note_type
    raw = tmp_path / "Raw.md"
    raw.write_text("---\n" + yaml.safe_dump({"type": note_type}, allow_unicode=True) + "---\nUnprepared project original\n")
    calls.clear()
    monkeypatch.setattr(sys, "argv", ["batch", "--db", "db", "--expected-type", note_type, str(ready), str(raw)])
    with pytest.raises(SystemExit):
        BATCH.main()
    assert calls == []


@pytest.mark.parametrize("fields", [{"graduated_by": [""]}, {"graduated_from": [{"project": "Demo"}]}, {"graduated_from": {"project": "Demo", "path": "cairn/topic.md"}}])
def test_malformed_provenance_rejected_before_requests(tmp_path, fields):
    fm = {"type": "项目经验", "graduated_from": [{"project": "Demo", "path": "cairn/topic.md"}], "graduated_by": ["Alice"], **fields}
    note = tmp_path / "Bad.md"
    note.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\nBody\n")
    with pytest.raises(BATCH.NoteValidationError):
        BATCH.parse_note(note, "项目经验")
