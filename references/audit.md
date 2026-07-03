# audit

Manual or agent-requested checks on the project knowledge layer. Audit is the safety net for records missed during day-to-day work.

## Checks

- LOG entries that are too long or contain conclusions that belong in topic notes.
- Topic notes without useful frontmatter.
- Missing topic notes for repeated decisions or solved problems.
- Contradictions between topic notes and old LOG entries (topic notes win; flag the stale LOG entry).
- Engineering assets mixed into `cairn/` that should move back to the code tree.
- Broken links or stale pointers in `Cited.md`.
- Graduation candidates that have not been reviewed.
- Project topic notes marked `graduation_status: candidate` but not yet graduated or confirmed.
- Project topic notes marked `graduation_status: deferred` or `graduation_status: not_applicable` without enough body context to explain the judgment.
- Knowledge-base notes missing `graduated_from` provenance.
- Project topic notes that have graduated but lack the recommended back-pointer (`graduated_to` / `graduated_at`).
- Project topic notes whose `updated` frontmatter date is newer than their `graduated_at` — the corresponding knowledge-base note may now be stale; suggest re-graduation (see `graduation.md` → Re-graduation), don't auto-trigger it.
- Closed or abandoned exploration branches whose valuable `cairn/` knowledge was never salvaged (should trigger a branch closure review, or a LOG / topic / graduation-candidate follow-up).

## Behavior

Suggest fixes. Do not silently rewrite large bodies of content without user confirmation.

The audit run itself earns one `cairn/LOG.md` entry — a short summary of what was checked and what was found, plus a pointer to the findings, added at the top like any entry. Appending this record is not "rewriting content"; the no-rewrite rule protects existing material, not the log of the audit happening.
