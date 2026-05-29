---
name: nash-run
description: "Use when the user asks to run a simulation, execute an experiment, test a game theory model, sweep parameters, compare environments. Triggers on: run simulation, execute experiment, test game, hawk dove, prisoner's dilemma, public goods, common pool, vickrey, parameter sweep, start experiment, compare models."
---

# NASH Run — Simulation Execution (Agent Team Mode)

You are a game theory simulation agent. You execute experiments by invoking the NASH CLI (`uv run nash`). All commands output JSON to stdout, progress to stderr.

> **Memory:** This skill uses Claude Code's native memory system for context persistence. No additional MCP setup needed.

## Multilingual Summary / 多语言概要 / 多言語概要

- English: Orchestrate reproducible simulations (multi-seed, sweeps, multi-model comparisons) by calling the CLI; always follow with validation + visualization; report results with Mermaid/HTML-friendly outputs.
- 中文：通过 CLI 编排可复现实验（多种子、参数扫描、多模型对照）；默认并行跑 validate + viz；用 Mermaid/HTML 友好的格式产出报告。
- 日本語：CLI を呼び出して再現可能な実験（複数シード、パラメータ掃引、モデル比較）を編成し、必ず検証と可視化を並列実行。Mermaid/HTML に適した形式でレポート化する。

## Notes / 约束 / 注意

- English: The scripts must remain generic (no case-specific hardcoding). Core value is the agent-side reasoning: subagents, agent teams, research, and report generation.
- 中文：脚本必须保持通用（不做案例硬编码）。核心价值在通用 Agents 的推理与编排：subagents、agent teams、调研与报告生成。
- 日本語：スクリプトは汎用性を保つ（ケース固有のハードコード禁止）。価値の中心は subagents / agent teams による調査・判断・レポート生成。

## 核心理念：火力全开

**Every run deserves a validate+viz follow-up. Every comparison deserves parallel execution. Every experiment deserves memory persistence.**

- Single run → background it, move on to analysis while it runs
- Multi-model comparison → ALL models in parallel, single message
- Multi-seed → ALL seeds in parallel, compute mean±std after
- Parameter sweep → split range across subagents
- After ANY run → validate + viz in parallel, persist to memory

## 1. When to Use

- User asks to run a simulation, experiment, or game theory test
- User mentions any preset name: `hawk_dove`, `prisoners_dilemma`, `public_goods`, `common_pool`, `vickrey`, `spence`, `matching`, `auction_common_value`
- User wants to sweep parameters: "sweep resource_value from 1 to 10"
- User wants to compare multiple environments or configurations
- User says: run, simulate, test, experiment, sweep, execute, start experiment

## 2. Quick Decision: Which Execution Pattern?

```
User wants to run simulation?
├─ Single model, quick (rounds <= 200) → Preset run + auto validate+viz (Section 3)
├─ Single model, heavy (rounds > 200) → Background task + notify on complete (Section 4)
├─ Compare 2-8 models → Parallel execution ALL at once (Section 5)
├─ Explore parameter space → Config template + sweep (Section 6)
├─ Research-grade reproducibility → 5-seed parallel (Section 7)
└─ Full hypothesis test → Control + treatment groups, both with 5 seeds (Section 8)
```

## 3. Standard Preset Run (with Auto Analysis)

Run a known game environment. Always follow with validate+viz in parallel:

```bash
# Step 1: Run the simulation
uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o results.json

# Step 2: Analyze in parallel (launch both simultaneously)
Bash: uv run nash validate --data results.json --type nobel -o validation.json
Bash: uv run nash viz --data results.json --type all -o charts.png

# Step 3: Persist to memory
mcp__memory__add_observations({...})
```

### Preset Quick Reference

| Preset | Recommended --agents | Typical --rounds | Nobel Year |
|--------|---------------------|-------------------|------------|
| `hawk_dove` | 100 | 200 | 2005 (Aumann, Schelling) |
| `prisoners_dilemma` | 100 | 200 | 2005 (Aumann, Schelling) |
| `public_goods` | 100 | 200 | 2009 (Ostrom) |
| `common_pool` | 100 | 200 | 2009 (Ostrom) |
| `vickrey` | 50 | 100 | 1996 (Vickrey) |
| `spence` | 50 | 100 | 2001 (Akerlof, Spence, Stiglitz) |
| `matching` | 50 | 100 | 2012 (Roth, Shapley) |
| `auction_common_value` | 50 | 100 | 2020 (Milgrom, Wilson) |

Key parameters:
- `--preset`: game environment (REQUIRED)
- `--agents`: number of agents (10-1000)
- `--rounds`: simulation rounds (default: 100)
- `--seed`: random seed for reproducibility
- `-o` / `--output`: save results to JSON file

## 4. Background Execution for Heavy Simulations

When rounds > 200 or agents > 500, run in background. You'll be notified on completion.

```bash
# Launch in background — don't wait
Bash(run_in_background=true): uv run nash run --preset hawk_dove --agents 500 --rounds 1000 --seed 42 -o large_run.json
```

While the simulation runs, continue with other work. When notified:
1. Read `large_run.json` to check convergence
2. Launch validate+viz in parallel
3. Report results to user

**Pro tip:** You can launch multiple heavy simulations in background simultaneously:
```
Bash(run_in_background=true): uv run nash run --preset hawk_dove --agents 500 --rounds 500 --seed 42 -o bg_hd.json
Bash(run_in_background=true): uv run nash run --preset prisoners_dilemma --agents 500 --rounds 500 --seed 42 -o bg_pd.json
Bash(run_in_background=true): uv run nash run --preset public_goods --agents 500 --rounds 500 --seed 42 -o bg_pg.json
Bash(run_in_background=true): uv run nash run --preset common_pool --agents 500 --rounds 500 --seed 42 -o bg_cp.json
```

## 5. Parallel Multi-Model Comparison (Agent Team Power)

When comparing environments, launch ALL in ONE message. Never run sequentially.

```bash
# User asks: "Compare hawk_dove, prisoners_dilemma, public_goods, and common_pool"

# Launch ALL 4 in ONE message as parallel Bash calls:
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o compare_hawk_dove.json
Bash: uv run nash run --preset prisoners_dilemma --agents 100 --rounds 200 --seed 42 -o compare_pd.json
Bash: uv run nash run --preset public_goods --agents 100 --rounds 200 --seed 42 -o compare_pg.json
Bash: uv run nash run --preset common_pool --agents 100 --rounds 200 --seed 42 -o compare_cp.json
```

**After all complete, collect results and present comparison table:**

```bash
python -c "
import json, glob
print('| Environment | Converged | Key Metric | Value |')
print('|-------------|-----------|------------|-------|')
for f in sorted(glob.glob('compare_*.json')):
    with open(f) as fp:
        d = json.load(fp)
    env = d.get('environment', 'unknown')
    conv = 'Yes' if d.get('converged') else 'No'
    metrics = d.get('final_metrics', {})
    for k, v in metrics.items():
        print(f'| {env} | {conv} | {k} | {v:.3f} |')
        break
"
```

**Then validate ALL in parallel:**
```bash
Bash: uv run nash validate --data compare_hawk_dove.json --type nobel
Bash: uv run nash validate --data compare_pd.json --type nobel
Bash: uv run nash validate --data compare_pg.json --type nobel
Bash: uv run nash validate --data compare_cp.json --type nobel
```

## 6. Parameter Sweep

When exploring a parameter range, first generate a config template, then sweep.

### Small sweep (<= 100 configs)

```bash
# Step 1: Generate config template
uv run nash config template --preset hawk_dove -o cfg.json

# Step 2: Sweep over a parameter
uv run nash sweep --config cfg.json --param resource_value --range 1,10 --step 1 --rounds 200 -o sweep.json
```

### Large sweep (> 100 configs) — Split across subagents

Split the range across 4 parallel subagents:

```
Agent({description: "Sweep part 1",
       prompt: "Run: uv run nash sweep --config cfg.json --param resource_value --range 0,125 --step 25 --rounds 100 -o sweep_p1.json"})

Agent({description: "Sweep part 2",
       prompt: "Run: uv run nash sweep --config cfg.json --param resource_value --range 125,250 --step 25 --rounds 100 -o sweep_p2.json"})

Agent({description: "Sweep part 3",
       prompt: "Run: uv run nash sweep --config cfg.json --param resource_value --range 250,375 --step 25 --rounds 100 -o sweep_p3.json"})

Agent({description: "Sweep part 4",
       prompt: "Run: uv run nash sweep --config cfg.json --param resource_value --range 375,500 --step 25 --rounds 100 -o sweep_p4.json"})
```

**Merge when all complete:**

```bash
python -c "
import json, glob
all_results = []
for f in sorted(glob.glob('sweep_p*.json')):
    with open(f) as fp:
        data = json.load(fp)
        all_results.extend(data['results'])
with open('sweep_merged.json', 'w') as out:
    json.dump({'status': 'completed', 'results': all_results, 'total': len(all_results)}, out, indent=2)
"
```

## 7. Multi-Seed Reproducibility (Default for Research)

For research-grade results, always run 5 seeds. Launch ALL in parallel:

```bash
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o seed_42.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 123 -o seed_123.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 456 -o seed_456.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 789 -o seed_789.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 1024 -o seed_1024.json
```

**After all complete, compute mean±std:**

```bash
python -c "
import json, glob, numpy as np
seeds = []
for f in sorted(glob.glob('seed_*.json')):
    with open(f) as fp:
        d = json.load(fp)
        seeds.append(d['final_metrics'])

# Compute per-metric mean and std
keys = seeds[0].keys()
for k in keys:
    vals = [s[k] for s in seeds]
    print(f'{k}: {np.mean(vals):.4f} ± {np.std(vals):.4f}')
print(f'CV: {np.std([s[list(keys)[0]] for s in seeds]) / np.mean([s[list(keys)[0]] for s in seeds]):.1%}')
"
```

Report: if CV < 10%, results are robust. Otherwise, increase seeds or rounds.

## 8. Full Hypothesis Test (Control vs Treatment)

When testing a causal hypothesis (e.g., "does punishment reduce free-riding?"), design control and treatment groups:

**Step 1 — Generate base configs**

```bash
uv run nash config template --preset public_goods -o ctrl_cfg.json
uv run nash config template --preset public_goods -o treat_cfg.json
# Manually edit treat_cfg.json to add treatment (e.g., punishment mechanism)
```

**Step 2 — Run both groups with 5 seeds each (ALL in parallel)**

```bash
# Control group (5 seeds)
Bash: uv run nash run --config ctrl_cfg.json --seed 42 -o ctrl_s42.json
Bash: uv run nash run --config ctrl_cfg.json --seed 43 -o ctrl_s43.json
Bash: uv run nash run --config ctrl_cfg.json --seed 44 -o ctrl_s44.json
Bash: uv run nash run --config ctrl_cfg.json --seed 45 -o ctrl_s45.json
Bash: uv run nash run --config ctrl_cfg.json --seed 46 -o ctrl_s46.json
# Treatment group (5 seeds)
Bash: uv run nash run --config treat_cfg.json --seed 42 -o treat_s42.json
Bash: uv run nash run --config treat_cfg.json --seed 43 -o treat_s43.json
Bash: uv run nash run --config treat_cfg.json --seed 44 -o treat_s44.json
Bash: uv run nash run --config treat_cfg.json --seed 45 -o treat_s45.json
Bash: uv run nash run --config treat_cfg.json --seed 46 -o treat_s46.json
```

**Step 3 — Statistical comparison**

```bash
uv run nash validate --type statistical \
  --control-group "$(python -c 'import json,glob; print(json.dumps([json.load(open(f))["final_metrics"] for f in sorted(glob.glob("ctrl_s*.json"))]))')" \
  --treatment-group "$(python -c 'import json,glob; print(json.dumps([json.load(open(f))["final_metrics"] for f in sorted(glob.glob("treat_s*.json"))]))')"
```

Report: p-value, effect size (Cohen's d), and whether hypothesis is supported.

## 9. Memory Persistence (Every Run)

After EVERY experiment, persist to native memory. This builds a cross-session knowledge base.

```python
mcp__memory__add_observations({
    "observations": [
        {
            "entityName": f"experiment:{preset_name}-{timestamp}",
            "contents": [
                f"Preset: {preset_name}",
                f"Config: agents={n_agents}, rounds={n_rounds}, seed={seed}",
                f"Converged: {converged}",
                f"Final metrics: {json.dumps(metrics)}",
                f"Nobel validation: {nobel_conclusion}",
                f"Timestamp: {iso_timestamp}"
            ]
        }
    ]
})
```

**Minimum data to record for every run:**
- Preset name, agent count, rounds, seed
- Final metrics summary
- Convergence status and message
- Nobel validation result (if run)
- Timestamp (ISO format)

## 10. CLI Quick Reference

```bash
# Run presets
uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o results.json
uv run nash run --preset prisoners_dilemma --agents 100 --rounds 200 --seed 42
uv run nash run --preset public_goods --agents 100 --rounds 200
uv run nash run --preset common_pool --agents 100 --rounds 200
uv run nash run --preset vickrey --agents 50 --rounds 100
uv run nash run --preset spence --agents 50 --rounds 100
uv run nash run --preset matching --agents 50 --rounds 100
uv run nash run --preset auction_common_value --agents 50 --rounds 100

# Config + sweep
uv run nash config template --preset hawk_dove -o cfg.json
uv run nash config validate cfg.json
uv run nash sweep --config cfg.json --param resource_value --range 1,10 --step 1 --rounds 200 -o sweep.json
```

## 11. Error Recovery

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `No module named 'src'` | Python path not set | Run from nash-cli/ root directory. |
| `Unknown preset: X` | Typo or unsupported preset | Run `uv run nash env list` to see all 8 presets. |
| Simulation crashes mid-run | Too many agents | Reduce `--agents` to 50-100, reduce `--rounds` to 50-100. |
| Sweep config parse error | Wrong config format | Use `config template --preset <name>` first, then edit. |
| matplotlib not installed | Missing dep | `pip install matplotlib` |
| Background task timeout | Too many rounds | Reduce rounds or split into multiple shorter runs. |

## 12. Cross-References

- [[nash-cli]] -- CLI execution engine (all run/sweep/config commands)
- [[nash-env]] -- to list available environments and understand game mechanics before running
- [[nash-analyze]] -- to statistically validate results and generate visualizations after running
- [[nash-game-theory]] -- to create new custom game environments
