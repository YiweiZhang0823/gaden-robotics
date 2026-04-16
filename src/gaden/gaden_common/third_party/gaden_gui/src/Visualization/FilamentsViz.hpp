#pragma once
#include "Visualization/Shader.hpp"
#include "gaden/datatypes/Color.hpp"
#include "gaden/datatypes/Filament.hpp"
#include <glm/vec3.hpp>
#include <mutex>
#include <optional>
#include <vector>

class FilamentsViz
{
public:
    FilamentsViz(class Scene& scene);
    void SetUp();
    void DrawFilaments(std::vector<gaden::Filament> const& filaments, gaden::Color color);
    void Draw();
    void Clear();

private:
    struct DrawFilamentsCommand
    {
        std::vector<glm::vec3> positions;
        glm::vec3 color;
    };

    std::vector<DrawFilamentsCommand> drawCommands;
    std::mutex mutex;
    std::optional<Shader> shader;
    Scene& scene;

    GLuint instanceVBO;
    GLuint quadVAO, quadVBO;
};