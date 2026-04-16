#pragma once
#include "Modes/ConfigurationMode.hpp"
#include "Modes/Mode.hpp"
#include "Modes/SceneMode.hpp"

class SceneListMode : public Mode
{
public:
    SceneListMode(ConfigurationMode& _configMode)
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

        for (auto& name : configMode.configMetadata.scenes)
        {
            std::string buttonText = fmt::format("Open scene {}", name);
            if (ImGui::ButtonCenteredOnLine(buttonText.c_str()))
                g_app->PushMode(std::make_shared<SceneMode>(configMode, name));
        }

        ImGui::PushStyleColor(ImGuiCol_Button, Colors::CreateNew);
        if (ImGui::ButtonCenteredOnLine("Create new scene"))
        {
            std::string name = Utils::TextInput("Create new scene", "Scene name");
            if (name == "")
            {
                GADEN_ERROR("Invalid scene name. Using 'scene' instead");
                name = "scene";
            }
            auto [iterator, inserted] = configMode.configMetadata.scenes.insert(name);
            if (inserted)
            {
                std::filesystem::path simFile = configMode.configMetadata.GetSceneFilePath(name);
                std::filesystem::create_directories(simFile.parent_path());
                configMode.configMetadata.GetRunningScene(name).WriteToYAML(simFile);

                g_app->PushMode(std::make_shared<SceneMode>(configMode, name));
            }
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

private:
    ConfigurationMode& configMode;
};