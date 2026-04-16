#pragma once
#include "Application.hpp"
#include "Mode.hpp"
#include "Visualization/Scene.hpp"
#include "gaden/EnvironmentConfigMetadata.hpp"

class ConfigurationMode : public Mode
{
public:
    ConfigurationMode(gaden::EnvironmentConfigMetadata& metadata)
        : configMetadata(metadata)
    {
        config = gaden::EnvironmentConfiguration::ReadDirectory(configMetadata.rootDirectory);
    }

    void OnPush() override
    {
    }

    void OnPop() override
    {}

    void OnGainFocus() override
    {}

    void OnLoseFocus() override
    {
        g_app->vizScene->active = false;
    }

    void OnGUI() override;

    void CreateScene();

private:
    void ModelsList(std::vector<gaden::Model3D>& models, const char* label);

public:
    gaden::EnvironmentConfigMetadata& configMetadata;
    std::shared_ptr<gaden::EnvironmentConfiguration> config;
};