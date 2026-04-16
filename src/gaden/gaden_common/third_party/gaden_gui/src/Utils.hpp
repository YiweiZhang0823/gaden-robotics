#pragma once
#include <cstdio>
#include <filesystem>
#include <fmt/format.h>
#include <gaden/internal/PathUtils.hpp>
#include <vector>

namespace Utils
{
    namespace internal
    {
        inline std::string Zenity(const char* command)
        {
            char buffer[1024];
            buffer[0] = '\0'; // in case zenity returns nothing at all (canceled interaction)

            FILE* f = popen(command, "r");
            char* b = fgets(buffer, 1024, f); // gcc complains about unused result here

            // zenity returns a newline character at the end!
            std::string response(buffer);
            if (!response.empty())
                response.erase(response.end() - 1);
            return response;
        }

    } // namespace internal
    inline std::filesystem::path FileDialog(const char* filter = "Any files | *", std::filesystem::path const& startingDirectory = "")
    {
        std::string command = fmt::format("zenity --file-selection --file-filter=\"{}\" --filename=\"{}\"", filter, startingDirectory);
        return std::filesystem::path(internal::Zenity(command.c_str()));
    }

    inline std::vector<std::filesystem::path> MultiFileDialog(const char* filter = "Any files | *", std::filesystem::path const& startingDirectory = "")
    {
        std::string command = fmt::format("zenity --file-selection --file-filter=\"{}\" --multiple --separator=\";\" --filename=\"{}\"", filter, startingDirectory);
        std::string result = internal::Zenity(command.c_str());

        // split by ';'
        std::vector<std::filesystem::path> paths;
        while (!result.empty())
        {
            size_t posDelim = result.find(';');
            if (posDelim != std::string::npos)
            {
                paths.emplace_back(result.substr(0, posDelim));
                result.erase(0, posDelim + 1);
            }
            else
            {
                paths.emplace_back(result);
                break;
            }
        }

        return paths;
    }

    inline std::filesystem::path DirectoryDialog(std::filesystem::path const& startingDirectory = "")
    {
        std::string command = fmt::format("zenity --file-selection --directory --filename=\"{}\"", startingDirectory);
        return std::filesystem::path(internal::Zenity(command.c_str()));
    }

    inline std::string TextInput(std::string_view title, std::string_view prompt)
    {
        std::string command = fmt::format("zenity --entry --title=\"{}\" --text=\"{}\"", title, prompt);
        return internal::Zenity(command.c_str());
    }

    inline void DisplayError(std::string_view msg)
    {
        std::string command = fmt::format("zenity --error --title=\"Error!\" --text=\"{}\"", msg.data());
        internal::Zenity(command.c_str());
    }

    inline void DisplayInfo(std::string_view msg)
    {
        std::string command = fmt::format("zenity --info --title=\"Info\" --text=\"{}\"", msg.data());
        internal::Zenity(command.c_str());
    }

    inline void DisplayWarn(std::string_view msg)
    {
        std::string command = fmt::format("zenity --warning --title=\"Warning!\" --text=\"{}\"", msg.data());
        internal::Zenity(command.c_str());
    }

} // namespace Utils