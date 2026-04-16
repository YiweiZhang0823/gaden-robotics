#pragma once
#include "imgui.h"
#include "misc/cpp/imgui_stdlib.h"
#include <cstdint>
#include <string>

namespace Colors
{
    constexpr uint32_t Back = 0xff828078;
    constexpr uint32_t Secondary = 0xff7f6352;

    constexpr uint32_t CreateNew = 0xff8e5b52;
    constexpr uint32_t Save = 0xff7b7c17;

    constexpr uint32_t Background = 0xff33281f;
    constexpr uint32_t Header = 0xff724427;

    constexpr uint32_t InfoText = 0xffbedb1a;
    constexpr uint32_t ErrorText = 0xff2e48c9;

    constexpr uint32_t RequiredField = 0xff2e4899;

    inline ImVec4 AsVec(uint32_t hex)
    {
        ImVec4 vec;
        vec.w = (hex >> 24 & 0xff) / 255.f;
        vec.z = (hex >> 16 & 0xff) / 255.f;
        vec.y = (hex >> 8 & 0xff) / 255.f;
        vec.x = (hex >> 0 & 0xff) / 255.f;
        return vec;
    }
} // namespace Colors

namespace Fonts
{
    inline ImFont* body;
    inline ImFont* header;

    inline ImFont* logo;
} // namespace Fonts

namespace ImGui
{
    class ScopedStyle
    {
    public:
        ScopedStyle(ImGuiCol_ key, ImU32 color)
        {
            type = Color;
            ImGui::PushStyleColor(key, color);
        }

        ScopedStyle(ImGuiStyleVar_ key, ImU32 color)
        {
            type = Color;
            ImGui::PushStyleVar(key, color);
        }

        ~ScopedStyle()
        {
            if (type == Color)
                ImGui::PopStyleColor();
            else if (type == Var)
                ImGui::PopStyleVar();
            else
                fprintf(stderr, "Incorrect ScopedStyle type!");
        }

    private:
        enum Type
        {
            None,
            Color,
            Var
        };
        Type type;
    };

    inline void TextCenteredOnLine(const char* label, float alignment = 0.5f)
    {
        ImGuiStyle& style = ImGui::GetStyle();

        float size = ImGui::CalcTextSize(label).x + style.FramePadding.x * 2.0f;
        float avail = ImGui::GetContentRegionAvail().x;

        float off = (avail - size) * alignment;
        if (off > 0.0f)
            ImGui::SetCursorPosX(ImGui::GetCursorPosX() + off);

        ImGui::Text("%s", label);
    }

    inline bool ButtonCenteredOnLine(const char* label, float alignment = 0.5f)
    {
        ImGuiStyle& style = ImGui::GetStyle();

        float size = ImGui::CalcTextSize(label).x + style.FramePadding.x * 2.0f;
        float avail = ImGui::GetContentRegionAvail().x;

        float off = (avail - size) * alignment;
        if (off > 0.0f)
            ImGui::SetCursorPosX(ImGui::GetCursorPosX() + off);

        return ImGui::Button(label);
    }

    inline void HorizontalSpace(float space)
    {
        ImGui::Dummy(ImVec2(space, 0.f));
        ImGui::SameLine();
    }

    inline void VerticalSpace(float space)
    {
        ImGui::Dummy(ImVec2(0.f, space));
    }

    // set viewport to prevent the tooltip from becoming its own window
    inline void HelpMarker(const char* desc, float hsize = 35.f, bool canLeaveViewport = false)
    {
        ImGui::TextDisabled("(?)");
        if (IsItemHovered(ImGuiHoveredFlags_ForTooltip))
        {
            if (!canLeaveViewport)
                ImGui::SetNextWindowViewport(ImGui::GetWindowViewport()->ID);
            ImGui::BeginItemTooltip();
            ImGui::PushTextWrapPos(ImGui::GetFontSize() * hsize);
            ImGui::TextUnformatted(desc);
            ImGui::PopTextWrapPos();
            ImGui::EndTooltip();
        }
    }

    inline void TextInputRequired(const char* label, std::string* text)
    {
        if (text->empty())
        {
            ScopedStyle bgstyle(ImGuiCol_FrameBg, Colors::RequiredField);
            ScopedStyle textstyle(ImGuiCol_TextDisabled, 0xccffffff);
            ImGui::InputTextWithHint(label, "Required!", text);
        }
        else
            ImGui::InputText(label, text);
    }

#define CalculateSize(result, ...)                                                              \
    {                                                                                           \
        ImGui::BeginDisabled(true);                                                             \
        ImVec2 cursorPos = ImGui::GetCursorPos();                                               \
        float alpha = ImGui::GetStyle().Alpha;                                                  \
                                                                                                \
        /*draw everything with 0 alpha to calculate the size that the child frame should have*/ \
        ImGui::GetStyle().Alpha = 0;                                                            \
        ImGui::BeginGroup();                                                                    \
        __VA_ARGS__;                                                                            \
        ImGui::EndGroup();                                                                      \
        result = ImGui::GetItemRectSize();                                                      \
        ImGui::GetStyle().Alpha = alpha;                                                        \
        ImGui::SetCursorPos(cursorPos);                                                         \
        ImGui::EndDisabled();                                                                   \
    }

#define DrawInChild(childID, ...)           \
    {                                       \
        ImVec2 offset;                      \
        CalculateSize(offset, __VA_ARGS__); \
                                            \
        /*actually draw the stuff*/         \
        ImGui::BeginChild(childID, offset); \
        __VA_ARGS__;                        \
        ImGui::EndChild();                  \
    }

#define DrawInChildSpanHorizontal(childID, ...)          \
    {                                                    \
        ImVec2 offset;                                   \
        CalculateSize(offset, __VA_ARGS__);              \
        float height = offset.y;                         \
                                                         \
        /*actually draw the stuff*/                      \
        ImGui::BeginChild(childID, ImVec2(0.f, height)); \
        __VA_ARGS__;                                     \
        ImGui::EndChild();                               \
    }

} // namespace ImGui