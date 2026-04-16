#pragma once

#include "Visualization/RenderModel.hpp"


struct DrawCommand
{
    Shader& shader;
    RenderModel& model;
    glm::vec3 color;
    Transform transform;
};