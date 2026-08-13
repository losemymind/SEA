# CHANGELOG — 进化留痕

每次记忆/技能/定义变更在此记录，与 git 提交对应。

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
