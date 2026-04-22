# Case 3 超参数敏感性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 场景 | `exp2_time_varying` |
| 初始状态 | `far_near_edge` |
| 导师要求对应情况 | 远离气源，但接近羽流边缘 |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| Franka 基座位置 | `(0.8, 4.65, 0.0)` |
| 初始末端位置 | `(1.45, 4.25, 0.65)` |
| 初始距离 | `0.8337 m` |
| 关注问题 | 时变风场边缘状态下，confidence、检测阈值、plume loss 和 SPIRAL 进入条件是否敏感 |

## 实验结果

| param_set | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `sensitivity_baseline` | 1 | distance_confidence_confirmed | 84.2 | 5.082 | 0.230 | 0.230 | 34.219 | 0.619 | 81.796 | 51 | 24 | 0 |
| `sensitivity_conf_low` | 1 | distance_confidence_confirmed | 120.4 | 6.848 | 0.223 | 0.223 | 89.839 | 0.313 | 115.919 | 72 | 35 | 0 |
| `sensitivity_conf_high` | 0 | timeout | 180.2 | 11.934 | 0.757 | 1.102 | 5.817 | 0.000 | 65.274 | 110 | 50 | 0 |
| `sensitivity_threshold_low` | 1 | stop_mode_confirmed | 149.6 | 10.005 | 0.736 | 1.118 | 5.567 | 0.680 | 69.182 | 62 | 34 | 39 |
| `sensitivity_loss_tolerant` | 0 | timeout | 180.0 | 5.361 | 0.666 | 1.111 | 2.718 | 0.000 | 28.660 | 56 | 106 | 0 |
| `sensitivity_spiral_easy` | 0 | timeout | 180.2 | 14.414 | 0.632 | 1.125 | 3.417 | 0.000 | 77.935 | 102 | 60 | 0 |

## 结果解读

这一组和 Case 2 完全不同。Case 2 中所有实验都 `raw=0`、`SURGE=0`，说明机器人没有接触羽流；而 Case 3 中 baseline 能成功，说明时变风场的羽流边缘虽然间歇，但仍然能提供可追踪的气味线索。

`sensitivity_baseline` 是本组表现最好的参数组。它在 `84.2 s` 内成功，路径长度 `5.082 m`，最终距离 `0.230 m`，最终 confidence `0.619`。这说明默认参数在该时变边缘状态下能够完成定位。

`sensitivity_conf_low` 也成功，但时间更长、路径更长。它最终 confidence 为 `0.313`，刚好超过降低后的门槛 `0.3`。这说明降低成功确认门槛并没有提高效率，反而可能让搜索过程变得更长。

`sensitivity_conf_high` 失败，说明该状态对高 confidence 门槛敏感。时变风场边缘的气味线索不稳定，如果要求 `required_confidence=0.8`，机器人容易错过确认机会，并在后续搜索中逐渐远离气源。

`sensitivity_threshold_low` 成功，但需要谨慎解释。它的 `stop_reason=stop_mode_confirmed`，不是 `distance_confidence_confirmed`；同时 `min_dist_m=0.736`、`final_dist_m=1.118`，都离气源较远。这说明降低检测阈值可能导致算法根据瞬时或漂移气味线索触发 stop mode，而不一定真正靠近气源。

`sensitivity_loss_tolerant` 失败，但状态分布变化明显：SURGE steps 从 baseline 的 `24` 增加到 `106`。这说明 `surge_loss_steps` 等 plume loss 参数在时变风场中非常敏感；但过度容忍 plume loss 会让机器人沿着不稳定线索继续 SURGE，最终远离气源。

`sensitivity_spiral_easy` 也失败。虽然它降低了 SPIRAL 进入门槛，但最终 `SPIRAL=0`，说明该次试验中并没有形成足够可靠的 SPIRAL 入口条件。它的 CAST 和 SURGE 步数都较高，最终距离 `1.125 m`，说明更早 SPIRAL 的设置没有解决边缘羽流中的 tracking 不稳定问题。

## 第六条实验单独分析：`sensitivity_spiral_easy`

第六条实验修改的是 SPIRAL 进入条件：

| 参数 | baseline | `sensitivity_spiral_easy` |
| --- | ---: | ---: |
| `spiral_enter_confidence` | `0.45` | `0.25` |
| `spiral_enter_steps` | `3` | `2` |
| `spiral_loss_steps` | `3` | `6` |
| `required_confidence` | `0.6` | `0.6` |

实验结果为：

| 指标 | 结果 |
| --- | ---: |
| `success` | `0` |
| `stop_reason` | `timeout` |
| `time_s` | `180.2` |
| `path_m` | `14.414` |
| `min_dist_m` | `0.632` |
| `final_dist_m` | `1.125` |
| `final_raw` | `3.417` |
| `final_conf` | `0.000` |
| `CAST / SURGE / SPIRAL` | `102 / 60 / 0` |

这条结果说明，降低 SPIRAL 进入门槛并没有让算法进入 SPIRAL。虽然参数更宽松，但该次实验中的气味线索和 confidence 并没有稳定到足以触发 SPIRAL 的程度。

与 Case 1 不同，Case 1 的 `sensitivity_spiral_easy` 产生了 `60` 个 SPIRAL steps；而 Case 3 的第六条仍然是 `SPIRAL=0`。这说明 SPIRAL 参数是否敏感，也依赖初始状态和风场中的气味稳定性。仅仅降低门槛不够，算法还必须先获得足够连续、可靠的 plume cue。

因此第六条可以写成：

> 在时变风场的羽流边缘状态下，降低 SPIRAL 进入门槛并不一定触发局部精搜索。如果气味线索持续性不足，算法仍会主要停留在 CAST/SURGE 之间，无法进入 SPIRAL 并完成定位。

## 初步结论

对于 `exp2_time_varying / far_near_edge`，算法对以下参数敏感：

- `required_confidence`：过高会导致失败，过低不一定提升效率。
- `theta_low/theta_mid/theta_high`：过低可能引发远离气源的 stop mode 确认，有 false positive 风险。
- `surge_loss_steps`：放宽后显著增加 SURGE 步数，但可能沿着不稳定 plume cue 远离气源。

本组最好的结果是 baseline。它在距离、时间、路径长度和 confidence 之间取得了更好的平衡。

## 与 Case 1 / Case 2 的对比

Case 1 `exp3_advection / far_inside_plume` 已经在羽流内部，因此状态切换和确认稳定性会明显影响结果。

Case 2 `exp3_advection / far_off_plume` 完全缺少 plume contact，因此所有超参数都几乎不起作用。

Case 3 `exp2_time_varying / far_near_edge` 介于两者之间：有气味线索，但线索间歇、不稳定，所以参数会显著影响成功率、确认方式和状态分布。

这说明导师提到的“某些状态下 fine tune 的参数不一定适合其他初始状态”是成立的。参数敏感性不是固定的，而是由初始位置与羽流、气源、风向之间的关系共同决定。
