#pragma once
#include "Application.hpp"
#include "ImGuiUtils.hpp"
#include "Mode.hpp"
#include "Modes/ConfigurationMode.hpp"
#include "Project.hpp"
#include "Utils.hpp"
#include "imgui.h"

class ProjectMode : public Mode
{
public:
    ProjectMode(std::shared_ptr<Project> _project)
    {
        g_app->project = _project;
    }

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
        ImGui::VerticalSpace(10);
        ImGui::Separator();
        ImGui::VerticalSpace(40);

        for (auto& [name, config] : g_app->project->configurations)
        {
            std::string buttonText = fmt::format("Open configuration {}", config.GetName());
            if (ImGui::ButtonCenteredOnLine(buttonText.c_str()))
            {
                g_app->PushMode(std::make_shared<ConfigurationMode>(config));
            }
        }

        ImGui::PushStyleColor(ImGuiCol_Button, Colors::CreateNew);
        if (ImGui::ButtonCenteredOnLine("Create new configuration"))
        {
            std::string name = Utils::TextInput("Create new configuration", "Configuration name");
            if (name == "")
            {
                GADEN_ERROR("Invalid configuration name. Using 'config' instead");
                name = "config";
            }
            auto path = g_app->project->GetConfigurationPath(name);
            gaden::EnvironmentConfigMetadata::CreateTemplate(path);
            auto [iterator, inserted] = g_app->project->configurations.emplace(name, path);
            auto& configuration = iterator->second;
            configuration.ReadDirectory();

            g_app->PushMode(std::make_shared<ConfigurationMode>(configuration));
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
};