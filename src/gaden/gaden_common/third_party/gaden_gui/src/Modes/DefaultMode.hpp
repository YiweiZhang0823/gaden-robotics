#pragma once
#include "Application.hpp"
#include "Mode.hpp"
#include "Project.hpp"
#include "ProjectMode.hpp"
#include "Utils.hpp"
#include "imgui.h"

class DefaultMode : public Mode
{
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
        ImGui::VerticalSpace(20);
        ImGui::PushFont(Fonts::logo);
        ImGui::TextCenteredOnLine("gaden");
        ImGui::PopFont();

        ImGui::VerticalSpace(105);
        ImGui::Separator();
        ImGui::VerticalSpace(75);

        if (ImGui::ButtonCenteredOnLine("Load Existing Gaden Project"))
        {
            auto path = Utils::FileDialog("Gaden project file '.gproj' | *.gproj", std::filesystem::current_path() / "");
            if (path.is_absolute() && std::filesystem::exists(path))
            {
                auto project = Project::LoadExisting(path);
                if (project)
                    g_app->PushMode(std::make_shared<ProjectMode>(project));
                else
                    Utils::DisplayError(fmt::format("'{}' is not the path of a valid gaden project", path));
            }
        }

        ImGui::PushStyleColor(ImGuiCol_Button, Colors::CreateNew);
        if (ImGui::ButtonCenteredOnLine("Create New Gaden Project"))
        {
            auto path = Utils::DirectoryDialog(std::filesystem::current_path() / "");
            if (path.is_absolute() && std::filesystem::exists(path) && std::filesystem::is_directory(path))
            {
                auto project = Project::CreateNew(path);
                if (project)
                    g_app->PushMode(std::make_shared<ProjectMode>(project));
                else
                    Utils::DisplayError(fmt::format("Failed to create project at directory '{}'!", path));
            }
            else
                Utils::DisplayError(fmt::format("Directory '{}' does not exist", path));
        }
        ImGui::PopStyleColor();

        ImGui::PushStyleColor(ImGuiCol_Button, Colors::Back);
        if (ImGui::ButtonCenteredOnLine("Exit GadenGUI"))
        {
            g_app->shouldClose = true;
        }
        ImGui::PopStyleColor();
    }
};