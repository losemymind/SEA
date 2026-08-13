---
name: agent-improvement
description: 优化 Agent 定义文件（.md 规则/提示）。GEPA 式反思进化：在评测集上评估当前定义 → 针对性补丁 → 复测 → HITL 审批 → 棘轮保留或回滚。用于让 agent 的定义随实践演化而不退化。
---

# Agent 定义自改进

## 何时使用
- 某条定义/规则反复导致错误或低效（可归因到定义文件）
- 领域知识或实践变化，需要修订规则
- 收到用户纠正，值得固化进定义

## 流程（严格按序）

### 1. 登记候选
在 `SEA/agents/_improvements/improvements.json` 追加 `status: pending` 条目（target / kind / signal / patch 描述）。跑 `python SEA/scripts/validate-agent-improvements.py` 校验。

### 2. Evaluate（基线）
- 结构侧：检查目标文件结构完整性
- 效果侧：在目标对应的 `test-prompts.json` 上跑，记 `score_before`
- 读取 `SEA/agents/_improvements/baselines.json` 中该文件的 `best_score`；若 `score_before` 更低，以 `score_before` 为棘轮参考

### 3. Improve（补丁）
- **一次只改一个目标文件**
- 生成最小 diff（不改无关内容）
- 更新 `improvements.json` 条目（补丁描述 + `score_before`）

### 4. Validate（复测）
- 在评测集上复测，记 `score_after`

### 5. Confirm（HITL 审批）
- 展示 diff + `score_before` → `score_after` 变化
- 人工 approve → 继续；reject → 状态置 `rejected`，回滚改动

### 6. Keep or Revert（棘轮）
- `score_after > best_score` → 保留（git commit），更新 `baselines.json`，状态置 `approved`
- 否则 → `git revert`，状态置 `reverted`
- 基线单调不降

## 验收
- 通过 `validate-agent-improvements.py`
- 状态机一致：pending → approved / rejected / reverted
- CHANGELOG 已更新，git 干净

## 反例（不要这样）
- 一次改多个文件
- 无评测集分数就保留改动（违背棘轮）
- 跳过 HITL 审批直接 solidify
