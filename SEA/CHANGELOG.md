# CHANGELOG — 进化留痕

每次记忆/技能/定义变更在此记录，与 git 提交对应。

## 0.3.3 — 2026-08-14 — 记忆检索：补齐"只写不检"短板

- **`SEA/scripts/search-memory.py`**：记忆检索召回——对 memory/*.yaml 的 active 条目做关键词 + 结构索引（整词 + 字符二元组双特征，中文短语稳健），置信度 = 0.7×查询覆盖度 + 0.2×条目 confidence + 0.1×热度；支持 `--top`/`--category`/`--json`/`--all`
- **纪律**：AGENTS.md 记忆写入守则新增「检索优先」——需要历史经验时先 `search-memory.py` 召回，而非读文件；task-retrospective 技能 Reflect 步骤加入检索
- **验证**：中文"自进化"正确命中偏好条目（排第一，0.453）；"复制 技能 同步"命中经验条目（0.667）；无结果场景正常；category 过滤与 top 生效
- **版本**：0.3.2 → 0.3.3（补丁，新增脚本，向后兼容）


## 0.3.2 — 2026-08-14 — 技能修复：补拒绝路径（基于 L1 主动评估发现）

L1 主动评估（SEA评估 0.3.1）暴露三个技能共同短板：教"怎么做"强、教"何时不做"弱。本次 FIX：

- **agent-craft**（evo-agent-craft-fix-1）：新增「不生成（拒绝路径）」小节——无独立职责/无评测价值/职责重叠 → 拒绝生成，建议替代方案。L1 0.725 → 0.900
- **task-retrospective**（evo-task-retrospective-fix-1）：新增「不沉淀（跳过路径）」小节——纯查询/无泛化价值/内容已存在 → 不写记忆条目，NOTES 记录。L1 0.725 → 0.900
- **tool-craft**（evo-tool-craft-fix-1）：新增「拒绝修复（门槛门）」小节——未达阈值不修复，继续采集信号。L1 0.700 → 0.875
- **流程**：P2 FIX 生命周期——登记 pending → L1 判官评估（内联协议，会话模型）→ 棘轮全部通过（+0.175）→ solidify
- **验证**：validate-skill 通过；sync-workspace 同步到工作区
- **版本**：0.3.1 → 0.3.2（补丁，技能正文增强，向后兼容）


## 0.3.1 — 2026-08-14 — 模型继承 + 主动评估 + 内联判官协议

- **内联判官协议（免配置）**：`evaluate-skill.py` 新增 `--emit`/`--apply`——生成判定请求文件 → agent 用当前会话模型逐条判定 → 收集分数；无需 `SEA_JUDGE_URL/API_KEY`
- **模型继承**：`--model` 显式传当前会话模型名（脚本独立进程无法自动感知）；`SEA_EVAL_MODEL` 环境变量切换便宜模型；模型解析优先级 `--model` > `SEA_EVAL_MODEL` > `SEA_JUDGE_MODEL` > 默认
- **主动评估**：`ratchet-gate.py --active` 全量评估所有带 verifiable 用例的技能（用户输入「SEA评估」关键词触发）；`--collect <技能名>` 收集分数；token 不设上限
- **预算分级**：`--budget N`——自动评估（变更门）默认 20 用例（推荐值），主动评估默认 0（不设上限）
- **纪律**：AGENTS.md 新增「评估纪律」章节（模型继承/免配置/主动评估关键词/预算分级）
- **版本**：0.3.0 → 0.3.1（补丁，新增评估协议与模式，向后兼容）
- **验证**：emit→answers→apply 全闭环（L1=0.725）；active 生成 3 技能判定请求；--collect 正确继承请求内判官模型；budget 过滤生效


## 0.3.0 — 2026-08-14 — 评估器真话化（L1 真实评估 + 棘轮变更门）

补齐最大短板：棘轮分数从"启发式覆盖度"升级为"真实执行/判官评估"。

- **schema**：`SEA/templates/test-prompts.json` 用例新增 `verifiable`（可真实判定 pass/fail）与 `split`（train|heldout，棘轮计分只用 heldout 防过拟合）
- **评估器**：`evaluate-skill.py` 升级——`--mode judge` 只评 verifiable 用例、`--split heldout` 过滤、`--model` 支持直接用当前任务模型（优先于 `SEA_JUDGE_MODEL`）；输出带 `eval_source: l1|l0` 标记；无 JUDGE 配置回退启发式
- **变更门**：`SEA/scripts/ratchet-gate.py`（选项 B 落地）——检测 evolutions/improvements 的 pending 候选才触发 L1 真实评估，通过线 0.7，无候选不评估（token 零开销）；定义改进维持 HITL 人工评估
- **校验**：`validate-skill.py` 增加 verifiable/split 字段校验
- **用例**：3 个技能 test-prompts 补 verifiable/split 标记（各 ≥2 heldout 真实计分用例）
- **验证**：heldout 过滤正确（各剩 2 用例）；ratchet-gate 无候选不触发、有候选触发并裁决（无配置时 l0 回退保守判 FAIL）
- **版本**：0.2.3 → 0.3.0（次版本：新增评估机制，向后兼容——旧 test-prompts 缺失字段按 false/train 处理）


## 0.2.3 — 2026-08-14 — EVOLUTION.md 整体流程图文档

- **新增** `SEA/EVOLUTION.md`：自进化机制权威总览（总览流程图 + 各层演化路径 + 治理横切原则 + 脚本索引 + 版本演化记录）
- **纪律**：AGENTS.md 明示「机制/脚本/流程变更必须同步更新 EVOLUTION.md」；README 目录表登记该文件
- **版本**：0.2.2 → 0.2.3（补丁，纯文档，非破坏性）


## 0.2.2 — 2026-08-14 — 工具修复闭环 + 工作流实例化 + LLM 判官 + 远程 Hub

四项未来计划补齐（§5.5/§8.2/§10.3/§10.4）：

- **工具修复闭环（§10.3 后半）**：`SEA/scripts/tool-fix-candidates.py`（信号按工具聚合→degraded/broken 状态→`--promote` 生成修复候选）+ `SEA/tools/_registry/tools.json`（工具资产注册表）+ 新技能 `skills/tool-craft`（聚合→审批→修复→留痕生命周期，evo-tool-craft CAPTURED→HITL 批准→solidified，score_after=0.47）
- **多智能体工作流实例化（§5.5）**：`SEA/scripts/workflow-craft.py` 从任务描述生成工作流（步骤→子 Agent 定义→边），中文步骤名映射 kebab-case（读取→reader 等），复用 agent-definition 模板
- **LLM-as-Judge（§8.2）**：`evaluate-skill.py --mode judge --skill <名>`，经 `SEA_JUDGE_URL/API_KEY/MODEL` 环境变量调外部 LLM 判官（Agent-as-a-Judge 思路），未配置回退确定性打分
- **远程经验 Hub（§10.4 完整形态轻量版）**：`SEA/scripts/hub-sync.py` 用 git 远程分支作为共享存储，push 前强制审计门（scan-secrets + audit-skill，检出即拦截），快照提交后推送
- **版本**：0.2.1 → 0.2.2（次版本，新增机制，向后兼容）
- **验证**：tool-fix-candidates 信号→broken→promote 全流程实测；workflow-craft 中文步骤映射 kebab-case 正确；judge 回退路径正常；hub-sync dry-run 审计门+快照+push 通过


## 0.2.1 — 2026-08-14 — 拓扑搜索闭环（§10.1）

- **`SEA/scripts/search-topology.py`**：多智能体拓扑自动搜索——seeded 候选（single/chain/parallel）→ 评估 → 棘轮保留（score > best 才 approved 入库）→ 变异（加边/删边/换 agent/反转边）迭代搜索；`--dry-run` 只评估既有候选；`--seed` 可复现
- **`SEA/scripts/validate-topology.py`**：拓扑注册表 schema 校验（id 唯一、必填字段、status 枚举、agent 定义存在、边 from/to 引用完整）
- **评估复用**：search-topology 通过 importlib 复用 evaluate-skill 的 evaluate_topology（结构 0.4+覆盖 0.3+一致性 0.3）
- **版本**：0.2.0 → 0.2.1（补丁，新增脚本，向后兼容）
- **验证**：dry-run 评估既有候选、多 agent 搜索（single/chain/parallel 满分）、变异无改进被棘轮丢弃；validate-topology 在工作区 cwd 下通过


## 0.2.0 — 2026-08-14 — 未来计划落地：工具层进化 + 群体智能 + 拓扑搜索（§10.1/10.3/10.4）

- **工具层进化（§10.3）**：`SEA/tools/_registry/tool-signals.json`（工具失败信号注册表）+ `SEA/scripts/collect-tool-signals.py`（采集 MCP/工具调用失败→修复候选，同工具 3+ 条触发修复流程）；接入收尾协议与 task-retrospective 技能（§3.5）
- **群体智能（§10.4）**：`SEA/scripts/sync-workspace.py` 双向同步（工作区↔框架仓库）：memory/agents/tools/skills/scripts/templates；yaml 按 id 合并、json 注册表按 id 合并、冲突仅报告不静默覆盖；`--update` 按 mtime+size 更新脚本/模板、`--overwrite` 整体覆盖、`--dry-run` 模拟
- **谱系 DAG**：evolutions.json 条目支持 `parent_id`（OpenSpace 版本谱系思路），`validate-skill.py` 两遍校验（id 唯一 + parent_id 引用完整性）
- **拓扑搜索（§10.1）**：`SEA/agents/topology.json`（agent 拓扑注册表）+ `evaluate-skill.py --mode topology`（结构 0.4 + 定义覆盖 0.3 + 边一致性 0.3 确定性打分）；首个候选 tp-20260814-001 登记
- **版本**：0.1.3 → 0.2.0（次版本：新增机制，向后兼容）
- **验证**：tool-signals 增删/统计通过；sync-workspace push/pull/update/conflict 全路径实测；parent_id 非法引用被拦截；topology 在工作区 cwd 下 coverage=1.0


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
