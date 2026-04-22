# GSL 阶段一与阶段二实验汇报总结

## 汇报目标

本阶段工作围绕导师提出的两个问题展开：

1. 不同初始状态是否会影响机械臂气源定位算法表现？
2. 在不同初始状态和风场下，哪些算法超参数更敏感？

实验均使用同一套 `CAST/SURGE/SPIRAL` 气源定位流程，气源位置固定为 `(1.0, 4.95, 0.7)`，Franka 基座位置固定为 `(0.8, 4.65, 0.0)`。不同实验只改变风场场景、末端初始位置和算法参数。

## 阶段一：不同风场与初始状态实验

阶段一对应导师要求的“观察羽流形态，然后设计多种机械臂初始状态”。我在三个场景中设置了五类初始状态：

| 初始状态 | 导师要求对应情况 |
| --- | --- |
| `far_off_plume` | 远离气源，且离羽流边缘也有一段距离 |
| `far_near_edge` | 远离气源，但接近羽流边缘 |
| `far_inside_plume` | 远离气源，但已经在羽流内部 |
| `near_source_outside_plume` | 靠近气源，但完全在羽流外 |
| `near_source_upwind` | 靠近气源，且位于气源上游一侧 |

这五类状态覆盖了三种关系：

- 与气源的距离关系：远 / 近
- 与羽流边界的关系：外部 / 边缘 / 内部
- 与风向的关系：下游 / 横向 / 上游

### 阶段一结果总览

| 场景 | 风场/羽流特点 | 成功情况 | 主要现象 |
| --- | --- | --- | --- |
| `exp1_diffusion` | 扩散主导，弱/无平均风，气体分布更弥散 | 5/5 成功 | 初始状态影响较弱，即使上游或羽流外也能获得气味线索 |
| `exp2_time_varying` | 时变风场，羽流摆动、间歇 | 主表 3/5 成功，且 `far_off_plume` 重复试验一次失败一次成功 | 表现介于 exp1 和 exp3 之间，随机性/间歇性明显 |
| `exp3_advection` | 平流主导，定常风约为 `+x`，羽流较窄 | 1/5 成功 | 初始状态影响最强，是否接触羽流比是否靠近气源更重要 |

### Example1: 扩散主导场景

`exp1_diffusion` 中五类初始状态均成功。典型结果如下：

| 初始状态 | success | time_s | final_raw | final_confidence |
| --- | ---: | ---: | ---: | ---: |
| `far_off_plume` | 1 | 27.0 | 44.574 | 0.925 |
| `far_near_edge` | 1 | 26.8 | 138.182 | 0.918 |
| `far_inside_plume` | 1 | 29.8 | 339.636 | 0.958 |
| `near_source_outside_plume` | 1 | 25.4 | 82.448 | 0.926 |
| `near_source_upwind` | 1 | 9.4 | 278.618 | 0.628 |

结论：扩散主导场景中气味覆盖范围宽，初始位置对成功率影响较小。即使末端位于上游参考侧或横向偏离羽流，也仍可能检测到气味并成功定位。

### Example2: 时变风场

`exp2_time_varying` 中，主表五组里三组成功，且 `far_off_plume` 出现重复试验一次失败、一次成功。

| 初始状态 | success | time_s | min_distance_m | final_confidence | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| `far_off_plume` | 0 | 180.0 | 0.252 | 0.000 | 首次 timeout；重复试验中曾成功 |
| `far_near_edge` | 0 | 180.2 | 0.215 | 0.002 | 靠近气源但 confidence 不稳定 |
| `far_inside_plume` | 1 | 63.2 | 0.207 | 0.616 | 成功 |
| `near_source_outside_plume` | 1 | 39.6 | 0.245 | 0.810 | 成功 |
| `near_source_upwind` | 1 | 16.6 | 0.200 | 0.621 | 成功 |

结论：时变风场下羽流会摆动和间歇，因此同一初始状态可能因瞬时羽流形态不同而表现不同。它比扩散场更受初始状态影响，但不像定常平流场那样严格依赖固定羽流区域。

### Example3: 平流主导场景

`exp3_advection` 中只有 `far_near_edge` 成功。它也是最能体现导师要求的场景。

| 初始状态 | success | time_s | min_distance_m | final_raw | CAST/SURGE/SPIRAL |
| --- | ---: | ---: | ---: | ---: | --- |
| `far_inside_plume` | 0 | 180.0 | 0.087 | 0.000 | 128 / 33 / 0 |
| `far_near_edge` | 1 | 156.0 | 0.236 | 9.620 | 65 / 38 / 36 |
| `far_off_plume` | 0 | 180.2 | 0.715 | 0.000 | 162 / 0 / 0 |
| `near_source_outside_plume` | 0 | 180.0 | 0.534 | 0.000 | 162 / 0 / 0 |
| `near_source_upwind` | 0 | 180.2 | 0.170 | 0.000 | 162 / 0 / 0 |

结论：在平流主导场景中，“离气源近”不一定有利。例如 `near_source_upwind` 初始距离只有 `0.255 m`，但由于处于上游侧，几乎没有气味线索，最终失败。真正重要的是末端是否位于羽流内部或边缘，是否能获得 plume contact。

## 阶段一核心结论

阶段一证明了：初始状态会显著影响气源定位算法表现，而且这种影响取决于风场类型。

- 扩散主导场景中，羽流宽，初始状态影响较弱。
- 时变风场中，羽流间歇，结果具有随机性。
- 平流主导场景中，羽流窄，是否处于羽流边缘/内部比是否离气源近更重要。

这直接回应了导师关于“相对气源位置、相对羽流边界位置、相对风向位置”三类关系的要求。

## 阶段二：超参数敏感性实验

阶段二不是继续换初始位置，而是在代表性状态中改变算法参数，观察哪些超参数敏感。

重点关注四类参数：

| 参数类型 | 具体参数 | 含义 |
| --- | --- | --- |
| 成功确认门槛 | `required_confidence` | 离气源足够近后，需要多高 confidence 才算成功 |
| 气味检测阈值 | `theta_low`, `theta_mid`, `theta_high`, `contact_threshold` | 多大的气味读数算 plume contact |
| 羽流丢失判定 | `surge_loss_steps`, `surge_peak_drop_abs`, `surge_peak_drop_ratio` | SURGE 中气味变弱多久后认为羽流丢失 |
| SPIRAL 进入条件 | `spiral_enter_confidence`, `spiral_enter_steps`, `spiral_loss_steps` | 何时进入局部精搜索 |

我选择了三组 focused cases：

| Case | 场景 / 初始状态 | 选择原因 |
| --- | --- | --- |
| Case 1 | `exp3_advection / far_inside_plume` | 有 plume contact，但定位和确认不稳定 |
| Case 2 | `exp3_advection / far_off_plume` | 没有 plume contact，用于测试调参是否仍有作用 |
| Case 3 | `exp2_time_varying / far_near_edge` | 时变风场边缘，气味间歇，理论上最容易对参数敏感 |

### 阶段二结果总览

| Case | baseline 结果 | 参数敏感性判断 |
| --- | --- | --- |
| Case 1 `exp3/far_inside` | 成功，`71.0 s`，`final_dist=0.159 m`，`final_conf=0.610` | 对状态切换和确认稳定性敏感；不是单纯调低 confidence 就能改善 |
| Case 2 `exp3/far_off` | 失败，`raw=0`，`conf=0`，`SURGE=0`，`SPIRAL=0` | 几乎不受这些超参数影响，因为没有气味输入 |
| Case 3 `exp2/far_near_edge` | 成功，`84.2 s`，`final_dist=0.230 m`，`final_conf=0.619` | 对 confidence、检测阈值、plume loss 都敏感 |

### 六组参数横向观察

| 参数组 | 观察结果 | 结论 |
| --- | --- | --- |
| `sensitivity_baseline` | Case 1 和 Case 3 表现最好，Case 2 失败 | baseline 在有 plume cue 时较稳，但不能解决完全无气味状态 |
| `sensitivity_conf_low` | Case 3 成功但更慢；Case 1 失败 | 降低 confidence 不一定提升效率 |
| `sensitivity_conf_high` | Case 3 失败 | 高 confidence 对边缘/间歇羽流不友好 |
| `sensitivity_threshold_low` | Case 3 出现 `stop_mode_confirmed`，但离气源较远 | 阈值过低有 false positive 风险 |
| `sensitivity_loss_tolerant` | Case 3 的 SURGE steps 从 `24` 增到 `106`，但失败 | plume loss 过度放宽会沿不稳定线索走远 |
| `sensitivity_spiral_easy` | Case 1 的 SPIRAL steps 增到 `60`，但失败；Case 2/3 未进入 SPIRAL | SPIRAL 参数只有在已有稳定 plume cue 时才可能生效 |

## 阶段二核心结论

阶段二证明了：超参数敏感性不是固定属性，而是依赖初始状态和风场。

- 如果没有 plume contact，如 Case 2，调节 confidence、threshold、loss 或 SPIRAL 参数都基本不起作用。
- 如果已经接触羽流，如 Case 1，参数会明显改变状态分布，但放宽参数不一定提高成功率。
- 如果处于时变羽流边缘，如 Case 3，参数最敏感。`required_confidence` 过高会失败，检测阈值过低可能 false positive，plume loss 过宽松会导致错误 SURGE。

因此，导师提到的“某种状态下 fine tune 的参数不一定适合其他初始状态”是成立的。

## 两个阶段合并后的主要结论

1. 初始位置相对羽流的关系比单纯相对气源距离更重要。
2. 平流主导场景中，上游或羽流外位置即使靠近气源，也可能完全没有气味输入。
3. 时变风场中，羽流边缘状态容易受到瞬时气味波动影响，成功与失败可能并存。
4. 超参数只有在算法机制被触发时才有意义。例如没有 plume contact 时，SPIRAL 和 plume loss 参数无法生效。
5. 参数不能简单理解为“越宽松越好”。阈值过低和 plume loss 过宽松都可能导致错误确认或远离气源。

## 下一步建议

不建议马上扩展到更大的参数矩阵。更合理的下一步是做少量重复实验，验证关键结论是否稳定：

| 重复项 | 次数 | 目的 |
| --- | ---: | --- |
| Case 1 `baseline` | 3 次 | 验证平流场羽流内部 baseline 是否稳定成功 |
| Case 3 `baseline` | 3 次 | 验证时变风场边缘 baseline 是否稳定 |
| Case 3 `threshold_low` | 3 次 | 验证低阈值是否稳定引发 false positive |
| Case 3 `loss_tolerant` | 3 次 | 验证 plume loss 过宽松是否稳定有害 |

如果导师希望进一步扩展新 case，建议优先补：

```text
exp3_advection / far_near_edge
```

理由是它可以和 `exp2_time_varying / far_near_edge` 对比，进一步分析“同样处于羽流边缘，定常平流和时变风场下参数敏感性是否不同”。

## 可用于汇报的简短表述

本阶段我先完成了三种风场下五类初始状态的对比实验，发现初始末端相对羽流的位置比单纯离气源距离更关键。扩散主导场景中五类状态均能成功；时变风场中表现具有间歇性和随机性；平流主导场景中，只有羽流边缘状态稳定触发有效搜索，上游或羽流外状态即使靠近气源也可能失败。

随后我选取三个代表性状态做超参数敏感性分析。结果显示，超参数敏感性依赖初始状态和风场：完全没有 plume contact 时，调参基本不起作用；已经接触羽流时，状态切换和确认条件会影响结果；时变羽流边缘对 confidence、检测阈值和 plume loss 最敏感。下一步我计划对关键设置做少量重复试验，以验证这些现象是否稳定。
