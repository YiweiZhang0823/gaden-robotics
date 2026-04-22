# 第三阶段 Case 3 Loss Tolerant 重复性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 重复项 | `case3_loss_tolerant` |
| 场景 | `exp2_time_varying` |
| 初始状态 | `far_near_edge` |
| 导师要求对应情况 | 远离气源，但接近羽流边缘 |
| 参数组 | `sensitivity_loss_tolerant` |
| 重复次数 | `3` |
| 初始末端位置 | `(1.45, 4.25, 0.65)` |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| 验证目的 | 检查放宽 plume loss 是否稳定导致过长 SURGE 和远离气源 |

## 三次重复结果

| trial | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | timeout | 180.0 | 6.676 | 0.656 | 0.704 | 3.285 | 0.000 | 27.152 | 60 | 102 | 0 |
| 2 | 1 | distance_confidence_confirmed | 47.0 | 3.225 | 0.174 | 0.174 | 86.481 | 0.628 | 86.176 | 17 | 25 | 0 |
| 3 | 1 | distance_confidence_confirmed | 79.0 | 3.634 | 0.152 | 0.159 | 109.243 | 0.621 | 110.479 | 29 | 42 | 0 |

## 汇总指标

| 指标 | 数值 |
| --- | ---: |
| success rate | `2/3 = 0.67` |
| mean time_s | `102.0` |
| mean path_m | `4.512` |
| mean min_dist_m | `0.327` |
| mean final_dist_m | `0.346` |
| mean final_confidence | `0.416` |
| mean CAST steps | `35.3` |
| mean SURGE steps | `56.3` |
| mean SPIRAL steps | `0.0` |

## 结果解读

三次重复实验中有两次成功、一次 timeout。这个结果修正了第二阶段的初步判断：放宽 plume loss 并不是稳定有害，也不是稳定有效，而是在时变羽流边缘状态下表现出明显的随机性。

trial 1 失败，并且 `SURGE=102`，最终距离 `0.704 m`，final confidence 为 `0`。这说明在某些时刻，放宽 plume loss 会让机器人长时间沿着不可靠的气味线索继续 SURGE，最后没有靠近气源。

trial 2 和 trial 3 均成功，且时间分别为 `47.0 s` 和 `79.0 s`，比 baseline 重复实验中的成功试验 `152.6 s` 更快。这说明在羽流线索比较连续时，放宽 plume loss 可以避免算法过早退出 SURGE，从而更快沿气味线索靠近气源。

因此，`sensitivity_loss_tolerant` 的效果是双面的：

- 好处：当羽流线索连续但有短时波动时，放宽 loss 可以保持 SURGE，提高搜索连续性。
- 风险：当气味线索不可靠或漂移时，放宽 loss 会让机器人继续沿错误方向 SURGE，造成 timeout。

## 阶段性结论

Case 3 loss-tolerant 重复实验说明：

> `surge_loss_steps` 和 plume loss 相关参数确实是时变风场边缘状态下的敏感参数。它们可以提升成功速度，也可能导致错误追踪；因此不能简单设置得越宽松越好。

更合理的改进方向是让 plume loss 判定同时考虑：

- 当前气味强度是否仍然高于阈值
- 最近一段时间气味是否连续
- 机器人是否正在接近气源估计区域
- 风场是否时变、羽流是否间歇

这也回应了导师提到的“敏感超参数是否和风速/风场有关”：在时变风场边缘状态下，plume loss 参数确实会明显影响算法行为。
