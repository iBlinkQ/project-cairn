# Chinese Terminology Glossary

Fixed English → Chinese term mapping for Project Cairn's own vocabulary. Use this when writing project docs (`AGENTS.md`, `LOG.md`, `ROADMAP.md`, topic notes) in Chinese, so wording stays consistent across independently-initialized projects instead of drifting per translator.

| English | Chinese |
|---|---|
| cairn (the name / imagery) | 路标石堆（不用"玛尼堆"） |
| graduate / graduation | 经验入库（动词可简称“入库”） |
| graduation candidate | 待入库经验 |
| graduation-symmetry test | 入库条件判断 |
| graduation-worthy | 符合入库条件 |
| reusable kernel | 可复用内核 |
| adoption bar | 采用门槛 |
| negative adoption | 排除法式采用 |
| topic note | 知识专题文档 |
| process document | 过程文档 |
| one-shot graduation | 直接整理入库 |
| re-graduation | 更新已入库经验 |
| knowledge base / project experience library | 知识库 / 项目经验库 |
| audit / project audit | 检查项目经验 |
| knowledge-base audit | 检查经验库 |
| contributor | 贡献者 |
| origin quote | 原话引述 |
| scene summary | 场景摘要 |
| current truth | 当前真相 |
| distill | 沉淀 |
| knowledge distillation | 知识沉淀 |
| conflict arbitration | 冲突仲裁 |
| cascading defaults | 分级默认值 |
| provider | provider（不译） |
| deferred provider / defer connecting | 暂缓对接 |
| roadmap | 路线图 |
| milestone | 里程碑 |
| open question | 开放问题 |
| branch closure review | 分支关闭复盘 |
| Current Conclusions (heading) | 当前结论 |
| Background (heading) | 背景 |
| Conclusion (heading) | 结论 |
| Evidence (heading) | 论据 |
| Practice Guide (heading) | 实践指南 |
| Decision Log (heading) | 决策记录 |
| Experience (heading) | 经验 |
| Lessons (heading) | 教训 |
| Open Questions (heading) | 开放问题 |

This table only covers vocabulary this skill itself uses. It is not a general-purpose translation glossary.


## Graduation wording and compatibility (2026-11-09)

“经验入库” means distilling validated, cross-project reusable experience into a knowledge-base note after human confirmation, with provenance. It does not mean copying arbitrary files or merely registering an existing note in an index. Keep the candidate criteria and write gates in `graduation.md` unchanged.

Use the new Chinese terms in current instructions, generated project rules, UI copy and new records. In prose, explain the graduation-symmetry test as “本次工作产生或依赖的结论符合入库条件时，先查知识库”; both produced and depended-on conclusions still count.

Recognize legacy “知识毕业”“毕业”“一次性毕业”“再次毕业”“重新毕业” requests as aliases for the same flows. They confer no extra write authorization: propose candidates and wait for human confirmation as before. Prefer “看看这个文件夹里，有哪些经验值得存进知识库” as a new example prompt.

Keep English names, paths, configuration keys, script arguments and frontmatter fields (`graduate`, `graduation`, `graduation_status`, `graduated_from`, `graduated_to`, `graduated_at`, `graduated_by`) unchanged. Existing note types and stored provider identifiers also stay valid. Preserve historical LOG entries, dated plans, original quotations and existing filenames; update live wording without rewriting history or breaking links.


## Audit wording, aliases and scope (2026-11-10)

Use “检查项目经验” as the main project-audit action and timeline label. Put “定期或按需” in the trigger description. For a standalone knowledge-base audit, use “检查经验库” (also “检查项目经验库”).

Recognize “检查知识文档”“检查主题文档” and legacy “给项目知识做个体检”“定期体检”“项目经验库体检” / “体检” as audit requests when context indicates project knowledge or its experience library. Match the intended action, not a fixed trigger-word list; an unrelated use of “检查” is not enough.

Resolve the target from the user's named file, document kind, folder and context. A request naming one topic note checks that note; a request naming a document kind stays within that kind. A general project request checks relevant topic notes, LOG and ROADMAP together. Read linked context only as needed to assess a finding; do not expand a scoped request into a whole-project or external-library audit. Findings list missing experience, contradictions, outdated conclusions and broken links, with concrete locations and suggested fixes. See `audit.md` for the report-before-repair and log rules.

Keep English `audit`, paths, schemas, configuration keys and historical records unchanged. Aliases change neither scope nor write authorization; checking is not automatic maintenance, graduation or provider connection.
