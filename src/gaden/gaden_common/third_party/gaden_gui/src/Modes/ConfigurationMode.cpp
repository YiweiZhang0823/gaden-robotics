#include "ConfigurationMode.hpp"
#include "Application.hpp"
#include "ImGuiUtils.hpp"
#include "Modes/SceneListMode.hpp"
#include "SimulationListMode.hpp"
#include "Utils.hpp"
#include "Visualization/Scene.hpp"
#include "gaden/Preprocessing.hpp"
#include "gaden/internal/STL.hpp"
#include "imgui.h"
#include <regex>

void ConfigurationMode::OnGUI()
{
    ImGui::Text("Project: '%s'", g_app->project->GetRoot().c_str());
    ImGui::Text("%s", fmt::format("Editing configuration '{}'", configMetadata.GetName()).c_str());
    ImGui::VerticalSpace(10);
    ImGui::Separator();
    ImGui::VerticalSpace(20);

    ImGui::InputFloat("Cell size", &configMetadata.cellSize, 0.0f, 0.0f, "%.2f");
    ImGui::Checkbox("Uniform Wind", &configMetadata.uniformWind);
    ImGui::TextInputRequired("Unprocessed Wind Files", &configMetadata.unprocessedWindFiles);
    ImGui::SameLine();
    if (ImGui::Button("Find"))
    {
        std::filesystem::path path = Utils::FileDialog("OpenFOAM vector clouds | *.csv", g_app->project->GetRoot() / "");
        std::cmatch m;
        if (std::regex_match(path.c_str(), m, std::regex("(.*)_\\d+.csv")))
            configMetadata.unprocessedWindFiles = m[1];
        else
            Utils::DisplayError("Selected file does not have the correct name pattern (ending in _[i].csv)");
    }
    ImGui::VerticalSpace(20);

    //------------------------
    if (ImGui::CollapsingHeader("Obstacle Models"))
    {
        ModelsList(configMetadata.envModels, "Obstacle Models");
        ImGui::VerticalSpace(20);
    }
    if (ImGui::CollapsingHeader("Outlet Models"))
    {
        ModelsList(configMetadata.outletModels, "Outlet Models");
        ImGui::VerticalSpace(20);
    }

    ImGui::DragFloat3("Empty point", &configMetadata.emptyPoint.x, 0.05f, 0.0f, 0.0f, "%.2f");
    ImGui::SameLine();
    if (ImGui::Button("View in scene"))
        CreateScene();

    g_app->vizScene->DrawSphere(configMetadata.emptyPoint, 0.1f);
    //------------------------

    ImGui::VerticalSpace(30);
    if (config)
        ImGui::TextColored(Colors::AsVec(Colors::InfoText), "Preprocessed data available");
    else
        ImGui::TextColored(Colors::AsVec(Colors::ErrorText), "No preprocessed data available");

    //------------------------
    ImGui::PushStyleColor(ImGuiCol_Button, Colors::Save);
    if (ImGui::Button("Save Changes"))
    {
        configMetadata.WriteConfigYAML(g_app->project->GetRoot());
    }

    //------------------------
    ImGui::SameLine();
    if (ImGui::Button("Run Preprocessing"))
    {
        config = gaden::Preprocessing::Preprocess(configMetadata);
        if (config && config->WriteToDirectory(configMetadata.rootDirectory))
        {
            Utils::DisplayInfo("Preprocessing completed!");
        }
        else
            Utils::DisplayError("Preprocessing failed! See logs for more info");
    }

    ImGui::SameLine();
    if (ImGui::Button("Go to 'Simulations'"))
    {
        g_app->PushMode(std::make_shared<SimulationListMode>(*this));
    }


    ImGui::SameLine();
    if (ImGui::Button("Go to 'Scenes'"))
    {
        g_app->PushMode(std::make_shared<SceneListMode>(*this));
    }
    ImGui::PopStyleColor();

    //------------------------
    ImGui::PushStyleColor(ImGuiCol_Button, Colors::Back);
    if (ImGui::Button("Back"))
    {
        g_app->PopMode();
    }
    ImGui::PopStyleColor();
}

void ConfigurationMode::ModelsList(std::vector<gaden::Model3D>& models, const char* label)
{
    ImGui::PushID(label);
    // ImGui::Text("%s", label);
    for (size_t i = 0; i < models.size(); i++)
    {
        ImGui::VerticalSpace(5);
        ImGui::PushID(i);
        gaden::Model3D& model = models.at(i);

        // path
        std::string temp = model.path.string();
        ImGui::TextInputRequired("Path", &temp);
        ImGui::SameLine();
        if (ImGui::Button("Find"))
            temp = Utils::FileDialog("STL models | *.stl", model.path);
        model.path = temp;
        ImGui::SameLine();
        if (ImGui::Button("Remove"))
        {
            models.erase(models.begin() + i);
            i--;
            ImGui::PopID();
            continue;
        }

        // color
        ImGui::SetNextItemWidth(200);
        ImGui::ColorEdit4("color", &model.color.r, ImGuiColorEditFlags_::ImGuiColorEditFlags_Float);
        if (i > 0)
        {
            ImGui::SameLine();
            ImGui::PushStyleColor(ImGuiCol_Button, Colors::Secondary);
            if (ImGui::Button("Copy previous color"))
                model.color = models.at(i - 1).color;
            ImGui::PopStyleColor();
        }
        ImGui::PopID();
        ImGui::VerticalSpace(5);
        ImGui::Separator();
    }

    if (ImGui::Button("Add models"))
    {
        auto paths = Utils::MultiFileDialog("STL models | *.stl", g_app->project->GetRoot() / "");
        for (auto& path : paths)
            models.push_back({.path = path});
    }
    ImGui::PopID();
}

void ConfigurationMode::CreateScene()
{
    std::vector<std::vector<gaden::Triangle>> models;
    std::vector<gaden::Color> colors;
    for (auto const& model : configMetadata.envModels)
    {
        models.push_back(gaden::ParseSTLFile(model));
        colors.push_back(model.color);
    }
    for (auto const& model : configMetadata.outletModels)
    {
        models.push_back(gaden::ParseSTLFile(model));
        colors.push_back(model.color);
    }
    g_app->vizScene->CreateSceneGeometry(models, colors);
    g_app->vizScene->active = true;
}
