# 第三阶段重复性验证总结报告

## 实验目的

第三阶段不是继续更换参数，而是验证第二阶段中几个关键结论是否稳定。由于 GADEN 羽流和时变风场具有瞬时波动，单次实验结果可能偶然，因此需要对关键设置做少量重复实验。

## 重复实验总览

| 重复项 | 场景 / 初始状态 | 参数组 | 成功率 | 主要结论 |
| --- | --- | --- | ---: | --- |
| Case 1 baseline | `exp3_advection / far_inside_plume` | `sensitivity_baseline` | `0/3` | 即使在羽流内部，baseline 也不稳定；机器人能靠近气源但 confidence 不能稳定累积 |
| Case 3 baseline | `exp2_time_varying / far_near_edge` | `sensitivity_baseline` | `1/3` | 时变羽流边缘下 baseline 可成功但不鲁棒 |
| Case 3 threshold low | `exp2_time_varying / far_near_edge` | `sensitivity_threshold_low` | `3/3` | 低阈值提高成功率，但有 `stop_mode_confirmed` 的 false positive 风险 |
| Case 3 loss tolerant | `exp2_time_varying / far_near_edge` | `sensitivity_loss_tolerant` | `2/3` | 放宽 plume loss 有时更快成功，有时沿错误线索失败，表现不稳定 |

## 关键数据对比

| 重复项 | mean_time_s | mean_path_m | mean_min_dist_m | mean_final_dist_m | mean_final_conf | mean CAST/SURGE/SPIRAL |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Case 1 baseline | 180.2 | 16.237 | 0.076 | 0.209 | 0.000 | 154.7 / 7.7 / 0.0 |
| Case 3 baseline | 170.9 | 11.177 | 0.438 | 0.837 | 0.334 | 103.0 / 49.7 / 0.7 |
| Case 3 threshold low | 106.2 | 6.504 | 0.254 | 0.293 | 0.690 | 44.0 / 33.0 / 17.3 |
| Case 3 loss tolerant | 102.0 | 4.512 | 0.327 | 0.346 | 0.416 | 35.3 / 56.3 / 0.0 |

## 主要发现

### 1. Case 1 baseline 的单次成功不稳定

第二阶段中 `exp3_advection / far_inside_plume` 的 baseline 曾经成功，但第三阶段重复 3 次全部 timeout。三次实验的 `min_dist_m` 分别为 `0.035 m`、`0.084 m`、`0.111 m`，都已经非常接近气源，但最终 `final_confidence=0`。

这说明失败不是因为机器人无法靠近气源，而是因为靠近后没有稳定保持气味线索，也没有形成持续 confidence。

### 2. Case 3 baseline 在时变边缘羽流下不鲁棒

`exp2_time_varying / far_near_edge` 的 baseline 重复成功率为 `1/3`。它可以成功，但不稳定。同一初始状态下，是否成功取决于时变羽流是否提供足够连续的 plume cue。

### 3. threshold low 提高成功率，但存在 false positive 风险

`sensitivity_threshold_low` 三次都成功，其中两次是 `distance_confidence_confirmed`，一次是 `stop_mode_confirmed`。第三次虽然 success=1，但最终距离 `0.435 m`，没有进入 `success_radius=0.25 m`。

因此，低阈值能提高弱羽流检测能力，但也可能把瞬时/漂移气味线索误认为可靠气源线索。

### 4. loss tolerant 的效果是双面的

`sensitivity_loss_tolerant` 三次中两次成功，一次失败。成功时它比 baseline 更快；失败时则长时间 SURGE 并最终远离气源。这说明 plume loss 参数确实敏感，但不能简单认为越宽松越好。

## 对第二阶段结论的修正

第三阶段帮助我们把第二阶段的单次实验结论修正得更准确：

- Case 1 baseline 不是稳定成功，而是存在明显不稳定性。
- Case 3 baseline 不是鲁棒成功，重复成功率只有 `1/3`。
- threshold low 确实能提高成功率，但 false positive 风险也被重复实验验证。
- loss tolerant 不是稳定有害，而是风险与收益并存。

## 给导师汇报的简短表述

第三阶段我对第二阶段中最关键的四个设置做了重复实验。结果显示，单次实验确实会受到羽流瞬时波动影响。平流场中位于羽流内部的 baseline 三次都 timeout，虽然机器人曾非常接近气源，但 confidence 无法稳定累积。时变风场边缘的 baseline 成功率为 `1/3`，说明该状态具有明显随机性。降低检测阈值将成功率提高到 `3/3`，但其中一次是在距离气源较远时通过 stop mode 确认，说明有 false positive 风险。放宽 plume loss 的成功率为 `2/3`，有时能更快成功，有时会沿错误气味线索失败。因此，后续参数设计应考虑气味线索的持续性和风场稳定性，而不是简单放宽阈值或 plume loss 条件。

## 后续建议

下一步可以考虑两条路线：

1. 算法改进：加入更严格的 source confirmation，例如要求距离、confidence 和气味持续性同时满足，减少 stop mode false positive。
2. 参数自适应：根据风场类型和羽流间歇性调整 detection threshold 与 plume loss 判定，而不是使用固定参数。
