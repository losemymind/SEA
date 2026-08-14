# CHANGELOG — 进化留痕

每次记忆/技能/定义变更在此记录，与 git 提交对应。

## 0.1.3 — 2026-08-14 — 评估器/守卫/遗忘/仪表盘 四类新脚本

补齐 §8「评估器比生成器更重要」与硬规则 5「可持续 = 会遗忘」、§5.4 供应链审计、§7.1 PII 治理的落地实现：

- **评估器（A1/A2）**：`SEA/scripts/evaluate-skill.py` — 独立确定性评测器，从 test-prompts 的 expect 提取特征短语，计算对 SKILL.md 的覆盖度打分；failure 用例强制要求反例章节。棘轮 score_before/score_after 从此有可复现基线（替代生成器自评）
- **供应链审计（C7）**：`SEA/scripts/audit-skill.py` — 静态扫描技能目录：敏感路径读取/危险命令/远程脚本下载/写入 secret/污染他方技能或全局库（纯路径引用豁免，仅写操作动词判定）
- **PII/secret 扫描（B6）**：`SEA/scripts/scan-secrets.py` — 检出 API key/token/私钥块/云密钥签名/邮箱/手机号，含占位符豁免，检出仅提示不自动改
- **记忆衰减（B4）**：`SEA/scripts/memory-decay.py` — 健康分 = 0.6·指数衰减(age) + 0.4·命中活跃度(hits)，低于阈值建议 deprecated；`--mark` 实际写入
- **指标仪表盘（C8）**：`SEA/scripts/report-metrics.py` — 记忆库/技能库/定义改进/技能演进汇总 + 健康提示（复用 evaluate-skill 打分逻辑，importlib 加载含连字符文件名）
- **纪律更新**：`AGENTS.md` 新增「守卫脚本」小节（收尾协议后可选跑）；README/INSTALL 命令清单补充 5 个新脚本
- **版本**：0.1.2 → 0.1.3（次版本，新增机制，向后兼容）
- **验证**：全部新脚本自测通过（evaluate-skill 确定性复现、audit-skill 0 危险信号、scan-secrets 0 检出、memory-decay 阈值调严正确检出、report-metrics 正常输出）


## 0.1.2 — 2026-08-14 — AGENTS.md 硬规则新增元规则第 0 条

- **定义**：硬规则顶部新增第 0 条元规则「自进化是至高目标」——任何阻碍自进化的规则/方案/方法可变更，不得以既有纪律为由阻止框架改进（来源：用户纠正 m-20260814-006）
- **流程**：P3 定义自改进（im-20260814-002，DERIVED）：登记 pending → 评估 → 最小 diff → HITL 批准 → approved
- **棘轮**：baselines.json 记录 AGENTS.md 首次基线 0.85
- **版本**：0.1.1 → 0.1.2（补丁，非破坏性）
- **验证**：validate-agent-improvements / validate-memory 通过

## 0.1.1 — 2026-08-14 — agent-definition 模板补 model 字段说明

- **模板**：`SEA/templates/agent-definition.md` frontmatter 补充可选 `model` 字段注释——不填则 subagent 默认使用调用它的主 Agent 的模型（primary agent 用全局配置模型）
- **技能**：`skills/agent-craft/SKILL.md` 注明 `model` 可选及默认行为，需要专用模型时才显式指定
- **版本**：0.1.0 → 0.1.1（补丁，非破坏性）
- **验证**：`framework-version.py --check` 通过；validate-skill 通过

## 2026-08-14 — 新技能：agent-craft（子 Agent 生成）

- **技能**：`skills/agent-craft/SKILL.md`（CAPTURED，来源于 research §10.1/§5.5）— 从任务描述/历史经验生成子 Agent 定义到 `.opencode/agents/` 或全局 agents 目录，流程：登记 pending → 生成 → 结构/效果评估 → HITL 审批 → 棘轮保留/回滚，含供应链审计与最小权限
- **评测集**：`skills/agent-craft/test-prompts.json`（4 用例：success×2 生成/拆解、failure×2 过度拆解/高危权限）
- **注册表**：`_evolutions/evolutions.json` 登记 `evo-agent-craft` → HITL 批准 → solidify（score_after=0.75，首次入库为基线）
- **验证**：validate-skill OK（5 技能）；validate-memory / dedup / validate-agent-improvements 均通过

## 2026-08-13 — 清除全部演示条目

- 回退到 02eb0b2 后，随 1873763 一并回退的演示条目重新出现，本次彻底清除
- **移除**：lessons m-001/002/003（初始种子示例）、preferences m-010（虚构偏好）、verified_facts f-003（`verified:false` 演示）、improvements im-001（模板示例）、baselines AGENTS.md 占位、evolutions evo-001（初始示例）
- **保留**：lessons m-004/005（真实复制测试沉淀）、verified_facts f-001/002（真实已核实事实）
- **验证**：validate-memory 0 / dedup 0 / improvements 0 / verify-versions 0（WARN 消失）/ validate-skill 0

## 0.1.0 — 2026-08-13 — P0 框架版本与兼容性

- **版本机制**：新增顶层 `VERSION` 与 `SEA/VERSION`（随运行时进入工作区，版本一致）
- **脚本**：`SEA/scripts/framework-version.py`（打印版本 / `--check` 校验两处一致 / `--installed <工作区>` 检测过期）
- **文档**：INSTALL.md 新增「框架升级流程」章节（版本规则、升级步骤、`[BREAKING]` 标记、同步已装工作区）；README 标注当前版本；AGENTS.md 新增「框架版本纪律」
- **验证**：`framework-version.py --print/--check` 通过；`--installed E:\TempOpenWork` 正确检出旧安装无 VERSION 为过期

## 2026-08-13 — 仓库重构：SEA 运行时包 + INSTALL.md

- **结构**：`agents/`、`memory/`、`scripts/`、`templates/`、`CHANGELOG.md` 移入 `SEA/`（SelfEvolutionAgent 运行时包），`skills/` 留在顶层作为技能源
- **路径**：全部技能正文、AGENTS.md、文档内的引用改为 `SEA/` 前缀（相对工作区根）；`validate-skill.py` 新增 `--skills-dir` 参数（自动探测 `.opencode/skills` → 仓库根 `skills/`）
- **INSTALL.md**：新增两种安装方式（技能装全局 vs 工作区）+ 路径询问机制说明
- **验证**：5 个校验脚本全部通过（memory/dedup/skill/improvements/versions），`validate-skill.py` 带 `--skills-dir` 与默认探测两种调用均通过

## 2026-08-13 — 首次真实收尾闭环（从 TempOpenWork 回流）

- 复制测试产生的真实经验沉淀（m-20260813-004 YAML 注释坑、m-20260813-005 skills 双份拷贝同步）
- 与 TempOpenWork 工作区记忆同步，保持单一事实来源一致
- 验证：validate-memory 0 / dedup 0

## 2026-08-13 — Phase 3 + Phase 4：定义自改进 + 版本自适应

### Phase 3：定义自改进
- `skills/agent-improvement/SKILL.md`：GEPA 式反思进化（Evaluate→Improve→Validate→Confirm→Keep/Revert）+ HITL + 棘轮
- `agents/_improvements/improvements.json`（候选改进注册表 schema）+ `baselines.json`（棘轮基线）
- `templates/agent-improvement/README.md`：工作流说明
- `scripts/validate-agent-improvements.py`：注册表 schema + 棘轮一致性校验
- 修复 Phase 2 遗留：`templates/test-prompts.json` 改为合法 JSON（schema 移入 `_doc`）；`validate-skill.py` 现校验技能内 test-prompts.json

### Phase 4：版本自适应
- `memory/verified_facts.yaml`：3 条 UE 5.8 版本锚定事实（含 1 条故意 `verified: false` 演示告警）
- `templates/verify-facts/schema.md`：事实注册表 schema（active/deprecated 生命周期）
- `skills/version-verify/SKILL.md`：re-verify + 废弃检测 + 修正触发流程
- `scripts/verify-versions.py`：schema 校验 + 逾期检测（--stale）+ 未核实告警

### 纪律与验证
- `AGENTS.md` 新增「定义自改进（Phase 3）」「版本自适应（Phase 4）」
- 全部脚本通过：memory / dedup / skill / agent-improvements / verify-versions（1 条非阻塞 WARN 为演示）

## 2026-08-13 — Phase 2：技能库成熟化

- **技能资产生命周期**：`skills/README.md`（候选→评估→HITL审批→solidify→棘轮回滚）；`skills/_evolutions/evolutions.json`（候选演进注册表，含 1 条 FIX 示例）；`skills/skill-craft/SKILL.md`（创建/演进元技能）
- **评测集**：`templates/test-prompts.json`（schema）+ `skills/task-retrospective/test-prompts.json`（3 用例：成功×2、边界×1）
- **技能校验脚本**：`scripts/validate-skill.py`（SKILL.md frontmatter 必填 + evolutions.json schema）— 通过（2 技能 + 注册表 OK）
- **纪律更新**：`AGENTS.md` 新增「技能生命周期（Phase 2）」：质量门、供应链审计、棘轮
- **验证**：`validate-skill.py` 通过；既有记忆校验仍通过

## 2026-08-13 — 初始搭建（Phase 0 + Phase 1）

- **地基（Phase 0）**：`git init`；`AGENTS.md` 硬规则 + 五步闭环 + 任务收尾协议；`.gitignore`
- **记忆库（Phase 1）**：`memory/` 目录（README + lessons.yaml 3 条 + preferences.yaml 1 条 + NOTES.md 模板）；`templates/lesson-schema.yaml`
- **技能**：`skills/task-retrospective/SKILL.md`（收尾反思→蒸馏→提交流程）
- **模板**：`templates/agent-definition.md`、`templates/skill-template/SKILL.md`
- **脚本**：`scripts/validate-memory.py`（schema 校验）、`scripts/dedup-check.py`（近重复检测）— 均通过自测（坏条目被拦截，`exit=1`）
- **验证**：`validate-memory.py` 2 文件通过；`dedup-check.py` 4 条目无疑似重复

### 来源与依据
- 设计文档：`sustainable-agent-research.md`
- 记忆条目：m-20260813-001/002/003（经验/工程知识）、m-20260813-010（偏好）
