#include "gaden/EnvironmentConfiguration.hpp"
#include <gaden/internal/PathUtils.hpp>
#include <algorithm>

namespace gaden
{
    std::shared_ptr<EnvironmentConfiguration> EnvironmentConfiguration::ReadDirectory(const std::filesystem::path& directory)
    {
        if (!std::filesystem::is_directory(directory))
        {
            GADEN_ERROR("Path '{}' is not a directory.", directory.c_str());
            return nullptr;
        }
        auto config = std::make_shared<EnvironmentConfiguration>();

        std::filesystem::path envPath = directory / "OccupancyGrid3D.csv";
        if (config->environment.ReadFromFile(envPath) == ReadResult::NO_FILE)
        {
            GADEN_INFO("Could not read environment file '{}'. Preprocessing is needed.", envPath.c_str());
            return nullptr;
        }

        std::vector<std::filesystem::path> windFiles = paths::GetAllFilesInDirectory(directory / "wind");
        // 只保留常规文件：避免目录项、断掉的符号链接等导致 parseFile → NO_FILE
        windFiles.erase(
            std::remove_if(
                windFiles.begin(),
                windFiles.end(),
                [](std::filesystem::path const& p)
                {
                    std::error_code ec;
                    return !std::filesystem::is_regular_file(p, ec);
                }),
            windFiles.end());
        if (windFiles.empty())
            GADEN_WARN("No wind files in directory '{}'", directory.c_str());

        config->windSequence.Initialize(windFiles, config->environment.numCells(), {}); // defaults to no looping

        config->localAirflowDisturbances.resize(config->environment.numCells(), {0, 0, 0});
        
        return config;
    }

    bool EnvironmentConfiguration::WriteToDirectory(const std::filesystem::path& path)
    {
        try
        {
            if (!std::filesystem::exists(path))
            {
                GADEN_INFO("Output directory '{}' does not exist. Trying to create it.", path.c_str());
                if (!std::filesystem::create_directories(path))
                {
                    GADEN_ERROR("Failed to create output directory!");
                    return false;
                }
            }

            if (!environment.WriteToFile(path / "OccupancyGrid3D.csv"))
                return false;

            // 先清空 wind/：colcon symlink-install 可能留下指向 src 的断链，ofstream 无法得到真实 wind_iteration_* 文件
            if (std::filesystem::exists(path / "wind"))
                std::filesystem::remove_all(path / "wind");
            std::filesystem::create_directories(path / "wind");
            if (!windSequence.WriteToFiles(path / "wind", "wind_iteration"))
                return false;

            GADEN_INFO("Wrote environment configuration to '{}'", path.c_str());
            return true;
        }
        catch (std::exception const& e)
        {
            GADEN_ERROR("Error when trying to write environment configuration to '{}'", path);
            return false;
        }
    }
} // namespace gaden
