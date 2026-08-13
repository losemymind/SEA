# skills/ — 技能资产库

技能是可复用工作流的外显资产：`SKILL.md`（何时用、怎么做、约束、反例）+ 可选脚本/模板/评测集。本目录每个子目录是一个技能。

## 技能资产生命周期

技能与记忆不同：技能影响未来任务的行为，**必须过质量门与审批**。

```
信号检测（规则式：工具结果 / 用户措辞 / 评测指标）
  → 写入 _evolutions/evolutions.json（候选区，未生效）
  → 评估（结构 + 效果）→ HITL 审批（展示 diff）
  → solidify：合并回对应 SKILL.md，状态置 solidified
  → 谱系记录（FIX / DERIVED / CAPTURED）
  → 验证通过才保留；否则 revert
```

- **候选区**：`_evolutions/evolutions.json` 中的条目**不会生效**，只是提案
- **solidify**：审批通过后合并回 `SKILL.md`（失败类→`Troubleshooting`；用户纠正→`Examples`）
- **谱系**：FIX（修补失效说明）/ DERIVED（派生增强变体）/ CAPTURED（从成功执行抽取全新流程）
- **回滚**：任何一轮验证不通过 → 从 SKILL.md 移除，状态置 reverted

## 技能目录约定

| 项 | 约定 |
|---|---|
| 目录名 | kebab-case（如 `task-retrospective`） |
| 入口 | `SKILL.md`（frontmatter 含 `name` + `description`） |
| 评测集 | 可选 `test-prompts.json`（见 `templates/test-prompts.json`） |
| 辅助文件 | 脚本/模板随目录携带，SKILL.md 中说明 |
| 禁用前缀 | `_` 开头目录（如 `_evolutions/`）是元数据，不是技能 |

## 入库质量门

1. `description` 写得能按描述自动匹配（何时触发、做什么、产出什么）
2. 步骤可执行、有验收、有反例
3. 通过 `scripts/validate-skill.py`（frontmatter 必填 + evolutions.json schema）
4. 供应链审计（第 5.4 节）：无敏感路径读取、无危险命令、无远程脚本下载、无 secret 写入、不污染其他技能/记忆
5. HITL 审批后才 solidify

## 验证与审计

```powershell
# 校验所有技能 frontmatter 与 evolutions.json
python scripts/validate-skill.py
```
