#include "FilamentsViz.hpp"
#include "Scene.hpp"
#include "Visualization/Utils.hpp"

static const char* vertexShader = R"(
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec3 aOffset;

uniform mat4 view;
uniform mat4 projection;

void main()
{
    vec3 CameraRight_world = vec3(view[0][0], view[1][0], view[2][0]);
    vec3 CameraUp_world = vec3(view[0][1], view[1][1], view[2][1]);

    float size = 0.045;
    vec3 pos_world = aOffset
                    + CameraRight_world * aPos.x * size
                    + CameraUp_world * aPos.y * size;

    gl_Position = projection * view * vec4(pos_world, 1.0);
})";

static const char* fragmentShader = R"(
#version 330 core
out vec4 FragColor;

uniform vec3 color;

void main()
{
    FragColor = vec4(color, 1.0);
})";

FilamentsViz::FilamentsViz(Scene& scene)
    : scene(scene) {}

void FilamentsViz::SetUp()
{
    // instanced rendering
    // we need two sets of info: one for the geometry (single quad) and one for the positions of all the instances
    // these are stored in two different VBOs

    // clang-format off
    float quadVertices[] = {
        // positions
        -0.5f,        0.5f,
        0.5f,        -0.5f,
        -0.5f,        -0.5f,
        
        -0.5f,        0.5f,
        0.5f,        0.5f,
        0.5f,        -0.5f,
    };
    // clang-format on

    // create the buffers for the quad data
    glGenVertexArrays(1, &quadVAO);
    glGenBuffers(1, &quadVBO);

    glBindVertexArray(quadVAO);
    glBindBuffer(GL_ARRAY_BUFFER, quadVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(quadVertices), quadVertices, GL_STATIC_DRAW);

    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);

    // also set instance data
    glGenBuffers(1, &instanceVBO);
    glEnableVertexAttribArray(1);
    glBindBuffer(GL_ARRAY_BUFFER, instanceVBO); // this attribute comes from a different vertex buffer
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glVertexAttribDivisor(1, 1); // tell OpenGL this is an instanced vertex attribute.

    shader.emplace(vertexShader, fragmentShader);
}

void FilamentsViz::DrawFilaments(std::vector<gaden::Filament> const& filaments, gaden::Color color)
{
    std::scoped_lock<std::mutex> lock(mutex);

    drawCommands.push_back(DrawFilamentsCommand{
        .positions = std::vector<glm::vec3>(filaments.size()),
        .color = glm::vec3{color.r, color.g, color.b}});

#pragma omp parallel for
    for (size_t i = 0; i < filaments.size(); i++)
        drawCommands.back().positions[i] = VizUtils::vecToGL(filaments[i].position);
}

void FilamentsViz::Draw()
{
    std::scoped_lock<std::mutex> lock(mutex);
    if (drawCommands.size() == 0)
        return;

    shader->use();
    scene.SetCameraInfoShader(*shader);

    for (auto const& command : drawCommands)
    {
        shader->setVec3("color", command.color);

        // set the updated positions
        glBindBuffer(GL_ARRAY_BUFFER, instanceVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(glm::vec3) * command.positions.size(), command.positions.data(), GL_STATIC_DRAW);
        glBindBuffer(GL_ARRAY_BUFFER, 0);

        // draw
        glBindVertexArray(quadVAO);
        glDrawArraysInstanced(GL_TRIANGLES, 0, 6, command.positions.size()); // 100 triangles of 6 vertices each
    }
}

void FilamentsViz::Clear()
{
    drawCommands.clear();
}
