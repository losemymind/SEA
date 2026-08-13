# CHANGELOG — 进化留痕

每次记忆/技能/定义变更在此记录，与 git 提交对应。

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
