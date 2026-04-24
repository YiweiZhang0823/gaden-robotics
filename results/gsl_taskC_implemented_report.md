# 任务 C 已实现说明：随机化初始条件与自动记录流程

## 实现目的

本部分对应导师提出的第三点：完善测试流程，使仿真可以更自动化地运行和记录结果，并允许某些初始条件带有受控随机性。

这次实现的目标不是修改 `CAST/SURGE/SPIRAL` 的搜索逻辑，而是先把实验流程从：

> 测试一个固定初始点

扩展为：

> 对同一类初始条件自动生成一组可复现的随机样本，并自动记录样本信息与实验结果

## 这次实现改动了什么

### 1. 在初始状态配置中加入默认扰动范围

文件：

- [initial_states.yaml](/home/yiwei/ros2_ws/src/gaden/test_env/scenarios/10x6_empty_room/initial_states.yaml)

我为几个关键状态加入了 `sampling_defaults`，例如：

- `far_near_edge`
- `far_inside_plume`

当前采用的是最简单的 `box` 采样方式，并给出默认 `sigma_xyz`。

这意味着后续不再只能把这些状态理解为一个固定点，而是可以理解为：

> 以该点为中心、在小范围扰动下的一类初始条件

### 2. 新增随机样本命令生成脚本

文件：

- [gsl_randomized_initial_state_commands.py](/home/yiwei/ros2_ws/src/gaden/test_env/scripts/gsl_randomized_initial_state_commands.py)

这个脚本现在可以：

1. 读取某个场景和状态模板
2. 根据 `seed` 和 `sigma` 自动生成若干随机样本
3. 把样本写入新的 sampled YAML 文件
4. 打印每个样本对应的实验命令

支持的核心参数包括：

- `scenario`
- `state`
- `samples`
- `seed`
- `sigma-x / sigma-y / sigma-z`

### 3. 扩展结果 CSV 的记录字段

文件：

- [surge_cast_spiral_gsl.py](/home/yiwei/ros2_ws/src/gaden/test_env/scripts/surge_cast_spiral_gsl.py)

我没有改算法核心状态机，只扩展了结果写入部分，让 CSV 额外记录：

- `parent_initial_state`
- `sample_id`
- `sampling_seed`
- `sampling_mode`
- `nominal_ee_x/y/z`
- `sampling_sigma_x/y/z`
- `sampling_offset_x/y/z`

这样每一条实验结果都可以追溯到：

- 它来自哪个原始状态类别
- 使用了哪个随机种子
- 中心点是多少
- 实际扰动了多少

### 4. 把新脚本接入 ROS2 安装流程

文件：

- [CMakeLists.txt](/home/yiwei/ros2_ws/src/gaden/test_env/CMakeLists.txt)

我已经把 `gsl_randomized_initial_state_commands.py` 加入安装，因此后续可以通过 `ros2 run test_env ...` 调用。

## 这次实现没有改什么

为了控制风险，这一版**没有修改**：

- `threshold`
- `plume loss`
- `required_confidence`
- `SPIRAL` 状态切换逻辑
- 任何搜索策略本身

也就是说，这次实现改的是：

> 实验流程层

而不是：

> 算法决策层

因此，如果后面实验结果发生变化，主要原因应理解为：

> 初始条件采样方式改变了

而不是算法核心被重写了。

## 已完成的验证

为了确认这次实现没有把原流程改坏，我做了两类验证。

### 验证 1：同一 `seed` 的可复现性

对 `exp2_time_varying / far_near_edge` 使用：

- `samples = 5`
- `seed = 42`

重复生成两次，得到完全相同的 5 个样本坐标：

| sample_id | sampled_ee_target |
| --- | --- |
| `001` | `(1.4639, 4.2025, 0.6410)` |
| `002` | `(1.4223, 4.2736, 0.6571)` |
| `003` | `(1.4892, 4.2087, 0.6469)` |
| `004` | `(1.4030, 4.2219, 0.6502)` |
| `005` | `(1.4027, 4.2199, 0.6560)` |

这说明：

> 随机采样不是不可控的，而是可复现的。

### 验证 2：`sigma = 0` 的回归验证

我把：

- `sigma_x = 0`
- `sigma_y = 0`
- `sigma_z = 0`

输入到随机样本脚本中，生成结果为：

| sample_id | sampled_ee_target | offsets |
| --- | --- | --- |
| `001` | `(1.4500, 4.2500, 0.6500)` | `(+0.0000, +0.0000, +0.0000)` |

这正好退化回原始固定点：

```text
far_near_edge = (1.45, 4.25, 0.65)
```

这说明：

> 当不施加扰动时，新流程不会破坏原有固定点实验逻辑。

## 已产生的结果样例

当前已经生成并写入：

- [gsl_randomized_trials.csv](/home/yiwei/ros2_ws/results/gsl_randomized_trials.csv)
- [exp2_time_varying_far_near_edge_seed42.yaml](/home/yiwei/ros2_ws/results/randomized_initial_states/exp2_time_varying_far_near_edge_seed42.yaml)

从 CSV 中可以看到，随机实验结果已经带有完整采样元数据，例如：

- `initial_state = far_near_edge__sample_001`
- `parent_initial_state = far_near_edge`
- `sample_id = 001`
- `sampling_seed = 42`
- `nominal_ee_x/y/z`
- `sampling_offset_x/y/z`

这说明这套流程已经从“只记录实验结果”升级为“同时记录样本来源信息”。

## 这次实现的意义

这次实现最重要的意义是：

### 以前

实验对象更像是：

> 一个固定点

### 现在

实验对象更像是：

> 一类带小范围扰动的初始条件

这使得后续论文里可以更有底气地说：

> 某个结论不是只对单个坐标点成立，而是在这类初始条件附近都大致成立。

因此，这次实现提升的是实验设计的统计性和可重复性，而不是单纯增加更多数据量。

## 当前版本的边界

这次实现还是第一版，因此仍有几个限制：

1. 当前只支持最简单的 `box` 采样
2. 随机样本主要依赖几何约束和工作空间约束，还没有加入更强的“语义守卫”
3. 目前还没有做“自动批量运行 + 自动汇总随机样本统计”的完整一键工作流

因此，这一版更适合被理解为：

> 已完成随机样本生成与结果记录的基础设施搭建

而不是已经完成最终版自动化平台。

## 下一步建议

在这个基础上，下一步最合理的是：

1. 先对 `far_near_edge` 做小规模随机实验统计
2. 再考虑把 `far_inside_plume` 也纳入随机采样
3. 后续如果需要，再加入更强的语义约束，例如：
   - 保证样本仍属于 `far`
   - 保证样本仍位于 `edge` 附近
   - 保证样本不越过上游/下游语义边界

## 可直接向导师汇报的版本

> 我已经完成了任务 C 的第一版实现。当前我没有修改搜索算法本身，而是先把实验流程扩展成支持受控随机初始条件的形式。现在可以针对某个状态模板，例如 far_near_edge，在给定 sigma 范围内自动生成多个随机样本，并自动记录 sample_id、seed、中心点、扰动量和实验结果。我已经做了两步验证：第一，同一个 seed 会生成完全相同的一组样本，说明流程可复现；第二，当 sigma=0 时，新流程会退化回原始固定点实验，说明没有破坏旧逻辑。这样后续分析的对象就不再只是单个点，而是一类初始条件。
