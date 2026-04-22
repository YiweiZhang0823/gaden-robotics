# 第三阶段 Case 3 Threshold Low 重复性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 重复项 | `case3_threshold_low` |
| 场景 | `exp2_time_varying` |
| 初始状态 | `far_near_edge` |
| 导师要求对应情况 | 远离气源，但接近羽流边缘 |
| 参数组 | `sensitivity_threshold_low` |
| 重复次数 | `3` |
| 初始末端位置 | `(1.45, 4.25, 0.65)` |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| 验证目的 | 检查低检测阈值是否稳定引发 false positive 风险 |

## 三次重复结果

| trial | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | distance_confidence_confirmed | 112.4 | 6.361 | 0.221 | 0.243 | 12.470 | 0.620 | 23.944 | 64 | 36 | 0 |
| 2 | 1 | distance_confidence_confirmed | 60.0 | 3.621 | 0.184 | 0.200 | 9.707 | 0.607 | 57.194 | 33 | 20 | 0 |
| 3 | 1 | stop_mode_confirmed | 146.2 | 9.532 | 0.357 | 0.435 | 17.312 | 0.843 | 38.107 | 35 | 43 | 52 |

## 汇总指标

| 指标 | 数值 |
| --- | ---: |
| success rate | `3/3 = 1.00` |
| distance-confidence success | `2/3` |
| stop-mode success | `1/3` |
| mean time_s | `106.2` |
| mean path_m | `6.504` |
| mean min_dist_m | `0.254` |
| mean final_dist_m | `0.293` |
| mean final_confidence | `0.690` |
| mean CAST steps | `44.0` |
| mean SURGE steps | `33.0` |
| mean SPIRAL steps | `17.3` |

## 结果解读

三次重复实验全部显示 success，说明低检测阈值确实提高了算法在时变羽流边缘状态下触发有效搜索和成功判定的能力。与 `case3_baseline` 的 `1/3` 成功相比，`threshold_low` 的成功率提升到 `3/3`。

但是这三次成功的性质并不完全相同。trial 1 和 trial 2 是 `distance_confidence_confirmed`，最终距离分别为 `0.243 m` 和 `0.200 m`，都真正进入了 `success_radius=0.25 m`。这说明在某些时刻，降低阈值可以帮助机器人更早捕捉到边缘羽流并靠近气源。

trial 3 则是 `stop_mode_confirmed`，最终距离 `0.435 m`，最小距离 `0.357 m`，都没有进入 `success_radius=0.25 m`。也就是说，trial 3 虽然成功标记为 `1`，但不是通过距离与 confidence 同时满足的严格判定，而是通过 stop mode 确认。这正是第二阶段中担心的 false positive 风险。

此外，trial 3 的 SPIRAL steps 达到 `52`，而 trial 1 和 trial 2 的 SPIRAL steps 为 `0`。这说明低阈值可能让算法更容易进入局部搜索，但如果气味线索来自时变羽流中的瞬时/漂移结构，SPIRAL 可能围绕非气源附近的线索运行。

## 阶段性结论

Case 3 threshold-low 重复实验部分验证了第二阶段判断：

> 降低检测阈值可以提高时变羽流边缘状态下的触发能力和成功率，但也带来 false positive 风险。

更准确地说，低阈值不是单纯“更好”。它有两面性：

- 好处：更容易检测到弱羽流，可能更快靠近气源。
- 风险：更容易把瞬时/漂移气味线索当作可靠线索，在没有真正靠近气源时触发 stop mode。

因此，`theta_low/theta_mid/theta_high` 不应简单设置得越低越好。后续更合理的方向是让检测阈值和风场波动、气味持续性、confidence 稳定性结合，而不是只根据瞬时读数判断。
