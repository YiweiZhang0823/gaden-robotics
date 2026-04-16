#include "Application.hpp"
#include "Modes/DefaultMode.hpp"
#include "imgui_gl/fonts.hpp"
#include "imgui_gl/imgui_gl.h"
#include <gaden/internal/Time.hpp>

void Application::Run()
{
    ImguiGL imgui;
    imgui.Setup(nullptr,
                "Gaden",
                900,
                930,
                imgui.FlagsFixedLayout() | ImGuiConfigFlags_ViewportsEnable); // enable multi-viewports so we can render the geometry on a popup window!

    vizScene = std::make_unique<Scene>();
    // load fonts
    {
        // avoid an invalid free() on shutdown
        ImFontConfig* cfg = new ImFontConfig();
        cfg->FontDataOwnedByAtlas = false;

        Fonts::body = ImGui::GetIO().Fonts->AddFontFromMemoryTTF((void*)ImGui::Fonts::Roboto_Variable, ImGui::Fonts::Roboto_Variable_size, 18.f, cfg);
        Fonts::header = ImGui::GetIO().Fonts->AddFontFromMemoryTTF((void*)ImGui::Fonts::Roboto_Variable, ImGui::Fonts::Roboto_Variable_size, 16.f, cfg);
        Fonts::logo = ImGui::GetIO().Fonts->AddFontFromMemoryTTF((void*)ImGui::Fonts::Revalia_Regular, ImGui::Fonts::Revalia_Regular_size, 125.f, cfg);
        ImGui::GetIO().Fonts->Build();
    }

    auto defaultMode = std::make_shared<DefaultMode>();
    PushMode(defaultMode);

    gaden::Utils::Time::Clock clock;
    gaden::Utils::Time::TimePoint lastIteration = clock.now();
    gaden::Utils::Time::Rate rate(60);
    while (!shouldClose && !imgui.ShouldClose())
    {
        // calculate deltaTime
        deltaT = gaden::Utils::Time::toSeconds(clock.now() - lastIteration);
        lastIteration = clock.now();

        // start the frame
        imgui.StartFrame();

        // render the main window
        ImGui::PushFont(Fonts::body, 0.f);
        imgui.SetNextWindowFullscreen();
        ImGui::PushStyleColor(ImGuiCol_WindowBg, Colors::Background);
        ImGui::Begin("Main", NULL, imgui.FlagsFixedLayout() | ImGuiWindowFlags_NoTitleBar);
        {
            DrawHeader();
            ImGui::VerticalSpace(10.f);
            modeStack.top()->OnGUI();
            
            // render the scene visualization (if it is currently active)
            vizScene->Render();
        }
        ImGui::End();
        ImGui::PopStyleColor();
        ImGui::PopFont();


        // finalize the frame
        imgui.Render();
        rate.sleep();
    }

    imgui.Close();
}

void Application::PushMode(std::shared_ptr<Mode> mode)
{
    if (!modeStack.empty())
        modeStack.top()->OnLoseFocus();

    modeStack.push(mode);

    modeStack.top()->OnPush();
    modeStack.top()->OnGainFocus();
}

void Application::PopMode()
{
    modeStack.top()->OnLoseFocus();
    modeStack.top()->OnPop();

    modeStack.pop();

    if (!modeStack.empty())
        modeStack.top()->OnGainFocus();
}

std::shared_ptr<Mode> Application::GetCurrentMode()
{
    return modeStack.top();
}

void Application::DrawHeader()
{
    ImGui::PushFont(Fonts::header, 0.f);
    ImGui::PushStyleColor(ImGuiCol_ChildBg, Colors::Header);
    DrawInChildSpanHorizontal("header",
                              {
                                  ImGui::VerticalSpace(10.f);
                                  ImGui::HorizontalSpace(10.f);
                                  ImGui::Text("%s", fmt::format("GadenGUI v{}.{}", 0, 1).c_str());
                                  ImGui::HorizontalSpace(10.f);
                                  ImGui::Text("%s", fmt::format("Gaden v{}.{}", gaden::versionMajor, gaden::versionMinor).c_str());
                                  ImGui::VerticalSpace(10.f);
                              });
    ImGui::PopStyleColor();
    ImGui::PopFont();
}