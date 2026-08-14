# SEA

可持续进化 Agent（Self-Evolution Agent）的构建研究 + 可落地基础设施。

**当前版本**：`0.2.2`（见 `VERSION`；升级流程见 `INSTALL.md`）

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
| `SEA/scripts/` | 记忆/技能/改进/版本校验脚本（Python，零额外依赖除 PyYAML）+ 评测（evaluate-skill）、审计（audit-skill）、secret 扫描（scan-secrets）、记忆衰减（memory-decay）、指标仪表盘（report-metrics）、工具信号采集（collect-tool-signals）、工作区同步（sync-workspace） |
| `SEA/CHANGELOG.md` | 进化留痕 |
| `SEA/EVOLUTION.md` | 自进化整体流程图（权威总览：五步闭环/各层路径/治理/脚本索引/版本记录） |
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

# 技能独立评测（棘轮 score_before/score_after 用）
python SEA/scripts/evaluate-skill.py --skills-dir .opencode/skills

# 技能供应链审计（入库前必查：敏感路径/危险命令/远程脚本/污染）
python SEA/scripts/audit-skill.py --skills-dir .opencode/skills

# 入库前 PII/secret 扫描（检出即拦截）
python SEA/scripts/scan-secrets.py

# 记忆衰减检测（久未使用+低命中 → 建议 deprecated；--mark 实际写入）
python SEA/scripts/memory-decay.py
python SEA/scripts/memory-decay.py --mark

# 进化指标仪表盘（记忆/技能/改进/演进健康度）
python SEA/scripts/report-metrics.py --skills-dir .opencode/skills

# 工具失败信号采集（MCP/工具调用失败 → 修复候选，§10.3）
python SEA/scripts/collect-tool-signals.py <tool> --type <call-failure|missing|broken|slow|unsafe> --detail "<说明>"

# 工作区 ↔ 框架仓库 双向同步（经验回流/下发，§10.4）
python SEA/scripts/sync-workspace.py --workspace <工作区> --push
python SEA/scripts/sync-workspace.py --workspace <工作区> --pull --update

# Agent 拓扑评测（§10.1 多智能体拓扑搜索）
python SEA/scripts/evaluate-skill.py --mode topology

# 拓扑注册表校验（schema + 边引用完整性）
python SEA/scripts/validate-topology.py --agents-dir .opencode/agents

# 多智能体拓扑自动搜索（生成候选→评估→棘轮保留→变异）
python SEA/scripts/search-topology.py --budget 10 --agents-dir .opencode/agents
python SEA/scripts/search-topology.py --dry-run --agents-dir .opencode/agents

# 工具修复候选（信号聚合 → 修复候选，§10.3）
python SEA/scripts/tool-fix-candidates.py
python SEA/scripts/tool-fix-candidates.py --promote <工具名>

# 多智能体工作流实例化（从任务描述生成工作流图 + 子 Agent，§5.5）
python SEA/scripts/workflow-craft.py --task "调研+实现+验证" --steps 读取,实现,验证

# LLM-as-Judge 评测（§8.2，需 SEA_JUDGE_URL/API_KEY/MODEL 环境变量）
python SEA/scripts/evaluate-skill.py --mode judge --skill tool-craft

# 远程经验 Hub 同步（§10.4，用 git 远程作为共享存储）
python SEA/scripts/hub-sync.py --remote origin --push --dry-run

# 校验定义改进注册表与棘轮基线
python SEA/scripts/validate-agent-improvements.py

# 版本核实健康检查（默认 90 天逾期；--stale N 自定义）
python SEA/scripts/verify-versions.py
python SEA/scripts/verify-versions.py --stale 30

# 框架版本（打印 / 检查两处一致 / 检查已安装工作区是否过期）
python SEA/scripts/framework-version.py
python SEA/scripts/framework-version.py --check
# --installed 在框架仓库根目录运行；<工作区> 为已安装 SEA 的目标工作区路径（如 E:\TempOpenWork）
python SEA/scripts/framework-version.py --installed <工作区>
```

## 核心原则（速记）

- 评估器比生成器更重要；只保留可验证的增益（棘轮）
- 可回滚是基础设施；按最轻层解决（记忆→技能→代码→参数）
- 可持续 = 会遗忘；守卫与进化同步演进

## 未来计划

见设计文档第 10–11 章：多智能体拓扑搜索、符号化自进化、工具层进化、群体智能、推理记忆 × 测试时扩展、参数级 RL（前提成熟后）。
