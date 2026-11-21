#pragma once
#include <stdint.h>
#include "protocol.h"

// Gränssnitt mot radion. NodeController känner bara till det här, så samma logik kan testas
// på en dator med en låtsasradio (host_test/) och köras på ESP32 med ESP-NOW (radio_espnow.*).
class IRadio {
public:
    virtual ~IRadio() {}
    virtual void sendAlert(uint8_t sender) = 0;     // broadcast "jag larmar"
    virtual void sendCancel(uint8_t sender) = 0;    // broadcast "jag stänger av mitt larm"
    virtual bool poll(RadioMsg &out) = 0;           // nästa godkända meddelande, false = inga fler
};
