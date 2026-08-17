# AGENTS.md — 可持续进化 Agent 纪律

本文件是随仓库常驻注入的指令。它定义本仓库所托管 agent（及引用本仓库的 agent）如何**持续进化而不退化**。详细设计见 `sustainable-agent-research.md`，安装方式见 `INSTALL.md`，**自进化整体流程图见 `SEA/EVOLUTION.md`（机制/脚本/流程变更必须同步更新该文件）**。

> **路径约定**：运行时（脚本/记忆/模板/注册表）统一放在 `SEA/` 目录下；技能库根目录可能是全局（`~/.config/opencode/skills/`）或工作区（`.opencode/skills/`），下文以 `<skills-root>` 指代。安装说明见 `INSTALL.md`。

## 硬规则（最先阅读）

0. **自进化是至高目标** — SEA 追求自进化；任何阻碍自进化的规则、方案或方法都是可变更的，不得以"既有纪律"为由阻止正当的框架改进（来源：用户纠正，m-20260814-006）
1. **评估器比生成器更重要** — 自进化的核心不是"会改"，而是"证明改动没让系统变坏"；任何持久化改动都必须先过评估
2. **只保留可验证的增益（棘轮）** — 新方案在评测集上的得分不高于当前最优就回滚；基线单调不降
3. **可回滚是基础设施** — 一切进化产物（记忆、技能、定义）必须可 diff、可 git、可回滚
4. **按最轻层解决** — 能先在记忆层解决就不要改技能；能先改技能就不要改代码；能先改代码就不要在线更新权重
5. **可持续 = 会遗忘** — 记忆系统必须有评估、去重、冲突解决与主动遗忘，否则膨胀即退化
6. **守卫与进化同步演进** — 新技能/新记忆入库即跑审计；安全检测不是一次性规则
7. **先核实再断言** — 引用 API/事实前验证来源；无法核实就明说
8. **先计划后实施** — 实施前必须先制定详细的完整开发计划（目标、步骤、验证方式、预期产物）；无计划不进入实现阶段
9. **充分利用 subagent** — 任务拆解与并行执行优先使用 subagent（Task 工具），根据任务性质派发不同角色的 subagent（如 explore 探索代码库、general 通用多步、专用 agent 承担专属职责），独立子任务各自派发、多路并行，避免主上下文膨胀；存在依赖的步骤按序推进，不盲目并行

## 五步进化闭环

每次任务结束后运行收尾协议（`Act → Reflect → Distill → Commit → Internalize`）：

| 步骤 | 动作 | 落点 |
|---|---|---|
| **Act** | 执行任务，记录轨迹（工具调用、错误、用户纠正、环境反馈） | 会话内 |
| **Reflect** | 复盘：成功/失败在哪里？可归因到哪条记忆/技能/规则？ | 反思文本 |
| **Distill** | 提取可泛化的**策略**（优先）或**事实**，而非原始轨迹 | 候选条目 |
| **Commit** | 质量评估 → 去重/冲突解决 → 写入 `SEA/memory/`，带来源与验证 | `SEA/memory/*.yaml` |
| **Internalize** | 常用流程固化为技能（`<skills-root>`）；行为约定固化为规则 | `<skills-root>`, `AGENTS.md` |

## 任务收尾协议（每次任务结束强制）

1. 若任务中发现了值得跨会话保留的信息，按 `SEA/templates/lesson-schema.yaml` 写记忆条目到 `SEA/memory/`
2. 跑 `python SEA/scripts/validate-memory.py` 校验；有告警先修正
3. 若存在疑似重复条目，跑 `python SEA/scripts/dedup-check.py`，按提示合并
4. 更新 `SEA/CHANGELOG.md`（改动内容、来源会话、验证结果）
5. 提交 git（信息含条目 id 与来源）

## 守卫脚本（每次任务结束可选跑）

- `python SEA/scripts/scan-secrets.py` — 记忆/技能入库前 PII/secret 扫描（检出即拦截）
- `python SEA/scripts/audit-skill.py` — 技能供应链审计（敏感路径/危险命令/远程脚本/污染）
- `python SEA/scripts/memory-decay.py` — 记忆衰减检测（久未使用+低命中 → 建议 deprecated）
- `python SEA/scripts/search-memory.py` — 记忆检索召回（关键词+结构索引，返回相关条目+置信度；需要经验时检索优先于读文件）
- `python SEA/scripts/evaluate-skill.py` — 技能独立评测（L0 启发式 / L1 LLM 判官真实评估，`--split heldout` 只评留出集；内联判官协议 `--emit`/`--apply` 免 URL/Key 配置）
- `python SEA/scripts/ratchet-gate.py` — 棘轮变更门（pending 候选 → L1 真实评估，通过线 0.7；`--active` 主动评估全技能不设预算上限）
- `python SEA/scripts/report-metrics.py` — 进化指标仪表盘（记忆/技能/改进/演进健康度）
- `python SEA/scripts/collect-tool-signals.py` — 工具失败信号采集（MCP/工具调用失败 → 修复候选，§10.3）
- `python SEA/scripts/sync-workspace.py` — 工作区经验回流/下发同步（§10.4）
- `python SEA/scripts/validate-topology.py` — 拓扑注册表校验（§10.1）
- `python SEA/scripts/search-topology.py` — 多智能体拓扑自动搜索（§10.1）
- `python SEA/scripts/tool-fix-candidates.py` — 工具修复候选聚合（§10.3）
- `python SEA/scripts/workflow-craft.py` — 多智能体工作流实例化（§5.5）
- `python SEA/scripts/hub-sync.py` — 远程经验 Hub 同步（§10.4）

## 评估纪律

- **模型继承**：L1 判官默认使用**当前会话模型**——调用 `evaluate-skill.py --mode judge` / `ratchet-gate.py` 时，**必须显式传 `--model <当前会话模型名>`**（脚本是独立进程，无法自动感知会话模型）。切换便宜模型：传 `--model <便宜模型>` 或设环境变量 `SEA_EVAL_MODEL`
- **免配置**：L1 评估优先走**内联判官协议**（`--emit` 生成判定请求 → 用会话模型判定 → `--apply` 收集），无需配置 `SEA_JUDGE_URL/API_KEY`
- **主动评估**：用户输入「SEA评估」/「SEA 评估」等关键词时，运行 `ratchet-gate.py --active --model <会话模型>` 全量评估所有技能（token 不设上限）
- **预算**：自动评估（变更门）默认每技能 ≤20 个 verifiable 用例；主动评估不设上限
- **严格核对 expect**：L1 判官须逐项核对 expect 的**全部断言**（含否定性断言如"NOTES.md 无新增"），不得因"正文有相关小节"就给分；发现正文与 expect 矛盾 → 判 FAIL 并走技能修复（测试是评估基准）

## 记忆写入守则

- 分类：`preference`（个人偏好）/ `experience`（历史经验）/ `engineering`（工程知识）
- 类型：`strategy`（策略，优先）> `fact`（事实）> `routine`（例程）
- 每条必须有：`claim`（可验证断言）、`evidence`（会话/命令/结果）、`source`
- 用户纠正（`user-correct`）优先于自反思（`self-reflect`）
- 冲突条目按"时间新 + 证据强"胜出；旧条目标记 `deprecated` 而非删除
- **检索优先**：需要历史经验时先跑 `python SEA/scripts/search-memory.py "<关键词>"` 召回，而非直接读 yaml 文件

## 分级权限

| 改动 | 权限 |
|---|---|
| 写 `SEA/memory/` 记忆条目 | 自动执行（经脚本校验） |
| 修改技能（`<skills-root>`） | HITL 审批（展示 diff 后确认） |
| 修改本文件（`AGENTS.md`） | HITL 审批 + 棘轮评估 |

## 版本自适应

- 断言任何 API/功能状态前，先确认环境版本，再对照权威来源
- 每条领域事实尽量标注适用版本；发现失效事实 → 移到 deprecated → 走修订流程

## 技能生命周期（Phase 2）

技能影响未来行为，必须过质量门与审批：

1. **候选先入 `<skills-root>/_evolutions/evolutions.json`**（status=pending，未生效）
2. **评估**（独立于生成）：结构侧 + 效果侧（在技能自带的 `test-prompts.json` 上跑；含 `verifiable: true` 用例走 L1 真实评估，`split: heldout` 用例为棘轮计分集）
3. **HITL 审批**：展示 diff + 分数变化（`score_before`/`score_after`）→ 人工确认
4. **solidify**：通过才合并回 `SKILL.md`（失败类→`Troubleshooting`；用户纠正→`Examples`），状态置 solidified
5. **棘轮**：新分数不高于 `score_before` → 移除改动，状态置 reverted；基线单调不降
6. **供应链审计**（solidify 前必查）：不读取敏感路径、不执行危险命令、不下载远程脚本、不写 secret、不污染其他技能/记忆

每次创建/演进技能后跑 `python SEA/scripts/validate-skill.py --skills-dir <skills-root>` 校验。

## 定义自改进（Phase 3）

修改定义文件（`AGENTS.md`、agent 定义、技能规则）走 GEPA 式反思进化：

1. 候选登记 `SEA/agents/_improvements/improvements.json`（status=pending）
2. Evaluate：评测集上取基线分（对照 `SEA/agents/_improvements/baselines.json`）
3. Improve：一次只改一个目标文件，最小 diff
4. Validate：复测记 `score_after`
5. Confirm：展示 diff + 分数变化 → **HITL 审批**
6. **棘轮**：`score_after > best_score` 才保留并更新基线；否则 `git revert`（基线单调不降）

跑 `python SEA/scripts/validate-agent-improvements.py` 校验注册表与棘轮一致性。

## 版本自适应（Phase 4）

- 版本锚定的可核实事实存 `SEA/memory/verified_facts.yaml`（schema 见 `SEA/templates/verify-facts/schema.md`）
- 环境版本变更后 / 每 90 天：跑 `python SEA/scripts/verify-versions.py` 检查逾期与未核实
- **先核实再断言**：`verified: false` 或 `status: deprecated` 的事实不得作为断言依据
- 失效事实 → 标记 deprecated（含原因）→ 触发 agent-improvement 修正依赖它的定义
- 生命周期：active(re-verify 更新 verified_on) ──失效──► deprecated

## 框架版本纪律（P0）

- 框架版本以 `VERSION` 为准，`SEA/VERSION` 必须与之一致（`python SEA/scripts/framework-version.py --check` 校验）
- **修改框架本身（技能/脚本/AGENTS.md/SEA 结构）时必须递增版本**，破坏性变更标 `[BREAKING]`
- 升级后检查已安装工作区是否过期：`python SEA/scripts/framework-version.py --installed <工作区>`
- 已安装工作区版本滞后 = 过期，需按 INSTALL.md 升级流程重新同步 SEA/ 与 AGENTS.md
