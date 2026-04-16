#include "RunSimMode.hpp"
#include "ImGuiUtils.hpp"

void RunSimMode::DrawTimeControlsGUI(float deltaTime)
{
    ImGui::BeginDisabled(runSimThread.has_value());
    {
        ImGui::VerticalSpace(10);
        ImGui::InputFloat("Simulation Duration", &simDuration);
        ImGui::Checkbox("Limit simulation rate", &isRateLimited);
        ImGui::SameLine();
        ImGui::HelpMarker("Make the simulation run slower for easier visualization");
        ImGui::BeginDisabled(!isRateLimited);
        {
            ImGui::InputFloat("Simulation rate", &rateLimit);
            ImGui::SameLine();
            if (ImGui::Button("Match deltaT"))
                rateLimit = 1.f / deltaTime;
        }
        ImGui::EndDisabled();
    }
    ImGui::EndDisabled();

    ImGui::VerticalSpace(10);
}

void RunSimMode::DrawSimulationStateGUI()
{
    if (runSimThread)
    {
        ImVec4 color = Colors::AsVec(Colors::InfoText);
        ImGui::TextColored(color, "Simulation running...");
        ImGui::TextColored(color, "Progress: %.2f/%.2fs", (float)currentSimTime, simDuration);
        if (simDone)
        {
            runSimThread->join();
            runSimThread = std::nullopt;
        }
    }
    else if (!configMode.config)
    {
        ImGui::VerticalSpace(ImGui::GetTextLineHeight());
        ImGui::TextColored(Colors::AsVec(Colors::ErrorText), "Need to run preprocessing before simulations!");
    }
    else
    {
        // keep the same spacing
        ImGui::VerticalSpace(ImGui::GetTextLineHeight());
        ImGui::TextColored(Colors::AsVec(Colors::InfoText), "Ready for simulation");
    }
}

void RunSimMode::DrawButtonsGUI()
{
    ImGui::BeginDisabled(runSimThread.has_value());
    {
        ImGui::PushStyleColor(ImGuiCol_Button, Colors::Save);
        {
            // Run
            //------------------------
            ImGui::BeginDisabled(!configMode.config); // need a valid environment configuration to run the simulation
            if (ImGui::Button("Run Simulation"))
            {
                simDone = false;
                if (runSimThread)
                    runSimThread->join();

                runSimThread.emplace(std::bind(&RunSimMode::Run, this));
            }
            ImGui::EndDisabled();
        }
        ImGui::PopStyleColor();
    }
    ImGui::EndDisabled();

    // stop button
    //----------------
    ImGui::BeginDisabled(!runSimThread.has_value());
    {
        ImGui::PushStyleColor(ImGuiCol_Button, Colors::Back);
        ImGui::SameLine();
        if (ImGui::Button("Stop Simulation"))
            canRun = false;
        ImGui::PopStyleColor();
    }
    ImGui::EndDisabled();

    // Open view button
    //----------------
    {
        ImGui::PushStyleColor(ImGuiCol_Button, Colors::Save);
        ImGui::SameLine();
        if (ImGui::Button("Toggle Scene View"))
            ToggleSceneView();
        ImGui::SameLine();
        ImGui::HelpMarker("Open a view of the scene where you can see the filaments moving.\nThis has a performance impact on the simulation.");
        ImGui::PopStyleColor();
    }

    // Back
    //------------------------
    ImGui::BeginDisabled(runSimThread.has_value());
    {
        ImGui::PushStyleColor(ImGuiCol_Button, Colors::Back);
        {
            if (ImGui::Button("Back"))
                g_app->PopMode();
            ImGui::PopStyleColor();
        }
    }
    ImGui::EndDisabled();
}
