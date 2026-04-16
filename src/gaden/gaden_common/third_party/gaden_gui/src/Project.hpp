#pragma once
#include <gaden/EnvironmentConfigMetadata.hpp>

class Project
{
public:
    bool ReadDirectory();
    bool CreateTemplate();
    std::filesystem::path GetRoot() { return rootDirectory; }
    std::string GetConfigurationPath(std::string const& name) { return rootDirectory / configsDir / name; }

    static std::shared_ptr<Project> CreateNew(std::filesystem::path const& directory);
    static std::shared_ptr<Project> LoadExisting(std::filesystem::path const& projectFile);

public:
    std::map<std::string, gaden::EnvironmentConfigMetadata> configurations;
    std::string configsDir = "environment_configurations";

private:
    Project();
    std::filesystem::path rootDirectory;
};