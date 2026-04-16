#pragma once

class Mode
{
public:
    virtual void OnPush() = 0;
    virtual void OnPop() = 0;
    virtual void OnGainFocus() = 0;
    virtual void OnLoseFocus() = 0;
    virtual void OnGUI() = 0;
};