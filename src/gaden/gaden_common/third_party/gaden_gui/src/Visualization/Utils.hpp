#pragma once
#include "glm/vec3.hpp"

namespace VizUtils
{
    inline glm::vec3 vecToGL(glm::vec3 const& vec)
    {
        return glm::vec3(vec.x, vec.z, -vec.y);
    }

    inline glm::vec3 vecFromGL(glm::vec3 const& vec)
    {
        return glm::vec3(vec.x, -vec.z, vec.y);
    }

    inline glm::vec3 scaleToGL(glm::vec3 const& vec)
    {
        return glm::vec3(vec.x, vec.z, vec.y);
    }

    inline glm::vec3 scaleFromGL(glm::vec3 const& vec)
    {
        return glm::vec3(vec.x, vec.z, vec.y);
    }
} // namespace VizUtils