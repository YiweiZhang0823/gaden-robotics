#include "Scene.hpp"
#include "Application.hpp"
#include "GLFW/glfw3.h"
#include "ImGuiUtils.hpp"
#include "imgui.h"
#include <iostream>

//      - give the correct format to the triangle arrays
//      - create and bind array and index buffers
//      - create and bind the framebuffer to a textureID
//      - render into framebuffer
//      - pass the textureID to ImGui through ImGui::Image

namespace geometry
{
    const char* vertexShaderSource = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 normal;
layout (location = 2) in vec3 color;

uniform mat4 view;
uniform mat4 projection;
uniform mat4 model;

out vec4 vertexColor; 
out vec3 vertexNormal;

void main()
{
	gl_Position = projection * view * model * vec4(aPos, 1.0f);
    vertexColor = vec4(color,1);
    vertexNormal = (model * vec4(normal,0)).xyz;
})";

    const char* fragmentShaderSource = R"(
#version 330 core
out vec4 FragColor;

in vec4 vertexColor;
in vec3 vertexNormal;
uniform vec3 lightDir = vec3(1, -1, 0);

void main()
{
    float diff = max(dot(normalize(vertexNormal), normalize(lightDir)), 0.0) * 0.5 + 0.5;
	FragColor.rgb = vertexColor.rgb * diff;
	FragColor.a = vertexColor.a;
})";
} // namespace geometry

namespace markers
{
    const char* vertexShaderSource = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec3 aColor; //ignored

uniform mat4 view;
uniform mat4 projection;
uniform mat4 model;
uniform vec3 objectColor;

out vec4 vertexColor; 
out vec3 vertexNormal;

void main()
{
	gl_Position = projection * view * model * vec4(aPos, 1.0f);
    vertexColor = vec4(objectColor, 0.4);
    vertexNormal =( model * vec4(aNormal, 0)).xyz;
})";

    const char* fragmentShaderSource = R"(
#version 330 core
out vec4 FragColor;

in vec4 vertexColor;
in vec3 vertexNormal;
uniform vec3 lightDir = vec3(1, -1, 0);

void main()
{
    float diff = max(dot(normalize(vertexNormal), normalize(lightDir)), 0.0) * 0.5 + 0.5;
	FragColor.rgb = vertexColor.rgb * diff;
	FragColor.a = vertexColor.a;
})";
} // namespace markers

static ImVec2 windowSize = ImVec2(800, 600);
// constexpr ImVec2 windowSize = ImVec2(1920, 1080);

Scene::Scene()
    : filamentsViz(*this)
{
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        std::cerr << "Failed to initialize GLAD" << std::endl;
        raise(SIGTRAP);
    }

    sphereMarker = RenderModel::CreateSphere(1, 20, 20, gaden::Color{1, 0, 1, 1});
    cubeMarker = RenderModel::CreateCube(gaden::Color{1, 0, 1, 1});
    cylinderMarker = RenderModel::CreateCylinder(20, gaden::Color{1, 0, 1, 1});

    geometryShader.emplace(geometry::vertexShaderSource, geometry::fragmentShaderSource);
    markersShader.emplace(markers::vertexShaderSource, markers::fragmentShaderSource);
    filamentsViz.SetUp();

    create_framebuffer();
}

void Scene::CreateSceneGeometry(std::vector<std::vector<gaden::Triangle>> const& models, std::vector<gaden::Color> const& colors)
{
    renderModels.clear();
    renderModels.reserve(models.size());
    for (size_t i = 0; i < models.size(); i++)
        renderModels.push_back({models[i], colors[i]});
}

void Scene::DrawSphere(glm::vec3 position, float radius, gaden::Color color)
{
    Transform transform;
    transform.position = VizUtils::vecToGL(position);
    transform.scale = glm::vec3{radius, radius, radius};
    DrawCommand command{.shader = *markersShader,
                        .model = sphereMarker,
                        .color = {color.r, color.g, color.b},
                        .transform = transform};
    drawCommands.push_back(command);
}

void Scene::DrawCube(glm::vec3 position, glm::vec3 scale, gaden::Color color)
{
    Transform transform;
    transform.position = VizUtils::vecToGL(position);
    transform.scale = VizUtils::scaleToGL(scale);
    transform.rotation = glm::quat(1, 0, 0, 0);
    DrawCommand command{.shader = *markersShader,
                        .model = cubeMarker,
                        .color = {color.r, color.g, color.b},
                        .transform = transform};
    drawCommands.push_back(command);
}

void Scene::DrawLine(glm::vec3 start, glm::vec3 end, float width, gaden::Color color)
{
    start = VizUtils::vecToGL(start);
    end = VizUtils::vecToGL(end);

    glm::vec3 line = end - start;
    glm::vec3 direction = glm::normalize(line);

    bool isVertical = std::abs(direction.x) < 0.005f && std::abs(direction.z) < 0.005f;

    Transform transform;
    transform.position = line * 0.5f + start;
    transform.rotation = glm::quatLookAt(direction,
                                         isVertical ? glm::vec3(1, 0, 0) : glm::vec3(0, 1, 0));
    transform.scale = glm::vec3{width, width, glm::length(line)};
    DrawCommand command{.shader = *markersShader,
                        .model = cubeMarker,
                        .color = {color.r, color.g, color.b},
                        .transform = transform};
    drawCommands.push_back(command);
}

void Scene::DrawCylinder(glm::vec3 position, float radius, float height, gaden::Color color)
{
    Transform transform;
    transform.position = VizUtils::vecToGL(position);
    transform.scale = glm::vec3{radius, height, radius};
    DrawCommand command{.shader = *markersShader,
                        .model = cylinderMarker,
                        .color = {color.r, color.g, color.b},
                        .transform = transform};
    drawCommands.push_back(command);
}

void Scene::Render()
{
    if (active)
    {
        //initial size and position
        {
            ImGui::SetNextWindowSize(windowSize, ImGuiCond_Appearing);
            // offset the window so it is not perfectly aligned with the main viewport -- since you want to be able to see both at the same time
            ImVec2 pos = ImGui::GetMainViewport()->GetCenter();
            pos.x += 400;
            pos.y -= 200;
            ImGui::SetNextWindowPos(pos, ImGuiCond_Appearing);
        }

        ImGui::Begin("Scene", &active, ImGuiWindowFlags_NoCollapse);

        //handle resizing
        ImVec2 _windowSize = ImGui::GetWindowSize();
        if(_windowSize.x != windowSize.x || _windowSize.y != windowSize.y)
        {
            windowSize = _windowSize;
            rescale_framebuffer(windowSize.x, windowSize.y);
        }

        camera.HandleInput(g_app->GetDeltaTime());

        // render into a framebuffer (texture), which will then be used by ImGui::Image
        bind_framebuffer();
        glViewport(0, 0, windowSize.x, windowSize.y);

        // clear the buffer
        glClearColor(0.4f, 0.55f, 0.7f, 1.f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glEnable(GL_DEPTH_TEST);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glEnable(GL_CULL_FACE);

        // draw scene geometry
        geometryShader->use();
        SetCameraInfoShader(*geometryShader);

        for (auto const& model : renderModels)
            model.Draw(*geometryShader);

        // draw filaments (if present)
        filamentsViz.Draw();

        // draw the transparents (deferred so that we can get blending)
        glEnable(GL_BLEND);
        for (auto& command : drawCommands)
        {
            command.shader.use();
            command.shader.setVec3("objectColor", command.color);
            SetCameraInfoShader(command.shader);

            command.model.transform = command.transform;
            command.model.Draw(command.shader);
        }
        glDisable(GL_BLEND);

        // cleanup
        glBindVertexArray(0);
        glUseProgram(0);
        unbind_framebuffer();

        // show the rendered image to a window

        const float window_width = ImGui::GetContentRegionAvail().x;
        const float window_height = ImGui::GetContentRegionAvail().y;
        ImGui::Image((ImTextureID)(intptr_t)texture_id, ImVec2(window_width, window_height));
        DrawControlsBox();

        ImGui::End();
    }
    drawCommands.clear();
}

void Scene::SetCameraInfoShader(Shader const& s)
{
    // calculate the camera matrices and send them to the shader
    glm::mat4 projection = glm::perspective(glm::radians(60.f), windowSize.x / windowSize.y, 0.1f, 100.0f);
    projection[1] *= -1;
    s.setMat4("projection", projection);

    glm::mat4 view = camera.GetViewMatrix();
    s.setMat4("view", view);
    s.setVec3("lightDir", glm::vec3(0.3, 1, 0.5));
}

void Scene::DrawControlsBox()
{
    ImGui::SetCursorPos({0, 0});
    const char* msg = "Hold RMB to control camera\n"
                      "Move mouse - rotate\n"
                      "W - Move forward\n"
                      "S - Move back\n"
                      "A - Move left\n"
                      "D - Move right\n"
                      "Q - Move up\n"
                      "E - Move down\n"
                      "LShift - Speed up";

    float padding = 10;
    ImVec2 offset;
    CalculateSize(offset,
                  ImGui::VerticalSpace(padding);
                  ImGui::HorizontalSpace(padding);
                  ImGui::Text("%s", msg););

    offset.x += 2 * padding;
    offset.y += 2 * padding;

    ImVec2 pos = {ImGui::GetContentRegionMax().x - offset.x, ImGui::GetContentRegionMax().y - offset.y};
    ImGui::SetCursorPos(pos);

    ImGui::PushStyleColor(ImGuiCol_ChildBg, 0x8833281f);
    ImGui::BeginChild("controls");
    ImGui::VerticalSpace(padding);
    ImGui::HorizontalSpace(padding);
    ImGui::Text("%s", msg);
    ImGui::EndChild();
    ImGui::PopStyleColor();
}

void Scene::create_framebuffer()
{
    const GLint WIDTH = windowSize.x;
    const GLint HEIGHT = windowSize.y;

    glGenFramebuffers(1, &FBO);
    glBindFramebuffer(GL_FRAMEBUFFER, FBO);

    glGenTextures(1, &texture_id);
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, WIDTH, HEIGHT, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture_id, 0);

    glGenRenderbuffers(1, &RBO);
    glBindRenderbuffer(GL_RENDERBUFFER, RBO);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, WIDTH, HEIGHT);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, RBO);

    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        std::cerr << "ERROR::FRAMEBUFFER:: Framebuffer is not complete!\n";

    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    glBindTexture(GL_TEXTURE_2D, 0);
    glBindRenderbuffer(GL_RENDERBUFFER, 0);
}

void Scene::bind_framebuffer()
{
    glBindFramebuffer(GL_FRAMEBUFFER, FBO);
}

void Scene::unbind_framebuffer()
{
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
}

void Scene::rescale_framebuffer(float width, float height)
{
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture_id, 0);

    glBindRenderbuffer(GL_RENDERBUFFER, RBO);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, RBO);
}