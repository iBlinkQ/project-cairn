# graduation

Human-confirmed promotion of validated project knowledge into an external knowledge base. One-directional: project → knowledge base. Never silently graduate knowledge.

## Candidate criteria

A graduation candidate must be:

- Verified in the project, not just guessed.
- Reusable outside the current project.
- Abstracted from local implementation details.
- Not an engineering asset itself (assets never graduate; only knowledge about them does).
- Safe to move into the target knowledge base.
- Traceable with `graduated_from`.

## Deferred provider (connect at first graduation)

`graduation.provider: none` in `.cairn/config.yaml` means connecting a knowledge base was deferred at init (`init.md` → Deferred graduation provider). Candidate detection and confirmation (Flow steps 1–3) work unchanged; only the provider write waits. When a confirmed candidate is ready:

1. Collect provider decisions #3–#4 (`~/.config/cairn/config.yaml` offers one-key reuse).
2. Run the provider's preflight (`init.md` → Tool-backed provider preflight) until `ok`.
3. Freeze the result into `.cairn/config.yaml`, replacing `provider: none`.
4. Update `AGENTS.md` to the connected form per `init.md`.
5. Continue the Flow below and fold "connected provider X" into the graduation's `cairn/LOG.md` entry (or log the connection alone if aborted).

If the user still declines, stop: the candidate stays recorded (optionally `graduation_status: candidate`) and audit surfaces it.

## Flow

In an initialized Cairn project, graduation sources are always project topic notes (`cairn/<topic>.md`). When asked what qualifies for graduation or to graduate a project process document (proposal, spec, plan, review, meeting record, retrospective, or in-project experience/convention note), first distill its validated conclusions into `cairn/<topic>.md` (`type: project_topic`) per `maintenance.md` → Topic distillation sources (or point to the existing topic note), then graduate from that topic note (`graduated_from` points to the topic note and may also list the original process document).

1. Propose topic-note candidates (audit is the backstop).
2. Wait for user confirmation before writing anything.
3. Optionally set `graduation_status` (`candidate`, `deferred`, or `not_applicable`) on an explicitly judged topic note; do not pre-stamp every topic.
4. After confirmation and before the provider write:
   1. Resolve the confirmer per `frontmatter.md`; write `graduated_by` on both sides.
   2. Merge and de-duplicate `contributors` across source topics.
   3. Re-check any Origin quote for the target audience; carry a safe quote into **Background** or sanitize/omit on both copies.
   4. Treat quote absence as valid; never add a placeholder section.
5. Prepare the knowledge-base note per `frontmatter.md` (`type: project_insight` for new notes, `graduated_from`, non-empty `graduated_by`), and record `graduated_by` plus `graduated_to` / `graduated_at` on the source topic. Check the provider's tag inventory (Obsidian: `obsidian tags counts`) and reuse tags before coining near-synonyms (`provider-interface.md` → Read side).
6. Record one `cairn/LOG.md` entry — summary plus pointer to the knowledge-base note (`audit.md` → Behavior).

## One-shot graduation (without project init)

For finished, archived, or lightweight folders without Cairn initialized, distill and graduate in one step without creating `.cairn/`, `cairn/`, `AGENTS.md`, or intermediate topic files:

1. **Knowledge-base location**: read `~/.config/cairn/config.yaml`. If absent, ask once for provider, target, and index, and suggest saving them to `~/.config/cairn/config.yaml`.
2. **Two ways to start**:
   - **Specify note(s)**: the user names one or more retrospective, summary, or experience notes directly.
   - **Scan a folder**: the user asks to scan a folder (including archived projects), e.g. “看看这个文件夹里有什么经验可以毕业” or “看看这个文件夹里有什么可以毕业”. Exclude external reference materials via `maintenance.md`'s basic check; skip already-graduated notes (carrying `graduated_to` or already in `INDEX.md`); judge remaining notes by `Candidate criteria` and `maintenance.md`'s experience/convention rules; merge duplicate conclusions across notes into one candidate (listing all contributing files in `graduated_from`); list candidates and wait for confirmation before writing.
3. **Write and source back-pointers**: after confirmation and preflight `ok`, write the knowledge-base note directly per `Note body structure` (**Background** then **Conclusion**) and `frontmatter.md` (`type: project_insight`, non-empty `graduated_by`, `authoring_mode`), preserving original wording and data.
   - `graduated_from` points directly to the source note(s) (`project`: folder/project name, `path`: folder-relative path).
   - Add only `graduated_to` and `graduated_at` to the source note's frontmatter, leaving its body and any existing `type` untouched (included in pre-graduation confirmation, not asked separately).
   - When the folder has a project record note (e.g. CLIP `【PRO】<project>.md` or `type: project_log`), add `毕业：[[<knowledge-base note title>]]` (or `Graduated: [[<knowledge-base note title>]]`) under today's date (`[[YYYY-MM-DD]]`) in its progress section so the daily note lists it automatically.

## Note body structure

The knowledge-base note body must open with **Background**, then **Conclusion**, in that order:

1. **Background** (required, first) — what problem it solved, how it was encountered, and why it was needed, so readers can judge applicability.
2. **Conclusion** (required, second) — the core claim or solution itself.
3. **Further sections** (as needed) — evidence (reasoning, verified cases, comparisons, counter-examples), a practice guide (procedures, safe patterns, decision tests), or applicability and boundaries.

Do not open the body with the conclusion; frontmatter `summary` serves quick scanning. Chinese heading names are in `zh-glossary.md`.

### Origin quote

When a safe short direct excerpt materially restores the scene, place it inside **Background**:

```markdown
### Origin quote

> "Exact excerpt."
>
> — identity, YYYY-MM-DD, short context
```

Preserve direct wording and apply `maintenance.md` redaction/scene-summary rules. Omit the subsection when no suitable quote exists.

## Re-graduation (updating an already-graduated topic)

Read and preserve the target's type, including `knowledge_note`, Chinese, or custom values. A type migration needs separate location/old/new confirmation; declining it still permits the confirmed content update (`frontmatter.md`, `upgrade.md`).

A graduated project topic remains local current truth and can evolve in place; “one-directional” means project edits never silently overwrite the knowledge-base note. When a topic with `graduated_to` gains substantive new knowledge, propose re-graduation via the adapter's update mode: target the stored identifier, update `graduated_at`, and union the confirmer into `graduated_by` on both sides without duplicates before calling the adapter. LOG records the event; audit flags lagging notes.

## Provider adapter constraints

Every adapter script must satisfy `references/provider-interface.md`. Cross-provider transport and API-surface principles live there; each provider reference below adds that provider's consequences.

Write mechanics differ per provider; keep them in each provider's `.cairn/config.yaml` entry, not hardcoded in the flow.

Provider mechanics live in one reference per provider. Before any write, read that reference, run its Step 0 preflight, and proceed only on `status: ok`.

| Provider type | Required provider reference | Required Step 0 preflight | Write adapter |
|---|---|---|---|
| `obsidian` | [`graduation/obsidian.md`](graduation/obsidian.md) | `scripts/obsidian-preflight.sh` | `scripts/obsidian-graduate.sh` |
| `lark-wiki` | [`graduation/lark-wiki.md`](graduation/lark-wiki.md) | `scripts/lark-preflight.sh` | `scripts/lark-wiki-graduate.sh` |
| `notion` | [`graduation/notion.md`](graduation/notion.md) | `scripts/notion-preflight.sh` | `scripts/notion-graduate.sh` |

The write-adapter column pins each provider's primary entry; the provider reference lists its complete script set. If the configured provider is `none`, use the Deferred provider flow above. If the provider is unsupported, its reference is unread, or the named preflight has not returned `ok`, stop before any write and report the error. An absent preflight result is a blocking state; a dry-run does not substitute for this gate before a real write.

### Lark / Feishu wiki adapter (worked example)

Moved to [`graduation/lark-wiki.md`](graduation/lark-wiki.md).

### Notion adapter (worked example)

Moved to [`graduation/notion.md`](graduation/notion.md).

### Obsidian adapter (worked example)

Moved to [`graduation/obsidian.md`](graduation/obsidian.md).

## Knowledge-base links

When the target provider supports wiki-style links, add links only when useful in context; do not add a generic "Related" list.

- Add a wiki link when a sentence depends on, explains, contrasts with, or operationalizes another note, with surrounding text making the connection clear.
- Do not link merely because two notes share a tag, project, or batch.

After graduation the knowledge-base note is cross-project current truth; the project topic note stays local current truth.
