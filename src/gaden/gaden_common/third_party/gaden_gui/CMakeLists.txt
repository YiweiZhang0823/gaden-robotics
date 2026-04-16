cmake_minimum_required(VERSION 3.11)

project(gaden_gui)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_BUILD_TYPE "Debug")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -g -fno-omit-frame-pointer")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")

include(FetchContent)
set(FETCHCONTENT_QUIET FALSE)
include(cmake/gaden.cmake)
include(cmake/ament_imgui.cmake)

include_directories(
    src
    src/glad/include
)

add_executable(gaden_gui
    src/main.cpp
    src/Application.cpp
    src/Project.cpp
    src/Modes/ConfigurationMode.cpp
    src/Modes/RunSimMode.cpp

    src/glad/src/glad.c
    src/Visualization/Scene.cpp
    src/Visualization/Camera.cpp
    src/Visualization/FilamentsViz.cpp
    )

target_link_libraries(gaden_gui
    gaden
    imgui_gl
)
