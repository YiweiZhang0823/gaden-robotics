# CAST/SURGE/SPIRAL Runner

`surge_cast_spiral_gsl` is a first executable baseline for the thesis-style
finite-state machine:

- `CAST`: probe around the current end-effector position and estimate a coarse
  direction from left/right, up/down, and forward/backward gas samples.
- `SURGE`: move along the estimated direction while the plume cue is improving.
- `SPIRAL`: perform small local Lissajous-like probing when the signal is stable
  and the zone is classified as core.

The implementation follows the thesis structure but uses Cartesian TCP goals
instead of reproducing the exact joint-angle saddle and wrist trajectories. It is
intended as a runnable baseline for collecting success/time/path-length CSV data.

## Run One Trial

Terminal 1 starts a scenario and places the Franka base for the selected initial
state. Example:

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env open_field_initial_state_commands exp3_advection far_inside_plume
```

Copy the printed Terminal 1 launch command and run it.

Terminal 2 starts the runner:

```bash
cd /home/yiwei/ros2_ws
source install/setup.bash
ros2 run test_env surge_cast_spiral_gsl --ros-args \
  -p scenario_key:=exp3_advection \
  -p initial_state_key:=far_inside_plume \
  -p param_set:=baseline \
  -p timeout_s:=600.0 \
  -p success_radius:=0.25 \
  -p required_confidence:=0.6 \
  -p goal_preset:=tilt_x_90
```

The runner appends one row to:

```text
/home/yiwei/ros2_ws/results/gsl_trials.csv
```

## Important Limitation

The current Franka base is fixed during a trial. If the source is several meters
away from the base, the arm cannot physically reach it. For real success-rate
experiments, choose initial states/base placements such that the source is inside
the reachable workspace, or add a mobile-base layer.

## Key Parameters

| Parameter | Role |
| --- | --- |
| `theta_low`, `theta_mid`, `theta_high` | Plume-zone thresholds (`far/near/edge/core`) |
| `cast_step` | Cartesian probing amplitude in CAST |
| `cast_vertical_step` | Vertical probing amplitude in CAST |
| `surge_step_far/near/edge/core` | Advancement step size in SURGE |
| `spiral_radius` | Initial probing radius in SPIRAL |
| `spiral_radius_decay` | Scale decay after each local SPIRAL cycle |
| `success_radius` | Ground-truth source-distance threshold for success |
| `required_confidence` | Minimum source confidence for declaring success |

These are the first parameters to vary for sensitivity analysis.

For the supervisor-requested initial-state matrix, prefer generating commands
with:

```bash
ros2 run test_env open_field_initial_state_commands exp3_advection far_inside_plume
```
