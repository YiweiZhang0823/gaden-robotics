#pragma once
#include "Modes/Mode.hpp"
#include "Project.hpp"
#include <memory>
#include <stack>
#include <Visualization/Scene.hpp>

class Application
{
public:
    void Run();
    void PushMode(std::shared_ptr<Mode> mode);
    void PopMode();
    std::shared_ptr<Mode> GetCurrentMode();
    float GetDeltaTime() { return deltaT; }

public:
    bool shouldClose = false;
    std::shared_ptr<Project> project;
    std::unique_ptr<Scene> vizScene;

private:
    void DrawHeader();

private:
    std::stack<std::shared_ptr<Mode>> modeStack;
    float deltaT = 0;
};

inline std::unique_ptr<Application> g_app;