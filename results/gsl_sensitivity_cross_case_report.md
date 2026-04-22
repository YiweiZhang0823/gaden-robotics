# GSL 超参数敏感性三组 Case 对比报告

## 对比目的

本报告把三组 focused sensitivity experiment 放在一起比较，用来回答两个问题：

1. 不同初始状态下，哪些超参数最敏感？
2. 现在是否有必要继续做第二组 sensitivity experiment？

这三组实验不是为了穷举所有参数，而是选择最能解释现象的代表性状态：

| Case | 场景 / 初始状态 | 导师要求对应情况 | 为什么选它 |
| --- | --- | --- | --- |
| Case 1 | `exp3_advection / far_inside_plume` | 远离气源，但已经在羽流内部 | 有 plume contact，但定位和确认可能不稳定。 |
| Case 2 | `exp3_advection / far_off_plume` | 远离气源，且离羽流边缘也有一段距离 | 基本没有 plume contact，测试参数是否还有作用。 |
| Case 3 | `exp2_time_varying / far_near_edge` | 远离气源，但接近羽流边缘 | 时变风场边缘状态，气味间歇且不稳定。 |

## 最佳/代表性结果对比

| Case | baseline 结果 | 最主要现象 | 参数敏感性判断 |
| --- | --- | --- | --- |
| Case 1 `exp3 / far_inside` | 成功，`71.0 s`，`final_dist=0.159 m`，`final_conf=0.610` | 已经在羽流内部，baseline 可成功，但参数扰动后多数组失败 | 对状态切换和确认稳定性敏感；不是单纯 `required_confidence` 问题 |
| Case 2 `exp3 / far_off` | 失败，`raw=0`，`conf=0`，`SURGE=0`，`SPIRAL=0` | 六组参数全部长期 CAST，没有 plume contact | 对当前超参数不敏感；限制因素是初始位置离羽流太远 |
| Case 3 `exp2 / far_near_edge` | 成功，`84.2 s`，`final_dist=0.230 m`，`final_conf=0.619` | 时变羽流边缘可成功，但参数过松/过严都会出问题 | 对 `required_confidence`、检测阈值、plume loss 都敏感 |

## 六组参数横向对比

| 参数组 | Case 1: `exp3/far_inside` | Case 2: `exp3/far_off` | Case 3: `exp2/far_near_edge` | 总体结论 |
| --- | --- | --- | --- | --- |
| `sensitivity_baseline` | 成功，表现最好 | 失败，无气味输入 | 成功，表现最好 | baseline 在有可用 plume cue 的 Case 1/3 中较稳，但无法解决完全无气味的 Case 2 |
| `sensitivity_conf_low` | 失败，路径变长 | 失败，无变化 | 成功但更慢 | 降低 `required_confidence` 不一定提升效率；只有在已接近气源时才可能改变成功判定 |
| `sensitivity_conf_high` | 失败 | 失败，无变化 | 失败 | 高 `required_confidence` 对边缘/不稳定羽流不友好 |
| `sensitivity_threshold_low` | 失败，但曾接近气源 | 失败，无变化 | stop mode 成功但离气源很远 | 阈值过低可能导致 false positive；不是越低越好 |
| `sensitivity_loss_tolerant` | 失败，SPIRAL 增加到 `28` | 失败，无变化 | 失败，SURGE 增加到 `106` | plume loss 参数很敏感，但过度放宽会沿着不稳定线索搜索 |
| `sensitivity_spiral_easy` | 失败，SPIRAL 增加到 `60` | 失败，SPIRAL 仍为 `0` | 失败，SPIRAL 仍为 `0` | SPIRAL 参数只有在已有稳定 plume cue 时才可能生效；单独降低门槛不够 |

## 对导师要求的回应

导师提出的核心意思是：不同初始状态下，fine-tuned 参数不一定适合其他状态；需要观察羽流形态，并测试不同机械臂初始状态下哪些超参数敏感。

这三组实验已经能支撑这个判断：

- Case 1 表明：即使已经在羽流内部，参数放宽也可能导致更长路径或无效 SPIRAL，说明“有气味”不等于“容易稳定确认”。
- Case 2 表明：如果初始状态远离羽流边缘，机械臂局部搜索范围内没有 plume contact，那么调节算法超参数基本不起作用。
- Case 3 表明：在时变羽流边缘，参数非常敏感；过高 confidence 会失败，过低 detection threshold 会有 false positive 风险，过宽松 plume loss 会让 SURGE 沿着不稳定线索远离气源。

因此，可以写成：

> 参数敏感性并不是固定属性，而是由初始位置与气源、羽流边界、风向之间的关系共同决定。特别是在时变风场和羽流边缘状态下，confidence、detection threshold 和 plume loss 相关参数对成功率、路径长度和确认方式都有明显影响。

## 是否需要做第二组 experiment？

### 现在不建议立刻扩展到新的大矩阵

目前这三组已经回答了导师的主要问题：不同初始状态会导致不同参数敏感性。继续盲目扩展到所有场景/所有状态/所有参数，工作量会很大，而且结论可能重复。

### 更建议做“小型重复实验”

如果时间允许，最有价值的下一步不是换更多参数，而是对这三组中最关键的设置做重复试验，验证随机性/稳定性：

| 建议重复项 | 重复次数 | 为什么 |
| --- | ---: | --- |
| Case 1 `baseline` | 3 次 | Case 1 baseline 一次成功，但之前类似状态也有失败，需要确认平流羽流中的随机波动影响。 |
| Case 3 `baseline` | 3 次 | 当前 baseline 是 Case 3 最好结果，需要确认时变风场下是否稳定。 |
| Case 3 `threshold_low` | 3 次 | 当前出现远离气源的 `stop_mode_confirmed`，需要确认 false positive 是否稳定出现。 |
| Case 3 `loss_tolerant` | 3 次 | 当前 SURGE steps 显著增加但失败，需要确认 plume loss 过宽松是否稳定有害。 |

这样只需要大约 `12` 次实验，比重新做第二组大矩阵更有解释力。

### 什么时候需要第二组 experiment？

如果导师希望进一步比较“不同初始状态”的参数敏感性，可以做第二组 focused experiment，但建议只选一个新状态：

| 候选 | 推荐程度 | 原因 |
| --- | --- | --- |
| `exp3_advection / far_near_edge` | 高 | exp3 中唯一 baseline 成功的边缘状态，可与 Case 3 的 exp2 边缘状态对比，分析定常平流 vs 时变风场。 |
| `exp2_time_varying / far_off_plume` | 中 | 可测试时变风场是否能让原本远离边缘的位置偶尔获得气味。 |
| `exp1_diffusion / far_off_plume` | 低 | exp1 扩散主导大多容易成功，参数敏感性可能不明显。 |

如果只能选一个，我建议做：

```text
第二组 focused experiment: exp3_advection / far_near_edge
```

原因是它和 Case 3 的初始关系相似，都是“远离气源但接近羽流边缘”，但风场不同：

- Case 3: `exp2_time_varying / far_near_edge`
- 新 Case: `exp3_advection / far_near_edge`

这样可以更直接回答：参数敏感性是否和风场类型有关。

## 当前建议

短期建议：

1. 先把这三组作为 sensitivity experiment 的第一阶段结果。
2. 不急着扩大参数矩阵。
3. 优先做少量重复实验，验证 Case 1 和 Case 3 的随机性。
4. 如果还要补一个新 case，再做 `exp3_advection / far_near_edge`。

可以给导师汇报的版本：

> 我先选了三个代表性初始状态做超参数敏感性分析：平流场中位于羽流内部、平流场中远离羽流边缘、以及时变风场中接近羽流边缘。结果显示，完全远离羽流时超参数基本不起作用；已经接触羽流时，状态切换和确认稳定性会影响结果；时变边缘羽流对 confidence、检测阈值和 plume loss 最敏感。下一步我计划先对关键设置做少量重复试验，而不是盲目扩大参数矩阵。
