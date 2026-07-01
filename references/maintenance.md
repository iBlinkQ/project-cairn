# maintenance

Ongoing behavior after meaningful work. Driven by reading project `AGENTS.md` as rules — there is no automatic chat-end hook.

## Rules

- Add a new entry to the top of `cairn/LOG.md` after substantive progress (reverse-chronological, newest first): what happened, what was decided, a pointer to detail. Keep each entry short (≤ ~20 lines).
- Update or create `cairn/<topic>.md` when a stable conclusion, decision, lesson, or reusable pattern appears. Create the topic note from `assets/templates/topic.md`; keep only body sections that have content.
- A solved pitfall goes into the relevant topic note's lesson area, with `contains` gaining `lesson`. If no topic note exists yet, the pitfall triggers creating one — do not start a catch-all `PITFALLS.md`.
- Update `cairn/Cited.md` when knowledge from the configured external knowledge base is used (see `consume.md`).
- Do not put long conclusions into LOG — LOG holds summaries and pointers; conclusions live in topic notes.
- Correct old conclusions in topic notes in place and add a LOG pointer to the revision. Do not silently overwrite.
- Keep engineering assets outside `cairn/`. Only knowledge *about* assets (how they were built, pitfalls, design rationale) may enter `cairn/`.
- When an exploration branch is merged, abandoned, or rolled back, run a branch closure review (see `branch-closure.md`): classify its `cairn/` changes into discard / merge-to-project / graduate / archive-reference so valuable knowledge is not lost with the branch.
- When the project's `language` (in `.cairn/config.yaml`) is not English, write `cairn/LOG.md` and topic-note content per the rules above using the non-English writing rule in `references/init.md` → Documentation language.
