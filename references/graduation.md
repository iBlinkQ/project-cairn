# graduation

Human-confirmed promotion of validated project knowledge into an external knowledge base. One-directional: project → knowledge base. v0.1 must not silently graduate knowledge.

## Candidate criteria

A graduation candidate must be:

- Verified in the project, not just guessed.
- Reusable outside the current project.
- Abstracted from local implementation details.
- Not an engineering asset itself (assets never graduate; only knowledge about them does).
- Safe to move into the target knowledge base.
- Traceable with `graduated_from`.

## Flow

1. Propose candidates (the Skill may detect them; audit is the backstop).
2. The user confirms before anything is written or prepared.
3. If a project topic has been explicitly judged, optionally record `graduation_status` on the project topic note: `candidate`, `deferred`, or `not_applicable`. Do not add this field to every topic by default.
4. On confirmation, prepare the knowledge-base note with required frontmatter (`graduated_from` mandatory; see `frontmatter.md`), and optionally record `graduated_to` / `graduated_at` back on the project topic note.

## Provider adapter constraints

Write mechanics differ per provider; keep them in each provider's `.cairn/config.yaml` entry, not hardcoded in the flow. Two cross-provider principles learned from real runs:

- **`create_note` is not always a pure write.** Some providers must *resolve the target* (space/folder/node) before creating, and resolution needs read access. A wiki provider's "create node" implicitly reads the space, so a write-only grant is insufficient. Model the read dependency explicitly; don't assume write scope alone lets you create.
- **A provider's CLI conveniences may be stricter than its API.** Prefer the provider's raw/native API for graduation writes when its high-level shortcuts add their own preconditions (e.g. literal scope prechecks) that reject otherwise-valid calls.
- **A provider's official CLI is not automatically the most reliable transport.** A CLI that fetches a remote spec to resolve endpoints, or that ignores `HTTPS_PROXY`, can fail in proxied/CI environments while direct REST against the same API works. Verify the transport in the real environment; be ready to fall back to direct REST (curl) with per-request retry for flaky egress (e.g. random SSL EOFs).

### Lark / Feishu wiki adapter (worked example)

**Step 0 — preflight (run before any write).** `scripts/lark-preflight.sh` is read-only and returns a JSON verdict: `cli_missing` (not installed → give docs link, pause), `not_authed` (run `lark-cli auth login`), `missing_wiki_scope` (open `wiki:wiki` for user identity in the console, then re-auth), or `ok` (safe to graduate). Don't attempt the write loop until it reports `ok`.

Verified path for graduating into a Feishu knowledge base with `lark-cli`, user identity:

- **Scope:** request the coarse `wiki:wiki` (covers read + write). Granular read scopes (`wiki:space:retrieve` / `wiki:space:read` / `wiki:node:read`) may never enter the user token on CLI-style apps (they don't appear on the user consent page); the write-capable `wiki:wiki` does and reliably lands. Diagnostic: if `--as bot` works but `--as user` reports a missing scope, the block is in the user-authorization path, not the app's published permissions.
- **API:** use native resource commands (`wiki spaces get`, `wiki nodes create`, `wiki nodes list`, `wiki spaces get_node`) + `docs +update`/`docs +fetch`. The `wiki +space-list` / `+node-create` shortcuts do strict literal scope prechecks that don't recognize `wiki:wiki` coverage and reject locally.
- **Write loop:** resolve target space (`my_library` or a team `space_id`) → `wiki nodes create` (with `parent_node_token` to build the directory tree) → `docs +update` to write body + frontmatter → `docs +fetch` to verify → append a link into the INDEX/container node. Parent node = directory/index container; child nodes = individual graduated notes.
- **Executable adapter:** `scripts/lark-wiki-graduate.sh` encodes this loop end-to-end (resolve → create → write → read-back verify → optional INDEX link), enforcing the constraints above. Content is piped via stdin to dodge the CLI's cwd-relative `@file` restriction. Run with `--dry-run` to preview the exact native API calls before writing.
  - `scripts/lark-wiki-graduate.sh --title T --content body.md --space-id <id|my_library> [--parent-node-token TOK] [--index-doc OBJ_TOKEN]`

### Notion adapter (worked example)

**Step 0 — preflight (run before any write).** `scripts/notion-preflight.sh --db <DATABASE_ID>` is read-only and returns a JSON verdict: `not_authed` (`NOTION_API_TOKEN` unset/invalid), `db_unshared` (the integration can't see the DB — share it in Notion → ••• → Connections), `db_props_missing` (DB lacks the property columns Cairn maps frontmatter onto), `net_error` (proxy/SSL give-up), or `ok`. Don't write until `ok`.

Verified path for graduating into a Notion knowledge base:

- **Data model = database.** The DB is the knowledge-base container AND the INDEX (its views/properties are the index) — so there is **no `update_index` step** and no INDEX page to append into. Each graduated note is one DB row (page). Frontmatter maps to DB **properties**, not YAML: `type`/`authoring_mode`→Select, `contains`/`tags`→Multi-select, `graduated_from`→Text, `graduated_at`→Date.
- **Transport = direct REST (curl), not the `ntn` CLI.** `ntn` fetches an OpenAPI spec to resolve endpoints, does not honor `HTTPS_PROXY`, and fails `PATCH`/`query` behind a proxy. Direct REST via curl honors the proxy; wrap every request in backoff **retry** to ride out random SSL EOFs.
- **Auth = internal-integration token** in `NOTION_API_TOKEN` (kept in `.env`, referenced by name in config — never stored in `.cairn/config.yaml`). The DB (or its parent page) must be **shared with the integration** — this is the read dependency for `create_note`.
- **Pin `Notion-Version: 2022-06-28`** (classic single-source database; avoids 2025-09-03+ data-source semantics).
- **Write loop:** one graduated note = a single `POST /v1/pages` with `properties` + `children` (body blocks) together — no PATCH needed → read back with `GET /v1/pages/{id}` to verify the title round-trips.
- **`[[wikilinks]]` → real page mentions need a batch two-pass** (create all pages, collect title→id, then write bodies with `mention` blocks). The single-note adapter renders wikilinks as bold title text; use the batch tool when graduating an interlinked set at once.
- **Executable adapters** (all curl/REST + retry, pinned version; `--dry-run` previews):
  - `scripts/notion-init-db.sh --parent-page-id PAGE_ID --title "<knowledge base name>"` — create the KB database with the Cairn property schema under a shared parent page. `--title` is required — it's the database's display name, collected from the user at init time (see `init.md` → provider target naming), never a hardcoded default.
  - `scripts/notion-graduate.sh --db ID --title T --content body.md [--type …] [--contains a,b] [--tags a,b] [--graduated-from TEXT] [--graduated-at YYYY-MM-DD] [--authoring-mode …]` — one note (single POST, no PATCH); wikilinks→bold text.
  - `scripts/notion-graduate-batch.py --db ID --graduated-at DATE --src-dir DIR [--repo-prefix P]` — interlinked set, two-pass so `[[wikilinks]]` become real page mentions; frontmatter→properties; idempotent (skips notes already in the DB). Python (urllib+retry) because the title→id graph is awkward in bash.

## Knowledge-base links

When the target provider supports wiki-style links, add links only when they are useful in context. Do not add a generic "Related" list just to connect notes.

- Add a wiki link when a specific sentence or paragraph depends on, explains, contrasts with, or operationalizes another knowledge note.
- Put the link inside that local context, with surrounding text that makes the reason for the connection clear.
- Do not link merely because two notes share a tag, came from the same project, or were graduated in the same batch.

After graduation the knowledge-base note is the cross-project current truth for that topic and is not rewritten back from the project. The project topic note remains the current truth within this project's local context (and a historical record of how the knowledge was reached); the two layers do not compete.
