# n-nash CLI 扩展需求

## 目的

MOI（中间商机会指数）需要将真实市场数据喂入 n-nash 仿真，得到**因市场不同而不同**的输出指标。
当前 CLI 只暴露 `--agents` 和 `--rounds`，Python API 的完整参数无法从 CLI 调用。
同时，matching 环境的 `stability_index` 在数学上永远趋近 1.0（Gale-Shapley 的保证），无法区分不同市场。

---

## 需求一：CLI 暴露环境专属参数（`--params`）

### 问题

```bash
# 现在只能传 --agents 和 --rounds
uv run nash run --preset matching --agents 200 --rounds 200

# 无法传 num_men / num_women / discount_factor 等关键参数
# Python API 接受这些参数，但 CLI 没有暴露
```

### 要求

在 `nash run` 增加 `--params` 参数，接受 JSON 字符串，传递给对应环境的 create 函数。

```bash
# 新用法
uv run nash run --preset matching \
  --params '{"num_men": 50, "num_women": 200}' \
  --rounds 200 --seed 42 -o result.json

uv run nash run --preset prisoners_dilemma \
  --params '{"num_agents": 100, "discount_factor": 0.6, "learning_rate": 0.1}' \
  --rounds 200 --seed 42 -o result.json

uv run nash run --preset spence \
  --params '{"num_workers": 100, "num_firms": 20, "high_ability_threshold": 0.3}' \
  --rounds 200 --seed 42 -o result.json

uv run nash run --preset hawk_dove \
  --params '{"num_agents": 100, "resource_value": 6.0, "conflict_cost": 4.0}' \
  --rounds 200 --seed 42 -o result.json
```

### 每个环境的参数规格

| 环境 | 参数名 | 类型 | 默认值 | 合法范围 | 说明 |
|------|--------|------|--------|---------|------|
| matching | num_men | int | 10 | [2, 500] | 供给侧（供应商）数量 |
| matching | num_women | int | 10 | [2, 500] | 需求侧（买家）数量 |
| spence | num_workers | int | 100 | [10, 500] | 工人（供应商）数量 |
| spence | num_firms | int | 10 | [5, 200] | 企业（买家）数量 |
| spence | high_ability_threshold | float | 0.5 | [0.1, 0.9] | 高能力工人比例阈值，越低表示能力差异越大 |
| prisoners_dilemma | num_agents | int | 20 | [4, 500] | 参与者数量 |
| prisoners_dilemma | discount_factor | float | 0.95 | [0.1, 0.99] | 未来折现因子，越低表示越不重视长期关系 |
| prisoners_dilemma | learning_rate | float | 0.1 | [0.01, 0.5] | 策略学习速率 |
| hawk_dove | num_agents | int | 100 | [10, 500] | 参与者数量 |
| hawk_dove | resource_value | float | 4.0 | [1.0, 20.0] | 资源价值（市场利润空间） |
| hawk_dove | conflict_cost | float | 6.0 | [1.0, 30.0] | 冲突成本（竞争激烈程度） |

### 实现要求

1. `--params` 是可选参数，不传时使用各环境的默认值（向后兼容）
2. `--agents` 保留作为快捷方式：若 `--params` 中有对应数量参数则 `--params` 优先；否则 `--agents` 映射到各环境的主数量参数（matching→num_men，spence→num_workers，pd/hawk_dove→num_agents）
3. JSON 解析失败时，输出明确的参数错误信息，列出该环境支持的参数
4. 参数超出合法范围时，报错并提示合法范围

### 验证标准

```bash
# 测试 1: 默认行为不变（向后兼容）
uv run nash run --preset matching --agents 100 --rounds 50
# 应正常运行，结果与改动前一致

# 测试 2: --params 生效
uv run nash run --preset matching \
  --params '{"num_men": 50, "num_women": 200}' --rounds 50
# 输出 JSON 的 parameters 中应显示 num_men=50, num_women=200

# 测试 3: 不同参数产生不同结果
# 市场A: 供需均衡
uv run nash run --preset matching --params '{"num_men":100,"num_women":100}' --rounds 100 --seed 42 -o /tmp/a.json
# 市场B: 供需严重失衡
uv run nash run --preset matching --params '{"num_men":20,"num_women":200}' --rounds 100 --seed 42 -o /tmp/b.json
# /tmp/a.json 和 /tmp/b.json 的 final_metrics 中应有不同的匹配效率指标

# 测试 4: 错误参数提示
uv run nash run --preset matching --params '{"invalid_param": 5}'
# 应报错并列出 matching 支持的参数: num_men, num_women

# 测试 5: PD discount_factor 影响 cooperation_rate
uv run nash run --preset prisoners_dilemma \
  --params '{"discount_factor": 0.9}' --rounds 200 --seed 42 -o /tmp/high_df.json
uv run nash run --preset prisoners_dilemma \
  --params '{"discount_factor": 0.3}' --rounds 200 --seed 42 -o /tmp/low_df.json
# high_df.json 的 cooperation_rate 应 > low_df.json 的 cooperation_rate
```

---

## 需求二：matching 环境增加市场摩擦指标

### 问题

当前 `stability_index` 永远是 ~1.0。这是 Gale-Shapley 算法的数学保证（必然存在稳定匹配），不是市场特征的反映。

MOI 需要知道的是：**这个市场在没有中介的情况下，参与者找到合适匹配有多难？**

这个问题由三个因素决定：
1. 市场供需失衡程度（num_men vs num_women）
2. 搜索难度（市场越大，搜索越难）
3. 匹配质量（找到"好"匹配而不是"任意"匹配的难度）

### 要求：新增三个指标到 `final_metrics`

#### 指标 1：`matching_search_intensity`

定义：Gale-Shapley 算法运行过程中，每个供给侧参与者在匹配前被拒绝的平均次数。

```python
# 在 gale_shapley() 方法中记录拒绝次数
total_rejections = sum(men_next_proposal) - len(matches)
matching_search_intensity = total_rejections / self.num_men

# 解释：
# 值高 → 参与者需要大量搜索才能匹配 → 市场效率低 → 中介撮合价值高
# 值低 → 匹配容易达成 → 市场自发运转良好 → 中介价值低
```

预期行为：
- `num_men == num_women` 且偏好随机时：search_intensity ≈ num_women/2
- `num_men >> num_women`（供过于求）时：search_intensity 升高（大量被拒）
- `num_men << num_women`（供不应求）时：search_intensity 降低

#### 指标 2：`market_imbalance`

```python
market_imbalance = abs(num_men - num_women) / max(num_men, num_women)

# 解释：
# 0.0 → 供需完全均衡
# 接近 1.0 → 严重失衡（一方远多于另一方）
# 高 imbalance → 弱势方（数量多的一方）需要中介帮助
```

#### 指标 3：`unmatched_ratio`

```python
unmatched_ratio = 1.0 - len(matches) / min(num_men, num_women)

# 解释：
# 0.0 → 所有人都匹配成功
# > 0.0 → 有人找不到匹配（在 num_men != num_women 时必然发生）
# 高 unmatched_ratio → 市场中存在大量"找不到交易对象"的参与者 → 中介价值高
```

### 修改范围

文件：`src/environments/two_sided_matching.py`

1. `gale_shapley()` 方法：记录并返回 `total_rejections`
2. `run_step()` 方法：计算三个新指标，加入 `round_data`
3. `get_validation_metrics()` 方法：将三个新指标加入返回值
4. `check_convergence()` 不变（仍用 `stability_index` 判断收敛，这是 Nobel 验证需要）
5. `final_metrics`（CLI 输出）：增加三个新字段，`stability_index` 保留不动

### 验证标准

```bash
# 测试 1: 供需均衡市场
uv run nash run --preset matching \
  --params '{"num_men": 100, "num_women": 100}' \
  --rounds 50 --seed 42 -o /tmp/balanced.json

# 测试 2: 供过于求市场（供应商远多于买家）
uv run nash run --preset matching \
  --params '{"num_men": 200, "num_women": 30}' \
  --rounds 50 --seed 42 -o /tmp/oversupply.json

# 验证:
python -c "
import json
b = json.load(open('/tmp/balanced.json'))
o = json.load(open('/tmp/oversupply.json'))
bf = b['final_metrics']
of = o['final_metrics']

# 供过于求时搜索强度应更高
assert of['matching_search_intensity'] > bf['matching_search_intensity'], \
    f'供过于求应更难匹配: oversupply={of[\"matching_search_intensity\"]} vs balanced={bf[\"matching_search_intensity\"]}'

# 供过于求时市场失衡度应更高
assert of['market_imbalance'] > bf['market_imbalance'], \
    f'供需差应更大: oversupply={of[\"market_imbalance\"]} vs balanced={bf[\"market_imbalance\"]}'

# 供过于求时未匹配比例应更高
assert of['unmatched_ratio'] > bf['unmatched_ratio'], \
    f'应有更多人找不到匹配: oversupply={of[\"unmatched_ratio\"]} vs balanced={bf[\"unmatched_ratio\"]}'

print('All matching metric tests passed!')
"
```

---

## 需求三：spence 环境增加信号混同指标

### 问题

当前 `separation_index` 在多数参数下趋近 1.0（分离均衡容易达成）。MOI 需要区分"市场信号质量"，即：在没有中介背书的情况下，买家能否分辨供应商质量？

### 要求：新增指标 `signal_noise_ratio`

```python
signal_noise_ratio = 1.0 - (education_premium - 1.0) / max_possible_premium

# 解释：
# 接近 1.0 → 高能力和低能力工人的产出差异清晰可辨 → 市场可自行分辨质量
# 接近 0.0 → 高能力和低能力工人的产出差异模糊 → 需要中介提供质量信号

# 更直接的实现方式（如果教育溢价的数据允许）：
# 统计最终结果中，被雇主正确分类的工人比例
# signal_noise_ratio = correctly_classified / total_workers
```

### 修改范围

文件：`src/environments/spence_signaling.py`

1. 在 `run_step()` 中，统计被雇主正确识别为高/低能力的工人比例
2. 将 `signal_noise_ratio` 加入 `final_metrics`
3. `separation_index` 保留不变（Nobel 验证需要）

### 验证标准

```bash
# 高能力阈值（能力差异小，难以区分）
uv run nash run --preset spence \
  --params '{"high_ability_threshold": 0.8}' --rounds 100 --seed 42 -o /tmp/hard.json

# 低能力阈值（能力差异大，容易区分）
uv run nash run --preset spence \
  --params '{"high_ability_threshold": 0.2}' --rounds 100 --seed 42 -o /tmp/easy.json

# 验证:
python -c "
import json
h = json.load(open('/tmp/hard.json'))['final_metrics']
e = json.load(open('/tmp/easy.json'))['final_metrics']

# 能力差异小时，信号噪音应更高（更难区分）
# 注意：这里的预期方向取决于 signal_noise_ratio 的具体定义
# 如果 signal_noise_ratio 定义为'噪音比例'，则 hard > easy
# 如果定义为'信号清晰度'，则 hard < easy
print(f'hard (threshold=0.8): signal_noise_ratio = {h.get(\"signal_noise_ratio\", \"MISSING\")}')
print(f'easy (threshold=0.2): signal_noise_ratio = {e.get(\"signal_noise_ratio\", \"MISSING\")}')
assert 'signal_noise_ratio' in h, '指标未出现在输出中'
assert h['signal_noise_ratio'] != e['signal_noise_ratio'], '两组参数应有不同输出'
print('Spence signal_noise_ratio test passed!')
"
```

---

## 需求四：输出 JSON 包含输入参数回显

### 问题

当前输出 JSON 的 `final_metrics` 只有指标值，没有记录输入参数。对于 MOI 的审计需求，需要能从输出文件还原"用了什么市场参数，得到了什么结果"。

### 要求

输出 JSON 结构增加 `input_params` 字段：

```json
{
  "status": "ok",
  "preset": "matching",
  "input_params": {
    "num_men": 50,
    "num_women": 200,
    "seed": 42,
    "rounds": 200
  },
  "final_metrics": {
    "stability_index": 1.0,
    "matching_efficiency": 1.0,
    "matching_search_intensity": 47.3,
    "market_imbalance": 0.75,
    "unmatched_ratio": 0.85
  },
  "convergence": {
    "converged": true,
    "round": 100
  }
}
```

### 验证标准

```bash
uv run nash run --preset matching \
  --params '{"num_men": 30, "num_women": 100}' \
  --rounds 50 --seed 99 -o /tmp/echo_test.json

python -c "
import json
d = json.load(open('/tmp/echo_test.json'))
assert d['input_params']['num_men'] == 30, 'num_men 未回显'
assert d['input_params']['num_women'] == 100, 'num_women 未回显'
assert d['input_params']['seed'] == 99, 'seed 未回显'
assert 'final_metrics' in d, 'final_metrics 缺失'
print('Input echo test passed!')
"
```

---

## 需求五：多 seed 批量运行（可选，P2）

### 问题

单次仿真的有随机性。MOI 需要对同一市场跑 3-5 个 seed 取平均，才能作为可信的评估输入。

### 要求

增加 `--seeds` 参数，一次跑多个 seed，输出均值和标准差：

```bash
uv run nash run --preset matching \
  --params '{"num_men": 50, "num_women": 200}' \
  --rounds 200 --seeds 42,43,44,45,46 -o /tmp/multi_seed.json

# 输出：
{
  "seeds": [42, 43, 44, 45, 46],
  "aggregated_metrics": {
    "matching_search_intensity": {"mean": 47.3, "std": 2.1, "min": 44.2, "max": 49.8},
    "market_imbalance": {"mean": 0.75, "std": 0.0, "min": 0.75, "max": 0.75},
    "unmatched_ratio": {"mean": 0.75, "std": 0.0, "min": 0.75, "max": 0.75}
  },
  "per_seed_results": [...]
}
```

### 验证标准

```bash
uv run nash run --preset hawk_dove \
  --params '{"resource_value": 4.0, "conflict_cost": 6.0}' \
  --rounds 200 --seeds 1,2,3,4,5 -o /tmp/multi.json

python -c "
import json
d = json.load(open('/tmp/multi.json'))
assert len(d['seeds']) == 5, '应跑 5 个 seed'
assert 'aggregated_metrics' in d, '应有聚合结果'
assert 'mean' in d['aggregated_metrics']['hawk_ratio'], '应有均值'
assert 'std' in d['aggregated_metrics']['hawk_ratio'], '应有标准差'
print(f'hawk_ratio mean={d[\"aggregated_metrics\"][\"hawk_ratio\"][\"mean\"]:.3f}')
print('Multi-seed test passed!')
"
```

---

## 实现优先级

| 优先级 | 需求 | 对 MOI 的重要性 |
|--------|------|---------------|
| **P0** | 需求一（`--params` 参数暴露） | 没有这个，仿真完全无法接入市场数据 |
| **P0** | 需求二（matching 新指标） | 没有这个，matching 仿真对市场差异完全不敏感 |
| **P1** | 需求三（spence 新指标） | 增强信号质量区分度 |
| **P1** | 需求四（输入参数回显） | 审计和报告可追溯性 |
| **P2** | 需求五（多 seed 批量） | 提升结果可信度，可用多次单 seed 调用替代 |

---

## 向后兼容性要求

1. 不传 `--params` 时，行为与改动前完全一致
2. `--agents` 参数继续有效，作为各环境主数量参数的快捷方式
3. `--seed` 单 seed 参数继续有效
4. `validate` 命令不受影响，仍可用现有输出 JSON 做 Nobel 验证
5. 现有 `final_metrics` 中的字段（`stability_index`、`separation_index`、`cooperation_rate`、`hawk_ratio`）保留，只增不删

---

## 文件改动范围估算

| 文件 | 改动 |
|------|------|
| `nash-cli/src/cli.py` 或 `nash-cli/src/main.py`（CLI 入口） | 增加 `--params`、`--seeds` 参数解析，将 JSON 传给 create 函数 |
| `nash-cli/src/environments/two_sided_matching.py` | gale_shapley() 记录拒绝次数；run_step() 计算三个新指标；get_validation_metrics() 增加三个新字段 |
| `nash-cli/src/environments/spence_signaling.py` | run_step() 统计正确分类比例；get_validation_metrics() 增加 signal_noise_ratio |
| `nash-cli/src/environments/base.py`（可选） | 若输出 JSON 由 base 类生成，在此增加 input_params 回显 |

---

## 参考：MOI 如何使用这些参数

MOI 的参数校准层（`moi-cli` 的 `calibrate` 命令）将按如下逻辑映射市场数据：

```
市场数据                          n-nash 参数
────────────────────────────────────────────────────
供应商 5000 家                   → num_men = 50（按比例缩放）
买家 20000 家                    → num_women = 200
"描述不符"差评率 35%             → high_ability_threshold = 0.3（质量差异大）
成交流程 8 步、信任成本高         → discount_factor = 0.5（长期关系重要）
最大平台市占率 10%、3 家竞争      → resource_value = 8, conflict_cost = 3（市场空间大，竞争温和）
```

这些映射逻辑在 MOI 侧实现，n-nash 只需要接受这些参数并输出对应的指标。

---

**文档结束**
