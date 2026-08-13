---
title: 可持续进化 Agent 构建研究
description: 通用方法论研究 + 设计蓝图。如何构建不依赖人工重写、能随经验积累而持续提升能力的 Agent。覆盖跨会话记忆、自我改进、技能/子Agent进化、版本自适应四大支柱，并给出治理、评估、路线图与未来计划（群体智能、多智能体拓扑搜索、参数级RL）。
tags: [agent, self-evolution, memory, skills, research]
---

# 可持续进化 Agent 构建研究

> 通用方法论研究 + 设计蓝图。**核心章节（第 1–9 章）为当下可落地的工程设计；未来计划章节（第 10–11 章）为概念性前沿方向，明确标注"未落地"。**
>
> 写作日期：2026-08-13。所有引用均为写作时可见的公开资料；版本敏感内容请以最新文档为准。

## 硬规则摘要（最先阅读）

1. **评估器比生成器更重要** — 自进化的核心不是"会改"，而是"证明改动没让系统变坏"
2. **只保留可验证的增益** — 棘轮（ratchet）原则：新总分不高于当前最优就回滚，基线单调不降
3. **可回滚是基础设施** — 一切进化产物（记忆、技能、定义、提示）必须可 diff、可 git、可回滚
4. **按最轻层解决** — 能先在记忆层解决就不要改技能；能先改技能就不要改代码；能先改代码就不要在线更新权重
5. **可持续 = 会遗忘** — 记忆系统必须有评估、去重、冲突解决与主动遗忘，否则膨胀即退化
6. **守卫与进化同步演进** — 自适应安全检测 + 对抗演练；不做"事后补"的供应链安全
7. **先核实再断言** — 引用 API/事实前验证来源；无法核实就明说（沿袭 unreal-systems-engineer 的纪律）

---

# 第一部分 · 核心（当下可落地）

## 1. 绪论

### 1.1 为什么要"可持续进化"

传统 LLM Agent 部署后配置即静态：每次新会话都从零开始，同样的错误反复踩，同一份资料反复查，同一套操作步骤反复写。用户只得到了"聪明的冷启动"，没有"越用越强"。

**Agent Self-Evolution** 讨论的正是这个问题：把交互轨迹、任务反馈、用户纠正、工具执行结果、群体经验等信号沉淀下来，并让这些沉淀持续影响之后的行为。

> **自进化 Agent** 是一种能够依据自身交互轨迹、任务反馈或环境信号，对上下文、记忆、技能、工具、工作流、代码或模型参数进行持续更新，并让这些更新影响未来任务表现的智能体系统。

三个关键点：
1. **经验驱动** — 更新来自真实任务、执行反馈、用户纠错、评测结果，而不是一次性人工配置
2. **持续生效** — 更新进入记忆、技能库、工作流或定义中，在未来任务继续发挥作用
3. **可评估、可回滚** — 越强的自进化越需要评估器、版本记录、沙箱、权限控制和回滚机制

### 1.2 概念框架：四组件反馈环

引用 EvoAgentX 团队的自进化综述（arXiv:2508.07407）统一框架，任何自进化系统都可抽象为四个组件及其反馈回路：

```
System Inputs ──► Agent System ──► Environment
      ▲                │                │
      └─── Optimisers ◄┘◄───────────────┘
                （依据环境反馈优化 Agent 系统的任何组件）
```

- **System Inputs**：任务描述、用户指令、检索到的上下文
- **Agent System**：提示、记忆、技能、工具、工作流、代码、模型参数（可被优化的对象）
- **Environment**：执行环境返回的地面真值（工具结果、代码运行、测试通过/失败）
- **Optimisers**：把环境反馈转化为对 Agent System 的更新

本文全部章节都在回答同一个问题：**优化器应该改 Agent System 的哪一层、靠什么反馈改、如何证明改完没变坏。**

### 1.3 四类闭环分层

按"演化对象 + 工程风险"分层（据 datawhalechina/hello-agents Extra10），能力上限与工程风险自下而上递增：

| 层 | 闭环类型 | 演化对象 | 代表项目/方法 |
|---|---|---|---|
| ① | 内建上下文闭环 | 记忆、反思文本、会话索引、技能目录 | Hermes Agent、Agent Zero |
| ② | 技能资产化闭环 | SKILL.md（可版本化、可评测、可回滚的资产） | Darwin Skill、JiuwenClaw、EvoSkill |
| ③ | 群体智能闭环 | 跨会话/跨设备/跨用户/跨 Agent 的共享经验 | Ultron、OpenSpace、SkillClaw |
| ④ | 参数/代码/工作流自修改 | 模型权重、Agent 代码、工作流拓扑 | OpenClaw-RL、Agent Lightning |

**本文覆盖策略**：第 3–6 章（四支柱）聚焦 ①②；第 10 章未来计划覆盖 ③④ 的全深度形态与多智能体拓扑搜索；第 11 章未来计划单独展开参数级 RL。

### 1.4 本文四大支柱

经与你确认，本次研究聚焦四条进化方向：
1. **跨会话记忆**（第 3 章）— 知识/经验跨会话积累
2. **自我改进定义文件**（第 4 章）— 自我优化系统提示/规则
3. **进化出新技能/子 Agent**（第 5 章）— 从经验长出可复用资产
4. **版本与环境自适应**（第 6 章）— 领域事实漂移的应对

---

## 2. 核心架构：进化闭环

### 2.1 五步闭环

在经典"执行→反思"循环上，吸收 Experience-driven Lifelong Learning（ELL，arXiv:2508.19005）的"知识内化"原则，形成五步闭环：

```
Act ──► Reflect ──► Distill ──► Commit ──► Internalize
 ▲                                              │
 └────────────── 下一次任务 ◄───────────────────┘
```

| 步骤 | 动作 | 产出 |
|---|---|---|
| **Act** | 执行真实任务，记录轨迹（工具调用、环境反馈、错误、用户纠正） | 轨迹 |
| **Reflect** | 复盘：本次成功/失败在哪里；可归因到哪条记忆/哪个技能/哪条规则 | 反思文本 |
| **Distill** | 提取可泛化的经验（推理策略、踩坑教训、环境事实、用户偏好），而非原始轨迹 | 候选经验 |
| **Commit** | 评估质量 → 去重/冲突解决 → 写入持久层（记忆/技能/定义），带版本与来源 | 持久化增量 |
| **Internalize** | 让显式离散经验逐步成为"第二本能"：规则固化为行为约定，常用流程固化为技能 | 行为层变化 |

**关键认知**：context 是稀缺资源（Anthropic 上下文工程，2025-09）。进化闭环的实质是把 context 中的价值**转移**到持久层，让下个会话无需重演即可复用。若只在上下文里打转，就没有"进化"，只有"延长的对话"。

### 2.2 分层：L0 / L1 / L2

单 agent 宿主（如 OpenCode/OpenWork 或 Claude Code）内可自然形成三层：

- **L0 执行 Agent**：干活，产出轨迹与产物
- **L1 反思 Agent**：复盘评估（独立于 L0 的上下文，避免"自改自评"偏差）
- **L2 元进化 Agent**：修订记忆/技能/定义文件，跑验证，做回滚决策

个人场景的简化版：L1/L2 可以由同一主 agent 在"任务收尾"阶段以不同角色完成，但**评估与生成必须分离**（见 2.3 与第 8 章）。

### 2.3 横切原则

**原则一：评估器比生成器更重要。** 自进化系统最危险的幻觉是"只要会自动改，就会自动变好"。没有评估器的自动修改只是自动制造不确定性。Darwin Skill 的 ratchet、SkillClaw 的验证 worker、Ultron 的结构评分门控、OpenClaw-RL 的 PRM/Judge、OpenSpace 的执行后分析，全部指向同一结论：**自进化的核心是证明改动没有让系统变坏。**

**原则二：只保留可验证的增益（棘轮）。** 见第 4、8 章。新方案在评测集上得分不高于当前最优，一律回滚；基线单调不降。

**原则三：可回滚是基础设施。** 记忆可 diff、技能可 git commit、定义文件可 revert。参数层更新解释与回滚最重，因此置于最上层（见第 11 章）。

**原则四：按最轻层解决（分层决策）。**

```
能先在记忆层解决，就不要急着改技能；
能先在技能层解决，就不要急着改代码；
能先在代码/工作流层解决，就不要急着在线更新权重。
```

---

## 3. 支柱一：跨会话记忆系统

### 3.1 目标与三类记忆

目标：Agent 跨会话记住"用户偏好、历史经验、工程知识"，实现"用得越多，越懂你"（Qoder 长期记忆博客，2025-08）。

记忆按领域分三类：

| 类别 | 内容 | 来源 |
|---|---|---|
| **个人偏好** | 代码风格、行为偏好、用户指令（如"完成任务后一定要生成单元测试"） | 用户提问分析 |
| **历史经验** | 出错与解决办法、主要流程、测试框架排查、构建运行经验 | 执行过程提取 |
| **工程知识** | 技术栈、功能架构、API 文档、代码库顶层设计认知 | 工程实时建模 |

### 3.2 完整生命周期

Qoder 的记忆闭环 + Ultron 的分层检索，合并为以下生命周期（对应第 2.1 章闭环的记忆侧）：

```
召回 ─► 执行 ─► 多源提取 ─► 质量评估 ─► 整理 ─► 有效性评估 ─► 遗忘
 │                                                          │
 └────────── 重新入库（去重/冲突/融合后） ◄──────────────────┘
```

1. **召回**：基于当前上下文检索相关记忆（分层检索，见 3.3），选择性注入，避免"历史无限塞进 prompt"
2. **执行**：Agent 完成任务
3. **多源提取**：同时分析 ① 用户提问（偏好）② 智能体执行过程（经验）③ 代码工程实时建模（工程知识）
4. **质量评估**：类 RL 价值反馈——低质量记忆拒绝保留；结构/来源/可信度评分
5. **整理**：去重（近重复向量合并）、冲突解决（时间与证据优先）、融合（同类记忆聚类结晶）
6. **有效性评估**：任务结束后对本次召回的每条记忆评效——被正确使用且有效则加分
7. **遗忘**：根据质量分 + 有效性 + 热度时间衰减，剔除无效记忆。**遗忘是"可持续"的必备环节**——只积累不遗忘，记忆库必然退化

### 3.3 分层存储与检索（引用 Ultron 设计）

- **热度分层 HOT / WARM / COLD**：常命中 → 常驻或高优先级召回；低频 → 按需检索；久未命中 → 待遗忘候选
- **摘要层级 L0 / L1 / Full**：检索先返回短摘要省 token，命中后按需拉全文（符合"最小高信号 token"上下文原则）
- **向量语义检索 + 层级加权 + 意图扩展查询**（Ultron Memory Hub 方案）
- **PII 脱敏后入库**（Presidio 式检测），见第 7 章

### 3.4 升级点：蒸馏推理策略，而非存轨迹

最新研究（ReasoningBank，arXiv:2509.25140，ICLR'26）表明：**原始轨迹和"成功例程"都不是好的记忆单元**。更好的做法是——从 Agent **自判的成功与失败经验中蒸馏出可泛化的推理策略**（"这类问题先做 X 再验 Y"），失败经验与成功经验形成**对比信号**，提炼出更高质量的记忆。

落地建议：
- 记忆条目优先存**策略/规则**，其次存**事实**，最后才存**例程**
- 每次提炼至少对齐一条成功 + 一条失败（对比），而非只记成功
- 记忆条目 schema：

```yaml
id: m-2026-0813-001
type: strategy | fact | routine | preference
category: preference | experience | engineering
claim: 处理 UE 复制漂移时，先核对 DOREPLIFETIME 与 GetLifetimeReplicatedProps 的一致性
evidence: [session_id, 验证命令, 结果]
contrast: 失败侧——只查 OnRep 未查注册表导致误判
confidence: 0.9
hits: 3            # 有效性计数
last_used: 2026-08-13
source: self-reflect | user-correct | tool-feedback
```

### 3.5 落地机制（OpenCode/OpenWork 宿主）

| 层 | 载体 | 说明 |
|---|---|---|
| 短期（会话内） | NOTES.md / 会话笔记 | 结构化笔记随任务推进，压缩保留关键状态 |
| 长期（跨会话） | `memory/` 目录 + lessons schema | 精炼条目，按 3.4 schema 存 |
| 检索 | 关键词/向量 + session 历史 | OpenWork `session.list_sessions` / `session.read` 可回看历史会话；`AGENTS.md` 类文件常驻注入 |
| 常驻 vs 按需 | AGENTS.md（常驻） vs SKILL.md（按需） | 常驻只放"去掉会导致犯错的"内容（CLAUDE.md 原则）；其余按需加载 |

**风险与护栏**：
- **上下文膨胀**：只在调用时注入摘要；全量在库里
- **错误记忆污染**：来源标注 + 独立质量评估；用户纠正优先于自反思
- **记忆冲突**：冲突条目按"时间新 + 证据强"胜出，旧条目标记 deprecated 而非删除（可审计）

---

## 4. 支柱二：自我改进定义文件

### 4.1 目标

Agent 实践后自动修订自己的定义/技能/规则文件（如 `.opencode/agent/*.md`、`AGENTS.md`、`SKILL.md`），让系统提示随项目演进，而非永远依赖人工维护。

### 4.2 旗舰机制：GEPA 式反思进化

最新方法 GEPA（Genetic-Pareto，arXiv:2507.19457，ICLR'26 Oral）证明**自然语言反思式提示进化可超越 RL**：平均超 GRPO 6%、最高 20%，rollout 少 35 倍。核心流程可直接映射到定义文件优化：

```
采样轨迹（推理、工具调用、工具输出）
  → 自然语言反思：诊断问题
  → 提出针对性的提示/规则补丁
  → 在测试集上验证补丁
  → 把互补的教训合入 Pareto 前沿（保留多个不支配方案）
  → 棘轮：新总分 > 当前最优才保留，否则回滚
```

对照 Darwin Skill 的成熟闭环（Evaluate → Improve → Validate → Confirm → Keep or Revert）：

| 步骤 | Darwin Skill 做法 | 本文落地 |
|---|---|---|
| **Evaluate** | 结构侧静态分析 + 效果侧测试集实跑，八维 rubric 总分 100 | 结构分 + 效果分加权；效果分权重最高 |
| **Improve** | 找出得分最低维度，单次只改一个目标文件 | **单一可编辑资产**：一次只优化一个 `.md` |
| **Validate** | 在 test-prompts 集上复测 | 复用 8.3 评测集 |
| **Confirm** | 展示 diff 与分数变化，人在回路确认 | **HITL 拦截**：diff 展示后审批（见 4.3） |
| **Keep or Revert** | 新总分更高则保留，否则 `git revert` | 棘轮，基线单调不降 |

### 4.3 安全设计

- **分级权限**：
  - 自动执行：记忆条目写入（第 3 章，低风险）
  - HITL 审批：修改规则/技能/定义文件（高影响）
  - 审批模式参照 EvoAgentX `HITLInterceptorAgent`：在执行前拦截，`[a]pprove / [r]eject`
- **独立打分**：评估由子 Agent（L1）完成，减轻"自改自评"；必要时"fresh context reviewer"（新上下文审阅 diff，避免实现者自证正确）
- **版本管理**：`git` + diff 审查；改动前后效果对比记录在 CHANGELOG
- **回滚**：任何一轮验证不通过 → `git revert`

### 4.4 反模式：定义文件膨胀

Claude Code 最佳实践明确警告：**过长的 CLAUDE.md 会让模型忽略实际指令**。每条规则自问"去掉它会导致犯错吗？"——不会就删，或降级为技能按需加载。分级对策：

| 内容 | 归属 |
|---|---|
| 常适用的工作流/命令/行为约定 | 常驻定义文件（精简） |
| 特定领域的知识/流程 | SKILL.md（按需加载） |
| 快速变化的信息 | 记忆库（可遗忘） |

---

## 5. 支柱三：进化出新技能/子 Agent

### 5.1 目标

把成功流程沉淀为可复用资产：① 经验的资产化（SKILL.md）② 新子 Agent 的生成（从单一任务自动构造工作流）。

### 5.2 技能资产化生命周期

融合 JiuwenClaw 的"在线信号 + 两阶段固化"与 OpenSpace 的"技能谱系"：

```
信号检测（规则式，不调 LLM；监视工具结果与用户措辞）
  → 可归因到当前技能的事件？
  → 写演进条目到 evolutions.json（候选区，未生效）
  → solidify：在合适时机合并回 SKILL.md（可 /evolve 手动触发）
  → 谱系记录（DAG）：FIX / DERIVED / CAPTURED
```

- **失败类信号** → 写入 `Troubleshooting` 小节
- **用户纠正** → 整理为 `Examples`
- **FIX**：就地修补过时/失效说明；**DERIVED**：从父技能派生增强变体；**CAPTURED**：从一次成功执行抽取全新流程（OpenSpace 三主线）
- 每个技能独立目录（`~/.opencode/skills/<name>/` 或 workspace 内），天然可版本化

### 5.3 入库质量门槛（参照 EvoSkill 思路）

- 从**失败轨迹**驱动候选生成，而非只抄成功例程
- 在 **held-out 验证集**上打分；优秀候选以**全新技能版本**进入，而非原地打补丁
- 验证通过才进正式库；每条技能带来源（provenance）与验证证据

### 5.4 供应链安全（技能如软件包）

Agent Skills 是跨生态复用格式：一个技能可含 SKILL.md、脚本、模板、远程依赖和执行指令。入库前必须审计：

- 是否读取敏感路径 / 执行危险命令 / 下载远程脚本
- 是否把 secret 写入输出
- 是否试图污染其他技能或记忆
- **候选验证 + 版本审计**为默认能力（详见第 7 章）

### 5.5 子 Agent 生成

从单一任务描述自动构造多智能体工作流（EvoAgentX `WorkFlowGenerator` 思路的简化落地）：

```
自然语言目标 → 生成工作流图（步骤划分） → 为每个步骤实例化专用子 Agent → 执行 → 汇总
```

落地要点：子 Agent 各自持有小上下文、回报精简摘要（1–2k token），避免主上下文被研究性探索填满（Anthropic 多智能体研究系统结论：并行子 Agent 显著优于单 Agent 长任务）。新子 Agent 一旦验证有效，可固化为正式 subagent 定义文件（回填到第 4 章资产）。

---

## 6. 支柱四：版本与环境自适应

### 6.1 目标

领域事实随外部漂移（如 Unreal Engine 5.0 → 5.8 的 API 变化），agent 定义文件若写死过时事实，能力会随时间劣化。此支柱负责**让领域知识跟随环境版本演进**。

### 6.2 机制

- **验证协议（先核实再断言）**：断言任何 API/CVar/模块/功能状态前，先确认版本，再对照权威来源（引擎源码、官方 What's New 页）。这是 unreal-systems-engineer.md 已有的范式，作为所有领域 agent 的通用纪律
- **版本锚定**：每条领域事实标注适用版本（如 "5.8 基线"），防止跨版本误用
- **定期 re-verify**：按周期（如每版本发布后）重跑验证清单，标记"已验证/已废弃/未核实"
- **废弃检测**：re-verify 发现某事实不再成立 → 从活跃区移到 deprecated，触发修正流程（走第 4 章定义修改）
- **知识刷新回环**：版本漂移触发的修正，作为经验写入记忆库（第 3 章），形成"环境变了 → 知识更新 → 经验沉淀"闭环

### 6.3 案例：UE 5.x API 漂移

unreal-systems-engineer.md 已验证的具体教训（来自你的历史会话）：
- `PressInputID` 大小写（ID 大写）需对照官方 Blueprint API 页核实
- Iris 启用是 `.uproject` 插件 + `SetupIrisSupport(Target)` + `-UseIrisReplication=1`，非链接模块
- 5.x 小版本 API 漂移真实存在，禁止假设旧小版本 API 依然存在

这些正是"版本自适应"要自动化的对象：agent 在实践中的每次核实，都应成为可复用的验证记录，而非一次性工作。

---

## 7. 治理与安全

### 7.1 共享/持久化经验需要治理

无论经验进入本地记忆库还是未来共享层，默认具备四个能力（hello-agents 结论）：

1. **权限分层**：只读/候选/提交/审批不同权限级
2. **PII 脱敏**：入库前检测并脱敏（Presidio 式中英检测）
3. **候选验证**：进库前评估质量与有效性
4. **版本审计**：一切变更可追溯到来源与时间

### 7.2 守卫与进化同步演进

前沿安全研究（综述 4.3 节）揭示双向关系：
- **AGrail（arXiv:2502.11448）**：终身 agent 守卫，自适应安全检测——守卫必须随 agent 能力演进
- **AutoDAN-Turbo（arXiv:2410.05295）**：**自进化技术本身可被用于攻击**（策略自探索越狱）——你的进化回路越强，越可能被对抗利用

落地：
- 安全检测不是一次性规则，而是**与进化同步更新的守卫层**（新技能入库即跑审计，新记忆入库即查敏感信息）
- 定期对抗演练：用与攻击者相同的自进化手段检验自身护栏
- 参考 AgentHarm（arXiv:2410.09024）、RedCode（arXiv:2411.07781）的威胁分类做审计清单

### 7.3 技能供应链安全（见 5.4）

技能市场/共享不能只看"写得好不好"，要视为软件包做供应链审计：敏感路径、危险命令、远程脚本、secret 泄露、对记忆/技能的污染企图。

---

## 8. 评估与成功指标

### 8.1 横切原则落地

- **棘轮基线**：每次进化保留"当前最优"快照；新方案在评测集上不高于它 → 回滚
- **评估与生成分离**：L1 独立评估，fresh-context reviewer 审阅改动

### 8.2 评估器升级

从单 LLM 打分升级为更强形式（据综述 4.2 节）：
- **Agent-as-a-Judge**（arXiv:2410.10934）：用 agent 评估 agent，覆盖多步骤行为
- **Auto-Arena**（arXiv:2405.20267）：agent 同行辩论 + 委员会投票，缓解单一判官偏差
- **MCTS-Judge**（arXiv:2502.12468）：对代码正确性做测试时扩展评估

### 8.3 评测集设计

| 维度 | 设计 |
|---|---|
| **固定测试集** | 每领域维护 `test-prompts.json`（Darwin Skill 式），含成功与失败用例、边界用例 |
| **通用基准（可选）** | GAIA（general）、SWE-bench（软件工程）、AgentBench、OSWorld（环境）——验证进化通用性 |
| **领域基准** | UE 场景：test-prompts 集 + 编译/运行验证（Agent 输出可执行性本身就是评测信号） |
| **留出验证集** | 训练/进化用一套，评测用另一套（EvoSkill held-out 原则），防过拟合测试集 |

### 8.4 指标

| 指标 | 含义 | 趋势 |
|---|---|---|
| 任务成功率 | 核心任务在评测集上的通过率 | ↑ |
| 重复错误率 | 同类错误复发频率（记忆库有效性的直接信号） | ↓ |
| 知识复用率 | 已存经验在下游任务中被正确调用比例 | ↑ |
| 记忆库健康度 | 条目数增长但冗余/冲突/失效比例受控 | 平衡 |
| 定义文件健康度 | 大小、规则冲突数、指令被遵循率 | 平衡 |
| 回滚率 | 棘轮触发回滚的比例（异常高=评估器/生成器失配） | 受控 |

---

## 9. 渐进实施路线图

每阶段都有验收标准；只有通过才进入下一阶段。对齐 hello-agents 的"上下文→技能→群体→参数"递进。

### Phase 0 · 地基（0.5–1 周）
- git 仓库管理 agent 定义与记忆目录
- 建立目录约定：`memory/`、`skills/`、`agents/`、`CHANGELOG.md`
- **验收**：agent 定义文件全部入库，改动可 diff、可回滚

### Phase 1 · 跨会话记忆（1–2 周）
- 部署第 3 章生命周期：多源提取 → 质量评估 → 去重/冲突 → 有效性 → 遗忘
- 任务收尾固定流程：Reflect → Distill → Commit
- **验收**：同类问题重复排查次数显著下降；记忆库冗余率受控

### Phase 2 · 技能库（2–4 周）
- 第 5 章技能资产化：候选 → evolutions.json → solidify
- 建立领域 test-prompts 集（8.3）
- **验收**：复用流程以技能形式可被跨会话调用；技能入库有验证记录

### Phase 3 · 定义自改进（持续）
- 第 4 章 GEPA 式反思进化 + HITL 审批 + 棘轮
- **验收**：定义文件修订全部有 diff、有分数对比、可回滚；无膨胀

### Phase 4 · 版本自适应（持续）
- 第 6 章验证协议 + re-verify 周期 + 废弃检测
- **验收**：环境版本升级后，领域知识在主动/被动 re-verify 下保持新鲜

> **阶段推进原则**：前一步未证明"确实让系统变好"（8.4 指标），不要进入下一步。评估器与治理（第 7、8 章）从 Phase 0 起即为默认能力，不是后置项。

---

# 第二部分 · 未来计划（B 级全深度前沿）

> 本部分为概念性前沿方向，**未落地**，供路线图延伸与长期研究。标 ★ 者为与该文档核心最相关的升级路径。

## 10. 未来计划：全深度前沿

### 10.1 多智能体拓扑自动搜索 ★
不再只生成技能，而是对**整个 agent 系统的结构与提示做搜索进化**：
- **AFlow**（arXiv:2410.10762，ICLR'25）：MCTS 搜索工作流图结构 + 提示
- **ADAS / Automated Design of Agentic Systems**（arXiv:2408.08435）：元 Agent 在 agent 程序空间中搜索进化
- **MetaAgent**（arXiv:2507.22606）：基于有限状态机自动构造多智能体
- **GPTSwarm**（arXiv:2402.16823）：agent 作为可优化图
- 落地形态：本工作区现有 subagent 定义集合本身就是一个"agent 拓扑"，可成为搜索对象

### 10.2 符号化自进化 ★
**Symbolic Learning Enables Self-Evolving Agents**（arXiv:2406.18532）：把 agent 程序视为可学习的**符号程序**——梯度无关、可解释、可迭代。比"改 prompt"更系统，是第 4 章的进阶形态。

### 10.3 工具层进化 ★
- **ToolEVO**（arXiv:2410.06617）：学习演化工具定义
- **CREATOR**（arXiv:2305.14318）：agent 运行时创建工具
- **MCP-Zero**（arXiv:2506.01056）：**主动发现**可用 MCP 工具——对应本环境的 MCP 工具治理
- 落地形态：把"上报损坏 MCP 工具"从手工纪律升级为自动检测 + 工具修复候选

### 10.4 群体智能（第三类闭环）
跨会话、跨设备、跨用户、跨 Agent 的经验共享：
- **Ultron**（ModelScope）：Memory Hub / Skill Hub / Harness Hub；分层群体记忆、技能自演化、蓝图分发
- **OpenSpace**（HKUDS）：外部演化服务，技能版本谱系 DAG，失败可触发修复、成功可沉淀
- **SkillClaw**（AMAP-ML）：Client Proxy + 共享存储 + Evolve Server，多端合并去重分发
- **必须前置**（第 7 章）：权限分层、PII 脱敏、候选验证、版本审计

### 10.5 推理记忆 × 测试时扩展 ★
**ReasoningBank / MaTTS**（arXiv:2509.25140）：把"蒸馏推理策略记忆"与"memory-aware test-time scaling"结合——给任务分配更多算力 → 生成多样经验 → 对比信号提炼更高质记忆 → 更好记忆指导更有效扩展。**这是记忆驱动的经验扩展作为新的 scaling 维度**，是第 3 章记忆系统的长期演进方向。

### 10.6 终身学习框架化
**ELL**（arXiv:2508.19005）：经验探索 / 长期记忆 / 技能学习 / 知识内化的完整框架 + StuLife 基准，可作为本设计长期形态的参照系。

## 11. 未来计划：参数级 RL 自进化

> 四类闭环的最强形态，也是最重的：系统直接更新模型权重。前提、风险、触发时机如下。

### 11.1 前沿方法

- **零数据 RL 自进化**：R-Zero（arXiv:2508.05004，self-evolving reasoning LLM from zero data）、SPIRAL（arXiv:2506.24119，多智能体多轮自博弈）
- **自奖励模型**：Self-Rewarding LMs（arXiv:2401.10020）——模型自举训练数据与奖励
- **Agentic RL**：ARPO（arXiv:2507.19849）——针对 agent 行为的强化策略优化；ToolRL/ReTool 等工具使用 RL
- **解耦架构**：Agent Lightning（arXiv:2508.03680）——用 LightningStore 把在线执行观测与可插拔 Trainer 解耦，宿主框架语义不受影响
- **在线 RL 接入**：OpenClaw-RL——真实对话反馈转异步 RL/OPD 信号

### 11.2 前提条件（不满足不做）

1. **评估器成熟**：LLM-as-judge / PRM / 验证器可靠且经校准（评估器比生成器更重要的极端体现）
2. **沙箱与隔离执行**：rollout 在隔离环境（Docker/远程沙箱）执行
3. **版本治理与回滚**：权重可回滚、可对比；LoRA 而非全量
4. **数据合规**：真实用户反馈进入梯度路径前落实知情同意、留存周期、PII 脱敏

### 11.3 风险

- **奖励博弈**：系统学会"迎合评测"而非真正变强
- **上下文级未解先升级**：如果评估、沙箱、权限、版本治理不扎实，参数级只会放大错误
- **合规/法律风险**：技术指标容易被隐私与法律风险抵消

### 11.4 触发时机判断

```
上下文级优化收益递减（8.4 指标连续 N 个周期无提升）
  + 有可靠评测器 + 有隔离沙箱 + 有回滚能力
  → 才考虑参数级 RL
否则：优先走第 10 章（拓扑/符号/工具层）
```

---

## 12. 参考文献

### 12.1 综述与框架
- **A Comprehensive Survey of Self-Evolving AI Agents**（arXiv:2508.07407）+ 维护库 [Awesome-Self-Evolving-Agents](https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents) — 自进化全量索引
- **EvoAgentX: An Automated Framework for Evolving Agentic Workflows**（arXiv:2507.03616）+ [Repo](https://github.com/EvoAgentX/EvoAgentX)
- **Building Self-Evolving Agents via Experience-Driven Lifelong Learning**（ELL，arXiv:2508.19005）
- datawhalechina/hello-agents Extra10「Agent 自进化：四类闭环」 [链接](https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra10-Agent%E8%87%AA%E8%BF%9B%E5%8C%96.md)
- Qoder 博客「从长期记忆到自我进化」 [链接](https://qoder.com/zh/blog/long-term-memory)
- Anthropic「Effective context engineering for AI agents」（2025-09）[链接](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic「Building effective agents」（2024-12）[链接](https://www.anthropic.com/engineering/building-effective-agents)
- Claude Code 最佳实践（CLAUDE.md / skills / subagents / hooks）[链接](https://www.anthropic.com/engineering/claude-code-best-practices)

### 12.2 提示/定义优化（第 4 章）
- **GEPA: Reflective Prompt Evolution Can Outperform RL**（arXiv:2507.19457，ICLR'26 Oral）
- **Promptbreeder**（arXiv:2309.16797）— 自指式提示进化
- **TextGrad**（arXiv:2406.07496）— 文本梯度
- **OPRO / LLMs as Optimizers**（arXiv:2309.03409）
- **EvoPrompt**（arXiv:2309.08532）
- **MIPRO**（arXiv:2406.11695，DSPy）

### 12.3 记忆（第 3 章）
- **ReasoningBank + MaTTS**（arXiv:2509.25140，ICLR'26）
- **A-MEM: Agentic Memory for LLM Agents**（arXiv:2502.12110）
- **Mem0**（arXiv:2504.19413）— 生产级长期记忆
- **MemoryBank**（arXiv:2305.10250）
- **Agent Workflow Memory**（arXiv:2409.07429）
- **Compress to Impress（压缩记忆）**（arXiv:2402.11975）
- **Voyager**（arXiv:2305.16291）— 终身学习 + 技能库 + 自验证（早期奠基）

### 12.4 技能/工具进化（第 5 章）
- **EvoSkill**（arXiv:2603.02766）
- Darwin Skill（[Repo](https://github.com/alchaincyf/darwin-skill)）— 棘轮 + 八维评分
- JiuwenClaw — 在线信号 + evolutions.json solidify
- **ToolEVO**（arXiv:2410.06617）、**CREATOR**（arXiv:2305.14318）、**MCP-Zero**（arXiv:2506.01056）

### 12.5 群体智能 / 拓扑搜索 / 符号化（第 10 章）
- **AFlow**（arXiv:2410.10762）、**ADAS**（arXiv:2408.08435）、**MetaAgent**（arXiv:2507.22606）、**GPTSwarm**（arXiv:2402.16823）
- **Symbolic Learning Enables Self-Evolving Agents**（arXiv:2406.18532）
- Ultron（[Repo](https://github.com/modelscope/ultron)）、OpenSpace（[Repo](https://github.com/HKUDS/OpenSpace)）、SkillClaw（[Repo](https://github.com/AMAP-ML/SkillClaw)）

### 12.6 参数级 RL（第 11 章）
- **R-Zero**（arXiv:2508.05004）、**Self-Rewarding LMs**（arXiv:2401.10020）、**SPIRAL**（arXiv:2506.24119）
- **ARPO**（arXiv:2507.19849）、**Agent Lightning**（arXiv:2508.03680）、OpenClaw-RL

### 12.7 评估与安全（第 7、8 章）
- **Agent-as-a-Judge**（arXiv:2410.10934）、**Auto-Arena**（arXiv:2405.20267）、**MCTS-Judge**（arXiv:2502.12468）
- **AGrail**（arXiv:2502.11448）、**AutoDAN-Turbo**（arXiv:2410.05295）、**AgentHarm**（arXiv:2410.09024）、**RedCode**（arXiv:2411.07781）
- 基准：GAIA（arXiv:2311.12983）、SWE-bench（arXiv:2310.06770）、AgentBench（arXiv:2308.03688）、OSWorld（arXiv:2404.07972）

> 完整性提示：本清单为写作时精选；完整、持续更新的索引见 [Awesome-Self-Evolving-Agents](https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents)。
