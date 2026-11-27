
#pragma once

#include <stdint.h>

class PeopleCounter {
public:
    explicit PeopleCounter(uint32_t timeoutMs = 3000);

    // true = laser beam is blocked
    void update(bool beam1Blocked, bool beam2Blocked, uint32_t nowMs);

    uint32_t getTotalEntered() const;
    uint32_t getTotalExited() const;
    int32_t getCurrentOccupancy() const;

    void reset();

private:
    enum class State {
        IDLE,
        FIRST_1,
        FIRST_2,
        WAIT_2,
        WAIT_1,
        BOTH_FROM_1,
        BOTH_FROM_2,
        LAST_2,
        LAST_1,
        INVALID
    };

    State state = State::IDLE;

    uint32_t totalEntered = 0;
    uint32_t totalExited = 0;
    int32_t currentOccupancy = 0;

    uint32_t crossingStartedAt = 0;
    uint32_t timeoutMs;

    void setState(State newState);
    void registerEntry();
    void registerExit();
};
