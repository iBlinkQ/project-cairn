# audit

Manual or agent-requested checks on the project knowledge layer. Audit is the safety net for records missed during day-to-day work.

## Requests and scope

Chinese main action: **检查项目经验**. Accept **检查知识文档**, **检查主题文档** and legacy “体检” expressions as contextual aliases (`zh-glossary.md`), not as a requirement to use exact keywords. A knowledge-base-folder request uses the standalone flow below (**检查经验库** / **检查项目经验库**, legacy **项目经验库体检**).

- An explicitly named file or document kind limits the audit to that target; do not scan the whole project, run unrelated instance-drift checks or inspect an external knowledge base merely because an audit alias was used. Read linked context only as needed to assess a specific finding.
- A general project request checks relevant topic notes, LOG and ROADMAP, plus applicable items below. Use the explicitly named folder and context to distinguish the project layer from the experience library; do not infer the target only from the chat's working directory.
- Report missing experience, contradictions, outdated conclusions and broken links with locations, evidence and proposed fixes. Do not invent verification or silently promote an uncertain judgment to fact.
- Checking does not authorize repairs, index registration, file moves, note creation, project initialization, provider connection or graduation. Present changes for confirmation unless the user has already explicitly authorized those changes; an explicit read-only/no-edit request also forbids writing the audit log.

## Checks

Historical `knowledge_note`, Chinese, and custom note types remain valid. Old `cairn.note_type` / `defaults.note_type` fields are ignored, not invalid configuration. Report optional cleanup or migration per `upgrade.md`; do not block maintenance or graduation, rewrite old notes, or ask a new type-selection question.

- LOG entries that are too long or contain conclusions that belong in topic notes.
- Topic notes without useful frontmatter.
- Missing topic notes for repeated decisions or solved problems.
- Project process documents (proposals, implementation docs, requirement docs, review records, meeting minutes, retrospectives, Superpowers/grill-with-docs specs and plans, or in-project experience and convention notes — excluding external reference materials per `maintenance.md`) that hold stable, verified conclusions not yet distilled into any `cairn/<topic>.md` topic note.
- Contradictions between topic notes and old LOG entries (topic notes win; flag the stale LOG entry).
- Engineering assets mixed into `cairn/` that should move back to the code tree.
- Broken links or stale pointers in `Cited.md`.
- Graduation candidates that have not been reviewed.
- A deferred-provider project (`graduation.provider: none` in `.cairn/config.yaml`) holding confirmed graduation candidates — surface that connecting a knowledge base is pending (`graduation.md` → Deferred provider). Deferral itself is a valid state, not a defect; flag only when candidates are actually waiting.
- Project topic notes marked `graduation_status: candidate` but not yet graduated or confirmed.
- Project topic notes marked `graduation_status: deferred` or `graduation_status: not_applicable` without enough body context to explain the judgment.
- Cairn-graduated knowledge-base notes missing `graduated_from` provenance (manually written notes placed directly in the knowledge base may omit `graduated_from` and `graduated_by`; do not flag them).
- A new graduation missing a non-empty `graduated_by` list on either the project or knowledge-base side.
- A touched team topic whose safely identifiable substantive human contributors are missing from `contributors`.
- An empty Origin quote heading, or a direct quote without speaker/approved role, date, and context attribution.
- Potentially risky quote content. Flag it only as a prompt for human review; never issue an automatic safety verdict.
- Do not flag untouched legacy notes solely for lacking `contributors` or `graduated_by`: they remain valid and are backfilled only when touched or re-graduated.
- Project topic notes that have graduated but lack the recommended back-pointer (`graduated_to` / `graduated_at`).
- Project topic notes whose `updated` frontmatter date is newer than their `graduated_at` — the corresponding knowledge-base note may now be stale; suggest re-graduation (see `graduation.md` → Re-graduation), don't auto-trigger it.
- Closed or abandoned exploration branches whose valuable `cairn/` knowledge was never salvaged (should trigger a branch closure review, or a LOG / topic / graduation-candidate follow-up).
- Instance drift against the current skill spec: read `skill_spec_date` from `.cairn/config.yaml` and run the Detect step of every `references/upgrade.md` changelog entry newer than it (missing field = run the full changelog). Report drifted items with each entry's fix guidance and safety level; fixing them is the upgrade flow in `upgrade.md`, not audit's job.

## Behavior

List findings and suggest fixes first. Do not modify existing content, register index entries, move or delete files until the user confirms the concrete changes, unless those changes were already explicitly authorized. A request to check alone is not repair authorization.

Except for an explicit read-only/no-edit request, a project audit run itself earns one `cairn/LOG.md` entry — a short summary of what was checked and what was found, plus a pointer to the findings, added at the top like any entry. Appending this record is not "rewriting content"; the no-rewrite rule protects existing material, not the log of the audit happening.

## Knowledge-base audit (no project init required)

A standalone check on the project experience knowledge base itself (`检查经验库`; alias `检查项目经验库`, legacy `项目经验库体检`). It runs directly against the knowledge-base folder (located via user-level `~/.config/cairn/config.yaml` or a user-specified folder/vault) and **neither reads nor requires any project `.cairn/config.yaml` or `cairn/` directory**.

- **Provider support**:
  - **Obsidian**: supported. Use `scripts/obsidian-graduate.sh --index-only --vault "<vault>" --title "<Title>" --index "<folder>/INDEX.md" [--target "<folder>"] [--summary "<summary>"]` (or direct idempotent `[[Title]]` append when operating on an isolated local test directory) to backfill unindexed notes after confirmation (or prior explicit authorization), without rewriting note files.
  - **Notion / Lark wiki**: report **not supported yet** (`暂不支持`) — Notion uses the database itself as the index with no separate `INDEX.md`, and Lark wiki nodes do not round-trip parseable YAML frontmatter or support index-only registration in `lark-wiki-graduate.sh`.
- **What to do on the knowledge-base folder**:
  1. **Check `INDEX.md` registration (propose first)**: list knowledge-base notes in the requested folder that are not linked in `INDEX.md`. After confirmation (or prior explicit authorization to register them), add idempotent `[[Title]] — summary` entries. Checking alone must not write the index.
  2. **Check frontmatter and body structure (propose only, confirm before editing)**: list any note missing `type` (expected `project_insight`, or valid historical values) or `summary`, or whose body does not open with **Background** (`## 背景` / `## Background`) before **Conclusion** (`## 结论` / `## Conclusion`). Present concrete edit suggestions and wait for user confirmation before modifying any note file.
  3. **Respect manually written notes**: notes written manually and placed directly in the knowledge base may legitimately omit `graduated_from` and `graduated_by`. Do **not** flag missing `graduated_from` or `graduated_by` on manual notes, and never fabricate a confirmer (`graduated_by`) or source (`graduated_from`).
  4. **No knowledge-base log**: do not create a `LOG.md` inside the knowledge base. Manually written notes carry their creation date (and are surfaced automatically by the daily note in CLIP setups).
