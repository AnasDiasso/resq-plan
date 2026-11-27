
#include "people_counter.h"

PeopleCounter::PeopleCounter(uint32_t timeoutMs)
    : timeoutMs(timeoutMs) {
}

void PeopleCounter::setState(State newState) {
    state = newState;
}

void PeopleCounter::registerEntry() {
    totalEntered++;
    currentOccupancy++;
}

void PeopleCounter::registerExit() {
    totalExited++;

    if (currentOccupancy > 0) {
        currentOccupancy--;
    }
}

void PeopleCounter::update(bool beam1Blocked,
                           bool beam2Blocked,
                           uint32_t nowMs) {

    bool clear = !beam1Blocked && !beam2Blocked;
    bool both = beam1Blocked && beam2Blocked;

    // A crossing must finish within the timeout.
    if (state != State::IDLE &&
        state != State::INVALID &&
        (uint32_t)(nowMs - crossingStartedAt) > timeoutMs) {
        setState(State::INVALID);
    }

    switch (state) {

        case State::IDLE:
            if (beam1Blocked && !beam2Blocked) {
                crossingStartedAt = nowMs;
                setState(State::FIRST_1);
            }
            else if (beam2Blocked && !beam1Blocked) {
                crossingStartedAt = nowMs;
                setState(State::FIRST_2);
            }
            else if (both) {
                setState(State::INVALID);
            }
            break;

        case State::FIRST_1:
            if (both) {
                setState(State::BOTH_FROM_1);
            }
            else if (!beam1Blocked && beam2Blocked) {
                setState(State::LAST_2);
            }
            else if (clear) {
                setState(State::WAIT_2);
            }
            break;

        case State::FIRST_2:
            if (both) {
                setState(State::BOTH_FROM_2);
            }
            else if (beam1Blocked && !beam2Blocked) {
                setState(State::LAST_1);
            }
            else if (clear) {
                setState(State::WAIT_1);
            }
            break;

        case State::WAIT_2:
            if (beam2Blocked && !beam1Blocked) {
                setState(State::LAST_2);
            }
            else if (beam1Blocked || both) {
                setState(State::INVALID);
            }
            break;

        case State::WAIT_1:
            if (beam1Blocked && !beam2Blocked) {
                setState(State::LAST_1);
            }
            else if (beam2Blocked || both) {
                setState(State::INVALID);
            }
            break;

        case State::BOTH_FROM_1:
            if (!beam1Blocked && beam2Blocked) {
                setState(State::LAST_2);
            }
            else if (!beam2Blocked) {
                setState(State::INVALID);
            }
            break;

        case State::BOTH_FROM_2:
            if (!beam2Blocked && beam1Blocked) {
                setState(State::LAST_1);
            }
            else if (!beam1Blocked) {
                setState(State::INVALID);
            }
            break;

        case State::LAST_2:
            if (clear) {
                registerEntry();
                setState(State::IDLE);
            }
            else if (beam1Blocked) {
                setState(State::INVALID);
            }
            break;

        case State::LAST_1:
            if (clear) {
                registerExit();
                setState(State::IDLE);
            }
            else if (beam2Blocked) {
                setState(State::INVALID);
            }
            break;

        case State::INVALID:
            // Wait for both beams to clear before restarting.
            if (clear) {
                setState(State::IDLE);
            }
            break;
    }
}

uint32_t PeopleCounter::getTotalEntered() const {
    return totalEntered;
}

uint32_t PeopleCounter::getTotalExited() const {
    return totalExited;
}

int32_t PeopleCounter::getCurrentOccupancy() const {
    return currentOccupancy;
}

void PeopleCounter::reset() {
    totalEntered = 0;
    totalExited = 0;
    currentOccupancy = 0;
    state = State::IDLE;
    crossingStartedAt = 0;
}
