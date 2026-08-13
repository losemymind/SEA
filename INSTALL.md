# INSTALL.md — AgentsSelfEvolution 安装指南

把 AgentsSelfEvolution 安装到某个目标工作区（如 `E:\TempOpenWork`），使其 agent 获得"可持续进化"能力。

## 安装内容

| 组件 | 说明 | 安装到 |
|---|---|---|
| `skills/`（4 技能） | task-retrospective / skill-craft / agent-improvement / version-verify | 全局 或 工作区（二选一，见下） |
| `SEA/`（运行时包） | 脚本 / 记忆 / 模板 / 改进注册表 / CHANGELOG | 工作区根目录 |
| `AGENTS.md` | 可持续进化纪律（硬规则 + 闭环 + 收尾协议） | 工作区根目录 |

> 路径约定：所有技能正文、AGENTS.md 内的脚本/记忆/模板引用均使用 `SEA/` 前缀（相对工作区根），因此技能无论装在全局还是工作区，运行时都解析到目标工作区的 `SEA/` 目录。**技能可运行的前提是目标工作区已安装 `SEA/`。**

---

## 方式一：技能安装到全局（`~/.config/opencode/skills/`）

**适用**：希望多个工作区共享同一套技能，装一次即可。

### 步骤
1. 复制技能到全局技能库：
   ```powershell
   $src = "<AgentsSelfEvolution 路径>\skills"
   Copy-Item -LiteralPath "$src\task-retrospective" -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$src\skill-craft"        -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$src\agent-improvement"  -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$src\version-verify"     -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   ```
2. 复制运行时包与纪律到目标工作区：
   ```powershell
   $proj = "<AgentsSelfEvolution 路径>"
   $dst  = "<目标工作区，如 E:\TempOpenWork>"
   Copy-Item -LiteralPath "$proj\SEA"       -Destination $dst -Recurse -Force
   Copy-Item -LiteralPath "$proj\AGENTS.md" -Destination $dst -Force
   ```
3. 重启 opencode，使全局技能生效。
4. 校验（在工作区根目录）：
   ```powershell
   python SEA/scripts/validate-memory.py
   python SEA/scripts/dedup-check.py
   python SEA/scripts/validate-agent-improvements.py
   python SEA/scripts/verify-versions.py
   # 技能在全局已过质量门；工作区无需跑 validate-skill（技能演进注册表留在框架仓库）
   ```

### 结果
- 技能在**所有**工作区（含未来新建）均可被 agent 调用
- `_evolutions/evolutions.json`（技能演进注册表）留在框架仓库 `skills/_evolutions/`
- 工作区根目录只新增 `SEA/` 与 `AGENTS.md`

---

## 方式二：技能安装到工作区（`.opencode/skills/`）

**适用**：只想让某个工作区获得能力，或需要该工作区独立维护技能演进。

### 步骤
1. 复制技能与演进注册表到工作区技能库：
   ```powershell
   $proj = "<AgentsSelfEvolution 路径>"
   $dst  = "<目标工作区，如 E:\TempOpenWork>"
   New-Item -ItemType Directory -Path "$dst\.opencode\skills" -Force | Out-Null
   Copy-Item -LiteralPath "$proj\skills\task-retrospective" -Destination "$dst\.opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$proj\skills\skill-craft"        -Destination "$dst\.opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$proj\skills\agent-improvement"  -Destination "$dst\.opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$proj\skills\version-verify"     -Destination "$dst\.opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$proj\skills\_evolutions"        -Destination "$dst\.opencode\skills\" -Recurse -Force
   ```
2. 复制运行时包与纪律到目标工作区：
   ```powershell
   Copy-Item -LiteralPath "$proj\SEA"       -Destination $dst -Recurse -Force
   Copy-Item -LiteralPath "$proj\AGENTS.md" -Destination $dst -Force
   ```
3. 重启 opencode，使工作区技能生效。
4. 校验（在工作区根目录）：
   ```powershell
   python SEA/scripts/validate-memory.py
   python SEA/scripts/dedup-check.py
   python SEA/scripts/validate-agent-improvements.py
   python SEA/scripts/verify-versions.py
   python SEA/scripts/validate-skill.py --skills-dir .opencode/skills
   ```

### 结果
- 技能只在目标工作区生效，其他工作区不受影响
- 技能演进注册表 `_evolutions/evolutions.json` 随技能进入工作区，工作区可完整跑 `validate-skill.py`

---

## 两方式对比

| 维度 | 方式一（全局） | 方式二（工作区） |
|---|---|---|
| 生效范围 | 所有工作区 | 仅目标工作区 |
| evolutions 归属 | 框架仓库 | 随 `.opencode/skills/` |
| 工作区是否跑 validate-skill | 否（技能已在框架过门） | 是 |
| 多工作区扩展 | 装一次即可 | 每个工作区都要装 |
| 适合场景 | 统一工具链、多项目 | 单项目隔离、独立演进 |

---

## 指定路径与询问机制

安装时 agent 只需知道 **AgentsSelfEvolution 仓库路径**（如 `E:\GitHub\AgentsSelfEvolution`），随后：

1. **询问安装方式**：`技能安装到全局（~/.config/opencode/skills/）还是目标工作区（.opencode/skills/）？`
2. 询问目标工作区路径（若未提供）：`目标工作区路径是？`
3. 按所选方式执行上述复制命令（路径自动拼接）
4. 复跑校验确认

> 提示：若 AgentsSelfEvolution 不在固定路径，可在安装时用绝对路径替换 `<AgentsSelfEvolution 路径>` 占位符；技能正文中的 `SEA/` 前缀与仓库位置无关，只依赖工作区内的 `SEA/` 目录。

## 验证安装是否成功

在目标工作区执行 `python SEA/scripts/validate-memory.py` 输出 `OK：3 个文件校验通过。`，且 `AGENTS.md` 存在，即安装成功。
