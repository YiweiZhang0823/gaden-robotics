#pragma once

#include "Application.hpp"
#include "ImGuiUtils.hpp"
#include "gaden/RunningSimulation.hpp"
#include "gaden/datatypes/sources/BoxSource.hpp"
#include "gaden/datatypes/sources/CylinderSource.hpp"
#include "gaden/datatypes/sources/LineSource.hpp"
#include "gaden/datatypes/sources/SphereSource.hpp"
#include "gaden/internal/Pointers.hpp"
#include "imgui.h"

struct SimulationInfo
{
    std::string name;
    gaden::EnvironmentConfigMetadata configMetadata;
    gaden::RunningSimulation::Parameters params;
    gaden::Color displayColor;

    // hold copies of these to avoid having them reset when the type of source is changed and we have to create a new instance
    gaden::Vector3 sourcePosition;
    int sourceTypeSelected;
    gaden::GasType gasType;

    SimulationInfo(gaden::EnvironmentConfigMetadata const& _configMetadata,
                   std::string const& _name)
        : name(_name),
          configMetadata(_configMetadata),
          params(configMetadata.GetSimulationParams(name))
    {
        params.saveDataDirectory = configMetadata.GetSimulationFilePath(name).parent_path() / "result";

        sourceTypeSelected = std::find(gaden::GasSource::sourceTypeNames.begin(), gaden::GasSource::sourceTypeNames.end(), params.source->Type()) - gaden::GasSource::sourceTypeNames.begin();
        gasType = params.source->gasType;
        sourcePosition = params.source->sourcePosition;
        CreateSource();
    }

    void DrawGUI(bool allowWindLoop)
    {
        ImGui::Combo("Source type", &sourceTypeSelected, ConcatenatedNames().c_str());
        {
            CreateSource();

            if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "sphere")
                ImGui::DragFloat("Source radius", &As<gaden::SphereSource>(params.source)->radius, 0.05f);
            else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "box")
                ImGui::DragFloat3("Source size", &As<gaden::BoxSource>(params.source)->size.x, 0.05f);
            else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "line")
                ImGui::DragFloat3("Line end", &As<gaden::LineSource>(params.source)->lineEnd.x, 0.05f);
            else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "cylinder")
            {
                ImGui::DragFloat("Source Radius", &As<gaden::CylinderSource>(params.source)->radius, 0.05f);
                ImGui::DragFloat("Source Height", &As<gaden::CylinderSource>(params.source)->height, 0.05f);
            }
        }
        ImGui::DragFloat3("Source Position", &sourcePosition.x, 0.05f, 0.0f, 0.0f, "%.2f");
        params.source->sourcePosition = sourcePosition;

        if (gasType == gaden::GasType::unknown)
        {
            ImGui::ScopedStyle bgstyle(ImGuiCol_FrameBg, Colors::RequiredField);
            ImGui::Combo("Gas Type", (int*)&gasType, ConcatenatedGasTypes().c_str());
        }
        else
            ImGui::Combo("Gas Type", (int*)&gasType, ConcatenatedGasTypes().c_str());
        params.source->gasType = gasType;

        ImGui::VerticalSpace(10);

        // clang-format off
            ImGui::InputFloat("Delta Time",             &params.deltaTime); 
            ImGui::InputFloat("Wind iteration deltaT",  &params.windIterationDeltaTime); 
            ImGui::InputFloat("Temperature (K)",        &params.temperature);                       
            ImGui::InputFloat("Pressure (atm)",         &params.pressure);                             
            ImGui::InputFloat("Filament_ppm_center",    &params.filamentPPMcenter_initial);       
            ImGui::InputFloat("Filament_initial_sigma", &params.filamentInitialSigma); 
            ImGui::InputFloat("Filament_growth_gamma",  &params.filamentGrowthGamma);   
            ImGui::InputFloat("Filament_noise_std",     &params.filamentNoise_std);                          
            ImGui::InputFloat("Filaments/sec",          &params.numFilaments_sec);
            
            ImGui::VerticalSpace(10);
            if(allowWindLoop)
            {
                if(!params.windLoop)
                    params.windLoop = gaden::LoopConfig{};
                ImGui::Checkbox("Loop wind", &params.windLoop->loop);
                ImGui::BeginDisabled(!params.windLoop->loop);
                ImGui::InputScalar("Loop from", ImGuiDataType_U64, &params.windLoop->from, NULL);
                ImGui::InputScalar("Loop to", ImGuiDataType_U64, &params.windLoop->to, NULL);
                ImGui::EndDisabled();
            }
            
            ImGui::Checkbox("Save results", &params.saveResults);
            ImGui::InputFloat("Save deltaT",    &params.saveDeltaTime);
            ImGui::Checkbox("Pre-calculate concentration", &params.preCalculateConcentrations);
            ImGui::SameLine();
            ImGui::HelpMarker("This will make the simulation really slow! Don't use it unless you know you need it.");

            ImGui::ColorEdit4("Gas display color", &displayColor.r, ImGuiColorEditFlags_::ImGuiColorEditFlags_Float);

        // clang-format on
    }

    void DrawSource()
    {
        if (Is<gaden::PointSource>(params.source))
            g_app->vizScene->DrawSphere(params.source->sourcePosition, 0.1f, displayColor);
        else if (Is<gaden::SphereSource>(params.source))
            g_app->vizScene->DrawSphere(params.source->sourcePosition, As<gaden::SphereSource>(params.source)->radius, displayColor);
        else if (Is<gaden::BoxSource>(params.source))
            g_app->vizScene->DrawCube(params.source->sourcePosition, As<gaden::BoxSource>(params.source)->size, displayColor);
        else if (Is<gaden::LineSource>(params.source))
            g_app->vizScene->DrawLine(params.source->sourcePosition, As<gaden::LineSource>(params.source)->lineEnd, 0.02f, displayColor);
        else if (Is<gaden::CylinderSource>(params.source))
            g_app->vizScene->DrawCylinder(params.source->sourcePosition,
                                          As<gaden::CylinderSource>(params.source)->radius,
                                          As<gaden::CylinderSource>(params.source)->height,
                                          displayColor);
    }

    void Save()
    {
        params.WriteToYAML(configMetadata.GetSimulationFilePath(name));
    }

private:
    void CreateSource()
    {
        if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "point")
        {
            if (!Is<gaden::PointSource>(params.source))
                params.source = std::make_shared<gaden::PointSource>();
        }
        else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "sphere")
        {
            if (!Is<gaden::SphereSource>(params.source))
                params.source = std::make_shared<gaden::SphereSource>();
        }
        else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "box")
        {
            if (!Is<gaden::BoxSource>(params.source))
                params.source = std::make_shared<gaden::BoxSource>();
        }
        else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "line")
        {
            if (!Is<gaden::LineSource>(params.source))
                params.source = std::make_shared<gaden::LineSource>();
        }
        else if (gaden::GasSource::sourceTypeNames.at(sourceTypeSelected) == "cylinder")
        {
            if (!Is<gaden::CylinderSource>(params.source))
                params.source = std::make_shared<gaden::CylinderSource>();
        }
    }

    std::string ConcatenatedNames()
    {
        std::string s = "";
        for (size_t i = 0; i < gaden::GasSource::sourceTypeNames.size(); i++)
            s += gaden::GasSource::sourceTypeNames.at(i) + '\0';
        return s;
    }

    std::string ConcatenatedGasTypes()
    {
        std::string s = "";
        for (size_t i = 0; i < 14; i++)
            s += gaden::to_string(gaden::GasType(i)) + '\0';
        return s;
    }
};