#pragma once
#include "Modes/ConfigurationMode.hpp"
#include "Modes/Mode.hpp"
#include "Modes/SimulationMode.hpp"

class SimulationListMode : public Mode
{
public:
    SimulationListMode(ConfigurationMode& _configMode)
        : configMode(_configMode) {}

    void OnPush() override
    {}

    void OnPop() override
    {}

    void OnGainFocus() override
    {}

    void OnLoseFocus() override
    {}

    void OnGUI() override
    {
        ImGui::TextCenteredOnLine(fmt::format("Project: '{}'", g_app->project->GetRoot()).c_str());
        ImGui::TextCenteredOnLine(fmt::format("Configuration '{}'", configMode.configMetadata.GetName()).c_str());
        ImGui::VerticalSpace(10);
        ImGui::Separator();
        ImGui::VerticalSpace(40);

        for (auto& name : configMode.configMetadata.simulations)
        {
            std::string buttonText = fmt::format("Open simulation {}", name);
            if (ImGui::ButtonCenteredOnLine(buttonText.c_str()))
            {
                g_app->PushMode(std::make_shared<SimulationMode>(configMode, name));
            }
        }

        ImGui::PushStyleColor(ImGuiCol_Button, Colors::CreateNew);
        if (ImGui::ButtonCenteredOnLine("Create new simulation"))
        {
            std::optional<std::string> name = CreateSimulation(configMode);
            if (name)
                g_app->PushMode(std::make_shared<SimulationMode>(configMode, *name));
        }
        ImGui::PopStyleColor();

        ImGui::VerticalSpace(20);
        ImGui::PushStyleColor(ImGuiCol_Button, Colors::Back);
        if (ImGui::ButtonCenteredOnLine("Back"))
        {
            g_app->PopMode();
        }
        ImGui::PopStyleColor();
    }

    static std::optional<std::string> CreateSimulation(ConfigurationMode& configMode)
    {
        std::string name = Utils::TextInput("Create new simulation", "Simulation name");
        if (name == "")
        {
            return std::nullopt;
        }

        auto [iterator, inserted] = configMode.configMetadata.simulations.insert(name);
        if (inserted)
        {
            std::filesystem::path simFile = configMode.configMetadata.GetSimulationFilePath(name);
            std::filesystem::create_directories(simFile.parent_path());
            gaden::RunningSimulation::Parameters{}.WriteToYAML(simFile); // create a file with default params
        }
        else
        {
            Utils::DisplayError("Simulation {} already exists!");
            return std::nullopt;
        }
        return name;
    }

private:
    ConfigurationMode& configMode;
};