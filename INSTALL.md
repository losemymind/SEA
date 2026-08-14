# INSTALL.md — SEA 安装指南

把 SEA 安装到某个目标工作区（如 `E:\TempOpenWork`），使其 agent 获得"可持续进化"能力。

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
   $src = "<SEA 路径>\skills"
   Copy-Item -LiteralPath "$src\task-retrospective" -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$src\skill-craft"        -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$src\agent-improvement"  -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   Copy-Item -LiteralPath "$src\version-verify"     -Destination "$env:USERPROFILE\.config\opencode\skills\" -Recurse -Force
   ```
2. 复制运行时包与纪律到目标工作区：
   ```powershell
   $proj = "<SEA 路径>"
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
   $proj = "<SEA 路径>"
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

安装时 agent 只需知道 **SEA 仓库路径**（如 `E:\GitHub\SEA`），随后：

1. **询问安装方式**：`技能安装到全局（~/.config/opencode/skills/）还是目标工作区（.opencode/skills/）？`
2. 询问目标工作区路径（若未提供）：`目标工作区路径是？`
3. 按所选方式执行上述复制命令（路径自动拼接）
4. 复跑校验确认

> 提示：若 SEA 不在固定路径，可在安装时用绝对路径替换 `<SEA 路径>` 占位符；技能正文中的 `SEA/` 前缀与仓库位置无关，只依赖工作区内的 `SEA/` 目录。

## 验证安装是否成功

在目标工作区执行 `python SEA/scripts/validate-memory.py` 输出 `OK：3 个文件校验通过。`，且 `AGENTS.md` 存在，即安装成功。

---

## 框架升级流程（P0 版本兼容性）

框架使用 `VERSION` 文件管理版本（顶层与 `SEA/VERSION` 保持一致；`SEA/VERSION` 随运行时进入工作区）。升级必须遵循以下纪律：

### 升级前检查已装工作区
```powershell
# 列出/检查已安装工作区是否过期（在框架仓库根目录运行）
# <工作区> 为已安装 SEA 的目标工作区路径（如 E:\TempOpenWork）
python SEA/scripts/framework-version.py --installed <工作区>
```

### 升级步骤（改动框架本身时）
1. **修改版本**：按语义化版本递增 `VERSION` 与 `SEA/VERSION`（两处一致）
2. **记录**：更新 `SEA/CHANGELOG.md`（改动内容、破坏性变更标记）
3. **自检**：`python SEA/scripts/framework-version.py --check`（两处版本一致）+ 复跑全部校验脚本
4. **同步已装工作区**：对所有已安装工作区执行
   ```powershell
   python SEA/scripts/framework-version.py --installed <工作区>   # 确认过期
   # 按安装方式重新复制 SEA/ 与 AGENTS.md（必要时重新复制技能）
   ```
5. **破坏性变更**（技能正文路径、AGENTS.md 结构、脚本参数）必须在 CHANGELOG 标注 `[BREAKING]`，并提示工作区重新同步

### 版本规则
- **主版本**：破坏性结构变更（目录布局、路径约定、脚本 CLI 不兼容）
- **次版本**：新增机制/技能，向后兼容
- **补丁**：修复/文档，无行为变化
- 已安装工作区版本滞后即视为"过期"，用 `framework-version.py --installed` 检测

### 为什么需要版本纪律
框架一旦安装到工作区，技能正文 `SEA/` 前缀、AGENTS.md 结构、脚本参数就成了**对外契约**。没有版本号，未来升级会悄悄破坏已装工作区且无处追责；有了版本号，升级变得可检测、可回滚、可通知。
