#pragma once
#include "Application.hpp"
#include "ImGuiUtils.hpp"
#include "Modes/ConfigurationMode.hpp"
#include "Modes/RunSimMode.hpp"
#include "Modes/SimulationListMode.hpp"
#include "SimulationInfo.hpp"
#include "Utils.hpp"
#include "gaden/Scene.hpp"
#include <gaden/internal/Time.hpp>

class SceneMode : public RunSimMode
{
public:
    SceneMode(ConfigurationMode& configMode, std::string const& name)
        : RunSimMode(configMode), sceneName(name)
    {
        metadata = configMode.configMetadata.GetRunningScene(name);
        std::vector simNames = configMode.configMetadata.GetSimulationNamesInScene(name);
        for (size_t i = 0; i < metadata.params.size(); i++)
            simInfos.emplace_back(configMode.configMetadata, simNames.at(i));
    }

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
        ImGui::Text("%s", fmt::format("Editing scene '{}'", sceneName).c_str());
        ImGui::VerticalSpace(10);
        ImGui::Separator();

        for (size_t i = 0; i < simInfos.size(); i++)
        {
            auto& simInfo = simInfos.at(i);
            simInfo.DrawSource();
            if (ImGui::CollapsingHeader(simInfo.name.c_str()))
            {
                simInfo.DrawGUI(i == 0);
                {
                    ImGui::ScopedStyle style(ImGuiCol_Button, Colors::Save);
                    if (ImGui::Button("Save Changes"))
                        simInfo.Save();
                }
            }
        }

        if (ImGui::ButtonCenteredOnLine("Add existing simulation"))
        {
            ImGui::OpenPopup("Select Simulation");
            selectingSimulations = true;
        }
        if (ImGui::ButtonCenteredOnLine("Create new simulation"))
        {
            std::optional<std::string> name = SimulationListMode::CreateSimulation(configMode);
            if (name)
                simInfos.emplace_back(configMode.configMetadata, *name);
        }

        if (selectingSimulations)
        {
            ImGui::SetNextWindowSize({500, 600});
            if (ImGui::BeginPopupModal("Select Simulation", &selectingSimulations))
            {
                ImGui::VerticalSpace(10);
                ImGui::Text("Simulation list");
                ImGui::Separator();
                ImGui::VerticalSpace(10);
                for (auto const& name : configMode.configMetadata.simulations)
                    if (ImGui::ButtonCenteredOnLine(name.c_str()))
                    {
                        bool alreadyAdded = std::find_if(simInfos.begin(), simInfos.end(), [&name](SimulationInfo const& info)
                                                         {
                                                             return info.name == name;
                                                         }) != simInfos.end();
                        if (alreadyAdded)
                            Utils::DisplayError("Can't add multiple copies of the same simulation!");
                        else
                        {
                            simInfos.emplace_back(configMode.configMetadata, name);
                            selectingSimulations = false;
                        }
                    }

                ImGui::EndPopup();
            }
        }

        if (!simInfos.empty())
            DrawTimeControlsGUI(simInfos.at(0).params.deltaTime);
        DrawSimulationStateGUI();

        {
            ImGui::ScopedStyle s(ImGuiCol_Button, Colors::Save);
            if (ImGui::Button("Save Changes"))
            {
                for (auto& info : simInfos)
                    info.Save();
                UpdateMetadata();
                metadata.WriteToYAML(configMode.configMetadata.GetSceneFilePath(sceneName));
            }
        }
        DrawButtonsGUI();
    }

protected:
    void Run() override
    {
        try
        {
            currentSimTime = 0;
            UpdateMetadata();
            gaden::Scene scene(metadata, configMode.config);

            float r = 0;
            if (isRateLimited)
                r = rateLimit;
            gaden::Utils::Time::Rate rate(r > 0 ? r : 1); // passing 0 technically causes UB due to division by 0

            auto simulations = scene.GetSimulations();
            auto firstSim = As<gaden::RunningSimulation>(simulations.at(0));
            while (firstSim->GetCurrentTime() < simDuration && canRun)
            {
                scene.AdvanceTimestep();
                currentSimTime = firstSim->GetCurrentTime();

                // this is not very efficient, because we are potentially copying the filament positions multiple times on a single frame, when only the last copy matters
                // however, avoiding that would be a bit of a mess
                //  if speed is a concern you can always run the simulation without visualization
                if (g_app->vizScene->active)
                {
                    g_app->vizScene->filamentsViz.Clear();
                    for (size_t i = 0; i < scene.GetSimulations().size(); i++)
                        g_app->vizScene->filamentsViz.DrawFilaments(simulations.at(i)->GetFilaments(), scene.GetColors().at(i));
                }

                if (r != 0)
                    rate.sleep();
            }

            if (firstSim->GetCurrentTime() >= simDuration)
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

    void UpdateMetadata()
    {
        metadata.params.clear();
        metadata.gasDisplayColors.clear();

        for (auto const& sim : simInfos)
        {
            metadata.params.push_back(sim.params);
            metadata.gasDisplayColors.push_back(sim.displayColor);
        }
    }

private:
    std::vector<SimulationInfo> simInfos;
    std::string sceneName;
    gaden::RunningSceneMetadata metadata;

    bool selectingSimulations = false;
};