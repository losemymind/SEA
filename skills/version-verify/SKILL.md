---
name: version-verify
description: 版本与环境自适应。定期核对 SEA/memory/verified_facts.yaml 中的可核实事实：检查条目 schema 是否完整、标记过期（未在 N 天内 re-verify）与废弃（status=deprecated）、识别 verified=false 却仍被引用的风险。用于让 agent 的领域知识跟随环境版本漂移而不退化。
---

# 版本核实与自适应

## 何时使用
- 环境版本变更后（如项目切换 UE 小版本）
- 周期性维护（默认每 90 天或每次大版本发布）
- 收到"某 API/事实已过期"的信号时

## 流程

### 1. 检查注册表健康
跑 `python SEA/scripts/verify-versions.py`：
- schema 完整（缺 source / verified_on 视为风险）
- 列出去逾期（`--stale N`，默认 90 天未 re-verify）

### 2. re-verify 逾期/未核实的条目
对每条 `verified: false` 或逾期的 active 条目：
1. 确认目标版本（`.uproject` 的 EngineAssociation / 项目配置）
2. 对照权威来源（官方文档 / 引擎源码 / What's New 页），**先核实再断言**
3. 核实通过 → `verified: true` + 更新 `verified_on` + 记录 source
4. 核实失效 → `status: deprecated` + `deprecated_on` + `deprecated_reason`（如 API 变更、功能移除）

### 3. 废弃检测
`status: deprecated` 的条目：
- 不再作为断言依据
- 触发修正流程：把变更写入 `SEA/agents/_improvements/improvements.json`（走 agent-improvement），修正依赖该事实的定义/规则

### 4. 留痕
- 更新 `verified_on` / `status` 后跑 `verify-versions.py` 确认通过
- 更新 CHANGELOG

## 验收
- `verify-versions.py` 通过（schema 完整、无风险引用）
- 所有 active 条目都在 re-verify 周期内
- deprecated 条目已触发修正或明确标记

## 反例（不要这样）
- 引用 `verified: false` 或 `status: deprecated` 的事实
- 不核对来源就改 `verified_on`
- 版本变更后不触发 re-verify
