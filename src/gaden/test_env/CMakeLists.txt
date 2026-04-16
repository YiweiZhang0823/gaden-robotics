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

install(DIRECTORY .
DESTINATION share/${PROJECT_NAME}
)
ament_package()
