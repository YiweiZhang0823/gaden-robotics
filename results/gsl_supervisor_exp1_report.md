# Exp1 扩散主导场景初始状态实验汇总

## 统一实验设置

| 项目 | 设置 |
| --- | --- |
| 场景 | `exp1_diffusion` |
| 风场/羽流特点 | 扩散主导，弱/无平均风，气体在气源附近更弥散 |
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

## 五类初始状态与实验结果

| 初始状态 | 导师要求对应情况 | 末端初始位置 `(x,y,z)` | 初始距离 m | success | stop_reason | time_s | path_length_m | min_distance_m | final_distance_m | final_raw | final_confidence | max_margin_seen | CAST | SURGE | SPIRAL |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `far_off_plume` | 远离气源，且离羽流边缘也有一段距离 | `(1.25, 4.1, 0.65)` | 0.8874 | 1 | stop_mode_confirmed | 27.000 | 1.7863 | 0.6433 | 0.6433 | 44.5743 | 0.9254 | 43.6726 | 7 | 5 | 12 |
| `far_near_edge` | 远离气源，但接近羽流边缘 | `(1.35, 4.35, 0.65)` | 0.6964 | 1 | stop_mode_confirmed | 26.800 | 1.7395 | 0.3750 | 0.3750 | 138.1823 | 0.9183 | 137.0627 | 7 | 5 | 12 |
| `far_inside_plume` | 远离气源，但已经在羽流内部 | `(1.35, 4.95, 0.65)` | 0.3536 | 1 | distance_confidence_confirmed | 29.800 | 1.5079 | 0.2423 | 0.2423 | 339.6362 | 0.9579 | 172.4722 | 15 | 9 | 2 |
| `near_source_outside_plume` | 靠近气源，但完全在羽流外 | `(1.0, 4.25, 0.65)` | 0.7018 | 1 | stop_mode_confirmed | 25.400 | 1.5375 | 0.4828 | 0.5030 | 82.4480 | 0.9260 | 77.7316 | 7 | 3 | 13 |
| `near_source_upwind` | 靠近气源，且位于气源上游一侧 | `(0.75, 4.95, 0.65)` | 0.2550 | 1 | distance_confidence_confirmed | 9.400 | 0.6153 | 0.2293 | 0.2442 | 278.6183 | 0.6278 | 127.0842 | 7 | 1 | 0 |

## 结果解读

五类初始状态在 `exp1_diffusion` 中均成功。与 `exp3_advection` 相比，扩散主导场景中的气味分布更宽、更弥散，因此即使末端初始位置位于上游参考侧或横向偏离羽流，也仍然能够获得较强气味线索。

`near_source_upwind` 的成功时间最短，仅 `9.4 s`，说明在弱风/扩散主导场景中，上游参考位置并不会像平流主导场景那样完全缺乏气味。

`far_off_plume` 和 `near_source_outside_plume` 在设计上属于气味线索较弱的位置，但仍然分别在 `27.0 s` 和 `25.4 s` 成功，说明 Example1 中“羽流外”的惩罚明显小于 Example3。

`far_inside_plume` 的 final_raw 最高，达到 `339.6362`，符合其初始位置位于羽流内部的预期。

## 初步结论

在扩散主导场景中，初始状态对成功率的影响较弱，五类初始状态均能成功定位。该结果与 exp3 平流主导场景形成对比：平流主导场景中，是否位于羽流边缘/内部以及是否处于上游，会显著影响算法能否获得气味线索并进入有效搜索阶段。
