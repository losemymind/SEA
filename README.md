# AgentsSelfEvolution

可持续进化 Agent 的构建研究 + 可落地基础设施。

## 这是什么

把「可持续进化 Agent」设计文档（`sustainable-agent-research.md`）落成可运行的骨架：一个遵守硬规则、会跨会话积累经验、只保留可验证增益、可回滚、会遗忘的记忆与技能系统。

## 目录结构

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 常驻注入的纪律：硬规则、五步进化闭环、任务收尾协议、记忆写入守则、分级权限 |
| `memory/` | 长期记忆库（lessons / preferences / NOTES） |
| `skills/` | 技能资产源（可复制到 `.opencode/skills/` 后即可被调用） |
| `templates/` | 记忆条目 schema、子 agent 定义模板、技能模板 |
| `scripts/` | 记忆校验与查重脚本（Python，零额外依赖除 PyYAML） |
| `CHANGELOG.md` | 进化留痕 |
| `sustainable-agent-research.md` | 设计文档（研究结论 + 未来计划） |

## 启用方式

1. **纪律生效**：`AGENTS.md` 随本仓库被 agent 读取即生效（OpenCode/OpenWork 会在工作目录自动加载）
2. **技能启用**：把 `skills/task-retrospective/` 复制到 `.opencode/skills/`（或按你的宿主约定），任务收尾时即可被触发
3. **记忆写入**：任务结束按 `skills/task-retrospective/SKILL.md` 流程，把经验蒸馏进 `memory/*.yaml`，跑校验后提交

## 常用命令

```powershell
# 校验记忆条目是否符合 schema
python scripts/validate-memory.py

# 检测近重复条目（可传相似度阈值，默认 0.6）
python scripts/dedup-check.py
python scripts/dedup-check.py 0.5
```

## 核心原则（速记）

- 评估器比生成器更重要；只保留可验证的增益（棘轮）
- 可回滚是基础设施；按最轻层解决（记忆→技能→代码→参数）
- 可持续 = 会遗忘；守卫与进化同步演进

## 未来计划

见设计文档第 10–11 章：多智能体拓扑搜索、符号化自进化、工具层进化、群体智能、推理记忆 × 测试时扩展、参数级 RL（前提成熟后）。
