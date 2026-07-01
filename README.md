[English](README.md) | [中文](README.zh-CN.md)

# Project Cairn

**Turn project work into reusable knowledge.**

Project Cairn is an AI-agent skill for Claude Code, Codex, and compatible agents. It does **experience knowledge**: it turns what an AI-collaboration project *did* into reusable knowledge. Decisions, dead ends, solved pitfalls, validated approaches — none of it has to die with the session. It travels to the next project instead.

> Karpathy's [LLM Wiki](https://github.com/karpathy) pattern does **material knowledge**: it turns raw sources you *read* into a wiki. Project Cairn does **experience knowledge**: it turns the pitfalls, research, and hands-on work you *did* into a wiki. Raw-source ingestion is an optional input; distilling lived experience is the main road.

## The problem

Most AI-collaboration projects accumulate project knowledge ad hoc: an `AGENTS.md` here, a `MEMORY.md` there, a pile of debug notes nobody re-reads. Three failure modes show up over and over:

1. **No naming standard.** The same kind of document is called `LEARN.md` in one project and `DEBUG_LOG.md` in the next, so nothing is discoverable across projects.
2. **One file, two incompatible jobs.** A file like `MEMORY.md` ends up being both an append-only daily log *and* a topic-organized knowledge archive — two lifecycles that don't mix, so entries balloon and nothing stays current.
3. **Knowledge doesn't flow.** Experience earned in one project stays trapped in that project. The next project starts from zero.

Project Cairn's answer is a small set of documents, each with exactly one lifecycle, connected by explicit rules for when knowledge moves from a project into a reusable knowledge base — and never the other way around.

## How it works

### Two layers

| Layer | Contains | Lives in | Consumed by |
|---|---|---|---|
| **Project layer** | This project's rules, state, conclusions, cases | root `AGENTS.md` + `cairn/` | read automatically on entering the project |
| **Knowledge-base layer** | Cross-project, reusable domain knowledge | a provider-owned store (Obsidian, Lark/Feishu wiki, Notion, …) | pulled on demand |

Knowledge moves **one way**: project → knowledge base, at the moment it's validated as reusable (not at some fixed project phase). A graduated note becomes the new "current truth" for that topic; the source document in the project is left untouched as a historical record. Pulling knowledge back into a new project is a separate, explicit act — a pointer in `cairn/Cited.md`, never a copy of the body.

```
Project A experience ──graduate──▶ Knowledge base (single current truth) ──pull──▶ Project B's cairn/Cited.md
```

### Highlights

- **Trigger-based, not template-heavy.** A new project only needs `AGENTS.md`. Everything else — topic notes, `ROADMAP.md`, `Reference/`, `Cited.md` — is created only when a real signal shows up: a decision worth recording, a solved pitfall, a goal that outlives one session.
- **One file, one job.** Rules live in `AGENTS.md`, history lives in `cairn/LOG.md`, conclusions live in `cairn/<topic>.md` — no more overloaded `MEMORY.md` trying to be a log and a knowledge base at once.
- **Engineering assets stay out.** Specs and schemas that code depends on live in the code tree, never in `cairn/` — only the knowledge *about* them (why they're shaped that way, what broke building them) is eligible to graduate.
- **Branches don't lose knowledge.** Before an exploration branch is merged, abandoned, or rolled back, a lightweight review salvages anything worth keeping instead of letting it vanish with the branch.

## Providers

Project Cairn graduates knowledge into three verified platforms, each adapted to how that platform actually works rather than forced into one generic shape:

- **Obsidian** — notes land as vault-relative files with an `INDEX.md`, linked with native WikiLinks.
- **Lark / Feishu wiki** — notes become nodes in a wiki space's directory tree, written through the native resource API (the CLI shortcuts reject the coarse scope Project Cairn needs, so the adapter bypasses them).
- **Notion** — notes become rows in a database that doubles as both container and index, with frontmatter mapped straight onto database properties.

Each adapter owns its platform's link format (WikiLink, URL, page mention) and its own quirks (see `references/graduation.md`). Tool-backed providers ship a read-only preflight script (`scripts/lark-preflight.sh`, `scripts/notion-preflight.sh`) that checks install/auth/permissions before any write happens. These `scripts/*.sh` adapters are bash, verified on macOS/Linux — Windows users need WSL or Git Bash; the `scripts/*.py` scripts only need a Python 3 interpreter, no shell required.

## Install

Project Cairn ships as an agent skill. There's no package manager yet — install by placing `skill/project-cairn/` where your agent looks for skills.

**Claude Code** (user-level, as an independent git-tracked skill):

```bash
git clone https://github.com/iBlinkQ/project-cairn.git
cp -R project-cairn/skill/project-cairn ~/.claude/skills/project-cairn
```

**Codex** (user-level direct skill path):

```bash
git clone https://github.com/iBlinkQ/project-cairn.git
cp -R project-cairn/skill/project-cairn ~/.agents/skills/project-cairn
```

`agents/openai.yaml` carries Codex-specific metadata; `SKILL.md` is the entry point every agent reads first.

## Quick start

1. Open the project in Claude Code or Codex and just say something like *"Initialize Project Cairn in this project."* The skill interviews you — project summary, whether `cairn/` is git-tracked, one or more graduation providers, and a history-migration strategy — then freezes the answers into `.cairn/config.yaml`. Already set this up once before? It offers to reuse your usual config instead of asking again.
2. Work normally. `AGENTS.md` is read as project rules on every turn, so day-to-day maintenance (logging progress, updating topic notes) just happens — no separate command needed.
3. When something you learned would help a *different* project, say *"Graduate this to the knowledge base."* The agent proposes candidates, you confirm scope, and it writes into your configured provider(s) and updates the index.
4. Periodically, or when something feels off, say *"Audit the project knowledge."* The agent checks for contradictions, stale conclusions, orphaned notes, missing graduation back-pointers, and assets that leaked into `cairn/`.

## Docs map

| Reference | Use it for |
|---|---|
| `references/init.md` | Initializing or retrofitting Project Cairn in a project |
| `references/maintenance.md` | Recording progress, updating `LOG.md`/`ROADMAP.md`/topic notes |
| `references/graduation.md` | Distilling and writing validated knowledge into a knowledge base |
| `references/consume.md` | Pulling and citing external knowledge into a project |
| `references/audit.md` | Finding drift, contradictions, or missing records |
| `references/frontmatter.md` | Frontmatter fields for project topic notes and knowledge-base notes |
| `references/branch-closure.md` | Salvaging knowledge before closing an exploration branch |

## Relationship to other tools

- **[superpowers](https://github.com/obra/superpowers)-style process skills** (brainstorm → spec → plan → implement) operate at a **process layer** and write to a fixed `docs/superpowers/{specs,plans}/`. Project Cairn is a **knowledge/state layer** on top: a superpowers spec that reaches a stable conclusion is exactly the kind of input that gets a one-line `LOG.md` pointer and a distilled topic note. The two don't compete for the same files — Project Cairn renamed its roadmap file from `PLAN.md` to `ROADMAP.md` specifically to avoid colliding with superpowers' `plans/`.
- **An agent's built-in memory** (e.g. Claude Code's `~/.claude` memory) stores facts about *you* — preferences, cross-project personal context. Project Cairn stores facts about *the project* — decisions, conclusions, cases — as files that live in the repo, are human-readable, survive a tool switch, and can be open-sourced. The two never overlap.

## Contributing

Issues and PRs welcome. Since v0.1 is documentation-first, most contributions are to `SKILL.md`, `references/*.md`, `assets/templates/*`, or the provider adapter scripts in `scripts/`. If you change behavior, explain why in the PR description so the reasoning isn't lost.

## License

[MIT](LICENSE)
