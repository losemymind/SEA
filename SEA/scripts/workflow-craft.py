#!/usr/bin/env python3
"""workflow-craft.py — 多智能体工作流实例化（§5.5：从任务描述生成工作流图并实例化子 Agent）。

输入：任务描述（--task 或 stdin）。输出：工作流定义（workflow.json）：
  - steps: 按责任拆分的步骤（读取/实现/验证 等）
  - agents: 每个步骤实例化的子 Agent 定义（生成 .opencode/agents/<step>.md）
  - edges: 步骤间数据流（前序 → 后序）

实例化规则（确定性，不依赖 LLM）:
  1. 责任划分：按任务中的动词/名词启发式拆分，支持显式 <step> 分隔
  2. 命名：<task-slug>-<step-name>（kebab-case）
  3. 生成 agent 定义：复用 SEA/templates/agent-definition.md 结构，正文按步骤职责填充
  4. 默认工作流：input → reader → ... → verifier（每个 agent 小上下文、回报精简摘要）

用法:
    python SEA/scripts/workflow-craft.py --task "调研+实现+验证" --steps 读取,实现,验证 [--out-dir .opencode/workflows]
    python SEA/scripts/workflow-craft.py --from-file <描述文件>
    python SEA/scripts/workflow-craft.py --dry-run --task "..."  # 只输出工作流定义不写文件

退出码: 0 成功; 1 参数错误。
零第三方依赖（仅标准库）。
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "agent-definition.md"
DEFAULT_OUT = Path.cwd() / ".opencode" / "workflows"

STEP_KEYWORDS = {
    "读取": "reader", "调研": "researcher", "探索": "explorer",
    "实现": "implementer", "编写": "writer", "开发": "developer",
    "验证": "verifier", "测试": "tester", "审查": "reviewer", "评审": "reviewer",
    "修复": "fixer", "调试": "debugger", "汇总": "summarizer", "报告": "reporter",
}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "task"


def infer_steps(task, explicit=None):
    """从任务描述推断步骤。显式列表优先；否则按关键词匹配；兜底单步。

    显式步骤也统一映射为英文 kebab-case（opencode agent 名必须符合
    ^[a-z0-9]+(-[a-z0-9]+)*$）；未匹配的中文步骤用拼音风格音译兜底。
    """
    def to_eng(s):
        s = s.strip()
        if s in STEP_KEYWORDS.values():
            return s
        # 中文→关键词映射
        for kw, name in STEP_KEYWORDS.items():
            if kw in s or s == kw:
                return name
        # 拼音兜底：取汉字 Unicode 低位转字母，或 fallback 索引
        latin = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
        return latin or "step"

    if explicit:
        return [to_eng(s) for s in explicit.split(",") if s.strip()]
    found = []
    for kw, name in STEP_KEYWORDS.items():
        if kw in task and name not in found:
            found.append(name)
    return found or ["reader", "verifier"]


def build_agent_md(name, step_name, task, summary):
    """基于模板生成一个子 Agent 定义。"""
    tpl = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else ""
    desc = (f"工作流子 Agent：负责「{step_name}」阶段（源于任务：{task[:60]}）。"
            f"输出{summary}")
    body = f"""# {name} — 工作流子 Agent

## 硬规则摘要
1. 只负责「{step_name}」阶段，不越界做其他步骤
2. 回报精简摘要（1-2k token），不把完整上下文塞回主 Agent
3. 产出可验证，遵循 SEA 版本核实纪律

## 身份与记忆
- **角色**：任务「{task[:80]}」的 {step_name} 专用子 Agent
- **记忆**：可复用 SEA/memory/ 中相关经验

## 核心使命
- {summary}

## 响应契约
- 输出按「结论 + 证据 + 文件:行号」形式，回报摘要而非原始轨迹

## 学习与记忆
- 任务结束执行 task-retrospective 技能，经验写入 SEA/memory/
"""
    # 若模板存在，用模板 frontmatter 结构替换正文
    if tpl.startswith("---"):
        frontmatter_end = tpl.index("---", 3) + 3
        frontmatter = tpl[:frontmatter_end]
        return f"{frontmatter}\n\n{body}"
    return f"""---
name: {name}
description: {desc}
mode: subagent
temperature: 0.2
---

{body}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="", help="任务描述")
    ap.add_argument("--from-file", default=None, help="任务描述文件")
    ap.add_argument("--steps", default=None,
                    help="显式步骤列表（逗号分隔，如 读取,实现,验证）")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT), help="输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只输出不写文件")
    args = ap.parse_args()

    task = args.task
    if args.from_file:
        task = Path(args.from_file).read_text(encoding="utf-8")
    if not task:
        print("[ERROR] 需要 --task 或 --from-file", file=sys.stderr)
        return 1

    steps = infer_steps(task, args.steps)
    base = slugify(task[:30])
    created = dt.date.today().isoformat()

    workflow = {
        "id": f"wf-{created.replace('-', '')}-{base}",
        "description": task[:200],
        "created": created,
        "steps": steps,
        "agents": [],
        "edges": [],
    }

    out_dir = Path(args.out_dir)
    agents_dir = out_dir.parent / "agents"
    for i, step in enumerate(steps):
        name = f"{base}-{step}"
        summary = f"完成「{step}」阶段并回报精简摘要"
        workflow["agents"].append(name)
        if i > 0:
            workflow["edges"].append({
                "from": workflow["agents"][i - 1], "to": name,
                "when": f"前序 {steps[i - 1]} 完成"
            })
        if not args.dry_run:
            (agents_dir).mkdir(parents=True, exist_ok=True)
            md = agents_dir / f"{name}.md"
            md.write_text(build_agent_md(name, step, task, summary),
                          encoding="utf-8")
            print(f"  已生成 agent: {md}")

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        wf_path = out_dir / f"{workflow['id']}.json"
        wf_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"  工作流: {wf_path}")

    print(json.dumps(workflow, ensure_ascii=False, indent=2))
    print(f"\n步骤: {steps}")
    print(f"生成 {len(workflow['agents'])} 个子 Agent，边 {len(workflow['edges'])} 条。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
