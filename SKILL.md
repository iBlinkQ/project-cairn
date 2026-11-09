---
name: project-cairn
description: Standardize how an AI-collaboration project turns work into reusable knowledge. Use when initializing or retrofitting Project Cairn, recording progress, distilling process documents into topic notes, maintaining AGENTS/CLAUDE/cairn docs, auditing project knowledge or a project experience knowledge base, pulling/citing external knowledge, or graduating validated experience (including one-shot graduation without init) into a knowledge base.
---

# Project Cairn

Project Cairn gives AI-collaboration projects a durable way to keep and reuse what they learn while doing real work. The **Skill** supplies the method, **AGENTS.md** carries always-read project rules, and **`.cairn/config.yaml`** stores machine-readable configuration.

This Skill is documentation-first: instructions, templates, references, and provider adapters. It has no CLI, MCP server, background hook, chat-end trigger, automatic provider write, or automatic history migration. Routine maintenance happens during normal work because `AGENTS.md` carries the rules. Provider writes require human confirmation.

## Routing

Load only the reference your task needs:

- `references/init.md` — initialize, retrofit, bootstrap, or set up Project Cairn in a project.
- `references/consume.md` — pull, cite, reuse, or apply external knowledge from the configured knowledge base.
- `references/maintenance.md` — record progress, update LOG/ROADMAP, distill conclusions from dialogue or project process documents into topic notes (e.g. "整理已有经验"), or apply Cairn rules after work.
- `references/audit.md` — inspect, audit, or find missing project knowledge records; or run a knowledge-base audit (`项目经验库体检`, no project init) to register unindexed manual notes and check frontmatter/body structure.
- `references/upgrade.md` — upgrade an initialized project instance to the current skill spec, or check instance drift.
- `references/graduation.md` — graduate knowledge, judge readiness, or run one-shot graduation without init (`经验入库` / `直接整理入库`; legacy `毕业` / `一次性毕业`, e.g. “看看这个文件夹里，有哪些经验值得存进知识库”); provider writes also read the selected `references/graduation/<provider>.md`.
- `references/frontmatter.md` — create or review Cairn topic notes or knowledge-base notes.
- `references/branch-closure.md` — review, close, abandon, or roll back an exploration branch and salvage its `cairn/` knowledge.
- `references/zh-glossary.md` — writing project docs in Chinese; fixed English↔Chinese terminology mapping.

Frontmatter describes triggers, not workflow.

## Templates

`assets/templates/` holds `AGENTS.md`, `CLAUDE.md`, `config.yaml`, `user-config.yaml`, `LOG.md`, `ROADMAP.md`, `topic.md`, and `Cited.md`. `init` scaffolds `AGENTS.md`, `CLAUDE.md`, `.cairn/config.yaml`, `cairn/LOG.md`, and optional `cairn/ROADMAP.md`, and can seed `~/.config/cairn/config.yaml` from `user-config.yaml`. `topic.md`, `Cited.md`, and `Reference/` are trigger-created. Templates use `{{PLACEHOLDER}}` tokens; never hardcode a provider or path.

## Boundaries

- No background hook or chat-end trigger is assumed.
- Day-to-day maintenance happens because `AGENTS.md` is read as project rules.
- Audit is the safety net for missed records.
- Graduation is candidate detection plus human confirmation.
- Historical migration is optional and separate from init.
- `scripts/*.sh` use bash (macOS/Linux; Windows needs WSL/Git Bash). `scripts/*.py` use Python 3; `notion-graduate-batch.py` also needs PyYAML.
