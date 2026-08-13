# Agent 定义自改进工作流（Phase 3）

目标：让 Agent 实践后**自动修订自己的定义/技能/规则文件**，且只保留可验证的增益（棘轮）。依据设计文档第 4 章与 GEPA（arXiv:2507.19457）。

## 工作流总览（GEPA 式反思进化）

```
采样轨迹（推理、工具调用、工具输出）
  → 自然语言反思：诊断问题
  → 提出针对性的定义/规则补丁
  → 在评测集上验证补丁
  → 把互补教训合入 Pareto 前沿
  → 棘轮：新总分 > 当前最优才保留，否则回滚
```

## 输入

- **目标文件**：Agent 定义文件（如 `.opencode/agent/*.md`）或本仓库 `AGENTS.md`
- **评测集**：领域 `test-prompts.json`（见 `SEA/templates/test-prompts.json`）
- **当前基线**：目标文件当前评测分（存 `SEA/agents/_improvements/`，见下）

## 流程步骤

1. **Evaluate**：对目标文件做结构分析 + 在评测集上跑效果，得当前分（基线）
2. **Improve**：找出得分最低的维度，**一次只改一个目标文件**，生成一轮针对性补丁（写 diff）
3. **Validate**：在评测集上复测新版本，记录 `score_after`
4. **Confirm**：展示 diff 与分数变化 → **HITL 审批**（approve/reject）
5. **Keep or Revert**：`score_after > score_before` 才保留（git commit）；否则 `git revert`（棘轮，基线单调不降）

## 候选改进注册表

候选改进记录在 `SEA/agents/_improvements/improvements.json`（schema 见该文件内的 `_doc`）。每次改进必须先登记为 `pending`，再走评估/审批/棘轮。

## 分级权限

| 改动 | 权限 |
|---|---|
| 写 `SEA/memory/` 记忆 | 自动执行（脚本校验） |
| 修改技能/定义文件 | **HITL 审批 + 棘轮**（展示 diff + 分数对比） |

## 供应链审计（修改定义前必查）
- 补丁不引入敏感路径读取 / 危险命令 / secret 写入
- 补丁不污染其他技能或记忆
