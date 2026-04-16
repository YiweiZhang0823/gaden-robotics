#include "Camera.hpp"
#include "Visualization/Utils.hpp"
#include "gaden/core/Logging.hpp"
#include "gaden/core/Vectors.hpp"
#include "imgui.h"

Camera::Camera()
{
    transform.position = glm::vec3(5, 10, 5);

    // look towards (0,0,0)
    glm::vec3 cameraTarget = glm::vec3(0.0f, 0.0f, 0.0f);
    glm::vec3 cameraDirection = glm::normalize(cameraTarget - transform.position);

    glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f);
    if (std::abs(glm::dot(up, cameraDirection)) > 0.99f)
        up = glm::vec3(0, 0, 1);
    glm::vec3 cameraRight = glm::normalize(glm::cross(up, cameraDirection));
    glm::vec3 cameraUp = glm::cross(cameraDirection, cameraRight);

    transform.rotation = glm::quatLookAt(cameraDirection, cameraUp);
}

void Camera::HandleInput(float deltaTime)
{
    if (ImGui::IsWindowHovered() && ImGui::IsMouseDown(ImGuiMouseButton_Right))
        ImGui::SetWindowFocus();
    if (!ImGui::IsWindowFocused())
        return;

    float boost = 1.f;
    if (ImGui::IsKeyDown(ImGuiKey_LeftShift))
        boost = 3.f;

    if (ImGui::IsKeyDown(ImGuiKey_W))
        transform.position += transform.forward() * movementSpeed * boost * deltaTime;
    if (ImGui::IsKeyDown(ImGuiKey_S))
        transform.position += -transform.forward() * movementSpeed * boost * deltaTime;
    if (ImGui::IsKeyDown(ImGuiKey_A))
        transform.position += -transform.right() * movementSpeed * boost * deltaTime;
    if (ImGui::IsKeyDown(ImGuiKey_D))
        transform.position += transform.right() * movementSpeed * boost * deltaTime;
    if (ImGui::IsKeyDown(ImGuiKey_Q))
        transform.position += transform.up() * movementSpeed * boost * deltaTime;
    if (ImGui::IsKeyDown(ImGuiKey_E))
        transform.position += -transform.up() * movementSpeed * boost * deltaTime;

    ImVec2 mouseDelta = ImGui::GetMouseDragDelta(ImGuiMouseButton_Right, 0.0f);
    ImGui::ResetMouseDragDelta(ImGuiMouseButton_Right);
    // smoothing
    mouseDelta.x = std::lerp(previousMouseDelta.x, mouseDelta.x, 0.4);
    mouseDelta.y = std::lerp(previousMouseDelta.y, mouseDelta.y, 0.4);
    previousMouseDelta = mouseDelta;

    glm::quat pitchQuat(glm::vec3(-mouseDelta.y * rotationSpeed * deltaTime, 0, 0));
    glm::quat yawQuat(glm::vec3(0, -mouseDelta.x * rotationSpeed * deltaTime, 0));

    transform.rotation = yawQuat * transform.rotation * pitchQuat;
}
