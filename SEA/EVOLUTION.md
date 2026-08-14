# EVOLUTION.md — SEA 自进化整体流程

> 本文件是框架自进化机制的**权威总览**。任何机制/脚本/流程变更必须同步更新本文件，保持与代码一致。

当前版本：`0.2.2`（见 `VERSION`）

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
             │ 记忆自动/技能 │   │ score_after >│ │ 0.2.2 → 升级 │ │ 可回滚留痕    │
             │ 定义/工具人工 │   │ best 才保留  │ │ sync 工作区   │ │              │
             └──────────────┘   └──────────────┘ └──────────────┘ └──────────────┘
                                             │
                                             ▼
                             ┌──────────────────────────────────┐
                             │         群体智能 (P4/§10.4)       │
                             │ sync-workspace（工作区↔仓库）     │
                             │ hub-sync（远程 git Hub 共享）     │
                             └──────────────────────────────────┘
```

## 各层演化路径细分

```
┌─ 记忆层 ──────────────────────────────────────────────┐
│  经验 → Distill → 记忆条目(m-xxx)                      │
│  → validate-memory (schema) → dedup-check (去重)       │
│  → scan-secrets (PII 门)                              │
│  → memory-decay (久未用→deprecated 遗忘)              │
└───────────────────────────────────────────────────────┘

┌─ 技能层 ──────────────────────────────────────────────┐
│  信号 → evolutions.json (pending)                     │
│  → evaluate-skill (score_before) → audit-skill (供应链)│
│  → HITL 审批 → solidify (回 SKILL.md) → 棘轮           │
│  tool-craft / agent-craft / workflow-craft 皆此路径    │
└───────────────────────────────────────────────────────┘

┌─ 定义层 ──────────────────────────────────────────────┐
│  用户纠正 → improvements.json (pending)                │
│  → 最小 diff → validate-agent-improvements            │
│  → HITL → 棘轮 (score_after>best 保留/回滚)           │
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
- **可回滚**：全部产物 git 化，CHANGELOG 留痕
- **按最轻层**：记忆 → 技能 → 代码 → 参数（当前未到参数层）
- **HITL 分权**：记忆自动、技能/定义/工具人工审批
- **元规则（硬规则第 0 条）**：自进化是至高目标，阻碍自进化的规则/方案/方法可变更

## 脚本索引

| 脚本 | 层 | 作用 |
|---|---|---|
| validate-memory.py | 记忆 | schema 校验 |
| dedup-check.py | 记忆 | 近重复检测 |
| memory-decay.py | 记忆 | 衰减/遗忘候选 |
| validate-skill.py | 技能 | frontmatter + evolutions schema |
| evaluate-skill.py | 横切 | 确定性打分 / 拓扑 / LLM 判官 |
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
