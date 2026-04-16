#include "Application.hpp"

int main(int argc, char** argv)
{
    g_app = std::make_unique<Application>();
    g_app->Run();
}