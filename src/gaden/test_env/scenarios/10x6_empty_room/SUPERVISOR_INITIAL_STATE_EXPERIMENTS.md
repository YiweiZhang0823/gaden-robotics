# Supervisor Initial-State Experiments

这组实验严格对应导师要求：先观察每个场景中的羽流形态，然后设计多种机械臂末端初始状态，比较初始状态相对气源、相对羽流边界、相对风向的位置关系如何影响算法表现。

## 实验变量

每个场景都跑同一组五类初始状态：

| State key | 中文含义 | 主要考察关系 |
| --- | --- | --- |
| `far_off_plume` | 远离气源，且离羽流边缘也有一段距离 | 远离气源 + 完全无气味线索 |
| `far_near_edge` | 远离气源，但接近羽流边缘 | 远离气源 + 边界弱线索 |
| `far_inside_plume` | 远离气源，但已经在羽流内部 | 远离气源 + 已接触羽流 |
| `near_source_outside_plume` | 靠近气源，但完全在羽流外 | 靠近气源 + 横向偏离羽流 |
| `near_source_upwind` | 靠近气源，且位于气源上游一侧 | 靠近气源 + 风向上游 |

## Exp.3 实验设计

Exp.3 是平流主导风场，气源为 `(1.0, 4.95, 0.7)`，风向约为 `+x`。

注意：这是固定底座 Franka 实验，不是移动机器人实验。因此底座固定在 `(0.80, 4.65, 0.0)`，下面的“远离气源”指机械臂工作空间内相对更远的位置，而不是房间尺度的几米外位置。这样可以避免把“机械臂够不到气源”误当成算法失败。

| State key | TCP 初始位置 | 相对气源 | 相对羽流 | 相对风向 | 预期气味线索 |
| --- | --- | --- | --- | --- | --- |
| `far_off_plume` | `(1.35, 4.20, 0.65)` | 远 | 离羽流边缘也较远 | 下游但横向偏离 | 无或很弱 |
| `far_near_edge` | `(1.55, 4.55, 0.65)` | 远 | 羽流边缘 | 下游 | 弱或间歇 |
| `far_inside_plume` | `(1.55, 4.95, 0.65)` | 远 | 羽流内部 | 下游 | 明显接触羽流 |
| `near_source_outside_plume` | `(1.0, 4.35, 0.65)` | 近 | 横向完全在羽流外 | 横风方向 | 无或很弱 |
| `near_source_upwind` | `(0.75, 4.95, 0.65)` | 近 | 气源上游外侧 | 上游 | 无或很弱 |

三个场景分别代表：

| Scenario key | 场景含义 |
| --- | --- |
| `exp1_diffusion` | 扩散主导，弱/无平均风 |
| `exp2_time_varying` | 时变风场 |
| `exp3_advection` | 平流主导，定常 +x 强风 |

## 记录指标

runner 会写入 `/home/yiwei/ros2_ws/results/gsl_supervisor_trials.csv`：

| CSV 字段 | 用途 |
| --- | --- |
| `initial_label` / `source_relation` / `plume_relation` / `wind_relation` | 初始状态对应导师要求中的哪一类关系 |
| `success` | 是否满足 source 距离和 confidence 阈值 |
| `stop_reason` | 成功、超时、无气体消息等原因 |
| `time_s` | 从初始位置稳定后开始计时的实验时间 |
| `path_length_m` | 搜索阶段末端路径长度 |
| `initial_distance_m` | 初始末端位置距离气源多远 |
| `min_distance_m` | 搜索过程中距离气源最近距离 |
| `final_raw` / `final_margin` / `final_confidence` | 最终气体线索强弱 |
| `max_margin_seen` | 搜索过程中看到过的最强气味线索 |
| `cast_steps` / `surge_steps` / `spiral_steps` | 算法状态分布 |

注意：Franka 底座在单次实验中是固定的。对于 `far_*` 初始状态，机械臂物理上可能够不到气源，因此这些实验的重点不是强行要求成功，而是比较它是否能接触羽流、是否保持羽流、路径长度、状态切换和最终线索强弱。

## 运行方式

先列出完整实验矩阵：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env open_field_initial_state_commands --list
```

生成某一个初始状态的完整命令，例如 exp3 的“远处且在羽流内部”：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env open_field_initial_state_commands exp3_advection far_inside_plume
```

把输出中的 Terminal 1 命令和 Terminal 2 命令分别复制到两个终端运行。每跑完一个 state，关闭 Terminal 1 的 launch，再换下一个 state。

汇总 exp3 结果：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env gsl_supervisor_summary \
  --csv /home/yiwei/ros2_ws/results/gsl_supervisor_trials.csv \
  --scenario exp3_advection \
  --output-csv /home/yiwei/ros2_ws/results/gsl_supervisor_exp3_summary.csv
```
