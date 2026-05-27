---
name: nash-analyze
description: "Analyze NASH simulation results. Use when the user asks to analyze results, validate a simulation, verify a hypothesis, check convergence, visualize data, plot results, interpret output, or understand what simulation data means. Triggers on: analyze, validate, verify, hypothesis, convergence, visualize, plot, chart, significant, what does this mean."
---

> **Memory:** This skill uses Claude Code's native memory system for context persistence. No additional MCP setup needed.

# NASH Analyze — Statistical Validation & Visualization (Agent Team Mode)

You analyze NASH simulation output. You run Nobel benchmark verification, statistical tests, and generate charts. You explain results in plain language and persist conclusions to memory.

## 核心理念：多方验证 + 深度解读

**A single metric never tells the full story. Use parallel validation, multi-perspective interpretation, and proactive follow-up suggestions.**

- Validate AND visualize → always in parallel, never sequential
- Single result file → Nobel + statistical + viz, all at once
- Multiple result files → agent team interprets from different angles
- After ANY analysis → persist conclusions to memory, suggest next experiment

## 1. When to Use

Trigger words: "analyze results", "validate simulation", "verify hypothesis", "check convergence", "visualize data", "plot results", "is this significant?", "what does this mean?", "interpret", "chart", "graph".

## 2. Quick Decision: What Analysis?

```
User has results.json?
├─ Has "environment" key -> Environment results -> Nobel benchmark validation + metrics viz
├─ Has "history" array -> Time-series viz available
├─ Multiple .json files -> Comparison analysis (Section 7)
└─ Not sure -> Read the file first, check top-level keys
```

## 3. Standard Analysis Pipeline (Parallel Validate + Viz)

Validation and visualization are independent. Run them simultaneously:

```bash
# Launch BOTH in parallel, single message:
Bash: uv run nash validate --data results.json --type nobel -o validation.json
Bash: uv run nash viz --data results.json --type all -o charts.png
```

After both complete:
1. Read `validation.json` for the Nobel conclusion
2. View `charts.png` for visual inspection
3. Cross-reference: does the chart match the validator's conclusion?
4. Present unified interpretation to user

## 4. Data Type Detection

Before launching any analysis, read the JSON file and inspect its top-level keys:

| Key present | Data source | Validation | Viz |
|---|---|---|---|
| `environment` | Game environment | `--type nobel` | all (auto-detect) |
| `history` (array) | Game environment | `--type nobel` | all (time-series subplots) |

Detection example:
```bash
python -c "import json; d=json.load(open('results.json')); print(list(d.keys())[:10])"
```

## 5. Nobel Benchmark Validation

```bash
# Validate environment results against Nobel prize predictions
uv run nash validate --data env_results.json --type nobel

# Run both validations (if applicable)
uv run nash validate --data results.json --type both -o validation_report.json
```

### Interpreting Nobel validation output

| confidence | Meaning | Action |
|---|---|---|
| > 0.9 | Strong match to Nobel prediction | "The environment converged to the equilibrium predicted by Nobel-winning theory." |
| 0.7 - 0.9 | Moderate match | "The environment mostly aligns with the Nobel prediction, with some deviations." |
| < 0.7 | Weak match | "The environment did not converge to the expected equilibrium. Check the `suggestions` field." |

The validation output includes a `conclusion` string (human-readable verdict) and a `suggestions` array (actionable next steps). Always read both and relay to the user.

## 6. Visualization Guide

```bash
# All available charts (auto-detects what data supports)
uv run nash viz --data results.json --type all -o charts.png

# Specific chart types (if supported by data)
uv run nash viz --data results.json --type gini -o gini.png
uv run nash viz --data results.json --type hostility -o hostility.png
```

### Which chart for which data

| Chart type | Data requirement | What it shows |
|---|---|---|
| `gini` | `gini_history` in JSON | Inequality trend over time |
| `hostility` | `hostility_history` in JSON | Conflict trend over time |
| `all` | Auto-detect from `history` | Multi-panel of all available time-series |

**Important notes:**
- Environment results (from `--preset hawk_dove` etc.) use `viz --type all` which auto-extracts numeric time-series from the `history` array.
- Each environment produces different metrics — viz auto-discovers available fields.
- If unsure, always use `--type all`.

## 7. Agent Team Multi-Perspective Analysis

When analyzing complex results (multiple environments, hypothesis tests, or surprising outcomes), deploy an agent team to interpret from different angles:

```
# Launch analysis team in parallel:
Agent({description: "Economic theory perspective",
       prompt: "Read results.json. From a pure game theory perspective:
                1. Does the result match the Nash equilibrium prediction?
                2. Are there any anomalies that suggest model misspecification?
                3. What would a theorist question about these results?
                Report in under 200 words."})

Agent({description: "Empirical/statistical perspective",
       prompt: "Read results.json. From a statistical perspective:
                1. Is the convergence convincing (check trend, not just final value)?
                2. Are there signs of insufficient rounds (ongoing drift)?
                3. What statistical tests would strengthen the conclusion?
                Report in under 200 words."})

Agent({description: "Policy/practical perspective",
       prompt: "Read results.json. From a policy/practical perspective:
                1. What real-world implications can be drawn?
                2. What are the limitations of extrapolating from this model?
                3. What follow-up experiment would be most valuable?
                Report in under 200 words."})

Agent({description: "Devil's advocate",
       prompt: "Read results.json. As devil's advocate:
                1. What's the strongest counter-argument to the conclusion?
                2. What hidden assumptions could invalidate the result?
                3. What would make you reject these findings?
                Report in under 200 words."})
```

**Synthesize the 4 perspectives into:**
1. **Consensus conclusion** — what all perspectives agree on
2. **Dissenting views** — important disagreements or caveats
3. **Confidence assessment** — how robust is the finding?
4. **Recommended next step** — the single most valuable follow-up

## 8. Multi-File Comparison Analysis

When comparing results from multiple runs (e.g., different environments or parameters):

```bash
# Step 1: Validate all files in parallel
Bash: uv run nash validate --data hawk_dove_results.json --type nobel
Bash: uv run nash validate --data prisoners_dilemma_results.json --type nobel
Bash: uv run nash validate --data public_goods_results.json --type nobel
Bash: uv run nash validate --data common_pool_results.json --type nobel

# Step 2: Generate comparison table
python -c "
import json, glob
files = sorted(glob.glob('*_results.json'))
print('| Environment | Converged | Nobel Match | Key Metric |')
print('|-------------|-----------|-------------|------------|')
for f in files:
    d = json.load(open(f))
    env = d.get('environment', f)
    conv = 'Yes' if d.get('converged') else 'No'
    metrics = d.get('final_metrics', {})
    key = list(metrics.items())[0] if metrics else ('N/A', 0)
    print(f'| {env} | {conv} | - | {key[0]}={key[1]:.3f} |')
"
```

## 9. Memory Persistence

After completing analysis, persist conclusions to native memory:

```python
mcp__memory__add_observations({
    "observations": [
        {
            "entityName": f"nash-analysis-{date}-{brief-slug}",
            "contents": [
                "Analysis: <brief description>",
                "Environment: <preset name>",
                "Result: <converged / not converged>",
                "Nobel confidence: <confidence>",
                "Key metrics: <summary>",
                "Follow-up recommendation: <suggestion>",
                "Date: <today>"
            ]
        }
    ]
})
```

Also create relations to link analysis to its source experiment:
```python
mcp__memory__create_relations({
    "relations": [
        {
            "from": f"nash-analysis-{date}-{slug}",
            "to": f"experiment:{experiment_id}",
            "relationType": "analyzes"
        }
    ]
})
```

## 10. Presenting Results to Human

1. **Lead with the conclusion** in plain language:
   - "The hawk-dove simulation converged to the ESS prediction (deviation 4.4%)."
   - "The common pool environment exhibited the tragedy of the commons (depletion rate 73%)."

2. **Explain what it means** in one sentence:
   - "This means the evolutionary dynamics reached the predicted equilibrium."

3. **Show the validation confidence and Nobel reference:**
   - "Nobel validation confidence: 0.92 (2005, Aumann/Schelling — ESS theory)"

4. **Describe the charts** (if viz was generated). 1-2 sentences per chart.

5. **Suggest next steps** proactively:
   - "Would you like to run a parameter sweep to find the tipping point?"
   - "Should we compare this against a different environment?"
   - "Want me to run 5 seeds to verify reproducibility?"

**Never**: dump raw JSON at the user. Always interpret first.

## 11. Error Recovery

### "matplotlib not installed"
```
pip install matplotlib
```
Then retry the viz command.

### "No plot data available"
The data format does not match the expected schema. Verify:
- The file is valid NASH run output JSON
- Check `history` array exists and has numeric fields

### General troubleshooting flow
```
Error?
├─ matplotlib error -> pip install matplotlib
├─ missing key error -> Check data type detection (Section 4)
├─ schema error -> Verify the file is valid NASH output
└─ unknown error -> Read the full error message
```

## 12. CLI Quick Reference

```bash
# Validation
uv run nash validate --data <file> --type nobel
uv run nash validate --data <file> --type both -o report.json

# Visualization
uv run nash viz --data <file> --type all -o charts.png
```

## 13. Decision Tree

```
User asks to analyze results
├─ No file specified? -> Ask: "Which results file should I analyze?"
├─ Have a file -> Read first to detect data type
│   ├─ Has "environment" (Environment data)
│   │   └─ Parallel: validate nobel + viz --type all
│   ├─ Have multiple files -> Comparison mode (Section 8)
│   └─ Unknown format -> Read more of the file to determine type
├─ Complex/surprising results -> Agent team multi-perspective (Section 7)
├─ Error: matplotlib missing -> pip install matplotlib, retry
├─ Error: no plot data -> Check file format
└─ Success -> Interpret, persist to memory, present to user
    └─ MUST ask: "Would you like to run more rounds? Compare environments? Sweep parameters?"
```

## 14. Cross-references

- [[nash-cli]] -- CLI execution engine (all validate/viz commands)
- [[nash-run]] -- to run more simulations and generate new data
- [[nash-env]] -- to explore other game environments for comparison
- [[nash-game-theory]] -- to create new custom environments to test theories