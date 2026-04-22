# 第三阶段：重复性验证实验部署说明

## 为什么做第三阶段

第一阶段和第二阶段已经说明了不同初始状态下超参数敏感性不同。但目前每组参数大多只跑了一次，仍然可能受到羽流瞬时波动、时变风场和传感器读数随机性的影响。

第三阶段的目的不是继续换参数，而是验证关键结论是否稳定。

## 重复实验设计

| 重复项 | 场景 / 初始状态 | 参数组 | 重复次数 | 验证目的 |
| --- | --- | --- | ---: | --- |
| Case 1 baseline | `exp3_advection / far_inside_plume` | `sensitivity_baseline` | 3 | 验证平流羽流内部状态是否稳定成功。 |
| Case 3 baseline | `exp2_time_varying / far_near_edge` | `sensitivity_baseline` | 3 | 验证时变风场边缘下 baseline 是否稳定。 |
| Case 3 threshold low | `exp2_time_varying / far_near_edge` | `sensitivity_threshold_low` | 3 | 验证远离气源但 `stop_mode_confirmed` 是否稳定出现，即 false positive 风险。 |
| Case 3 loss tolerant | `exp2_time_varying / far_near_edge` | `sensitivity_loss_tolerant` | 3 | 验证放宽 plume loss 是否稳定导致过长 SURGE 和远离气源。 |

总计：

```text
4 个重复项 × 3 次 = 12 次实验
```

## 数据记录位置

第三阶段单独写入：

```text
/home/yiwei/ros2_ws/results/gsl_repeatability_trials.csv
```

不要和前面的 sensitivity 数据混在一起。

## 生成命令

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env gsl_repeatability_commands --repeats 3 | tee results/gsl_repeatability_phase3_commands.txt
```

查看可选重复项：

```bash
ros2 run test_env gsl_repeatability_commands --list
```

只生成某一个重复项：

```bash
ros2 run test_env gsl_repeatability_commands --case case1_baseline --repeats 3
ros2 run test_env gsl_repeatability_commands --case case3_baseline --repeats 3
ros2 run test_env gsl_repeatability_commands --case case3_threshold_low --repeats 3
ros2 run test_env gsl_repeatability_commands --case case3_loss_tolerant --repeats 3
```

## 汇总命令

跑完以后执行：

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env gsl_repeatability_summary \
  --csv /home/yiwei/ros2_ws/results/gsl_repeatability_trials.csv \
  --output-csv /home/yiwei/ros2_ws/results/gsl_repeatability_summary.csv
```

查看汇总：

```bash
column -s, -t results/gsl_repeatability_summary.csv | less -S
```

## 如何判断结果

如果 Case 1 baseline 三次都成功，说明平流场内部羽流状态下 baseline 相对稳定。

如果 Case 1 baseline 成功率波动明显，说明即使在羽流内部，平流场的瞬时读数和 tracking 过程仍会影响定位。

如果 Case 3 baseline 三次都成功，说明 baseline 对时变边缘羽流有一定鲁棒性。

如果 Case 3 threshold low 多次出现 `stop_mode_confirmed` 且 `final_distance_m` 较大，说明低阈值确实有 false positive 风险。

如果 Case 3 loss tolerant 多次失败且 `surge_steps` 明显增大，说明 plume loss 过度放宽会稳定地产生错误 tracking。
