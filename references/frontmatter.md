# frontmatter

Defines project-side and knowledge-base-side frontmatter.

## Project topic note — recommended fields

- `type`
- `status`
- `summary`
- `tags`
- `contains`
- `created`
- `updated`
- `graduated_to` (added at graduation time, not pre-stamped)
- `graduated_at` (added at graduation time, not pre-stamped)
- `graduation_status` (optional; only add after a graduation-readiness judgment)
- `related`
- `authoring_mode`

## Knowledge-base note — required fields (v0.1)

- `type`
- `summary`
- `contains`
- `tags`
- `graduated_from`
- `authoring_mode`

`graduated_from` is required on the knowledge-base side. Project-side `graduated_to` is recommended but not mandatory. Applicability, version/time context, last-verification time, and source backlinks should appear in the note body if not promoted to frontmatter in v0.1.

### `graduated_from` shape

`graduated_from` is a **list of `{project, path}` entries**, not a scalar — verified against notes already graduated into the Obsidian knowledge base, several with more than one entry (a note distilled from more than one source topic/file):

```yaml
graduated_from:
  - project: "Project Cairn"
    path: "/absolute/or/vault-relative/source/path.md"
  - project: "Project Cairn"
    path: "/another/source/file.md"
```

Every provider that writes structured frontmatter (as opposed to leaving frontmatter for the caller to hand-embed, e.g. Lark) should use this shape, not a single string. `scripts/obsidian-graduate.sh` builds it from repeatable `--graduated-from "<project>|<path>"` flags.

## Enum values

- `type` (OKF-aligned concept-object kind):
  - v0.1-produced: `project_topic` (project side), `knowledge_note` (knowledge-base side).
  - forward-looking, not auto-created by v0.1 init/maintenance: `reference`, `playbook`, `decision_record`, `log_index`.
- `status`: `active`, `superseded`, `archived`, `needs_review`.
- `contains` (controlled, multi-value): any of `decision`, `experience`, `lesson`, `procedure`, `reference`, `open_question`.
- `graduation_status` (optional): `candidate`, `deferred`, `not_applicable`.

## Field semantics

- `type` answers "what kind of knowledge object is this?" — a single concept-object kind.
- `contains` answers "what kinds of knowledge ingredients are inside?" — multi-value content composition. A single topic note can hold both experience and lessons, so never use `type: experience/lesson`; represent mixed content with `contains`.
- `tags` answers "which topics, domains, projects, or technologies should this be found under?" — open, multi-value retrieval labels; they do not drive rule decisions.
- `graduation_status` records an explicit graduation-readiness judgment when one has been made. Do not pre-stamp `not_reviewed`; absence means no graduation judgment has been recorded. Use `candidate` when the topic appears reusable and ready for confirmation, `deferred` when it may become reusable after more validation or abstraction, and `not_applicable` when the topic has been reviewed and should not graduate as a note. Keep the reason in the body when it matters.
- `authoring_mode`: `ai_generated` | `human_written` | `ai_assisted`. Records how the note was written, to separate AI-generated, human-written, and human-AI notes in the knowledge base. It does not encode trust, review status, or ownership. Project Cairn auto-generated topic notes default to `ai_generated`.
