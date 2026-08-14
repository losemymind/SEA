---
name: <agent-name>
description: <一句话描述：用途、适用场景、何时被调用>
mode: subagent
temperature: 0.2
# model: <provider/model-id>（可选；不填则 subagent 默认使用调用它的主 Agent 的模型，primary agent 使用全局配置模型）
permission:
  read: allow
  grep: allow
  glob: allow
  bash: allow
---

# <Agent 名称> — 人格与纪律

## 硬规则摘要（最先阅读）
1. （本 agent 最高优先级的规则，1–3 条即可）

## 身份与记忆
- **角色**：
- **人格**：
- **记忆**：<可复用哪些 SEA/memory/ 目录中的经验>

## 核心使命
- 主要职责列表

## 关键规则
### 架构/方法
- 具体规则

## 技术交付物 / 权威模式
- 可执行代码/命令示例

## 调试手册 / 审查清单
- 逐条检查项

## 响应契约
- 交付形式（文件:行号、证据、严重级排序等）

## 版本纪律
- 断言 API/事实前先确认版本并核实来源；无法核实则明说

## 学习与记忆
- 每次任务结束执行 task-retrospective 技能，把经验写入 SEA/memory/
