# SEA

可持续进化 Agent（Self-Evolution Agent）的构建研究 + 可落地基础设施。

**当前版本**：`0.1.0`（见 `VERSION`；升级流程见 `INSTALL.md`）

## 这是什么

把「可持续进化 Agent」设计文档（`sustainable-agent-research.md`）落成可运行的骨架：一个遵守硬规则、会跨会话积累经验、只保留可验证增益、可回滚、会遗忘的记忆与技能系统。

**安装到目标工作区请看 `INSTALL.md`**（两种方式：技能装全局 or 工作区）。

## 目录结构

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 常驻注入的纪律：硬规则、五步进化闭环、任务收尾协议、记忆写入守则、分级权限、技能生命周期、定义自改进（P3）、版本自适应（P4） |
| `skills/` | 技能资产库（源）：`task-retrospective`（收尾反思）、`skill-craft`（技能创建/演进）、`agent-improvement`（定义自改进）、`version-verify`（版本核实）、`_evolutions/`（候选演进注册表）。安装到全局或工作区 `.opencode/skills/` |
| `SEA/` | **SelfEvolutionAgent 运行时包**（复制到目标工作区根目录） |
| `SEA/memory/` | 长期记忆库（lessons / preferences / verified_facts / NOTES） |
| `SEA/agents/_improvements/` | 定义改进注册表 + 棘轮基线（P3） |
| `SEA/templates/` | 记忆条目 schema、子 agent 定义模板、技能模板、技能评测集 schema、agent 改进工作流、事实核实 schema |
| `SEA/scripts/` | 记忆/技能/改进/版本校验脚本（Python，零额外依赖除 PyYAML） |
| `SEA/CHANGELOG.md` | 进化留痕 |
| `INSTALL.md` | 安装指南（两种方式 + 路径询问机制 + 升级流程） |
| `VERSION` | 框架版本号（与 `SEA/VERSION` 一致） |
| `sustainable-agent-research.md` | 设计文档（研究结论 + 未来计划） |

## 启用方式

1. **安装**：按 `INSTALL.md` 把 `SEA/` 与 `AGENTS.md` 复制到目标工作区，并把 4 个技能装到全局（`~/.config/opencode/skills/`）或工作区（`.opencode/skills/`）
2. **纪律生效**：目标工作区的 `AGENTS.md` 被 agent 读取即生效（OpenCode/OpenWork 会在工作目录自动加载）
3. **记忆写入**：任务结束按 `task-retrospective` 技能流程，把经验蒸馏进 `SEA/memory/*.yaml`，跑校验后提交

## 常用命令（在目标工作区根目录）

```powershell
# 校验记忆条目是否符合 schema
python SEA/scripts/validate-memory.py

# 检测近重复条目（可传相似度阈值，默认 0.6）
python SEA/scripts/dedup-check.py
python SEA/scripts/dedup-check.py 0.5

# 校验技能 frontmatter 与候选演进注册表（--skills-dir 指向技能库根目录）
python SEA/scripts/validate-skill.py --skills-dir .opencode/skills

# 校验定义改进注册表与棘轮基线
python SEA/scripts/validate-agent-improvements.py

# 版本核实健康检查（默认 90 天逾期；--stale N 自定义）
python SEA/scripts/verify-versions.py
python SEA/scripts/verify-versions.py --stale 30

# 框架版本（打印 / 检查两处一致 / 检查工作区是否过期）
python SEA/scripts/framework-version.py
python SEA/scripts/framework-version.py --check
python SEA/scripts/framework-version.py --installed E:\TempOpenWork
```

## 核心原则（速记）

- 评估器比生成器更重要；只保留可验证的增益（棘轮）
- 可回滚是基础设施；按最轻层解决（记忆→技能→代码→参数）
- 可持续 = 会遗忘；守卫与进化同步演进

## 未来计划

见设计文档第 10–11 章：多智能体拓扑搜索、符号化自进化、工具层进化、群体智能、推理记忆 × 测试时扩展、参数级 RL（前提成熟后）。
