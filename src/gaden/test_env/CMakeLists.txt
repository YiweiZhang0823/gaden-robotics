cmake_minimum_required(VERSION 3.5)
project(test_env)
find_package(ament_cmake REQUIRED)

install(PROGRAMS scripts/zero_joint_states.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME zero_joint_states
)
install(PROGRAMS scripts/franka_joint_interactive.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME franka_joint_interactive
)
install(PROGRAMS scripts/franka_fp3_ik_goal.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME franka_fp3_ik_goal
)
install(PROGRAMS scripts/publish_ee_goal.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME publish_ee_goal
)
install(PROGRAMS scripts/open_field_build_gaden_data.sh
  DESTINATION lib/${PROJECT_NAME}
  RENAME open_field_build_gaden_data
)
install(PROGRAMS scripts/open_field_initial_state_commands.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME open_field_initial_state_commands
)
install(PROGRAMS scripts/surge_cast_spiral_gsl.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME surge_cast_spiral_gsl
)
install(PROGRAMS scripts/gsl_supervisor_summary.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gsl_supervisor_summary
)
install(PROGRAMS scripts/gsl_sensitivity_commands.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gsl_sensitivity_commands
)
install(PROGRAMS scripts/gsl_sensitivity_summary.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gsl_sensitivity_summary
)
install(PROGRAMS scripts/gsl_repeatability_commands.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gsl_repeatability_commands
)
install(PROGRAMS scripts/gsl_repeatability_summary.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gsl_repeatability_summary
)
install(PROGRAMS scripts/gsl_randomized_initial_state_commands.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gsl_randomized_initial_state_commands
)

install(DIRECTORY .
DESTINATION share/${PROJECT_NAME}
)
ament_package()
