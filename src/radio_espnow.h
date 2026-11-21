#pragma once
#ifdef ARDUINO
#include "radio.h"

class EspNowRadio : public IRadio {
public:
    EspNowRadio();
    // channel: Wi-Fi-kanal 1-13, samma på alla noder. groupKey: 16 byte.
    bool begin(uint8_t channel, const uint8_t *groupKey);

    void sendAlert(uint8_t sender) override;
    void sendCancel(uint8_t sender) override;
    bool poll(RadioMsg &out) override;

    void handleReceive(const uint8_t *data, int len);   // anropas från ESP-NOW-callbacken

private:
    AlarmCodec codec;
    void sendCommand(uint8_t command, uint8_t sender);
};
#endif
