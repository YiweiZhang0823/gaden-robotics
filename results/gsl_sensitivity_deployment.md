# GSL 超参数敏感性实验部署说明

## 这次实验在做什么

这次不是重新验证五类初始位置，也不是训练机器人。前面的 Example1/2/3 已经说明了不同初始状态会影响 CAST/SURGE/SPIRAL 的表现。

这次要回答导师提到的另一个问题：

> 同一套算法参数是否适合所有初始状态？如果不适合，哪些超参数最敏感？

因此本实验固定场景和初始状态，只改变算法参数，然后比较：

- `success`
- `time_s`
- `path_length_m`
- `min_distance_m`
- `final_distance_m`
- `final_raw`
- `final_confidence`
- `cast_steps / surge_steps / spiral_steps`

## 先跑的三个代表性 case

| case | 初始状态含义 | 为什么选它 |
| --- | --- | --- |
| `exp3_advection / far_inside_plume` | 远离气源，但已经在羽流内部 | baseline 已经靠近气源，但 confidence 不稳定导致 timeout，适合测试确认门槛。 |
| `exp3_advection / far_off_plume` | 远离气源，且离羽流边缘也有一段距离 | baseline 基本没有气味线索，长期 CAST，适合测试气味检测阈值。 |
| `exp2_time_varying / far_near_edge` | 远离气源，但接近羽流边缘 | 时变风场下靠近边缘且确认不稳定，适合测试 plume loss 和间歇羽流容忍度。 |

## 每个 case 跑六组参数

| param_set | 改动 | 关注点 |
| --- | --- | --- |
| `sensitivity_baseline` | `required_confidence=0.6` | 原始参数，对照组。 |
| `sensitivity_conf_low` | `required_confidence=0.3` | 降低成功确认门槛，看 timeout 是否变成 success。 |
| `sensitivity_conf_high` | `required_confidence=0.8` | 提高成功确认门槛，看结果是否明显变差。 |
| `sensitivity_threshold_low` | 降低 `theta_low/mid/high` 和 `contact_threshold` | 看弱气味/羽流边缘是否之前被漏检。 |
| `sensitivity_loss_tolerant` | 放宽 SURGE 中羽流丢失判定 | 看时变风场是否需要更长记忆，避免太早回到 CAST。 |
| `sensitivity_spiral_easy` | 降低进入 SPIRAL 的门槛 | 看更早局部精搜索是否改善定位。 |

总实验数：

```text
3 个 case × 6 组参数 = 18 次实验
```

## 已生成的命令文件

完整 Terminal 命令已经生成在：

```text
/home/yiwei/ros2_ws/results/gsl_sensitivity_focused_commands.txt
```

查看命令：

```bash
cd /home/yiwei/ros2_ws
less results/gsl_sensitivity_focused_commands.txt
```

如果要重新生成：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env gsl_sensitivity_commands --cases focused | tee results/gsl_sensitivity_focused_commands.txt
```

## 推荐运行顺序

每个 case 都需要两个 terminal。

Terminal 1 负责启动对应场景和机械臂：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 launch test_env <对应launch文件> align_base_from_gas_yaml:=false map_x:=0.8 map_y:=4.65 map_yaw:=0 joint_state_mode:=interactive franka_joint_max_velocity:=0.15
```

Terminal 2 负责运行算法实验：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
stdbuf -oL ros2 run test_env surge_cast_spiral_gsl --ros-args \
  -p scenario_key:=<scenario> \
  -p initial_state_key:=<initial_state> \
  -p param_set:=<param_set> \
  -p output_csv:=/home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv \
  -p timeout_s:=180.0 \
  -p success_radius:=0.25 \
  -p control_period:=1.0 \
  -p initial_settle_s:=8.0 \
  -p goal_preset:=tilt_x_90 \
  -p search_heading_yaw:=3.1416 \
  <该参数组额外参数> \
  2>&1 | tee /home/yiwei/ros2_ws/results/<对应log文件>.log
```

## 每个 case 的启动命令

### Case 1: `exp3_advection / far_inside_plume`

关注：已经在羽流内部但确认失败，主要看 `required_confidence` 和 confidence 相关敏感性。

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 launch test_env gaden_franka_open_exp3.launch.py align_base_from_gas_yaml:=false map_x:=0.8 map_y:=4.65 map_yaw:=0 joint_state_mode:=interactive franka_joint_max_velocity:=0.15
```

生成这个 case 的六组参数命令：

```bash
ros2 run test_env gsl_sensitivity_commands --scenario exp3_advection --state far_inside_plume
```

### Case 2: `exp3_advection / far_off_plume`

关注：远离羽流边缘，baseline 几乎无气味，主要看检测阈值 `theta_*` 和 `contact_threshold`。

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 launch test_env gaden_franka_open_exp3.launch.py align_base_from_gas_yaml:=false map_x:=0.8 map_y:=4.65 map_yaw:=0 joint_state_mode:=interactive franka_joint_max_velocity:=0.15
```

生成这个 case 的六组参数命令：

```bash
ros2 run test_env gsl_sensitivity_commands --scenario exp3_advection --state far_off_plume
```

### Case 3: `exp2_time_varying / far_near_edge`

关注：时变风场边缘状态，主要看 `surge_loss_steps` 和 plume loss 是否太敏感。

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 launch test_env gaden_franka_open_exp2.launch.py align_base_from_gas_yaml:=false map_x:=0.8 map_y:=4.65 map_yaw:=0 joint_state_mode:=interactive franka_joint_max_velocity:=0.15
```

生成这个 case 的六组参数命令：

```bash
ros2 run test_env gsl_sensitivity_commands --scenario exp2_time_varying --state far_near_edge
```

## 数据记录位置

所有敏感性实验结果写入：

```text
/home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv
```

每次实验的 terminal log 写入：

```text
/home/yiwei/ros2_ws/results/sensitivity_<scenario>_<state>_<param_set>.log
```

## 跑完后汇总

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env gsl_sensitivity_summary \
  --csv /home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv \
  --output-csv /home/yiwei/ros2_ws/results/gsl_sensitivity_summary.csv
```

查看最近结果：

```bash
cd /home/yiwei/ros2_ws
tail -n 20 results/gsl_sensitivity_trials.csv
```

查看汇总表：

```bash
cd /home/yiwei/ros2_ws
column -s, -t results/gsl_sensitivity_summary.csv | less -S
```

## 结果应该怎么判断

如果 `sensitivity_conf_low` 把失败变成成功，说明该初始状态对 `required_confidence` 敏感。

如果 `sensitivity_threshold_low` 让 CAST 更早转入 SURGE，说明弱羽流或羽流边缘对气味检测阈值敏感。

如果 `sensitivity_loss_tolerant` 在 `exp2_time_varying / far_near_edge` 改善结果，说明时变风场下 plume loss 判定太敏感，需要和风速/羽流间歇性关联。

如果 `sensitivity_spiral_easy` 明显增加 SPIRAL 步数并缩短时间或路径，说明局部精搜索进入条件值得进一步调。
