#pragma once

enum class LedSignal {
    OFF,
    CROSS,   // röd X-lampa
    LEFT,    // vänsterpil
    RIGHT    // högerpil
};

class LedGuidance {
public:
    void begin();
    void setSignal(LedSignal signal);
    LedSignal current() const { return last; }   // senast tända signal (för test)
private:
    LedSignal last = LedSignal::OFF;
};
