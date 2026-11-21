#include <Arduino.h>
#include "led_guidance.h"

// ---- Pinnar (ändra här om du kopplar om) ------------------------------
// Varje lampa: GPIO -> 220-330 ohm -> LED (långa benet) -> LED (korta benet) -> GND
static const uint8_t PIN_X     = 2;    // röd  = X-lampan
static const uint8_t PIN_LEFT  = 23;   // grön = vänsterpil
static const uint8_t PIN_RIGHT = 22;   // gul  = högerpil
// -----------------------------------------------------------------------

static void allOff() {
    digitalWrite(PIN_X, LOW);
    digitalWrite(PIN_LEFT, LOW);
    digitalWrite(PIN_RIGHT, LOW);
}

void LedGuidance::begin() {
    pinMode(PIN_X, OUTPUT);
    pinMode(PIN_LEFT, OUTPUT);
    pinMode(PIN_RIGHT, OUTPUT);
    allOff();
    Serial.println("LED Guidance startad");
}

void LedGuidance::setSignal(LedSignal signal) {
    allOff();   // en signal i taget
    last = signal;

    switch (signal) {
        case LedSignal::CROSS:
            digitalWrite(PIN_X, HIGH);
            Serial.println("X-lampan tand");
            break;

        case LedSignal::LEFT:
            digitalWrite(PIN_LEFT, HIGH);
            Serial.println("Vansterpil tand");
            break;

        case LedSignal::RIGHT:
            digitalWrite(PIN_RIGHT, HIGH);
            Serial.println("Hogerpil tand");
            break;

        case LedSignal::OFF:
        default:
            Serial.println("Alla lampor slackta");
            break;
    }
}
