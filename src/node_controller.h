#pragma once
#include <stdint.h>
#include "led_guidance.h"
#include "radio.h"
#include "topology.h"

enum class NodeMode {
    STARTUP,
    NORMAL,
    ALARM,
    EVACUATION,
    ERROR
};

class NodeController {
public:
    void setRadio(IRadio *r) { radio = r; }     // utan radio fungerar noden lokalt (simulering via Serial)
    void begin(uint8_t nodeId);
    void update();
    void setMode(NodeMode newMode);
    NodeMode getMode() const;
    const char* modeToString(NodeMode mode) const;

    void onButtonPressed();                      // larma eller stäng av eget larm (public för test)
    LedSignal signal() const { return ledGuidance.current(); }
    uint32_t alarms() const { return alarmMask; }

private:
    NodeMode currentMode = NodeMode::STARTUP;
    LedGuidance ledGuidance;
    IRadio *radio = nullptr;

    // Utrymningsvägar
    int      selfIdx = -1;               // index i topologin, -1 = nodens ID finns inte i topology.json
    uint32_t alarmMask = 0;              // bit k = nod med index k larmar
    uint32_t alarmUntil[TOPO_N] = {0};   // när larmet från nod k löper ut (millis)

    // Eget larm
    enum class Own { NONE, ALARMING, CANCELING };
    Own      own = Own::NONE;
    uint32_t lastAnnounce = 0;
    uint32_t lastToggle = 0;
    int      cancelToggles = 0;
    bool     xOn = false;
    uint32_t cancelResendAt = 0;
    bool     cancelResendPending = false;

    // Knapp
    bool     lastRaw = true;
    bool     stable = true;
    uint32_t changedAt = 0;

    // Serial-kommandon
    char     capCmd = 0;
    uint32_t capValue = 0;
    bool     capHasDigit = false;
    uint32_t capLastMs = 0;

    void setAlarm(int idx, bool on, uint32_t now);
    void applyRoute();
    void show(LedSignal sig);
    void printHello();
    void handleRadio(uint32_t now);
    void expireAlarms(uint32_t now);
    void updateOwn(uint32_t now);
    void finishCapture();
    void printStatus();
    void handleChar(char c);
};
