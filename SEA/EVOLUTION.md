# EVOLUTION.md — SEA 自进化整体流程

> 本文件是框架自进化机制的**权威总览**。任何机制/脚本/流程变更必须同步更新本文件，保持与代码一致。

当前版本：`0.3.9`（见 `VERSION`）

## 总览流程图

```
                        ┌─────────────────────────────────────────────┐
                        │               信号源（Act 阶段）              │
                        │  工具结果 │ 用户纠正 │ 评测指标 │ 环境反馈      │
                        └──────┬──────────────────┬──────────────────┘
                               ▼                  ▼
                   ┌───────────────────────────────────────────────────┐
                   │            五步进化闭环（每次任务）                 │
                   │  Act → Reflect → Distill → Commit → Internalize   │
                   └──────┬──────────────┬──────────────┬──────────────┘
                          ▼              ▼              ▼
                  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐
                  │ 记忆层 (P1) │ │ 技能层 (P2) │ │ 定义层 (P3)          │
                  │ memory/     │ │ skills/     │ │ AGENTS.md +          │
                  └──────┬──────┘ └──────┬──────┘ │ agents/_improvements│
                         │               │        └──────────┬──────────┘
                         │               │                   ▼
                         │               │           ┌──────────────┐
                         │               │           │ 拓扑层 (§10.1)│
                         │               │           │ topology.json│
                         │               │           └──────┬───────┘
                         ▼               ▼                   ▼
                   ┌─────────────────────────────────────────────────────┐
                   │           守卫与评估（横切，所有层必经）             │
                   │  validate-* │ evaluate-skill │ scan-secrets │        │
                   │  audit-skill │ memory-decay │ framework-version     │
                   └──────────┬────────────────────────────────┬─────────┘
                              │                                │
                    ┌─────────┴──────────┐          ┌─────────┴──────────┐
                    ▼                    ▼          ▼                    ▼
             ┌──────────────┐   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
             │ HITL 审批     │   │ 棘轮（ratchet）│ │ 版本递增      │ │ CHANGELOG+git │
             │ 记忆自动/技能 │   │ L1 真实分≥0.7 │ │ 0.3.0 → 升级 │ │ 可回滚留痕    │
             │ 定义/工具人工 │   │ 才保留，否则回滚│ │ sync 工作区   │ │              │
             └──────────────┘   └──────────────┘ └──────────────┘ └──────────────┘
                                              │
                                              ▼
                              ┌──────────────────────────────────┐
                              │         群体智能 (P4/§10.4)       │
                              │ sync-workspace（工作区↔仓库）     │
                              │ hub-sync（远程 git Hub 共享）     │
                              └──────────────────────────────────┘
```

> **评估触发（选项 B 变更门）**：棘轮只在存在 pending 候选时触发 L1 真实评估
> （`ratchet-gate.py` → `evaluate-skill --mode judge --split heldout`）；无候选不评估。

## 各层演化路径细分

```
┌─ 记忆层 ──────────────────────────────────────────────┐
│  经验 → Distill → 记忆条目(m-xxx)                      │
│  → validate-memory (schema) → dedup-check (去重)       │
│  → scan-secrets (PII 门)                              │
│  → search-memory (检索召回，需要经验时优先)           │
│  → memory-decay (久未用→deprecated 遗忘)              │
└───────────────────────────────────────────────────────┘

┌─ 技能层 ──────────────────────────────────────────────┐
│  信号 → evolutions.json (pending)                     │
│  → ratchet-gate (变更门触发 L1 真实评估，通过线 0.7)  │
│  → audit-skill (供应链) → HITL 审批 → solidify → 棘轮  │
│  tool-craft / agent-craft / workflow-craft 皆此路径    │
└───────────────────────────────────────────────────────┘

┌─ 定义层 ──────────────────────────────────────────────┐
│  用户纠正 → improvements.json (pending)                │
│  → 最小 diff → validate-agent-improvements            │
│  → HITL → 棘轮 (L1 真实分≥0.7 保留/回滚)              │
└───────────────────────────────────────────────────────┘

┌─ 拓扑层 (§10.1) ─────────────────────────────────────┐
│  agent 池 → search-topology (生成候选→评估→棘轮→变异) │
│  → validate-topology (schema+边完整性)                │
└───────────────────────────────────────────────────────┘

┌─ 工具层 (§10.3) ─────────────────────────────────────┐
│  调用失败 → collect-tool-signals → tool-fix-candidates│
│  (3+ 信号→broken) → --promote 候选 → HITL → 修复      │
└───────────────────────────────────────────────────────┘

┌─ 版本/群体 (P0/P4/§10.4) ────────────────────────────┐
│  框架变更→VERSION 递增→framework-version --check      │
│  → --installed 查工作区过期→sync-workspace 同步       │
│  → hub-sync 推送远程 Hub（审计门先行）                │
└───────────────────────────────────────────────────────┘
```

## 治理横切原则

- **评估器 > 生成器**：一切持久化改动先过 `evaluate-*`/`validate-*`
- **棘轮**：`score_after > best_score` 才保留，基线单调不降（improvements.json + baselines.json + evolutions.json + topology.json 各自持有）
- **评估触发 = 变更门（选项 B）**：只有 evolutions/improvements 存在 pending 候选需要裁决时才触发 L1 真实评估（`ratchet-gate.py`）；无候选不评估，token 与价值对齐
- **L1 真实评估**：对 `verifiable: true` 的 heldout 用例做真实判定（`evaluate-skill.py --mode judge --split heldout`），通过线 0.7；**内联判官协议**（`--emit`/`--apply`）让 agent 用当前会话模型判定，免 URL/Key 配置
- **主动评估**：用户输入「SEA评估」关键词 → `ratchet-gate.py --active` 全量评估（token 不设上限）
- **预算**：自动评估（变更门）默认每技能 ≤20 个 verifiable 用例；主动评估不设上限
- **模型继承**：L1 判官默认当前会话模型（调用时显式传 `--model`）；`SEA_EVAL_MODEL` 环境变量可切换便宜模型
- **可回滚**：全部产物 git 化，CHANGELOG 留痕
- **按最轻层**：记忆 → 技能 → 代码 → 参数（当前未到参数层）
- **HITL 分权**：记忆自动、技能/定义/工具人工审批（评估可信后重大变更才介入）
- **元规则（硬规则第 0 条）**：自进化是至高目标，阻碍自进化的规则/方案/方法可变更
- **先计划后实施（硬规则第 8 条）**：实施前先制定详细的完整开发计划（目标/步骤/验证/产物），无计划不实现
- **充分利用 subagent（硬规则第 9 条）**：拆解与并行优先 Task 派发，按任务性质选择不同角色 subagent（explore/general/专用 agent），避免主上下文膨胀；存在依赖的步骤按序推进，不盲目并行

## 脚本索引

| 脚本 | 层 | 作用 |
|---|---|---|
| validate-memory.py | 记忆 | schema 校验 |
| dedup-check.py | 记忆 | 近重复检测 |
| memory-decay.py | 记忆 | 衰减/遗忘候选 |
| search-memory.py | 记忆 | 检索召回（关键词+结构索引，返回条目+置信度） |
| validate-skill.py | 技能 | frontmatter + evolutions schema |
| evaluate-skill.py | 横切 | L0 启发式 / L1 LLM 判官真实评估（内联协议 --emit/--apply，--split/--budget/--model） |
| ratchet-gate.py | 横切 | 棘轮变更门（pending→L1 评估，通过线 0.7）+ 主动评估（--active 全技能无上限） |
| audit-skill.py | 横切 | 供应链审计 |
| scan-secrets.py | 横切 | PII/secret 扫描 |
| validate-agent-improvements.py | 定义 | 改进注册表 + 棘轮一致性 |
| validate-topology.py | 拓扑 | 拓扑注册表校验 |
| search-topology.py | 拓扑 | 拓扑自动搜索 |
| collect-tool-signals.py | 工具 | 失败信号采集 |
| tool-fix-candidates.py | 工具 | 修复候选聚合 |
| workflow-craft.py | 工作流 | 多智能体工作流实例化 |
| sync-workspace.py | 群体 | 工作区↔仓库双向同步 |
| hub-sync.py | 群体 | 远程 git Hub 同步 |
| verify-versions.py | 版本 | 事实 re-verify 健康检查 |
| framework-version.py | 版本 | 框架版本一致性/过期检测 |
| report-metrics.py | 横切 | 进化指标仪表盘 |

## 版本演化记录

| 版本 | 日期 | 内容 |
|---|---|---|
| 0.1.0 | 2026-08-13 | P0-P4 基础：记忆/技能/定义/版本 |
| 0.1.1 | 2026-08-14 | agent-definition 模板 model 字段说明 |
| 0.1.2 | 2026-08-14 | AGENTS.md 硬规则第 0 条元规则 |
| 0.1.3 | 2026-08-14 | 评估器/守卫/遗忘/仪表盘 5 脚本 |
| 0.2.0 | 2026-08-14 | 工具层/群体/拓扑基础设施（§10.1/10.3/10.4） |
| 0.2.1 | 2026-08-14 | 拓扑搜索闭环（search/validate-topology） |
| 0.2.2 | 2026-08-14 | 工具修复闭环/工作流实例化/LLM 判官/远程 Hub |
| 0.2.3 | 2026-08-14 | EVOLUTION.md 整体流程图文档 |
| 0.3.0 | 2026-08-14 | 评估器真话化：L1 真实评估（verifiable/split）+ ratchet-gate 变更门 |
| 0.3.1 | 2026-08-14 | 模型继承+主动评估：内联判官协议（免配置）、SEA评估 关键词、budget 分级 |
| 0.3.2 | 2026-08-14 | 技能修复：agent-craft/task-retrospective/tool-craft 补拒绝路径（L1 评估驱动） |
| 0.3.3 | 2026-08-14 | 记忆检索：search-memory.py 补齐"只写不检"短板 |
| 0.3.4 | 2026-08-14 | 修复 ratchet-gate/report-metrics 的 --skills-dir 自动探测 |
| 0.3.5 | 2026-08-14 | 修复 evolutions 注册表路径（跟随解析后的技能库根目录） |
| 0.3.6 | 2026-08-14 | agent-definition 模板补 permission 字段（只读默认 + bash 按需） |
| 0.3.7 | 2026-08-14 | task-retrospective 修复回归（NOTES.md 冲突）+ 评估纪律「严格核对 expect」 |
| 0.3.8 | 2026-08-17 | 版本术语统一：顶层 VERSION → 仓库 VERSION |
| 0.3.9 | 2026-08-17 | 硬规则新增第 8、9 条：先计划后实施 + 充分利用 subagent |
