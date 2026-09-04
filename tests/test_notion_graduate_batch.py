import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "notion-graduate-batch.py"
SPEC = importlib.util.spec_from_file_location("notion_graduate_batch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_note(tmp_path, name, frontmatter):
    note = tmp_path / name
    note.write_text(f"---\n{frontmatter}\n---\n# Note\nBody\n", encoding="utf-8")
    return note


def test_parse_note_rejects_project_topic(tmp_path):
    note = write_note(
        tmp_path,
        "project-topic.md",
        """type: project_topic
graduated_from:
  - project: Demo
    path: cairn/topic.md
graduated_by: [Alice]""",
    )

    with pytest.raises(MODULE.NoteValidationError) as exc:
        MODULE.parse_note(note)

    message = str(exc.value)
    assert str(note) in message
    assert "project_topic" in message
    assert "knowledge_note" in message
    assert "prepared knowledge-base note" in message


@pytest.mark.parametrize("missing_field", ["graduated_from", "graduated_by"])
def test_parse_note_requires_knowledge_base_provenance(tmp_path, missing_field):
    fields = {
        "type": "type: knowledge_note",
        "graduated_from": "graduated_from: [{project: Demo, path: cairn/topic.md}]",
        "graduated_by": "graduated_by: [Alice]",
    }
    frontmatter = "\n".join(
        value for key, value in fields.items() if key != missing_field
    )
    note = write_note(tmp_path, f"missing-{missing_field}.md", frontmatter)

    with pytest.raises(MODULE.NoteValidationError) as exc:
        MODULE.parse_note(note)

    assert str(note) in str(exc.value)
    assert missing_field in str(exc.value)


def test_parse_note_reports_yaml_file_line_column_and_hint(tmp_path):
    note = write_note(
        tmp_path,
        "invalid-yaml.md",
        """type: knowledge_note
summary: "实体在 E:\\.dsh"
graduated_from: [{project: Demo, path: cairn/topic.md}]
graduated_by: [Alice]""",
    )

    with pytest.raises(MODULE.NoteValidationError) as exc:
        MODULE.parse_note(note)

    message = str(exc.value)
    assert f"{note}:3:" in message
    assert "invalid YAML frontmatter" in message
    assert "unknown escape character" in message
    assert "single quotes" in message


def test_parse_note_accepts_prepared_knowledge_base_note(tmp_path):
    note = write_note(
        tmp_path,
        "ready.md",
        """type: knowledge_note
graduated_from: [{project: Demo, path: cairn/topic.md}]
graduated_by: [Alice]""",
    )

    title, frontmatter, body = MODULE.parse_note(note)

    assert title == "ready"
    assert frontmatter["type"] == "knowledge_note"
    assert body == "# Note\nBody\n"


def test_parse_notes_reports_every_invalid_file(tmp_path):
    first = write_note(
        tmp_path,
        "first.md",
        """type: project_topic
graduated_from: [{project: Demo, path: cairn/first.md}]
graduated_by: [Alice]""",
    )
    second = write_note(
        tmp_path,
        "second.md",
        """type: knowledge_note
graduated_from: [{project: Demo, path: cairn/second.md}]""",
    )

    with pytest.raises(SystemExit) as exc:
        MODULE.parse_notes([first, second])

    message = str(exc.value)
    assert "input validation failed" in message
    assert str(first) in message
    assert str(second) in message
