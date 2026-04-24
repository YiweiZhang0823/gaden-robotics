# 任务 B 汇报稿：不同风场下表现较好的参数差异及其 wind-dependent 理解

## 汇报目的

本部分对应导师提出的第二点：不必立刻做大规模调参，而是先定性比较在 `diffusion-dominant` 和 `advection-dominant` 场景中，哪些参数更容易表现好，哪些参数差异可以理解为 `wind-dependent`。

这里的重点不是给出一套“全局最优参数”，而是回答：

1. 哪些参数在不同风场下更敏感？
2. 这些差异能否理解为与风场类型、风速或羽流间歇性有关？
3. 哪些判断已经有实验支撑，哪些目前还是基于现有结果的定性推断？

## 先说明当前证据边界

目前阶段二和阶段三的超参数敏感性实验，直接覆盖得最充分的是：

- `exp3_advection`
- `exp2_time_varying`

对 `exp1_diffusion`，目前主要有阶段一结果，即五类初始状态在 baseline 下均成功，但还没有做和 `exp2/exp3` 同样规模的参数扰动实验。

因此，本部分的比较应当分成两层：

1. **直接实验支持**：来自 `exp2` 和 `exp3` 的 sensitivity / repeatability 结果
2. **定性推断**：利用 `exp1` 的稳定成功结果，与 `exp3`、`exp2` 做物理上的对比解释

这也符合导师的意思：先做定性比较，不需要马上扩展成大规模参数搜索。

## 当前重点参数

结合阶段二和阶段三，目前最值得讨论的参数主要有三类：

| 参数类型 | 具体参数 | 它控制什么 |
| --- | --- | --- |
| 成功确认门槛 | `required_confidence` | 靠近气源后，需要多高 confidence 才判定成功 |
| 检测阈值 | `theta_low`, `theta_mid`, `theta_high`, `contact_threshold` | 多大的气味信号算 plume contact |
| plume loss 条件 | `surge_loss_steps`, `surge_peak_drop_abs`, `surge_peak_drop_ratio` | SURGE 中气味变弱多久后认为羽流丢失 |

`SPIRAL` 参数也有影响，但从当前结果看，它更像依赖前面是否已经存在稳定 plume cue；因此在风场差异讨论中，优先级低于前面三类参数。

## 一、`required_confidence` 的风场相关差异

### 现有实验现象

在 `exp2_time_varying / far_near_edge` 中：

- baseline (`required_confidence=0.6`) 单次成功，重复实验成功率 `1/3`
- `conf_low` 能成功，但更慢
- `conf_high` 失败

在 `exp3_advection / far_inside_plume` 中：

- baseline 单次成功，但重复 3 次全部失败
- 即使机器人非常接近气源，confidence 也未能稳定保持

### 物理解释

`required_confidence` 决定的不是“能不能靠近气源”，而是“靠近之后能不能稳定确认成功”。

因此：

- 在时变风场中，气味信号本来就间歇，`required_confidence` 过高会让算法很难在有限时间内完成确认；
- 在平流主导场景中，即使进入羽流内部，气味也可能因为羽流窄而迅速丢失，所以确认过程同样不稳定；
- 在扩散主导场景中，由于气味覆盖更宽、更连续，理论上对 `required_confidence` 的敏感性应更低。

### 可汇报的结论

> `required_confidence` 可以理解为与风场稳定性相关的参数。风场越不稳定、羽流越间歇，过高的 `required_confidence` 越容易导致“已经接近气源但仍无法确认成功”的问题。

## 二、检测阈值（threshold）的风场相关差异

### 现有实验现象

在 `exp2_time_varying / far_near_edge` 中：

- `threshold_low` 单次成功，但曾出现 `stop_mode_confirmed` 且距离气源较远的情况
- 重复实验成功率 `3/3`
- 其中两次是 `distance_confidence_confirmed`，一次是 `stop_mode_confirmed`

在 `exp3_advection / far_off_plume` 中：

- 即使降低阈值，仍然 `raw=0`、`conf=0`、`SURGE=0`
- 说明这个状态下的问题不是阈值过高，而是真的没有 plume contact

在 `exp3_advection / far_inside_plume` 中：

- `threshold_low` 曾使机器人更接近气源，但没有稳定成功

### 物理解释

threshold 控制的是：

> 在多大程度上把弱气味当成“有效 plume cue”。

因此：

- 在扩散或时变边缘场景中，降低阈值更容易捕捉到弱而间歇的气味；
- 但阈值过低也更容易把瞬时气味、漂移气味或噪声当成有效线索；
- 在平流主导且完全离开羽流的状态下，降低阈值本身并不能制造气味输入，因此不会改变结果。

### 可汇报的结论

> 检测阈值可以理解为与羽流“可检测性”和“间歇性”相关的风场依赖参数。风越乱、羽流越断续，低阈值越可能提高检测概率；但同时也更容易带来 false positive 风险。

## 三、plume loss 条件的风场相关差异

### 现有实验现象

在 `exp2_time_varying / far_near_edge` 中：

- 阶段二里 `loss_tolerant` 单次失败，`SURGE` 步数显著增加
- 阶段三重复实验中，`loss_tolerant` 成功率为 `2/3`
- 成功时比 baseline 更快，失败时会沿错误线索长时间 SURGE

在 `exp3_advection / far_inside_plume` 中：

- `loss_tolerant` 进入了更多状态切换甚至 SPIRAL，但没有改善最终成功率

在 `exp3_advection / far_off_plume` 中：

- 因为根本没有 plume contact，`loss_tolerant` 基本不起作用

### 物理解释

plume loss 条件决定的是：

> 检测到羽流之后，算法要多快放弃当前线索。

因此：

- 在时变风场中，羽流本身会短时中断，如果 plume loss 太严格，算法会过早放弃真实线索；
- 但如果 plume loss 太宽松，算法又可能沿着已经失真的线索继续追踪；
- 在扩散主导场景中，气味更连续，理论上 plume loss 参数的敏感性应弱于时变场景；
- 在平流主导场景中，羽流窄且边界清晰，plume loss 的作用更多体现在“是否保留边缘线索”，但前提仍然是先有 plume contact。

### 可汇报的结论

> plume loss 条件可以理解为与羽流持续性、也就是 plume intermittency 相关的风场依赖参数。风场越时变、羽流越断续，plume loss 条件越敏感；但它不是越宽松越好，而是在鲁棒性和误跟踪之间需要平衡。

## 四、从 diffusion-dominant 到 advection-dominant 的总体趋势

结合当前结果，可以把参数差异概括成下面这个趋势：

| 风场类型 | 参数表现特征 | 更合理的理解 |
| --- | --- | --- |
| diffusion-dominant | baseline 已能在多种状态下成功；参数差异暂未表现出强敏感性 | 气味覆盖更宽，固定参数更容易工作 |
| time-varying / intermediate | threshold 和 plume loss 最敏感；过松过严都会出问题 | 需要在“捕捉间歇弱气味”和“避免误判”之间平衡 |
| advection-dominant | plume contact 是前提；确认稳定性和边缘 plume cue 保持更关键 | 参数作用更依赖羽流是否被真正接触到 |

因此可以把它写成一句话：

> 风场从 diffusion-dominant 向 advection-dominant 变化时，算法对 plume contact、信号持续性和确认稳定性的依赖会增强，因此与 threshold、plume loss、required_confidence 相关的参数也更容易表现出 wind-dependent 差异。

## 哪些判断已经有数据支持，哪些还需要补强

### 已有直接实验支持的部分

1. `required_confidence` 在时变边缘羽流中确实敏感，过高会失败。
2. `threshold_low` 在时变边缘羽流中确实能提高成功率，但存在 false positive 风险。
3. `loss_tolerant` 在时变边缘羽流中不是稳定有害，而是风险与收益并存。
4. 在平流主导且没有 plume contact 的状态下，调参数基本不起作用。

### 目前仍属于定性推断的部分

1. `diffusion-dominant` 下 threshold 和 plume loss 的确切最优趋势
2. `diffusion-dominant` 与 `advection-dominant` 之间，哪些参数差异能否进一步用风速大小解释
3. 是否可以真正把参数写成显式的风速函数

因此，当前最稳妥的表达应当是：

> 现有结果已经支持“参数差异具有 wind-dependent 倾向”，但这种 wind dependence 目前主要体现为定性规律，而不是已完成的定量映射关系。

## 任务 B 的核心结论

本部分可以归纳为：

> 当前实验结果表明，算法超参数并不是在所有风场下都同样敏感。`required_confidence` 更容易受到风场稳定性的影响；检测阈值更容易受到弱羽流和间歇羽流可检测性的影响；plume loss 条件更容易受到羽流连续性和摆动程度的影响。因此，这些参数的差异可以被理解为 wind-dependent，也就是说，它们与风场类型和羽流间歇性密切相关，而不适合用一套固定参数覆盖所有场景。

## 可直接向导师汇报的版本

> 我现在没有直接去做大规模调参，而是先把已有结果整理成 wind-dependent 的角度来理解。当前可以看到，`required_confidence` 更多反映的是靠近气源后的确认稳定性，风场越时变、羽流越间歇，它越容易成为限制因素；检测阈值决定弱气味是否会被当作有效 plume cue，在时变边缘羽流里降低阈值确实能提高成功率，但会带来 false positive 风险；plume loss 条件则和羽流连续性有关，时变风场下放宽它有时会更快成功，有时又会导致误跟踪。对于 diffusion-dominant 场景，目前的直接证据是 baseline 在多种状态下都能成功，说明参数整体上更不敏感；而在 advection-dominant 和 time-varying 场景中，参数差异则明显放大。因此，我倾向于把这些参数差异理解为和风场类型、也就是 wind condition 相关的现象，而不是一套固定参数可以通用。

## 后续可衔接的工作

如果后面要继续补强任务 B，最合理的补充不是大矩阵，而是一个小型对比：

- `exp1_diffusion / far_near_edge`
- `exp3_advection / far_near_edge`

只对以下三组参数做对比：

- `baseline`
- `threshold_low`
- `loss_tolerant`

这样可以更直接比较：

- 在 diffusion-dominant 中，低阈值是否仍然有必要
- 在 advection-dominant 中，plume loss 是否更关键
- wind-dependent 差异是否能在同类初始状态下更清楚地显现
