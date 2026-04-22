# Case 1 超参数敏感性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 场景 | `exp3_advection` |
| 初始状态 | `far_inside_plume` |
| 导师要求对应情况 | 远离气源，但已经在羽流内部 |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| Franka 基座位置 | `(0.8, 4.65, 0.0)` |
| 初始末端位置 | `(1.55, 4.95, 0.65)` |
| 初始距离 | `0.5523 m` |
| 关注问题 | 已经在羽流内部时，哪些算法超参数会影响是否成功定位气源 |

## 实验结果

| param_set | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `sensitivity_baseline` | 1 | distance_confidence_confirmed | 71.0 | 4.307 | 0.159 | 0.159 | 9.047 | 0.610 | 15.195 | 44 | 19 | 0 |
| `sensitivity_conf_low` | 0 | timeout | 180.0 | 7.670 | 0.273 | 0.280 | 14.129 | 0.171 | 18.243 | 79 | 81 | 0 |
| `sensitivity_conf_high` | 0 | timeout | 180.0 | 8.612 | 0.299 | 0.389 | 8.014 | 0.080 | 17.006 | 92 | 68 | 0 |
| `sensitivity_threshold_low` | 0 | timeout | 180.2 | 15.730 | 0.149 | 0.307 | 0.000 | 0.000 | 12.160 | 145 | 16 | 0 |
| `sensitivity_loss_tolerant` | 0 | timeout | 180.2 | 11.049 | 0.263 | 0.673 | 0.000 | 0.000 | 20.888 | 97 | 36 | 28 |
| `sensitivity_spiral_easy` | 0 | timeout | 180.2 | 6.785 | 0.273 | 0.321 | 4.814 | 0.022 | 19.852 | 51 | 49 | 60 |

## 结果解读

这一组最直接的结论是：`far_inside_plume` 并不是简单对 `required_confidence` 单参数敏感。

`sensitivity_baseline` 成功，说明该初始状态本身可以完成定位。但 `sensitivity_conf_low` 和 `sensitivity_conf_high` 都失败，说明只降低或提高成功确认门槛并不能稳定改善结果。失败试验中的 `min_distance_m` 分别为 `0.273 m` 和 `0.299 m`，没有进入 `success_radius=0.25 m`，所以失败不仅是 confidence 门槛问题，也和路径是否稳定靠近气源有关。

`sensitivity_threshold_low` 的 `min_distance_m=0.149 m`，已经非常接近气源，但最终 `final_confidence=0` 且 `final_distance_m=0.307 m`。这说明降低检测阈值能让机器人一度靠近气源，但靠近后没有稳定确认，随后又离开了气源附近。

`sensitivity_loss_tolerant` 和 `sensitivity_spiral_easy` 都让 SPIRAL 进入了算法流程，分别产生 `28` 和 `60` 个 SPIRAL steps。但两者都没有成功，说明更容易进入或保持局部搜索不一定更好；如果进入 SPIRAL 时的气味线索不稳定，局部搜索可能围绕错误线索继续运动。

## 第六条实验单独分析：`sensitivity_spiral_easy`

第六条实验修改的是 SPIRAL 进入条件：

| 参数 | baseline | `sensitivity_spiral_easy` |
| --- | ---: | ---: |
| `spiral_enter_confidence` | `0.45` | `0.25` |
| `spiral_enter_steps` | `3` | `2` |
| `spiral_loss_steps` | `3` | `6` |
| `required_confidence` | `0.6` | `0.6` |

这组参数的意思是：只要 confidence 达到较低水平，并且连续较少步数满足条件，就更早进入 SPIRAL；同时进入 SPIRAL 后也更不容易因为短时气味丢失而退出。

实验结果为：

| 指标 | 结果 |
| --- | ---: |
| `success` | `0` |
| `stop_reason` | `timeout` |
| `time_s` | `180.2` |
| `path_m` | `6.785` |
| `min_dist_m` | `0.273` |
| `final_dist_m` | `0.321` |
| `final_raw` | `4.814` |
| `final_conf` | `0.022` |
| `CAST / SURGE / SPIRAL` | `51 / 49 / 60` |

这条结果说明：降低 SPIRAL 进入门槛确实显著改变了算法行为，因为 SPIRAL steps 从 baseline 的 `0` 增加到 `60`。也就是说，算法确实更早、更频繁地进入局部精搜索阶段。

但它没有成功。主要原因有两个：

- 最近距离 `min_dist_m=0.273 m`，没有进入 `success_radius=0.25 m`，所以即使中途 confidence 曾经升高，也没有满足“距离足够近”的成功条件。
- 最终 `final_conf=0.022`，说明机器人最后没有保持住稳定气味线索，而是从较强气味区域离开了。

因此，第六条不能解释为“SPIRAL 没有用”，更准确的解释是：

> 在这个初始状态下，过早进入 SPIRAL 会让机器人围绕局部、瞬时的气味线索搜索，但这些线索不一定对应气源附近。SPIRAL 的进入条件降低后，局部搜索变多了，但没有带来更稳定的气源确认。

从实验设计角度，这条证明了 `spiral_enter_confidence` 和 `spiral_enter_steps` 是敏感参数，因为它们明显改变了状态分布；但从定位性能看，单独降低 SPIRAL 门槛不是有效改进。

## 初步结论

对于 `exp3_advection / far_inside_plume`，算法表现主要受以下因素共同影响：

- 气味线索的瞬时波动
- SURGE 方向是否稳定
- 靠近气源后的 confidence 是否能持续累积
- SPIRAL 是否在可靠线索下进入

因此这组不能简单写成“降低 confidence 更好”或“更早 SPIRAL 更好”。更准确的表述是：

> 在平流主导场景中，即使初始末端位于羽流内部，算法也对 plume tracking 和确认稳定性非常敏感。单独降低成功确认阈值、降低检测阈值或提前进入 SPIRAL 都不能保证成功；相反，如果气味线索不稳定，参数放宽可能导致更长路径和更多无效搜索。

## 下一步

继续测试 Case 2：`exp3_advection / far_off_plume`。该 case 关注远离羽流边缘时是否主要受气味检测阈值影响。
