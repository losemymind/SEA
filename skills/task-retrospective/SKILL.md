---
name: task-retrospective
description: 任务收尾反思与经验沉淀。每次完成任务后调用：复盘本次成败、蒸馏可泛化的策略/事实、评估质量、写入记忆库（SEA/memory/lessons.yaml / preferences.yaml）、跑校验脚本并更新 CHANGELOG。用于把一次性工作转化为可跨会话复用的经验。
---

# 任务收尾反思与经验沉淀

## 何时使用
- 完成一个可能有长期价值的任务后（排错、实现、调研、评审）
- 发现值得跨会话保留的信息（踩坑、用户纠正、已验证事实、用户偏好）时

## 不沉淀（跳过路径）
以下情况**不写入任何新记忆条目**（避免无效沉淀）：
- 纯查询/信息检索：任务只是回答文档问题，无新信息产生
- 无泛化价值：本次经验是一次性、不可复用于未来任务
- 内容已存在：反思出的断言与既有记忆条目重复（应更新 hits 而非新建）
- 跳过时不写入任何文件（含 NOTES.md），保持记忆库与 NOTES 干净（纯查询零写入）

## 流程

### 1. Reflect — 复盘
回答三个问题：
1. 本次成功/失败在哪里？（具体到动作与结果）
2. 可归因到哪条既有记忆/技能/规则？先跑 `python SEA/scripts/search-memory.py "<主题>"` 检索，看相关条目是否已有
3. 有没有"下次再遇到同类问题会希望知道"的东西？

### 2. Distill — 蒸馏
把反思变成**可验证的断言**，遵循优先级：
- `strategy`（策略："这类问题先做 X 再验 Y"）> `fact`（事实）> `routine`（例程）
- 成功经验尽量带失败对比（`contrast`），形成对比信号
- 用户纠正（`user-correct`）优先于自反思（`self-reflect`）

### 3. Commit — 提交
1. 按 `SEA/templates/lesson-schema.yaml` 写入对应 yaml：
   - 偏好 → `SEA/memory/preferences.yaml`
   - 经验/工程知识 → `SEA/memory/lessons.yaml`
2. 跑 `python SEA/scripts/validate-memory.py`，有告警先修正
3. 跑 `python SEA/scripts/dedup-check.py`，疑似重复则与既有条目合并（保留证据更强、时间更新的）
4. 更新 `SEA/CHANGELOG.md`（条目 id、来源、验证结果）

### 3.5 工具信号（可选，§10.3）
- 若本次任务中 MCP/自定义工具调用失败、缺失、返回结构损坏或行为异常：
  `python SEA/scripts/collect-tool-signals.py <tool> --type <type> --detail "<说明>"`
- 同工具累计 3+ 条 pending → 触发工具修复候选流程（登记待修工具清单）

### 4. Internalize — 内化（可选）
- 若该流程会重复出现 → 固化为技能（复制 `SEA/templates/skill-template/` 新建）
- 若是常适用的行为约定 → 向 AGENTS.md 提出修订（需 HITL 审批）

## 验收
- 所有新条目通过 `validate-memory.py`
- 无未合并的疑似重复
- CHANGELOG 已更新
- 未引入 PII / 密钥

## 反例（不要这样）
- 把原始对话轨迹整段存入记忆（应存蒸馏后的断言）
- 跳过校验直接提交
- 只记成功不记失败对比
