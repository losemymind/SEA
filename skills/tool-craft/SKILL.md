---
name: tool-craft
description: 工具修复与工具资产生命周期管理。当 SEA/tools/_registry/tool-signals.json 中某工具达阈值（同工具 3+ 条 pending 信号）时，生成修复候选并走 HITL 审批；也可登记新工具、标记修复完成。用于工具层进化（§10.3）。
---

# 工具修复与资产生命周期

## 何时使用
- `tool-fix-candidates.py` 报告某工具达到修复阈值（3+ 条 pending 信号）
- MCP/自定义工具损坏、缺失、行为异常，需要登记与修复
- 新工具接入，需要登记到工具注册表

## 拒绝修复（门槛门）
**未达阈值不修复**（避免噪音修复），继续采集信号：
- 某工具 pending 信号 < 3 条（`tool-fix-candidates.py` 判定为 degraded 而非 broken）
- 只有单次偶发失败，无可归因模式
- 修复前先确认阈值：`python SEA/scripts/tool-fix-candidates.py` 查看聚合状态，达 broken 才 `--promote`
- 说明不修理由（信号不足），提示继续采集而非动手改 MCP 配置

## 流程（严格按序）

### 1. 聚合信号
跑 `python SEA/scripts/tool-fix-candidates.py` 查看各工具 pending 信号聚合与健康状态（degraded / broken）。

### 2. 生成修复候选
达阈值的工具跑 `python SEA/scripts/tool-fix-candidates.py --promote <工具名>`，候选写入 `SEA/tools/_registry/_candidates/<工具名>.json`。

### 3. HITL 审批
展示候选（信号列表 + 建议修复）→ 人工确认：
- approve → 执行修复（改 MCP 配置 / 换实现 / 更新定义）
- reject → 标记 `wonfix`，不修

### 4. 修复与回滚
- 修复完成 → 信号状态置 `fixed`，工具注册表状态置 `active`
- 修复后复测确认无复发
- 修复无效 → 回滚改动，信号置回 pending 或标记 wonfix

### 5. 登记与留痕
- 新工具登记：写入 `SEA/tools/_registry/tools.json`（name/kind/status/description）
- 更新 `SEA/CHANGELOG.md` 与 git

## 供应链审计（修复前必查）
- 修复不改动非本工具文件 / 不引入远程脚本 / 不写 secret
- 修复后的工具定义过 `scan-secrets.py` 与 `audit-skill.py`

## 验收
- 工具注册表状态与信号一致（broken → 已修复 → active）
- 候选文件已处理（approved/rejected/wonfix）
- CHANGELOG 更新，git 干净

## 反例（不要这样）
- 无信号聚合就凭空修工具
- 跳过 HITL 审批直接改 MCP 配置
- 修复后不复测
