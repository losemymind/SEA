# AGENTS.md — 可持续进化 Agent 纪律

本文件是随仓库常驻注入的指令。它定义本仓库所托管 agent（及引用本仓库的 agent）如何**持续进化而不退化**。详细设计见 `sustainable-agent-research.md`。

## 硬规则（最先阅读）

1. **评估器比生成器更重要** — 自进化的核心不是"会改"，而是"证明改动没让系统变坏"；任何持久化改动都必须先过评估
2. **只保留可验证的增益（棘轮）** — 新方案在评测集上的得分不高于当前最优就回滚；基线单调不降
3. **可回滚是基础设施** — 一切进化产物（记忆、技能、定义）必须可 diff、可 git、可回滚
4. **按最轻层解决** — 能先在记忆层解决就不要改技能；能先改技能就不要改代码；能先改代码就不要在线更新权重
5. **可持续 = 会遗忘** — 记忆系统必须有评估、去重、冲突解决与主动遗忘，否则膨胀即退化
6. **守卫与进化同步演进** — 新技能/新记忆入库即跑审计；安全检测不是一次性规则
7. **先核实再断言** — 引用 API/事实前验证来源；无法核实就明说

## 五步进化闭环

每次任务结束后运行收尾协议（`Act → Reflect → Distill → Commit → Internalize`）：

| 步骤 | 动作 | 落点 |
|---|---|---|
| **Act** | 执行任务，记录轨迹（工具调用、错误、用户纠正、环境反馈） | 会话内 |
| **Reflect** | 复盘：成功/失败在哪里？可归因到哪条记忆/技能/规则？ | 反思文本 |
| **Distill** | 提取可泛化的**策略**（优先）或**事实**，而非原始轨迹 | 候选条目 |
| **Commit** | 质量评估 → 去重/冲突解决 → 写入 `memory/`，带来源与验证 | `memory/*.yaml` |
| **Internalize** | 常用流程固化为技能（`skills/`）；行为约定固化为规则 | `skills/`, `AGENTS.md` |

## 任务收尾协议（每次任务结束强制）

1. 若任务中发现了值得跨会话保留的信息，按 `templates/lesson-schema.yaml` 写记忆条目到 `memory/`
2. 跑 `python scripts/validate-memory.py` 校验；有告警先修正
3. 若存在疑似重复条目，跑 `python scripts/dedup-check.py`，按提示合并
4. 更新 `CHANGELOG.md`（改动内容、来源会话、验证结果）
5. 提交 git（信息含条目 id 与来源）

## 记忆写入守则

- 分类：`preference`（个人偏好）/ `experience`（历史经验）/ `engineering`（工程知识）
- 类型：`strategy`（策略，优先）> `fact`（事实）> `routine`（例程）
- 每条必须有：`claim`（可验证断言）、`evidence`（会话/命令/结果）、`source`
- 用户纠正（`user-correct`）优先于自反思（`self-reflect`）
- 冲突条目按"时间新 + 证据强"胜出；旧条目标记 `deprecated` 而非删除

## 分级权限

| 改动 | 权限 |
|---|---|
| 写 `memory/` 记忆条目 | 自动执行（经脚本校验） |
| 修改 `skills/` 技能 | HITL 审批（展示 diff 后确认） |
| 修改本文件（`AGENTS.md`） | HITL 审批 + 棘轮评估 |

## 版本自适应

- 断言任何 API/功能状态前，先确认环境版本，再对照权威来源
- 每条领域事实尽量标注适用版本；发现失效事实 → 移到 deprecated → 走修订流程

## 技能生命周期（Phase 2）

技能影响未来行为，必须过质量门与审批：

1. **候选先入 `skills/_evolutions/evolutions.json`**（status=pending，未生效）
2. **评估**（独立于生成）：结构侧 + 效果侧（在技能自带的 `test-prompts.json` 上跑）
3. **HITL 审批**：展示 diff + 分数变化（`score_before`/`score_after`）→ 人工确认
4. **solidify**：通过才合并回 `SKILL.md`（失败类→`Troubleshooting`；用户纠正→`Examples`），状态置 solidified
5. **棘轮**：新分数不高于 `score_before` → 移除改动，状态置 reverted；基线单调不降
6. **供应链审计**（solidify 前必查）：不读取敏感路径、不执行危险命令、不下载远程脚本、不写 secret、不污染其他技能/记忆

每次创建/演进技能后跑 `python scripts/validate-skill.py` 校验。
