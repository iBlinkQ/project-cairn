"""Unit tests for scripts/notion-graduate-batch.py.

Focused on the Notion API-limit and robustness fixes:
  - CRLF frontmatter parsing
  - scalar contains/tags normalization
  - 2000-char rich_text splitting
  - 100-block chunked appends
  - write-before-delete body replacement order
  - Idempotency-Key on page creation

No network: urllib is monkeypatched wherever a call would leave the process.
"""
import importlib.util
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("nbg", ROOT / "scripts" / "notion-graduate-batch.py")
nbg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nbg)


# --- parse_note: CRLF + LF frontmatter -----------------------------------

def test_parse_note_crlf(tmp_path):
    f = tmp_path / "note.md"
    f.write_bytes(b"---\r\ntype: knowledge_note\r\ncontains: [decision]\r\n---\r\n## Background\r\nbody\r\n")
    title, fm, body = nbg.parse_note(str(f))
    assert title == "note"
    assert fm["contains"] == ["decision"]
    assert body.startswith("## Background")


def test_parse_note_lf(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntype: knowledge_note\n---\nbody\n", encoding="utf-8")
    title, fm, body = nbg.parse_note(str(f))
    assert title == "note"
    assert body == "body\n"  # trailing newline is kept (harmless: md_to_blocks ignores it)


# --- props(): scalar contains/tags normalization -------------------------

def test_contains_tags_scalar_normalized():
    fm = {"contains": "decision", "tags": "notion", "type": "knowledge_note"}
    p = nbg.props("t", fm, "2026-08-15", "", {})
    assert p["contains"]["multi_select"] == [{"name": "decision"}]
    assert p["tags"]["multi_select"] == [{"name": "notion"}]


def test_contains_list_unchanged():
    fm = {"contains": ["decision", "lesson"]}
    p = nbg.props("t", fm, "", "", {})
    assert p["contains"]["multi_select"] == [{"name": "decision"}, {"name": "lesson"}]


# --- rich_text 2000-char splitting ---------------------------------------

def test_text_items_split_at_2000():
    items = nbg._text_items("x" * 4500)
    assert [len(i["text"]["content"]) for i in items] == [2000, 2000, 500]
    assert all(i["type"] == "text" for i in items)


def test_rich_splits_long_paragraph():
    items = nbg.rich("x" * 3000, {})
    assert sum(len(i["text"]["content"]) for i in items) == 3000
    assert all(len(i["text"]["content"]) <= 2000 for i in items)


def test_rich_mention_keeps_structure():
    items = nbg.rich("see [[Other]] now", {"Other": "pageid"})
    assert [i["type"] for i in items] == ["text", "mention", "text"]
    assert items[1]["mention"]["page"]["id"] == "pageid"


def test_code_block_split_at_2000():
    blocks = nbg.md_to_blocks("```\n" + "y" * 3000 + "\n```", {})
    code = blocks[0]["code"]["rich_text"]
    assert [len(i["text"]["content"]) for i in code] == [2000, 1000]


# --- chunking ------------------------------------------------------------

def test_chunks():
    assert [len(c) for c in nbg.chunks(list(range(250)))] == [100, 100, 50]


class Recorder:
    def __init__(self, existing_children):
        self.calls = []
        self.existing_children = existing_children

    def api(self, method, path, body=None, tries=8, token=None, idem=None):
        self.calls.append((method, path, body, idem))
        if method == "GET" and "children" in path:
            return {"results": self.existing_children, "has_more": False}
        return {"id": "ok"}


def test_replace_body_write_before_delete_and_chunked(monkeypatch):
    old = [{"id": "old1"}, {"id": "old2"}, {"id": "old3"}]
    rec = Recorder(old)
    monkeypatch.setattr(nbg, "api", rec.api)
    blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}} for _ in range(250)]
    nbg.replace_body("pg", blocks, "tok")

    ops = [(m, p) for (m, p, _, _) in rec.calls]
    assert ops[0] == ("GET", "blocks/pg/children?page_size=100")

    patches = [b for (m, p, b, _) in rec.calls if m == "PATCH"]
    assert [len(b["children"]) for b in patches] == [100, 100, 50]

    methods = [m for (m, _, _, _) in rec.calls]
    assert methods.count("DELETE") == 3
    # every append precedes every delete
    assert max(i for i, m in enumerate(methods) if m == "PATCH") < \
        min(i for i, m in enumerate(methods) if m == "DELETE")


def test_replace_body_empty_blocks_still_deletes(monkeypatch):
    rec = Recorder([{"id": "old1"}])
    monkeypatch.setattr(nbg, "api", rec.api)
    nbg.replace_body("pg", [], "tok")
    methods = [m for (m, _, _, _) in rec.calls]
    assert "PATCH" not in methods
    assert methods == ["GET", "DELETE"]


# --- api(): Idempotency-Key header ---------------------------------------

def test_api_idempotency_header(monkeypatch):
    captured = {}

    class FakeResp:
        def read(self):
            return b'{"ok": true}'

    class FakeRequest:
        def __init__(self, url, data=None, method=None, headers=None):
            captured.update(headers or {})

    monkeypatch.setattr(nbg.urllib.request, "Request", FakeRequest)
    monkeypatch.setattr(nbg.urllib.request, "urlopen", lambda req, timeout=30: FakeResp())

    nbg.api("POST", "pages", {"a": 1}, token="t", idem="key-1")
    assert captured["Idempotency-Key"] == "key-1"

    captured.clear()
    nbg.api("POST", "pages", {"a": 1}, token="t")
    assert "Idempotency-Key" not in captured


# --- main(): page creation carries a non-empty Idempotency-Key -----------

def test_main_create_sends_idempotency_key(tmp_path, monkeypatch):
    f = tmp_path / "note.md"
    f.write_text("---\ntype: knowledge_note\n---\nbody\n", encoding="utf-8")
    calls = {}

    def fake_api(method, path, body=None, tries=8, token=None, idem=None):
        calls.setdefault((method, path), []).append(idem)
        if method == "POST" and path.endswith("/query"):
            return {"results": [], "has_more": False}
        if method == "POST" and path == "pages":
            return {"id": "page1"}
        if method == "GET" and "children" in path:
            return {"results": [], "has_more": False}
        return {}

    monkeypatch.setattr(nbg, "api", fake_api)
    monkeypatch.setenv("NOTION_API_TOKEN", "t")
    monkeypatch.setattr(sys, "argv", ["nbg", "--db", "DB1", str(f)])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)

    nbg.main()

    create_key = calls[("POST", "pages")][0]
    assert create_key and isinstance(create_key, str)
    assert "page1" in out.getvalue()
