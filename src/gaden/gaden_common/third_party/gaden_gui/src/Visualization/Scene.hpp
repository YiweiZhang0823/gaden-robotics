#pragma once
#include "Visualization/Camera.hpp"
#include "Visualization/DrawCommand.hpp"
#include "Visualization/FilamentsViz.hpp"
#include "Visualization/RenderModel.hpp"
#include "Visualization/Shader.hpp"
#include <gaden/internal/Triangle.hpp>
#include <glad/include/glad/glad.h>
#include <optional>

class Scene
{
public:
    Scene();
    void CreateSceneGeometry(std::vector<std::vector<gaden::Triangle>> const& models, std::vector<gaden::Color> const& colors);

    void DrawSphere(glm::vec3 position, float radius, gaden::Color color = {0, 0, 1, 1});
    void DrawCube(glm::vec3 position, glm::vec3 scale, gaden::Color color = {0, 0, 1, 1});
    void DrawLine(glm::vec3 start, glm::vec3 end, float width, gaden::Color color = {0, 0, 1, 1});
    void DrawCylinder(glm::vec3 position, float radius, float height, gaden::Color color = {0, 0, 1, 1});

    void Render();

    void SetCameraInfoShader(Shader const& s);
    bool active = false;
    FilamentsViz filamentsViz;

private:
    void create_framebuffer();
    void unbind_framebuffer();
    void rescale_framebuffer(float width, float height);
    void bind_framebuffer();
    void DrawControlsBox();

private:
    std::vector<RenderModel> renderModels;
    RenderModel sphereMarker;
    RenderModel cubeMarker;
    RenderModel cylinderMarker;

    GLuint FBO; // frame buffer object
    GLuint RBO; // render buffer object
    GLuint texture_id;

    std::optional<Shader> geometryShader;
    std::optional<Shader> markersShader;

    std::vector<DrawCommand> drawCommands;

    Camera camera;
};