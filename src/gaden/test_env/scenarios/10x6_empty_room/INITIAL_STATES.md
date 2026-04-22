# Open-Field Initial States

This file records the initial-state design used after visually/statistically
inspecting the three open-field plume simulations.

## Plume Observations

| Scenario | Qualitative plume shape | Practical boundary used for initial states |
| --- | --- | --- |
| Exp.1 diffusion | Broad, weak/no mean wind, concentrated around the source | Main late plume around `x=0.2..2.1`, `y=3.8..5.5` near sensor height |
| Exp.2 time-varying | Intermittent, net downwind `+x`, plume bends over time | Use a wide downwind corridor around `y=4.2..5.8` |
| Exp.3 advection | Narrow steady downwind corridor, approximately `+x` | Use centerline near `y=4.95`, edge near `y=4.55`, and fixed-base arm-scale offsets |

The shared source is `[1.0, 4.95, 0.7]`. For Exp.2/Exp.3, "upwind" means
the `x < 1.0` side of the source. For Exp.1 the wind is weak, so the same
upwind reference is kept only to make the experimental matrix comparable.

## How To Run One Initial State

Use the `base_pose` from `initial_states.yaml` in Terminal 1, then publish the
corresponding `ee_target` in Terminal 2.

Terminal 1 example:

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 launch test_env gaden_franka_open_exp3.launch.py \
  align_base_from_gas_yaml:=false \
  map_x:=0.8 map_y:=4.65 map_yaw:=0.0 \
  joint_state_mode:=interactive franka_joint_max_velocity:=0.15
```

Terminal 2 example:

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env publish_ee_goal 1.55 4.95 0.65 --frame map --preset tilt_x_90
```

## State Categories

| Key | Meaning |
| --- | --- |
| `far_off_plume` | Far from source, away from plume edge |
| `far_near_edge` | Far from source, close to plume boundary |
| `far_inside_plume` | Far from source, already inside plume body |
| `near_source_outside_plume` | Close to source, outside plume |
| `near_source_upwind` | Close to source, on the upwind side |

The full coordinate table is stored in `initial_states.yaml`.
