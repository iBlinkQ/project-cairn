# Note identity configuration

Read when selecting, resolving, or migrating `type`. `type` is the user's note identity; it does not describe which agent wrote the note or which side of graduation it occupies. Topic notes and newly graduated notes share one identity. Location and `graduated_from` / `graduated_to` distinguish their roles; `contains` still describes content ingredients.

## New project initialization

Explain: "type identifies a note so you and the agent can filter it; Cairn's accumulated project experience shares one identity." Offer `project_insight` (English), `项目经验` (Chinese), and custom, with the first two presented equally. Custom values are trimmed, non-empty, single-line strings. There is no omit-type option.

- A new explicit selection wins over a saved `defaults.note_type`.
- An explicit reuse or skip uses a saved `defaults.note_type` when present.
- Explicit skip with no saved value uses `project_insight`.
- No answer, blank input, and timeout are not skip. Do not persist a choice without an answer; an old user config lacking this field requires this one additional question. In unattended init, require a supplied selection, explicit skip, or reuse of an existing saved value rather than inventing an answer.
- Invalid saved values are errors, not an invitation to fall back silently.

Before persistence, show the resolved value and its source with the other final configuration choices. Freeze it as `cairn.note_type` in the new project's `.cairn/config.yaml`. Offer to save/update `defaults.note_type` in `~/.config/cairn/config.yaml` through the existing confirmation flow, preserving unrelated fields. Subsequent personal-default changes cannot alter the project's frozen choice. It is independent of `language` and is collected even when the graduation provider is deferred.

## Existing project resolution

Read only that project's `.cairn/config.yaml`:

| Project configuration | New topic `type` | New graduation `type` |
|---|---|---|
| Valid `cairn.note_type` present | That string | That same string |
| Field absent (legacy project) | `project_topic` | `knowledge_note` |

A missing field never consults user defaults, never stops ordinary maintenance/graduation, and never causes an automatic configuration edit. A present but invalid value requires correction. Only new initialization or an explicitly confirmed instance upgrade introduces the field.

`scripts/resolve-note-type.py` implements this read-only resolution (Python 3 + PyYAML):

```bash
python3 scripts/resolve-note-type.py --init --selection "项目经验"
python3 scripts/resolve-note-type.py --init --user-config /path/to/user-config.yaml --skip
python3 scripts/resolve-note-type.py --init --user-config /path/to/user-config.yaml --reuse
python3 scripts/resolve-note-type.py --project-config /path/to/project/.cairn/config.yaml
```

It prints `topic_type`, `knowledge_type`, JSON-quoted YAML scalars `topic_type_yaml` / `knowledge_type_yaml`, `source`, and `legacy`. It never writes files. Use the project result during maintenance/graduation; the init mode is exclusively for new initialization or confirmed type selection during upgrade.

## Rendering and provider calls

Replace `{{NOTE_TYPE_YAML}}` in the topic template with `topic_type_yaml`; in new project/user config templates use the selected quoted scalar. The placeholder is a complete YAML string scalar, with no extra quotes around it. Serialization must keep values such as `true`, `null`, `a: b`, `#标签`, and names with quotes as strings.

The workflow reads project configuration and passes `knowledge_type` explicitly using the selected adapter's `--type`; for Notion batch use `--expected-type`, and for database creation use `--type`. Adapters do not discover project directories or inherit personal defaults. Keep their omitted-argument compatibility: Obsidian defaults to `knowledge_note`; Lark defaults to it only when constructing metadata; Notion single omits the property; batch defaults its expected value to `knowledge_note`; database creation retains its legacy options.

Matching identity alone does not mean a note is ready to graduate. Prepare and confirm the material first; batch inputs require non-empty `graduated_from` and `graduated_by` and are all validated before any Notion request. Never relabel an unprepared project original to make it pass.

## Existing notes and upgrade

Routine edits preserve existing `type`. Configuration upgrade and historical-note migration are separate confirmations; retaining old values after choosing a new configuration is valid. For re-graduation, read the target's existing type and show any proposed change before confirmation. If type migration is declined, preserve that target value and pass it explicitly (including as batch expected type; split differently typed batches).

Use the `upgrade.md` entry to locate historical candidates by the configured project knowledge directory, actual provider target and stored graduation/provenance pointers. Show location, old value and proposed value for each note. Do not rewrite every note sharing an old type in the entire knowledge base. Back up confirmed candidates, change only `type` and normally maintained timestamps, and reread them independently. Audit reports the optional upgrade/migration opportunity; untouched legacy values and a declined migration remain valid.
