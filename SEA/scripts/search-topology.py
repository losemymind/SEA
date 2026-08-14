#!/usr/bin/env python3
"""search-topology.py — 多智能体拓扑自动搜索（§10.1，ADAS/AFlow 思路的最小落地）。

在 agent 程序空间搜索更优拓扑：基于现有 agent 定义池生成候选拓扑，
用确定性评估打分，棘轮只保留高于当前最优的候选。

搜索策略（迭代 budget 次）:
  1. 初始候选（seeded）：
     - single:  每个 agent 单独成拓扑
     - chain:   按目录顺序串成链（前序 → 后序）
     - parallel: 全部 agent 并行（无边的中心拓扑）
  2. 变异（mutation）：随机选一个已保留候选，做一次小变异：
     - 加边 / 删边 / 换一个 agent / 反转边方向
  3. 评估：复用 evaluate-skill 的 evaluate_topology（结构+覆盖+一致性）
  4. 棘轮：score > best_score 才写入注册表（status=approved），否则丢弃

用法:
    python SEA/scripts/search-topology.py [--budget N] [--agents-dir <目录>]
                                          [--topology <topology.json 路径>]
    python SEA/scripts/search-topology.py --dry-run   # 只评估既有候选，不生成新拓扑

退出码: 0 完成（无论是否找到更优）; 1 参数/IO 错误。
零第三方依赖（仅标准库）。
"""

import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOPO = ROOT / "agents" / "topology.json"
VALID_STATUS = {"pending", "approved", "reverted"}


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def discover_agents(agents_dir: Path, templates_dir: Path):
    """收集可用 agent 名：优先 .opencode/agents/，其次 templates/ 下非模板名。"""
    names = set()
    if agents_dir.exists():
        for f in agents_dir.glob("*.md"):
            names.add(f.stem)
    if templates_dir.exists():
        for f in templates_dir.glob("*.md"):
            if not f.name.startswith(("agent-definition", "skill-template")):
                names.add(f.stem)
    return sorted(names)


def evaluate_topo(topo, agents_dir, templates_dir):
    """复用 evaluate-skill 的打分逻辑（结构+覆盖+一致性）。"""
    import importlib.util
    es_path = Path(__file__).resolve().parent / "evaluate-skill.py"
    spec = importlib.util.spec_from_file_location("evaluate_skill", es_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.evaluate_topology(topo, agents_dir, templates_dir)


def make_candidate(agents, mode, base_id, created):
    """生成一个候选拓扑字典。"""
    agents = sorted(set(agents))
    topo = {
        "id": base_id,
        "name": f"{mode}@{created}",
        "description": f"{mode} 拓扑候选（§10.1 自动搜索生成）",
        "agents": agents,
        "edges": [],
        "status": "pending",
        "score": None,
        "created": created,
        "source": "search-topology.py 自动生成",
    }
    if mode == "chain":
        topo["edges"] = [{"from": agents[i], "to": agents[i + 1], "when": "顺序执行"}
                         for i in range(len(agents) - 1)]
    return topo


def mutate(topo, agent_pool, rng):
    """对候选做一次小变异。"""
    import copy
    m = copy.deepcopy(topo)
    agents = list(m.get("agents", []))
    edges = list(m.get("edges", []) or [])
    op = rng.choice(["add_edge", "del_edge", "swap_agent", "flip_edge"])
    if op == "add_edge" and len(agents) >= 2:
        a, b = rng.sample(agents, 2)
        edges.append({"from": a, "to": b, "when": "变异新增"})
    elif op == "del_edge" and edges:
        edges.pop(rng.randrange(len(edges)))
    elif op == "swap_agent" and agent_pool:
        spare = [a for a in agent_pool if a not in agents]
        if spare:
            idx = rng.randrange(len(agents))
            agents[idx] = spare[rng.randrange(len(spare))]
            edges = [e for e in edges if e["from"] in agents and e["to"] in agents]
    elif op == "flip_edge" and edges:
        e = edges[rng.randrange(len(edges))]
        e["from"], e["to"] = e["to"], e["from"]
    m["agents"] = agents
    m["edges"] = edges
    return m


def next_id(data, created):
    ids = [t.get("id", "") for t in data.get("topologies", [])]
    nums = [int(i.split("-")[-1]) for i in ids if i.startswith("tp-")]
    return f"tp-{created.replace('-', '')}-{max(nums, default=0) + 1:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=10, help="变异迭代次数（默认 10）")
    ap.add_argument("--agents-dir", type=str, default=None,
                    help="agent 定义目录（默认 cwd/.opencode/agents）")
    ap.add_argument("--topology", type=str, default=str(DEFAULT_TOPO),
                    help="拓扑注册表路径")
    ap.add_argument("--dry-run", action="store_true",
                    help="只评估既有候选，不生成新拓扑")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（可复现）")
    args = ap.parse_args()

    topo_path = Path(args.topology)
    if not topo_path.exists():
        print(f"[ERROR] 拓扑注册表不存在: {topo_path}", file=sys.stderr)
        return 1
    data = load_json(topo_path)
    if not isinstance(data, dict):
        print(f"[ERROR] {topo_path.name} 解析失败", file=sys.stderr)
        return 1

    agents_dir = Path(args.agents_dir) if args.agents_dir \
        else Path.cwd() / ".opencode" / "agents"
    templates_dir = ROOT / "templates"
    agent_pool = discover_agents(agents_dir, templates_dir)
    if not agent_pool:
        print(f"[ERROR] 没有可用 agent 定义（{agents_dir} 为空）", file=sys.stderr)
        return 1
    print(f"可用 agent: {agent_pool}")

    created = dt.date.today().isoformat()
    existing = data.get("topologies", []) or []

    if args.dry_run:
        best = None
        for t in existing:
            score, parts = evaluate_topo(t, agents_dir, templates_dir)
            print(f"  {t.get('id')} {t.get('name')}: {score:.3f} "
                  f"(struct={parts['structure']:.2f} cov={parts['coverage']:.2f} "
                  f"coh={parts['coherence']:.2f}) [{t.get('status')}]")
            if best is None or score > best[0]:
                best = (score, t.get("id"))
        print(f"\n当前最优: {best}")
        return 0

    rng = random.Random(args.seed)
    best_score = 0.0
    kept = 0
    rejected = 0

    # 1. 初始候选
    seed_modes = ["single", "chain", "parallel"]
    for mode in seed_modes:
        if mode == "single":
            seeds = [[a] for a in agent_pool]
        elif mode == "chain":
            seeds = [agent_pool]
        else:
            seeds = [agent_pool]
        for agents in seeds:
            cand = make_candidate(agents, mode, next_id(data, created), created)
            score, parts = evaluate_topo(cand, agents_dir, templates_dir)
            if score > best_score:
                best_score = score
                cand["score"] = round(score, 3)
                cand["status"] = "approved"
                existing.append(cand)
                data["topologies"] = existing
                topo_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
                kept += 1
                print(f"  [保留] {cand['id']} {mode}: {score:.3f} "
                      f"(struct={parts['structure']:.2f} cov={parts['coverage']:.2f} "
                      f"coh={parts['coherence']:.2f})")
            else:
                rejected += 1
                print(f"  [丢弃] {mode}: {score:.3f} ≤ 最优 {best_score:.3f}")

    # 2. 变异搜索
    pool = [t for t in data.get("topologies", []) if t.get("status") == "approved"]
    for i in range(args.budget):
        if not pool:
            break
        parent = rng.choice(pool)
        cand = mutate(parent, agent_pool, rng)
        cand["id"] = next_id(data, created)
        cand["name"] = f"mut@{created}-{i + 1}"
        cand["created"] = created
        cand["source"] = f"search-topology.py 变异（源于 {parent.get('id')}）"
        cand["status"] = "pending"
        cand["score"] = None
        score, parts = evaluate_topo(cand, agents_dir, templates_dir)
        if score > best_score:
            best_score = score
            cand["score"] = round(score, 3)
            cand["status"] = "approved"
            existing.append(cand)
            data["topologies"] = existing
            topo_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
            kept += 1
            print(f"  [保留] {cand['id']} mut#{i + 1}: {score:.3f} "
                  f"(struct={parts['structure']:.2f} cov={parts['coverage']:.2f} "
                  f"coh={parts['coherence']:.2f})")
            pool.append(cand)
        else:
            rejected += 1

    print(f"\n搜索完成：保留 {kept}，丢弃 {rejected}，当前最优 {best_score:.3f}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
