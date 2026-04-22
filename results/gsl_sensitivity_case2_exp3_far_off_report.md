# Case 2 超参数敏感性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 场景 | `exp3_advection` |
| 初始状态 | `far_off_plume` |
| 导师要求对应情况 | 远离气源，且离羽流边缘也有一段距离 |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| Franka 基座位置 | `(0.8, 4.65, 0.0)` |
| 初始末端位置 | `(1.35, 4.2, 0.65)` |
| 初始距离 | `0.8292 m` |
| 关注问题 | 远离羽流边缘时，调节检测阈值、确认阈值或状态切换参数是否能让算法获得气味线索 |

## 实验结果

| param_set | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `sensitivity_baseline` | 0 | timeout | 180.0 | 19.640 | 0.712 | 0.771 | 0.000 | 0.000 | 0.000 | 161 | 0 | 0 |
| `sensitivity_conf_low` | 0 | timeout | 180.0 | 19.625 | 0.719 | 0.850 | 0.000 | 0.000 | 0.000 | 162 | 0 | 0 |
| `sensitivity_conf_high` | 0 | timeout | 180.0 | 20.489 | 0.722 | 0.895 | 0.000 | 0.000 | 0.000 | 163 | 0 | 0 |
| `sensitivity_threshold_low` | 0 | timeout | 180.0 | 20.169 | 0.713 | 0.846 | 0.000 | 0.000 | 0.000 | 161 | 0 | 0 |
| `sensitivity_loss_tolerant` | 0 | timeout | 180.2 | 19.808 | 0.714 | 0.851 | 0.000 | 0.000 | 0.000 | 161 | 0 | 0 |
| `sensitivity_spiral_easy` | 0 | timeout | 180.2 | 19.673 | 0.713 | 0.779 | 0.000 | 0.000 | 0.000 | 161 | 0 | 0 |

## 结果解读

这一组结果非常一致：六组参数全部 timeout，并且所有实验中 `final_raw=0`、`final_conf=0`、`max_margin=0`、`SURGE=0`、`SPIRAL=0`。

这说明 `far_off_plume` 的失败发生在最前面的 plume detection 阶段。机器人没有获得可用于追踪的气味线索，因此后续与成功确认、SURGE 丢失判定或 SPIRAL 进入条件有关的参数都没有机会发挥作用。

`sensitivity_conf_low` 和 `sensitivity_conf_high` 改变的是 `required_confidence`，但在这一组里没有影响。原因是 confidence 只有在机器人接近气源并持续检测到有效气味时才有意义；当前所有实验的 raw 和 confidence 都为 `0`，所以成功确认门槛不是主要限制。

`sensitivity_threshold_low` 降低了气味检测阈值：`theta_low/theta_mid/theta_high = 0.25/1.0/2.5`。但结果仍然是 `SURGE=0`，说明问题不是阈值设置过高，而是该初始位置处及机械臂局部 CAST 搜索范围内基本没有可用气体信号。

`sensitivity_loss_tolerant` 和 `sensitivity_spiral_easy` 也没有改变状态分布。原因是这两个参数主要作用于 SURGE 或 SPIRAL 阶段，但算法从未离开 CAST。

## 第六条实验单独分析：`sensitivity_spiral_easy`

第六条实验修改的是 SPIRAL 进入条件：

| 参数 | baseline | `sensitivity_spiral_easy` |
| --- | ---: | ---: |
| `spiral_enter_confidence` | `0.45` | `0.25` |
| `spiral_enter_steps` | `3` | `2` |
| `spiral_loss_steps` | `3` | `6` |
| `required_confidence` | `0.6` | `0.6` |

这组参数的目的，是让算法更早进入 SPIRAL，并且进入后更不容易因为短时气味丢失而退出。它用于验证：如果机器人远离羽流边缘，降低 SPIRAL 门槛能不能帮助机器人扩大局部搜索、找到气源。

实验结果为：

| 指标 | 结果 |
| --- | ---: |
| `success` | `0` |
| `stop_reason` | `timeout` |
| `time_s` | `180.2` |
| `path_m` | `19.673` |
| `min_dist_m` | `0.713` |
| `final_dist_m` | `0.779` |
| `final_raw` | `0.000` |
| `final_conf` | `0.000` |
| `CAST / SURGE / SPIRAL` | `161 / 0 / 0` |

这条结果和 Case 1 的第六条形成了非常清楚的对比。Case 1 中 `sensitivity_spiral_easy` 让 SPIRAL steps 增加到 `60`，说明在已经接触羽流的情况下，降低 SPIRAL 门槛会明显改变算法行为。但 Case 2 中，即使降低 SPIRAL 进入门槛，SPIRAL steps 仍然是 `0`。

原因是：SPIRAL 不是无条件触发的。它仍然需要一定的气味线索、confidence 或 confirmed plume 状态作为入口。当前实验中 `raw=0`、`confidence=0`、`SURGE=0`，说明机器人从未获得有效 plume contact。因此 SPIRAL 相关参数没有机会生效。

所以第六条实验的结论是：

> 在 `far_off_plume` 这种完全远离羽流边缘的初始状态下，降低 SPIRAL 进入门槛不能弥补没有气味输入的问题。SPIRAL 参数只有在机器人已经获得一定 plume cue 后才会敏感；没有 plume cue 时，算法会长期停留在 CAST。

## 初步结论

对于 `exp3_advection / far_off_plume`，算法对这些超参数并不敏感。更准确地说，不是参数不重要，而是这个初始状态缺少气味输入，导致参数机制无法被触发。

这组实验可以作为导师要求中“远离气源，且离羽流边缘也有一段距离”的典型反例：

> 在平流主导风场中，如果初始末端远离羽流边缘，机械臂局部搜索区域内没有 plume contact，则调节 success confidence、detection threshold、plume loss 或 SPIRAL entry 都不能改善表现。此时限制因素不是算法超参数，而是初始位置与羽流空间分布之间的关系。

## 与 Case 1 的对比

Case 1 `far_inside_plume` 中，loss 和 SPIRAL 参数会明显改变状态分布，例如 SPIRAL steps 可以从 `0` 增加到 `60`。但 Case 2 中所有参数组都保持 `CAST≈161`、`SURGE=0`、`SPIRAL=0`。

这说明参数敏感性本身依赖初始状态：

- 已经接触羽流时，状态切换和确认参数会影响算法行为。
- 完全离开羽流时，算法无法获得气味输入，超参数调节基本不起作用。

## 下一步

继续测试 Case 3：`exp2_time_varying / far_near_edge`。该 case 关注时变风场和羽流边缘状态下，`surge_loss_steps`、confidence 和 SPIRAL 进入条件是否更敏感。
