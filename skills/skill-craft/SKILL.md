---
name: skill-craft
description: 创建或演进一个技能资产。把可复用工作流固化为 SKILL.md（含 frontmatter、流程、验收、反例），或把技能库根目录下 _evolutions/evolutions.json 中的候选经评估+审批后 solidify 回对应 SKILL.md。用于扩充技能库。
---

# 技能创建与演进

## 何时使用
- 发现一个会重复出现的工作流，值得固化为技能
- `_evolutions/evolutions.json` 有候选条目需要评估/审批/solidify
- 某技能需要修复失效说明（FIX）、派生变体（DERIVED）或抽取新流程（CAPTURED）

## 创建新技能（CAPTURED）

1. 复制 `SEA/templates/skill-template/SKILL.md` 到技能库 `skills/<kebab-name>/`（技能库根目录 = 安装位置，全局为 `~/.config/opencode/skills/`，工作区为 `.opencode/skills/`）
2. 填 frontmatter：
   - `name`：kebab-case
   - `description`：写清「何时触发 + 做什么 + 产出什么」，能让模型按描述自动匹配
3. 写正文：何时使用 / 流程 / 输入输出 / 约束 / 反例
4. 需要评测集的加 `test-prompts.json`（见 `SEA/templates/test-prompts.json`）
5. 跑 `python SEA/scripts/validate-skill.py --skills-dir <技能库根目录>` 校验

## 演进既有技能

### 候选先入 `_evolutions/evolutions.json`
在技能库根目录的 `_evolutions/evolutions.json` 追加条目（id / skill / kind / signal / proposal / status=pending / created）。

### 评估（独立于生成）
- 结构侧：SKILL.md 结构完整、描述可匹配
- 效果侧：在 `test-prompts.json` 上跑，对比分数（`score_before` / `score_after`）

### HITL 审批
- 展示 diff + 分数变化 → 人工确认（approve/reject）
- 通过 → `status: solidified` + `solidified_at`
- 驳回 → `status: rejected`

### solidify 合并规则
- 失败类信号 → 合并进 `Troubleshooting` 小节
- 用户纠正 → 整理进 `Examples` 小节
- 保留谱系信息（FIX / DERIVED / CAPTURED）在 evolutions.json 中

### 棘轮与回滚
- 新分数不高于 `score_before` → 从 SKILL.md 移除改动，`status: reverted`
- 基线单调不降

## 供应链审计（solidify 前必查）
- 不读取敏感路径 / 不执行危险命令 / 不下载远程脚本
- 不把 secret 写入输出 / 不污染其他技能或记忆

## 验收
- 通过 `validate-skill.py`
- evolutions.json 状态一致（pending→solidified/rejected/reverted）
- 已更新 CHANGELOG 与 git
