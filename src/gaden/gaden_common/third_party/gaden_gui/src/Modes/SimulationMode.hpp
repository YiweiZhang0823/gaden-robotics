#pragma once
#include "Application.hpp"
#include "ImGuiUtils.hpp"
#include "Modes/ConfigurationMode.hpp"
#include "Modes/RunSimMode.hpp"
#include "SimulationInfo.hpp"
#include "Utils.hpp"
#include "imgui.h"
#include <gaden/RunningSimulation.hpp>
#include <gaden/internal/Time.hpp>

class SimulationMode : public RunSimMode
{
public:
    SimulationMode(ConfigurationMode& _configMode,
                   std::string_view _name)
        : RunSimMode(_configMode),
          name(_name),
          simInfo(configMode.configMetadata, name)
    {}

    void OnPush() override
    {}

    void OnPop() override
    {}

    void OnGainFocus() override
    {}

    void OnLoseFocus() override
    {
        g_app->vizScene->active = false;
        g_app->vizScene->filamentsViz.Clear();
    }

    void OnGUI() override
    {
        ImGui::Text("Project: '%s'", g_app->project->GetRoot().c_str());
        ImGui::Text("%s", fmt::format("Configuration '{}'", configMode.configMetadata.GetName()).c_str());
        ImGui::Text("%s", fmt::format("Editing simulation '{}'", name).c_str());
        ImGui::VerticalSpace(10);
        ImGui::Separator();

        ImGui::BeginDisabled(runSimThread.has_value());
        {
            simInfo.DrawSource();
            simInfo.DrawGUI(true);
        }
        ImGui::EndDisabled();

        DrawTimeControlsGUI(simInfo.params.deltaTime);
        DrawSimulationStateGUI();
        {
            ImGui::ScopedStyle s(ImGuiCol_Button, Colors::Save);
            if (ImGui::Button("Save"))
                simInfo.Save();
        }
        ImGui::SameLine();
        DrawButtonsGUI();
    }

private:
    void Run() override
    {
        try
        {
            currentSimTime = 0;
            gaden::RunningSimulation sim(simInfo.params, configMode.config);

            float r = 0;
            if (isRateLimited)
                r = rateLimit;
            gaden::Utils::Time::Rate rate(r);

            while (sim.GetCurrentTime() < simDuration && canRun)
            {
                sim.AdvanceTimestep();
                currentSimTime = sim.GetCurrentTime();

                // this is not very efficient, because we are potentially copying the filament positions multiple times on a single frame, when only the last copy matters
                // however, avoiding that would be a bit of a mess
                //  if speed is a concern you can always run the simulation without visualization
                if (g_app->vizScene->active)
                {
                    g_app->vizScene->filamentsViz.Clear();
                    g_app->vizScene->filamentsViz.DrawFilaments(sim.GetFilaments(), simInfo.displayColor);
                }

                if (r != 0)
                    rate.sleep();
            }

            if (sim.GetCurrentTime() >= simDuration)
                Utils::DisplayInfo("Simulation completed!");

            canRun = true;
        }
        catch (std::exception const& e)
        {
            GADEN_ERROR("Caught exception while running simulation: '{}'", e.what());
            Utils::DisplayError("Simulation failed! See logs for more info");
        }

        simDone = true;
    }

private:
    std::string name;
    SimulationInfo simInfo;
};