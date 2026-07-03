[English](README.md) | [中文](README.zh-CN.md)

# Project Cairn

**把做过的事情，沉淀成可复用的知识。**

Cairn 是旅人用石头垒起的路标堆——名字本身就是这个 skill 想做的事：把学到的东西留在下一个项目找得到的地方。

Project Cairn 是一个 AI Agent Skill，适配 Claude Code、Codex 及其他兼容 Agent。它做的是**经验知识化**：把 AI 协作项目里"做过的事情"沉淀成可复用的知识。决策、走过的弯路、解决掉的坑、跑通的方案，都不会随会话结束而消失，而是传递给下一个项目。

> [Karpathy](https://github.com/karpathy) 的 LLM Wiki 模式做的是**资料知识化**：把你*读过*的原始资料整理成 wiki。Project Cairn 做的是**经验知识化**：把你*做过*的踩坑、研究和实战整理成 wiki。原始资料解析是可选输入，经验蒸馏才是主航道。

## 要解决的问题

大多数 AI 协作项目沉淀知识的方式是临时拼凑的：这个项目一个 `AGENTS.md`，那个项目一个 `MEMORY.md`，外加一堆没人会再翻的调试笔记。反复出现的三个问题：

1. **命名和形态不统一。** 同一类文档在这个项目叫 `LEARN.md`，在那个项目叫 `DEBUG_LOG.md`，跨项目根本无法互相发现。
2. **一个文件，两种互不兼容的角色。** 像 `MEMORY.md` 这样的文件，往往既是按时间追加的流水日志，又是按主题组织的知识档案——两种生命周期硬凑在一起，条目越写越膨胀，也没有哪部分能保持"当前是对的"。
3. **经验不跨项目流动。** 一个项目里挣来的经验，被困死在那个项目里；下一个项目只能从零开始。

Project Cairn 的解法是一小组文档，每个文档只承担一种生命周期，并用明确的规则规定知识什么时候从项目"流向"可复用的知识库——而且只单向流动，不回流。

## 工作原理

### 两层架构

| 层 | 内容 | 载体 | 消费方式 |
|---|---|---|---|
| **项目层** | 本项目的规则、状态、结论、案例 | 根 `AGENTS.md` + `cairn/` | 进入项目时自动读取 |
| **知识库层** | 跨项目、可复用的领域知识 | provider 拥有的外部存储（Obsidian、飞书/Lark wiki、Notion……） | 按需拉取 |

知识只**单向**流动：项目 → 知识库，触发时机是"知识被验证为可复用的那一刻"，而不是某个固定的项目阶段。一篇知识毕业后，就成为该主题跨项目的新"当前真相"；但项目侧的源文档仍是本项目自己的当前真相，可以随进展继续原地更新——"单向"约束的是知识库笔记不会被项目侧编辑悄悄覆盖，不是源文档从此冻结。已毕业主题有实质新进展时，再走一次毕业、刷新同一篇知识库笔记即可。把知识拉回一个新项目是另一个独立、显式的动作——只在 `cairn/Cited.md` 里挂一个指针，绝不复制正文。

```
项目 A 的经验 ──毕业(graduate)──▶ 知识库（唯一当前真相）──拉取(pull)──▶ 项目 B 的 cairn/Cited.md
```

### 亮点

- **触发式创建，不堆模板。** 新项目只需要一个 `AGENTS.md`。其余的一切——主题笔记、`ROADMAP.md`、`cairn/Reference/`（项目自己持有的外部原始材料，不要跟本 skill 自己的 `references/` 文档目录搞混）、`Cited.md`——只在具体信号出现的那一刻才创建：一个决策值得记、一个坑解决了、出现了一个跨会话的目标。
- **一个文件只干一件事。** 规则在 `AGENTS.md`，时序在 `cairn/LOG.md`，结论在 `cairn/<主题>.md`——不再有 `MEMORY.md` 那种既想当日志又想当知识库的超载文件。
- **工程资产不进系统。** 被代码依赖的规格和 schema 留在代码树里，永远不进 `cairn/`——能进去的只有"关于它的知识"（为什么这么设计、构建过程踩了什么坑）。
- **分支不会带走知识。** 探索分支在合并、放弃或回退之前，会先做一次轻量审查，把值得留的东西收拢下来，而不是让它跟着分支一起消失。

## Provider（毕业目标）

Project Cairn 把知识毕业到三个已验证的平台，每个都贴着该平台本身的特点来适配，而不是强行套一套通用格式：

- **Obsidian** —— 落地为 vault 内相对路径的文件 + `INDEX.md`，笔记间用原生 WikiLink 互链。
- **飞书 / Lark wiki** —— 落地为 wiki 空间目录树里的节点，走原生 resource API 写入（CLI 的 shortcut 命令会拒绝 Project Cairn 需要的粗粒度 scope，所以 adapter 绕开它们）。
- **Notion** —— 落地为一个数据库里的行，这个数据库同时充当容器和索引，frontmatter 直接映射成数据库属性列。

每个 adapter 各自负责自己平台的链接格式（WikiLink、URL、页面提及）和各自的坑（见 `references/graduation.md`）。依赖外部工具的 provider 都自带只读的 preflight 脚本（`scripts/lark-preflight.sh`、`scripts/notion-preflight.sh`），在真正写入前先检测安装/授权/权限是否齐全。这些 `scripts/*.sh` 脚本是 bash 编写的，已在 macOS/Linux 上验证——Windows 用户需要 WSL 或 Git Bash；`scripts/*.py` 脚本只需要 Python 3 解释器，不依赖 shell。

## 安装

Project Cairn 以 Agent Skill 的形式分发。目前还没有包管理器——把这个仓库 clone 到你的 Agent 会读取 skill 的位置即可。前置依赖：`git`；`scripts/*.sh` 需要 `bash`（macOS/Linux 原生支持，Windows 需要 WSL 或 Git Bash）；`scripts/*.py` 只需要 Python 3，不依赖 shell。

**Claude Code**（用户级，作为独立的 git 仓库 skill）：

```bash
git clone https://github.com/iBlinkQ/project-cairn.git ~/.claude/skills/project-cairn
```

**Codex**（用户级 direct skill 路径）：

```bash
git clone https://github.com/iBlinkQ/project-cairn.git ~/.agents/skills/project-cairn
```

无论哪种方式，装好之后 `SKILL.md` 都直接在安装目录的根部（`~/.claude/skills/project-cairn/SKILL.md`，不是再往下嵌一层）——这是每个 Agent 首先读取的入口文件。`agents/openai.yaml` 携带 Codex 专用的元数据。

## 快速开始

1. 在 Claude Code 或 Codex 里打开项目，直接说一句类似*"在这个项目里初始化 Project Cairn"*的话。Skill 会接手，问你项目定位、`cairn/` 是否随 git 提交、一个或多个毕业 provider、历史知识的迁移策略，然后把答案冻结进 `.cairn/config.yaml`。如果你之前已经跑过一次，它会直接问"沿用常用配置？"，不用重新走一遍问答。
2. 正常开展工作。因为 `AGENTS.md` 每轮都会被当作项目规则来读，日常维护（记录进展、更新主题笔记）不需要额外操作。
3. 当你学到的东西对**另一个**项目也有用时，说一句*"把这个毕业到知识库"*。Agent 会提出候选，你确认范围，它写入配置好的 provider 并更新索引。
4. 定期地，或者感觉哪里不对劲的时候，说一句*"审查一下项目知识"*。Agent 会检查矛盾结论、过期结论、孤立笔记、缺失的毕业回指针，以及混入 `cairn/` 的工程资产。

## 文档地图

| Reference | 用途 |
|---|---|
| `references/init.md` | 在项目中初始化或补建 Project Cairn |
| `references/maintenance.md` | 记录进展、更新 `LOG.md` / `ROADMAP.md` / 主题笔记 |
| `references/graduation.md` | 把验证过的知识蒸馏并写入知识库 |
| `references/provider-interface.md` | 每个 provider adapter 脚本必须满足的行为契约 |
| `references/consume.md` | 把外部知识拉取、引用进项目 |
| `references/audit.md` | 找出知识漂移、矛盾或缺失的记录 |
| `references/frontmatter.md` | 项目主题笔记与知识库笔记的 frontmatter 字段规范 |
| `references/branch-closure.md` | 在关闭探索分支前收拢其中的知识 |
| `references/zh-glossary.md` | 用中文写项目文档时的固定中英术语对照 |

## 和其他工具的关系

- **[superpowers](https://github.com/obra/superpowers) 一类的过程型 skill**（brainstorm → spec → plan → implement）工作在**过程层**，产物写死在固定的 `docs/superpowers/{specs,plans}/`。Project Cairn 是叠加在上面的**知识/状态层**：一份 superpowers 的 spec 一旦形成稳定结论，正是那种应该在 `LOG.md` 留一行指针、并蒸馏进主题笔记的输入。两者不会争抢同一批文件——Project Cairn 特意把自己的路线图文件从 `PLAN.md` 改名为 `ROADMAP.md`，就是为了避免和 superpowers 的 `plans/` 撞名。
- **Agent 自带的记忆系统**（例如 Claude Code 的 `~/.claude` 记忆）存的是关于*你*的事实——个人偏好、跨项目的个人上下文。Project Cairn 存的是关于*项目*的事实——决策、结论、案例——以文件形式活在代码仓库里，人可读、能开源、换工具也不会丢。两者不重叠。

## 贡献

欢迎 Issue 和 PR。因为 v0.1 是 documentation-first 的，大多数贡献会落在 `SKILL.md`、`references/*.md`、`assets/templates/*`，或 `scripts/` 里的 provider adapter 脚本。如果你改动了行为，请在 PR 描述里说明原因，别让这段推理过程丢掉。

## License

[MIT](LICENSE)
