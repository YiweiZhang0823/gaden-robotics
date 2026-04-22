# 第三阶段 Case 3 Baseline 重复性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 重复项 | `case3_baseline` |
| 场景 | `exp2_time_varying` |
| 初始状态 | `far_near_edge` |
| 导师要求对应情况 | 远离气源，但接近羽流边缘 |
| 参数组 | `sensitivity_baseline` |
| 重复次数 | `3` |
| 初始末端位置 | `(1.45, 4.25, 0.65)` |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| 验证目的 | 检查时变风场羽流边缘状态下 baseline 是否稳定成功 |

## 三次重复结果

| trial | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | timeout | 180.0 | 13.029 | 0.524 | 1.162 | 0.294 | 0.066 | 8.369 | 107 | 55 | 0 |
| 2 | 0 | timeout | 180.0 | 13.926 | 0.541 | 1.099 | 0.174 | 0.000 | 23.491 | 142 | 20 | 0 |
| 3 | 1 | distance_confidence_confirmed | 152.6 | 6.578 | 0.250 | 0.250 | 93.019 | 0.935 | 97.391 | 60 | 74 | 2 |

## 汇总指标

| 指标 | 数值 |
| --- | ---: |
| success rate | `1/3 = 0.33` |
| mean time_s | `170.9` |
| mean path_m | `11.177` |
| mean min_dist_m | `0.438` |
| mean final_dist_m | `0.837` |
| mean final_confidence | `0.334` |
| mean CAST steps | `103.0` |
| mean SURGE steps | `49.7` |
| mean SPIRAL steps | `0.7` |

## 结果解读

三次重复实验中只有一次成功，说明 `exp2_time_varying / far_near_edge` 的 baseline 并不是稳定成功。第二阶段中 baseline 单次表现最好，但重复实验表明该状态仍然受到时变羽流瞬时形态影响。

trial 1 和 trial 2 均 timeout，最终距离分别为 `1.162 m` 和 `1.099 m`，final confidence 很低。它们都进入了 SURGE，但没有稳定靠近气源，说明边缘羽流虽然提供了气味线索，但这些线索不一定可靠。

trial 3 成功，最终距离 `0.2496 m`，final confidence `0.935`。这一试验中 `SURGE=74`，说明当羽流线索足够连续时，baseline 可以沿气味线索靠近气源并完成确认。

## 阶段性结论

Case 3 baseline 重复实验支持第二阶段的判断：

> 时变风场中的羽流边缘状态具有明显随机性。baseline 可以成功，但成功并不稳定；同一初始状态下，羽流瞬时形态会决定机器人能否持续获得可靠 plume cue。

因此，`exp2_time_varying / far_near_edge` 适合作为研究参数敏感性的代表状态，因为它不是完全无气味，也不是稳定强气味，而是处在气味间歇区域。

这也说明后续分析中应避免只依据单次 baseline 成功得出“该参数鲁棒”的结论，应使用重复实验统计成功率、路径长度和最终距离。
