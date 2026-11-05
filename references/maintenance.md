# maintenance

Ongoing behavior after meaningful work. Driven by reading project `AGENTS.md` as rules — there is no automatic chat-end hook.

## Completion reply gate

Run this checkpoint before any completion claim, including but not limited to work being complete or implemented, finalized, updated, synchronized, verified or tests passing; a problem being fixed or resolved; a deliverable being ready to use; a statement that work has ended; and semantically equivalent wording. It does not trigger for an explanation, read-only assessment, waiting for confirmation, blocked work, or work without substantive progress.

1. Judge what this work changed or concluded.
2. Maintain only the records whose matrix condition is met.
3. Verify the records that changed.
4. Then send the completion reply.

| Record | Maintain when | Global constraint |
|---|---|---|
| `cairn/LOG.md` | There was substantive progress. | Add a short newest-first summary and pointer; do not put long conclusions in LOG. |
| `cairn/<topic>.md` | A stable conclusion, decision, lesson, or reusable pattern appeared. | Keep the current truth in a focused topic note. |
| `cairn/ROADMAP.md` | Project state changed. | Update it in place only for a changed focus, milestone, or open question. |
| `cairn/Cited.md` | Knowledge from the configured external knowledge base actually shaped the output. | Store pointers only; do not create or update it mechanically. |

An explicit read-only or no-edit request takes priority: do not write Cairn files, and state which candidate records are deferred instead.

The completion reply may proceed only after this self-check passes for records changed by this checkpoint:

- Every `cairn/LOG.md` entry added or modified by this checkpoint is in the correct newest-first position and is ≤20 lines; every local Markdown detail pointer in each such entry resolves to an existing target. Do not scan or block on unrelated historical entries here; broader history inspection belongs to `cairn audit`.
- Every new AI-generated topic has valid YAML frontmatter with `type: project_topic`, `authoring_mode: ai_generated`, and an inline `contains` list whose values match the actual content (for example, `decision` for a decision or `lesson` for a solved pitfall). Do not invent a different schema.
- ROADMAP changed only when project state changed.

If any check fails, fix the record before replying.

## Rules

- Add a new entry to the top of `cairn/LOG.md` after substantive progress (reverse-chronological, newest first): what happened, what was decided, a pointer to detail. Keep each entry short (≤ ~20 lines).
- Update or create `cairn/<topic>.md` when a stable conclusion, decision, lesson, or reusable pattern appears. Create new topics with `type: project_topic` from `assets/templates/topic.md` and keep only the body sections that have content. Routine edits preserve an existing topic's type, including historical Chinese or custom values. Old type configuration fields are ignored; never infer migration permission from a skill update (see `upgrade.md`).
- When identifiable humans substantively form a topic's knowledge, add them to the topic frontmatter `contributors` list; ask rather than invent an identity when it cannot be resolved safely.
- A topic may include `### Origin quote` (translated per `zh-glossary.md`) inside its formation/background section only when a short direct excerpt materially restores the scene and is safe to retain. Include speaker/approved role, date, and context; omit the subsection entirely when no suitable quote exists.
- Preserve direct wording. Mark limited redaction explicitly (`[redacted]` / `[已脱敏]`); if safe use requires substantial rewriting, write a scene summary instead of labeling it a quote.
- A solved pitfall goes into the relevant topic note's lesson area, with `contains` gaining `lesson`. If no topic note exists yet, the pitfall triggers creating one — do not start a catch-all `PITFALLS.md`.
- Update `cairn/Cited.md` when knowledge from the configured external knowledge base is used (see `consume.md`).
- Do not put long conclusions into LOG — LOG holds summaries and pointers; conclusions live in topic notes.
- Correct old conclusions in topic notes in place and add a LOG pointer to the revision. Do not silently overwrite.
- Keep engineering assets outside `cairn/`. Only knowledge *about* assets (how they were built, pitfalls, design rationale) may enter `cairn/`.
- When an exploration branch is merged, abandoned, or rolled back, run a branch closure review (see `branch-closure.md`): classify its `cairn/` changes into discard / merge-to-project / graduate / archive-reference so valuable knowledge is not lost with the branch.
- When the project's `language` (in `.cairn/config.yaml`) is not English, write `cairn/LOG.md` and topic-note content per the rules above using the non-English writing rule in `references/init.md` → Documentation language.

## Topic distillation sources

Two-layer flow stays unchanged in initialized projects: **process documents → distill into project topic notes (`cairn/<topic>.md`) → graduate to the knowledge base**. Graduation sources in an initialized project are always project topic notes, never raw process documents directly.

### 1. Sources that feed topic notes

- **Working dialogue and operations** during collaboration turns.
- **Project process documents** (judged by content, not by whether a human or AI wrote them): proposals and implementation docs, requirement docs, review records, meeting minutes, retrospectives, design specs and implementation plans generated by skills such as Superpowers or grill-with-docs, and in-project notes recording project experience, guidelines, or conventions.
  - Extract only stable, validated conclusions into `cairn/<topic>.md` and link to the source process document(s) in the topic note.
  - Leave process documents in place without modifying their body; do **not** require process documents to carry a `type` field (`project_insight` is reserved for graduated knowledge-base notes). How much AI participated is recorded later via `authoring_mode` when a note graduates.
  - When the user asks to organize existing project experience in an ongoing initialized project (e.g. "整理已有经验"), scan the project's process documents to update `cairn/ROADMAP.md` and distill still-valid conclusions into `cairn/<topic>.md`, keeping original files untouched.

### 2. External reference material vs. process documents (basic check)

- **External raw material in `cairn/Reference/`** (client/colleague-supplied documents, historical files, third-party material kept verbatim) is append-only input and verification basis, **not** a direct source of topic conclusions. Any judgment derived from it must be verified in project practice before entering a topic note.
- **Basic check for misplaced external material**: users sometimes place third-party material outside `cairn/Reference/` (for example in the project root). Before distilling, check every candidate document and treat it as external reference material — used only as verification basis, not distilled as project conclusions — if it matches any of these signals:
  - `type` is a web clipping (`网页摘录` / `clipping`) or frontmatter/body carries an external source URL;
  - the body consists mainly of verbatim excerpts, reposts, or transcripts;
  - authorship or provenance is attributed to an external person, client, or organization;
  - it is a third-party Word/PDF original or its direct Markdown conversion.
  Suggest moving such files to `cairn/Reference/`, but **never move them automatically**; ask the user when provenance is ambiguous.

### 3. Distilling from experience and convention process notes

- **Preserve key wording, judgments, and data**: do not rewrite validated judgments or drop concrete metrics. If the source note contains a suggestion the author has not yet verified, keep and label it explicitly as an unverified suggestion (e.g. `建议，待作者确认是否写入规范` / suggestion pending author confirmation).
- **Supply background and verification context for conventions**: convention/guideline notes often list bare rules without background or rationale. When distilling into a topic note, state *why* the rule exists and *in which project practice* it was verified; if the source does not say, **ask the author** rather than inventing a rationale.
- **Filter out purely local formatting conventions**: distill only items that carry a verified lesson or rationale that holds across projects. Project-local formatting conventions (such as punctuation preferences or figure-numbering syntax specific to one manuscript/repo) stay in the process document and are not distilled into reusable topic notes.
