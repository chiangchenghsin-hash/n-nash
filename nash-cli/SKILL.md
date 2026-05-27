---
name: nash-cli
description: "NASH computational core — CLI and game theory simulation engine. Provides env list/info, run, sweep, validate, viz, and config commands. Use when running simulations, listing environments, validating results, generating visualizations, or sweeping parameters. This skill is a dependency of nash-env, nash-run, nash-analyze, and nash-game-theory."
---

# NASH CLI — Computational Core

You are the NASH CLI execution engine. You provide the `uv run nash` command that all other NASH skills depend on.

Agent intelligence (memory, planning, task management, narrative generation, result analysis) is provided by Claude Code's built-in capabilities (subagents, agent teams, memory system, task tracking) — not by the simulation engine itself. NASH CLI focuses purely on game-theoretic simulation.

## Architecture

```
nash-cli/
├── pyproject.toml
├── src/
│   ├── contracts.py                  — Pydantic data models (minimal)
│   ├── statistical_validator.py      — t-test, Mann-Whitney, KS test, Gini
│   ├── visualization.py              — BeliefVisualizer, PhaseDiagram, NetworkAnalyzer
│   ├── error_handler.py              — Error handling utilities
│   ├── error_codes.py                — Error code definitions
│   ├── logger_config.py              — Logging configuration
│   ├── validators/
│   │   ├── convergence_detector.py
│   │   └── nobel_validator.py        — Nobel equilibrium validation
│   └── environments/                 — 8 Nobel prize-winning game environments
│       ├── base.py                    — BaseEnvironment + ConvergenceResult
│       ├── hawk_dove.py
│       ├── repeated_prisoners_dilemma.py
│       ├── public_goods.py
│       ├── common_pool_resource.py
│       ├── vickrey_auction.py
│       ├── spence_signaling.py
│       ├── two_sided_matching.py
│       └── auction_common_value.py
└── scripts/nash_cli/
    ├── main.py                       — Argument parsing & dispatch
    ├── commands/
    │   ├── run.py                    — Simulation runner (preset environments)
    │   ├── env_cmd.py                — Environment listing & info
    │   ├── validate.py               — Statistical & Nobel validation
    │   ├── viz.py                    — Matplotlib chart generation
    │   ├── sweep.py                  — Parameter sweeping (environment presets)
    │   └── config_cmd.py             — Environment config template & validation
    ├── nash.sh                       — Unix launcher
    └── nash.bat                      — Windows launcher
```

## Agent Team Power — CLI Orchestration Patterns

As the computational core, you are invoked by other NASH skills. When a skill asks you to run heavy workloads, use these patterns:

### Pattern 1: Parallel Multi-Environment Execution

When asked to run multiple environments (comparison, benchmarking), launch ALL in parallel — never sequentially:

```
# Launch 4 environments simultaneously in ONE message:
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o hd.json
Bash: uv run nash run --preset prisoners_dilemma --agents 100 --rounds 200 --seed 42 -o pd.json
Bash: uv run nash run --preset public_goods --agents 100 --rounds 200 --seed 42 -o pg.json
Bash: uv run nash run --preset common_pool --agents 100 --rounds 200 --seed 42 -o cp.json
```

### Pattern 2: Background Long-Running Simulations

For simulations with many rounds (>200) or many agents (>500), run in background:

```
Bash(run_in_background=true): uv run nash run --preset hawk_dove --agents 500 --rounds 1000 --seed 42 -o large_run.json
```

You will be notified when it completes. Continue with other work while waiting.

### Pattern 3: Parallel Validate + Viz After Run

After simulation completes, validate and visualize in parallel:

```
Bash: uv run nash validate --data results.json --type nobel -o validation.json
Bash: uv run nash viz --data results.json --type all -o charts.png
```

### Pattern 4: Split Large Sweeps Across Subagents

When a parameter sweep exceeds 100 configs, split the range across parallel subagents:

```
Agent(description: "Sweep part 1", prompt: "Run: uv run nash sweep --config cfg.json --param X --range 0,125 --step 25 --rounds 100 -o sweep_p1.json")
Agent(description: "Sweep part 2", prompt: "Run: uv run nash sweep --config cfg.json --param X --range 125,250 --step 25 --rounds 100 -o sweep_p2.json")
Agent(description: "Sweep part 3", prompt: "Run: uv run nash sweep --config cfg.json --param X --range 250,375 --step 25 --rounds 100 -o sweep_p3.json")
Agent(description: "Sweep part 4", prompt: "Run: uv run nash sweep --config cfg.json --param X --range 375,500 --step 25 --rounds 100 -o sweep_p4.json")
```

Then merge results:
```bash
python -c "
import json, glob
all_results = []
for f in sorted(glob.glob('sweep_p*.json')):
    with open(f) as fp:
        all_results.extend(json.load(fp)['results'])
with open('sweep_merged.json', 'w') as out:
    json.dump({'status': 'completed', 'results': all_results, 'total': len(all_results)}, out, indent=2)
"
```

### Pattern 5: Multi-Seed Reproducibility (Default for Research)

Always run at least 3 seeds for research-grade results. Launch all in parallel:

```
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o s42.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 123 -o s123.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 456 -o s456.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 789 -o s789.json
Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 1024 -o s1024.json
```

## CLI Commands

All commands output JSON to stdout, progress to stderr. Always run from the nash-cli root directory.

### env — List and inspect environments

```bash
uv run nash env list
uv run nash env info hawk_dove
uv run nash env info vickrey        # short alias -> vickrey_auction
uv run nash env info prisoners_dilemma
uv run nash env info common_pool
uv run nash env info spence
uv run nash env info matching
```

8 environments: `hawk_dove`, `repeated_prisoners_dilemma`, `public_goods`, `common_pool_resource`, `vickrey_auction`, `spence_signaling`, `two_sided_matching`, `auction_common_value`.

### run — Execute simulations

```bash
# Run a preset environment
uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o results.json
uv run nash run --preset vickrey --agents 50 --rounds 100
uv run nash run --preset prisoners_dilemma --rounds 200
```

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

### sweep — Parameter space exploration

```bash
# Generate config template first
uv run nash config template --preset hawk_dove -o cfg.json

# Sweep over a parameter
uv run nash sweep --config cfg.json --param resource_value --range 1,10 --step 1 --rounds 200 -o sweep.json
```

For large ranges (>100 configs), use Pattern 4 (split across parallel subagents).

### validate — Statistical and Nobel validation

```bash
uv run nash validate --data results.json --type statistical --baseline-gini 0.3 --baseline-hostility 0.4
uv run nash validate --data results.json --type nobel
uv run nash validate --data results.json --type both -o validation_report.json
```

### viz — Generate charts

```bash
uv run nash viz --data results.json --type all -o charts.png
uv run nash viz --data results.json --type gini -o gini.png
uv run nash viz --data results.json --type hostility -o hostility.png
```

`--type all` auto-detects available data and generates appropriate multi-panel charts.

### config — Environment config templates

```bash
uv run nash config template --preset hawk_dove -o cfg.json
uv run nash config template --preset common_pool -o pool_cfg.json
uv run nash config validate cfg.json
```

Presets: `hawk_dove`, `prisoners_dilemma`, `public_goods`, `common_pool`, `vickrey`, `spence`, `matching`, `auction_common_value`.

## Data Format

Run output JSON format:

```json
{
  "status": "completed",
  "environment": "hawk_dove",
  "total_rounds": 200,
  "converged": true,
  "convergence_message": "ESS reached (deviation 4.4%)",
  "final_metrics": { "hawk_ratio": 0.62, "ess_deviation": 0.04, ... },
  "history": [
    { "round": 1, "hawk_ratio": 0.55, ... },
    ...
  ],
  "config": { ... }
}
```

`viz --type all` auto-extracts time-series from `history`, `validate --type nobel` reads `environment` + `final_metrics`.

## Dependency Chain

```
nash-env       -> nash-cli (env list, env info)
nash-run       -> nash-cli (run, sweep, config)
nash-analyze   -> nash-cli (validate, viz)
nash-game-theory -> nash-cli (run for testing)
```

## Error Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| `No module named 'src'` | Python path | Run from nash-cli/ root. main.py auto-adds project root to sys.path. |
| `Unknown preset: X` | Typo | Run `env list` to see all 8 presets. |
| matplotlib not installed | Missing dep | `pip install matplotlib` |
| `No plot data available` | Data format mismatch | Use `--type all` for auto-detection. |
| Sweep config parse error | Wrong config format | Use `config template --preset <name> -o cfg.json` first. |

## Cross-References

- [[nash-env]] — uses env list/info to classify problems
- [[nash-run]] — uses run/sweep/config to execute experiments
- [[nash-analyze]] — uses validate/viz to analyze results
- [[nash-game-theory]] — uses run to test new environments