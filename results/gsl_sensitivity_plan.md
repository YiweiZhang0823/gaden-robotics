# GSL 超参数敏感性实验计划

## 实验目的

前面 Example1/2/3 的初始状态实验已经回答了“机器人初始位置和羽流/风向关系会不会影响结果”。下一步对应导师提到的超参数问题：在不同初始状态下，哪些算法参数最敏感，以及这些敏感性是否和风场/羽流形态有关。

这一步不是直接追求最好结果，而是做小规模参数扰动，观察成功率、时间、路径长度、最小距离、final confidence、CAST/SURGE/SPIRAL 步数如何变化。

## 先跑的 focused cases

| case | 为什么选它 |
| --- | --- |
| `exp3_advection / far_inside_plume` | baseline 已经进入羽流并靠近气源，但 confidence 不稳定导致 timeout，适合测试确认阈值和 confidence 相关参数。 |
| `exp3_advection / far_off_plume` | baseline 基本没有气味线索，长期 CAST，适合测试气味检测阈值是否过高。 |
| `exp2_time_varying / far_near_edge` | 时变风场下接近羽流边缘，能靠近气源但确认不稳定，适合测试 plume loss 和间歇羽流容忍度。 |

## 参数组

| param_set | 修改内容 | 观察目的 |
| --- | --- | --- |
| `sensitivity_baseline` | `required_confidence=0.6` | 对照组。 |
| `sensitivity_conf_low` | `required_confidence=0.3` | 如果失败变成功，说明成功判定/置信度门槛很敏感。 |
| `sensitivity_conf_high` | `required_confidence=0.8` | 如果成功明显变少，说明结果依赖较松的确认条件。 |
| `sensitivity_threshold_low` | `auto_thresholds=false`, `theta_low=0.25`, `theta_mid=1.0`, `theta_high=2.5`, `contact_threshold=0.02` | 检查弱气味或羽流边缘是否因为检测阈值过高被漏检。 |
| `sensitivity_loss_tolerant` | `surge_loss_steps=8`, `surge_peak_drop_abs=0.7`, `surge_peak_drop_ratio=0.7` | 检查时变/间歇羽流中是否需要更宽松的“羽流丢失”判定。 |
| `sensitivity_spiral_easy` | `spiral_enter_confidence=0.25`, `spiral_enter_steps=2`, `spiral_loss_steps=6` | 检查更早进入 SPIRAL 是否改善局部精搜索和确认。 |

## 运行方式

先重新 build：

```bash
cd /home/yiwei/ros2_ws
colcon build --packages-select test_env --symlink-install
source install/setup.bash
```

查看要跑的命令：

```bash
ros2 run test_env gsl_sensitivity_commands --list
ros2 run test_env gsl_sensitivity_commands --cases focused
```

每次实验会写入：

```text
/home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv
```

每条命令也会生成对应 log：

```text
/home/yiwei/ros2_ws/results/sensitivity_<scenario>_<state>_<param_set>.log
```

跑完后汇总：

```bash
ros2 run test_env gsl_sensitivity_summary \
  --csv /home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv \
  --output-csv /home/yiwei/ros2_ws/results/gsl_sensitivity_summary.csv
```

## 最后报告应该怎么写

报告里不要只说“哪个参数最好”，而是说明“哪个参数对哪类初始状态最敏感”：

- 如果 `sensitivity_conf_low` 明显提高 success，说明失败主要来自确认条件过严，而不是机器人没有靠近气源。
- 如果 `sensitivity_threshold_low` 让 `far_off_plume` 或边缘状态更早进入 SURGE，说明气味检测阈值对弱羽流很敏感。
- 如果 `sensitivity_loss_tolerant` 在 Example2 改善结果，说明时变风场下 plume loss 参数需要跟风速/羽流间歇性相关。
- 如果 `sensitivity_spiral_easy` 增加 SPIRAL 步数并缩短定位时间，说明局部精搜索进入条件可以进一步调优。
