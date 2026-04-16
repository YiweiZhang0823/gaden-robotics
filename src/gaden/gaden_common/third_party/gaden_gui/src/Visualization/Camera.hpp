#pragma once
#include "Visualization/Transform.hpp"
#include "imgui.h"

struct Camera
{
    Transform transform;
    float movementSpeed = 4.f;
    float rotationSpeed = 0.7f;

    Camera();

    void HandleInput(float deltaTime);

    glm::mat4 GetViewMatrix()
    {
        return glm::lookAt(transform.position, transform.position+transform.forward(), transform.up());
    }

private:
    ImVec2 previousMouseDelta = ImVec2(0, 0);
};