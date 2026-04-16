#pragma once
#include "Mode.hpp"
#include "Modes/ConfigurationMode.hpp"
#include <optional>
#include <thread>

class RunSimMode : public Mode
{
protected:
    RunSimMode(ConfigurationMode& _configMode) : configMode(_configMode) {}
    virtual void Run() = 0;

    void ToggleSceneView()
    {
        if (!g_app->vizScene->active)
            configMode.CreateScene();
        else
            g_app->vizScene->active = false;
    }

    void DrawTimeControlsGUI(float deltaTime);
    void DrawSimulationStateGUI();
    void DrawButtonsGUI();

protected:
    ConfigurationMode& configMode;

    float simDuration = 300.f;
    bool isRateLimited = false;
    float rateLimit = 0;
    bool canRun = true;

    std::optional<std::thread> runSimThread;
    std::atomic<float> currentSimTime;
    bool simDone = false;
};