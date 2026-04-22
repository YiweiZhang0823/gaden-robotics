# 第三阶段 Case 1 重复性实验报告

## 实验对象

| 项目 | 设置 |
| --- | --- |
| 重复项 | `case1_baseline` |
| 场景 | `exp3_advection` |
| 初始状态 | `far_inside_plume` |
| 导师要求对应情况 | 远离气源，但已经在羽流内部 |
| 参数组 | `sensitivity_baseline` |
| 重复次数 | `3` |
| 初始末端位置 | `(1.55, 4.95, 0.65)` |
| 气源位置 | `(1.0, 4.95, 0.7)` |
| 验证目的 | 检查平流主导场景中，位于羽流内部时 baseline 是否稳定成功 |

## 三次重复结果

| trial | success | stop_reason | time_s | path_m | min_dist_m | final_dist_m | final_raw | final_conf | max_margin | CAST | SURGE | SPIRAL |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | timeout | 180.2 | 13.570 | 0.035 | 0.188 | 0.000 | 0.000 | 9.977 | 140 | 23 | 0 |
| 2 | 0 | timeout | 180.2 | 17.733 | 0.084 | 0.236 | 0.000 | 0.000 | 0.000 | 162 | 0 | 0 |
| 3 | 0 | timeout | 180.2 | 17.410 | 0.111 | 0.203 | 0.000 | 0.000 | 0.000 | 162 | 0 | 0 |

## 汇总指标

| 指标 | 数值 |
| --- | ---: |
| success rate | `0/3 = 0.00` |
| mean time_s | `180.2` |
| mean path_m | `16.237` |
| mean min_dist_m | `0.076` |
| mean final_dist_m | `0.209` |
| mean final_confidence | `0.000` |
| mean CAST steps | `154.7` |
| mean SURGE steps | `7.7` |
| mean SPIRAL steps | `0.0` |

## 结果解读

三次重复实验全部 timeout，说明 `exp3_advection / far_inside_plume` 的 baseline 结果并不稳定。第二阶段中同一设置曾经成功一次，但第三阶段三次重复均失败，因此不能把单次成功解释为该设置稳定可靠。

值得注意的是，三次重复的 `min_dist_m` 都小于 `success_radius=0.25 m`：

- trial 1: `0.035 m`
- trial 2: `0.084 m`
- trial 3: `0.111 m`

这说明机器人曾经非常接近气源，但最终仍未满足成功判定。失败的关键不在于“有没有靠近气源”，而在于靠近气源后没有形成稳定的 confidence。三次实验最终 `final_raw=0`、`final_conf=0`，说明机器人最后都没有保持在稳定气味区域。

trial 1 出现过一定气味线索，`max_margin=9.977`，并进入了 `SURGE=23` 步；但 trial 2 和 trial 3 基本一直停留在 CAST，`SURGE=0`。这说明即使初始位置设计为羽流内部，平流主导场景中的局部气味线索仍可能具有明显波动。

## 阶段性结论

Case 1 重复实验支持第二阶段的判断：

> 在平流主导场景中，即使初始末端位于羽流内部，算法也会受到 plume cue 稳定性和 confidence 累积机制的影响。单次成功不能说明该初始状态稳定可靠；需要通过重复实验评估随机性。

这也说明后续如果要改进算法，重点不应只是降低 `required_confidence`，而应该关注：

- 接近气源后的停留/确认机制
- confidence 的时间累积方式
- plume cue 短时消失时是否应该保持局部搜索
- 是否需要基于风场稳定性调整确认条件
