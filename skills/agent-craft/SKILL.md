---
name: agent-craft
description: 从任务描述或历史经验生成新的子 Agent 定义文件（.md），输出到 opencode 可识别的 agents 目录（.opencode/agents/ 或全局 ~/.config/opencode/agents/），带质量评估、HITL 审批与棘轮回滚。用于扩充 agent 拓扑、把重复角色固化为专用子 Agent。
---

# 子 Agent 生成与入库

## 何时使用
- 出现重复出现的角色/职责，值得固化为专用子 Agent
- 单个长任务可拆分为多个小上下文子 Agent（§5.5：并行子 Agent 优于单 Agent 长任务）
- 从 `SEA/memory/` 经验或用户纠正中识别出可固化的行为约定
- 需要生成多个子 Agent 协同完成目标（多智能体工作流）

## 不生成（拒绝路径）
遇到以下情况**拒绝生成**定义文件，不登记候选：
- 无独立职责：任务是主 Agent 顺手能做的小事（如"写一行字"），固化成子 Agent 无增益
- 无评测价值：无法为它构造可验证的 success/failure 用例
- 职责重叠：与已有 agent 边界不清，应先合并/扩展而非新建
- 说明拒绝理由并建议替代方案（继续用主 Agent / 扩展现有 agent）

## 流程（严格按序）

### 1. 识别与登记候选
- 确认需求可归因到一个独立职责，而非已有 agent 的扩展
- 在 `SEA/agents/_improvements/improvements.json` 追加 `status: pending` 条目（target 指向待生成的 agent 名，kind=CAPTURED）
- 跑 `python SEA/scripts/validate-agent-improvements.py` 校验

### 2. 生成定义（Generate）
- 复制 `SEA/templates/agent-definition.md` 到目标位置：工作区 `.opencode/agents/<name>.md` 或全局 `~/.config/opencode/agents/<name>.md`
- frontmatter 必填：`name`（kebab-case，与文件名一致）、`description`（含触发条件，供 Task 工具自动匹配）、`mode: subagent`、`temperature`
- `model` 可选：不填则 subagent 默认使用调用它的主 Agent 的模型（primary agent 使用全局配置模型）；需要专用模型（如更快/更省）时才显式指定
- 正文按模板各小节填：硬规则 / 身份与记忆 / 核心使命 / 关键技术交付物 / 调试清单 / 响应契约 / 版本纪律 / 学习与记忆
- 若生成多个子 Agent，检查职责不重叠、边界清晰

### 3. 评估（Evaluate，独立于生成）
- 结构侧：frontmatter 完整、目录位置正确、可被 opencode 发现
- 效果侧：为该 agent 建 `test-prompts.json`（success/failure/boundary 用例），记 `score_before`
- 对照 `SEA/agents/_improvements/baselines.json` 的 `best_score`；更低则以 `score_before` 为棘轮参考

### 4. HITL 审批（Confirm）
- 展示：生成的 agent 定义 diff + `score_before`/`score_after` 变化 + 结构检查结果
- 人工 approve → 继续；reject → 状态置 `rejected`，删除生成文件

### 5. 入库与棘轮（Keep or Revert）
- `score_after > best_score` → 保留定义，更新 `baselines.json`，状态置 `approved`
- 否则 → 删除生成文件，状态置 `reverted`；基线单调不降
- 更新 `SEA/CHANGELOG.md`，git 提交（信息含 agent 名与来源）

## 供应链审计（入库前必查）
- 不读取敏感路径 / 不执行危险命令 / 不下载远程脚本
- 不把 secret 写入 agent 定义 / 不污染其他 agent、技能或记忆
- agent 定义中的权限（permission）默认最小化，按需放行

## 验收
- 通过 `validate-agent-improvements.py` 与 `validate-skill.py`
- 生成的定义被 opencode 识别：会话中 `@<name>` 可调用（重启 opencode 后生效）
- 状态机一致：pending → approved / rejected / reverted
- CHANGELOG 已更新，git 干净

## 反例（不要这样）
- 无评测分数就入库（违背棘轮）
- 跳过 HITL 审批直接 solidify
- 生成职责重叠的多个 agent
- 把主 agent 能做的小事固化为新 agent（过度拆解）
