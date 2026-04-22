#!/usr/bin/env bash
# 为 10x6_empty_room 的「论文开阔场」两套 configuration 生成 GADEN 所需数据：
#   1) gaden_preprocessing → OccupancyGrid3D.csv、occupancy.*、wind/wind_iteration_*
#   2) gaden_filament_simulator → simulations/sim1/result/iteration_*
#
# 用法（在已 colcon build 并 source install 的工作空间根目录）:
#   ./src/gaden/test_env/scripts/open_field_build_gaden_data.sh
# 或:
#   ros2 run test_env open_field_build_gaden_data
#
# 不用 set -u：colcon 的 install/setup.bash 会引用未定义的 COLCON_TRACE 等变量，nounset 会导致 source 失败
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 从 install/lib/test_env/ 或源码 tree 中定位工作空间
if command -v ros2 >/dev/null 2>&1; then
  _TP="$(ros2 pkg prefix test_env 2>/dev/null || true)"
  if [[ -n "$_TP" ]]; then
    WS="$(cd "$(dirname "$(dirname "$_TP")")" && pwd)"
  fi
fi
if [[ -z "${WS:-}" ]]; then
  WS="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
fi

if [[ -f "$WS/install/setup.bash" ]]; then
  # colcon setup 使用未定义变量；若父 shell 启用了 nounset，需先关闭再 source
  set +u
  # shellcheck source=/dev/null
  source "$WS/install/setup.bash"
else
  echo "请先: cd $WS && colcon build --packages-select test_env gaden_preprocessing gaden_filament_simulator gaden_environment --symlink-install && source install/setup.bash" >&2
  exit 1
fi

run_preproc() {
  local cfg="$1"
  echo ""
  echo "========== 预处理: $cfg =========="
  ros2 launch test_env gaden_preproc_launch.py scenario:=10x6_empty_room "configuration:=$cfg"
}

run_filament() {
  local cfg="$1"
  echo ""
  echo "========== Filament 仿真（无 RViz 批处理）: $cfg =========="
  ros2 launch test_env gaden_sim_launch.py scenario:=10x6_empty_room "configuration:=$cfg" simulation:=sim1 sim_time:=320.0 use_rviz:=False
}

echo "工作空间: $WS"
echo "将依次：预处理 Exp.1 → Exp.2 → Exp.3 → 各跑一遍 Filament（APPIS 开阔场三套 + 学位论文平流场景）"
echo "（若只想生成占用栅格与风，可在脚本中注释掉 run_filament 段）"

run_preproc "config_exp1_open_weak"
run_preproc "config_exp2_open_timevarying"
run_preproc "config_exp3_open_steady"

run_filament "config_exp1_open_weak"
run_filament "config_exp2_open_timevarying"
run_filament "config_exp3_open_steady"

echo ""
echo "完成。若要「房间 + 气体 + Franka 机械臂」在同一 RViz，请另开终端执行（不要用上面的 filament RViz 找机械臂）："
echo "  source $WS/install/setup.bash"
echo "  ros2 launch test_env gaden_franka_open_exp1.launch.py"
echo "  ros2 launch test_env gaden_franka_open_exp2.launch.py"
echo "  ros2 launch test_env gaden_franka_open_exp3.launch.py"
