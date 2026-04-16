#include "Project.hpp"
#include "gaden/internal/PathUtils.hpp"
#include "yaml-cpp/yaml.h"
#include <fstream>

Project::Project()
{
}

std::shared_ptr<Project> Project::CreateNew(std::filesystem::path const& directory)
{
    auto project = std::shared_ptr<Project>(new Project); // make_shared fails with a private constructor
    project->rootDirectory = directory;
    if (!project->CreateTemplate())
        return nullptr;
    if (!project->ReadDirectory())
        return nullptr;
    return project;
}

std::shared_ptr<Project> Project::LoadExisting(std::filesystem::path const& projectFilePath)
{
    auto project = std::shared_ptr<Project>(new Project); // make_shared fails with a private constructor
    try
    {
        project->rootDirectory = projectFilePath.parent_path();
        YAML::Node yaml = YAML::LoadFile(projectFilePath);
        int versionMajor = yaml["versionMajor"].as<int>();
        int versionMinor = yaml["versionMinor"].as<int>();
        project->configsDir = yaml["configurationsDirectory"].as<std::string>();

        if (!project->ReadDirectory())
            return nullptr;
    }
    catch (std::exception const& e)
    {
        GADEN_ERROR("Caught exception while parsing project yaml '{}':\n\t{}", projectFilePath, e.what());
        return nullptr;
    }
    return project;
}

bool Project::ReadDirectory()
{
    try
    {
        std::filesystem::path configurationsDir = rootDirectory / configsDir;
        if (!std::filesystem::exists(configurationsDir))
            return false;
        auto subDirs = gaden::paths::GetAllFilesInDirectory(configurationsDir);

        for (auto const& dir : subDirs)
        {
            gaden::EnvironmentConfigMetadata config(dir);
            GADEN_CHECK_RESULT(config.ReadDirectory());
            configurations.insert({config.GetName(), config});
        }
    }
    catch (std::exception const& e)
    {
        GADEN_ERROR("An error ocurred while trying to parse directory '{}':\n\t{}", rootDirectory, e.what());
        return false;
    }
    return true;
}

bool Project::CreateTemplate()
{
    std::filesystem::create_directories(rootDirectory / "wind_simulations");
    std::filesystem::create_directories(rootDirectory / "cad_models");

    std::ofstream projFile(rootDirectory / "gaden.gproj");
    YAML::Emitter emitter(projFile);
    emitter << YAML::BeginMap;

    emitter << YAML::Comment("Gaden Project");
    emitter << YAML::Key << "versionMajor" << YAML::Value << gaden::versionMajor //
            << YAML::Key << "versionMinor" << YAML::Value << gaden::versionMinor;
    emitter << YAML::Key << "configurationsDirectory" << YAML::Value << configsDir;
    emitter << YAML::EndMap;
    projFile.close();

    std::filesystem::remove_all(GetRoot() / configsDir);
    std::filesystem::path configPath = GetConfigurationPath("config1");
    std::filesystem::create_directories(configPath);

    if (!gaden::EnvironmentConfigMetadata::CreateTemplate(configPath))
    {
        GADEN_ERROR("Failed to create sample configuration at '{}'", configPath);
        return false;
    }

    return true;
}
