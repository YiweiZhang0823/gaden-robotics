# Exp2 时变风场初始状态实验汇总

## 统一实验设置

| 项目 | 设置 |
| --- | --- |
| 场景 | `exp2_time_varying` |
| 风场/羽流特点 | 时变风场，净下游方向约为 `+x`，羽流会随时间摆动和间歇变化 |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| Franka 基座位置 | `(0.8, 4.65, 0.0)` |
| 算法 | `CAST/SURGE/SPIRAL` |
| 参数组 | `supervisor_initial_state_matrix` |
| `timeout_s` | `180.0` |
| `success_radius` | `0.25 m` |
| `required_confidence` | `0.6` |
| `control_period` | `1.0 s` |
| `goal_preset` | `tilt_x_90` |
| `search_heading_yaw` | `3.1416` |

## 数据选择说明

本报告为了与 Example1 和 Example3 的单次实验表格保持一致，主表按每个初始状态选取一次记录。当前 `far_off_plume` 有两次记录：第一次 timeout，第二次成功。主表采用第一次记录；重复试验结果在“重复实验说明”中单独列出。

## 五类初始状态与实验结果（每组一次）

| 初始状态 | 导师要求对应情况 | 末端初始位置 `(x,y,z)` | 初始距离 m | success | stop_reason | time_s | path_length_m | min_distance_m | final_distance_m | final_raw | final_confidence | max_margin_seen | CAST | SURGE | SPIRAL |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `far_off_plume` | 远离气源，且离羽流边缘也有一段距离 | `(1.3, 4.05, 0.65)` | 0.9500 | 0 | timeout | 180.000 | 13.9318 | 0.2521 | 0.4246 | 3.2331 | 0.0000 | 132.4445 | 113 | 48 | 0 |
| `far_near_edge` | 远离气源，但接近羽流边缘 | `(1.45, 4.25, 0.65)` | 0.8337 | 0 | timeout | 180.200 | 12.7836 | 0.2146 | 0.3194 | 6.8498 | 0.0023 | 87.6701 | 94 | 67 | 0 |
| `far_inside_plume` | 远离气源，但已经在羽流内部 | `(1.45, 5.0, 0.65)` | 0.4555 | 1 | distance_confidence_confirmed | 63.200 | 3.8751 | 0.2068 | 0.2389 | 10.7529 | 0.6164 | 28.7933 | 42 | 15 | 0 |
| `near_source_outside_plume` | 靠近气源，但完全在羽流外 | `(1.0, 4.25, 0.65)` | 0.7018 | 1 | distance_confidence_confirmed | 39.600 | 2.0667 | 0.2449 | 0.2449 | 113.3023 | 0.8102 | 167.3519 | 14 | 11 | 10 |
| `near_source_upwind` | 靠近气源，且位于气源上游一侧 | `(0.75, 4.95, 0.65)` | 0.2550 | 1 | distance_confidence_confirmed | 16.600 | 1.2094 | 0.1995 | 0.1995 | 173.1943 | 0.6207 | 177.7018 | 13 | 1 | 0 |

## 重复实验说明

`far_off_plume` 被运行了两次，结果如下：

| trial | success | stop_reason | time_s | path_length_m | min_distance_m | final_distance_m | final_raw | final_confidence | max_margin_seen | CAST | SURGE | SPIRAL |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | timeout | 180.000 | 13.9318 | 0.2521 | 0.4246 | 3.2331 | 0.0000 | 132.4445 | 113 | 48 | 0 |
| 2 | 1 | distance_confidence_confirmed | 99.800 | 6.6193 | 0.2363 | 0.2363 | 216.2203 | 0.6257 | 223.7849 | 58 | 32 | 0 |

## 结果解读

Example2 是时变风场，整体表现介于 Example1 的扩散主导和 Example3 的平流主导之间。与 Example3 相比，多个初始状态都能获得较强气味线索并达到成功判定；但因为风场随时间变化，部分状态会出现靠近气源但 confidence 不稳定或最终 timeout 的情况。

`far_inside_plume`、`near_source_outside_plume` 和 `near_source_upwind` 在当前记录中成功，说明时变风场下气味线索覆盖范围比 exp3 的窄定常羽流更宽。尤其 `near_source_upwind` 虽然位于上游，但仍然在 `16.6 s` 成功，这表明时变风和扩散会使上游参考位置也短时获得有效气味。

`far_near_edge` timeout，但最近距离达到 `0.2146 m`，已经进入 `success_radius=0.25 m`，失败主要是因为当时 confidence 很低，没有满足 `required_confidence=0.6`。这和 exp3 中 `far_inside_plume` 的失败模式类似：机器人能接近气源，但确认条件不稳定。

`far_off_plume` 的两次重复实验一次失败、一次成功，说明时变风场下边缘/外部位置具有随机性和间歇性；同一初始状态可能因为羽流瞬时形态不同而得到不同结果。

## 初步结论

在时变风场中，初始状态仍然显著影响搜索表现，但影响不如 exp3 的定常平流场那样单调。羽流的摆动和间歇性会让原本在羽流外或上游的位置偶尔获得有效气味线索，因此同一初始状态可能出现成功和失败并存。这说明后续参数敏感性分析应重点关注与气味间歇性相关的参数，例如 `theta_low/theta_mid/theta_high`、`confidence` 更新、`surge_loss_steps` 和 `SPIRAL` 进入条件。
