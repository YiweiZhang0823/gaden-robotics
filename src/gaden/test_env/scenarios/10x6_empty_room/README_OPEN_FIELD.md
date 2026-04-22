# 10x6_empty_room：APPIS 2020 开阔场实验 × 学位论文叙事

**文献**：Pepe Ojeda, Javier Monroy, Javier Gonzalez-Jimenez, *An Evaluation of Gas Source Localization Algorithms for Mobile Robots*, APPIS 2020.  
PDF：<https://mapir.uma.es/papersrepo/2020/2020_ojeda_APPIS_Evaluation_of_GSL_algorithms.pdf>，DOI：<https://doi.org/10.1145/3378184.3378220>。

**文中不采用**：带障碍的 **§4.3（中央障碍）**、**§4.4（迷宫）** 的几何；本目录仅做 **无障碍开阔房间**（10×6 CAD，与文中 10m×10m **同类设定**）。

---

## 1. 短文里「问题—算法—评估」可作方法部分参考（摘要）

- **问题引入（§1）**：移动嗅觉 / GSL；仿真可在相同条件下复现、控制变量。  
- **算法（§2–§3）**：**反应式**（化学趋向 Spiral；风向趋向 Surge-Cast、Surge-Spiral）与 **基于模型/推断**（Li et al. **粒子滤波**）；PF 假设 **风在空间上均匀、可随时间变**（§3.4）。  
- **评估协议（§4 开头）**：成功 = 机器人（或 PF 粒子均值）进入气源 **0.5 m** 内；超时 **600 s**；初始已能测到气；不单独讨论「找羽流 / 宣告找到源」。  
- **四类仿真环境（§4.1–4.4）**：弱风开阔 / 时变均匀强风开阔 / 定常流+中央障碍 / 迷宫定常流。  

本仓库在 **开阔无障碍** 前提下对齐前三类 **物理角色**（扩散 / 时变风 / 定常强平流），见下表。

---

## 2. 三套 `configuration` 与论文、学位论文的对应

| configuration | APPIS 原文 | 学位论文叙事 | 风场实现要点 |
|-----------------|------------|----------------|--------------|
| `config_exp1_open_weak` | **§4.1** Weak airflow, open, **diffusion 为主** | 与前人一致的 **扩散主导** | `exp1_open_weak` 单帧 CFD 格点风（弱） |
| `config_exp2_open_timevarying` | **§4.2** **Homogeneous time-dependent** strong airflow；**narrow bent plume** | 前人未强调的 **时变均匀风** | `dynamic/` 多帧；`sim.yaml` 中 `windLooping` 0–24 |
| `config_exp3_open_steady` | **§4.3 的风型（steady airflow）**；原文 **带中央障碍** | **去掉障碍** 后的 **平流主导（advection）** | `uniformWind: true` + `exp3_open_steady/wind_0.csv` **定常均匀矢量** |

气源均为 **`simulations/sim1/sim.yaml` 中 `sourceType: point`**，与文中 **点释放** 一致。

---

## 3. Launch（场景 + 气体 + Franka）

```bash
ros2 launch test_env gaden_franka_open_exp1.launch.py
ros2 launch test_env gaden_franka_open_exp2.launch.py
ros2 launch test_env gaden_franka_open_exp3.launch.py
```

若你想按论文/导师语义来启动，也可用等价入口：

```bash
ros2 launch test_env gaden_franka_thesis_exp1_diffusion.launch.py
ros2 launch test_env gaden_franka_thesis_exp2_timevarying.launch.py
ros2 launch test_env gaden_franka_thesis_exp3_advection.launch.py
```

须先对对应 configuration 完成 **预处理 + filament**（见下）。

---

## 4. 本地生成 `OccupancyGrid3D`、`wind/`、`result/`

1. **预处理**：`gaden_preprocessing`  
2. **Filament**：`gaden_filament_simulator`  

```bash
ros2 run test_env open_field_build_gaden_data
```

或对单套配置：

```bash
ros2 launch test_env gaden_preproc_launch.py scenario:=10x6_empty_room configuration:=config_exp3_open_steady
ros2 launch test_env gaden_sim_launch.py scenario:=10x6_empty_room configuration:=config_exp3_open_steady simulation:=sim1 sim_time:=320.0 use_rviz:=False
```

**注意**：预处理输出在 **`$(ros2 pkg prefix test_env)/share/test_env/...`**；勿只盯 `src/.../wind/`（易遇 symlink 断链，见下文）。

---

## 5. Exp.2 与时变风

`config_exp2_open_timevarying/simulations/sim1/sim.yaml` 中 `windLooping: loop: true, from: 0, to: 24` 与 `dynamic/` 下 25 帧 CSV 一致。

---

## 6. Filament 报错 `WindSequence.cpp:17`

表示 `wind/wind_iteration_*` 未就绪或断链。**删对应配置下 `wind/` 后重跑预处理**；检查路径用：

`ls -la "$(ros2 pkg prefix test_env)/share/test_env/scenarios/10x6_empty_room/environment_configurations/<configuration>/wind/"`

---

## 7. 算法实现代码（与短文一致）

短文中的四种 GSL 实现见：<https://github.com/MAPIRlab/Gas-Source-Localization>（与论文脚注一致）。

---

## 8. 其它

- 上游：`gaden_preprocessing/README.md`、`GADEN_tutorial.md`。
