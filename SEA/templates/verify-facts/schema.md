# 版本可核实事实注册表 schema（Phase 4）

目标：领域事实随外部版本漂移（如 UE 5.0 → 5.8 API 变化）。本注册表记录"版本锚定"的可核实事实，供定期 re-verify 与废弃检测。

## 文件位置
`SEA/memory/verified_facts.yaml` — 顶层 `facts:` 数组。

## 条目字段

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `id` | ✓ | string | `f-YYYYMMDD-NNN` |
| `claim` | ✓ | string | 可验证断言（含版本锚定） |
| `applies_to` | ✓ | string | 适用版本/环境（如 `UE 5.8`） |
| `verified` | ✓ | bool | 当前是否通过 re-verify |
| `verified_on` | ✓ | date | 最近一次验证日期 yyyy-mm-dd |
| `source` | ✓ | string | 权威来源（官方文档/引擎源码/链接） |
| `status` | ✓ | enum | `active` / `deprecated` |
| `deprecated_on` |  | date | 标记废弃的日期 |
| `deprecated_reason` |  | string | 废弃原因（如 API 变更） |

## 生命周期

```
active(verified_on 更新) ──re-verify──► 通过 → 保持 active
                                    └─► 失效 → status=deprecated + deprecated_on/reason
```

- **re-verify 周期**：每次环境版本变更后；否则按 `verify-versions.py --stale N` 提示
- **废弃检测**：`status: deprecated` 的条目不再作为断言依据；触发修正流程（走 agent-improvement）
- **先核实再断言**：无 `source` 的条目不写入；`verified: false` 时不得作为断言引用

## 示例

```yaml
facts:
  - id: f-20260813-001
    claim: UE 5.8 中 Iris 启用需 .uproject Iris 插件 + SetupIrisSupport(Target) + -UseIrisReplication=1
    applies_to: UE 5.8
    verified: true
    verified_on: 2026-08-13
    source: 官方 5.8 Iris 文档
    status: active
```
