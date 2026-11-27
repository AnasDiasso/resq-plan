#include <Arduino.h>
#include "node_controller.h"
#include "led_guidance.h"
#include "route.h"
#include "topology.h"

// Knapp: GPIO4 -> knapp -> GND (intern pull-up, trycket ger LOW) 
static const uint8_t PIN_BUTTON = 4;
static const uint32_t DEBOUNCE_MS = 40;
static const uint32_t CAPTURE_TIMEOUT_MS = 800;       // tid efter sista siffran innan numret räknas

static const uint32_t ALARM_DURATION_MS = 5UL * 60UL * 1000UL;   // larm gäller i 5 minuter
static const uint32_t REANNOUNCE_MS = 10UL * 1000UL;             // larmande nod upprepar larmet var 10:e sekund
static const int      CANCEL_BLINKS = 3;                          // avstängning: X blinkar 3 gånger
static const uint32_t CANCEL_BLINK_MS = 200;                      // ms per tänd/släckt-steg
static const uint32_t CANCEL_RESEND_MS = 2000;                    // avstängningen skickas en gång till

static bool timeReached(uint32_t now, uint32_t target) { return (int32_t)(now - target) >= 0; }

// Maskinläsbara händelser på Serial (läses av sim/server.py):  EVT <NAMN> <nod> [extra]
static void evt(const char *name, int id, const char *extra = nullptr) {
    Serial.print("EVT ");
    Serial.print(name);
    Serial.print(" ");
    Serial.print(id);
    if (extra) {
        Serial.print(" ");
        Serial.print(extra);
    }
    Serial.println();
}

static const char *signalName(LedSignal s) {
    switch (s) {
        case LedSignal::CROSS: return "X";
        case LedSignal::LEFT:  return "LEFT";
        case LedSignal::RIGHT: return "RIGHT";
        default:               return "OFF";
    }
}

void NodeController::begin(uint8_t nodeId) {
    ledGuidance.begin();
    pinMode(PIN_BUTTON, INPUT_PULLUP);
    Serial.println();
    Serial.println("Evakueringsnod startad!");

    selfIdx = topoIndexOfId(nodeId);
    if (selfIdx < 0) {
        Serial.print("VARNING: NODE_ID ");
        Serial.print((int)nodeId);
        Serial.println(" finns inte i topology.json. Pilarna fungerar inte.");
    } else {
        Serial.print("Jag ar nod ");
        Serial.println((int)nodeId);
    }
    if (!radio) Serial.println("OBS: ingen radio, bara lokal simulering");
    evt("HELLO", nodeId);

    setMode(NodeMode::NORMAL);

    Serial.println();
    Serial.println("=== TESTMENY ===");
    Serial.println("0 - STARTUP");
    Serial.println("1 - NORMAL");
    Serial.println("2 - ALARM");
    Serial.println("3 - EVACUATION");
    Serial.println("4 - ERROR");
    Serial.println();
    Serial.println("=== LED TEST ===");
    Serial.println("x = X-lampa");
    Serial.println("r = Hogerpil");
    Serial.println("l = Vansterpil");
    Serial.println("o = Slack alla");
    Serial.println();
    Serial.println("=== UTRYMNINGSVAG ===");
    Serial.println("Knappen = larma fran det har kortet (tryck igen = stang av)");
    Serial.println("a<nr> = simulera larm lokalt fran nod <nr> (skickas inte), t.ex. a9 + Enter");
    Serial.println("c     = rensa alla larm lokalt");
    Serial.println("n<nr> = lat det har kortet vara nod <nr> (test)");
    Serial.println("s     = visa status");
    Serial.println("b     = tryck pa knappen (som den fysiska knappen)");
    Serial.println("d<nr> = ta bort simulerat larm fran nod <nr>");
    Serial.println("h     = skriv identitet och larm (for sim/server.py)");
}

void NodeController::setAlarm(int idx, bool on, uint32_t now) {
    if (idx < 0 || idx >= TOPO_N) return;
    if (on) {
        alarmMask |= (1UL << idx);
        alarmUntil[idx] = now + ALARM_DURATION_MS;
    } else {
        alarmMask &= ~(1UL << idx);
    }
}

void NodeController::show(LedSignal sig) {
    ledGuidance.setSignal(sig);
    if (selfIdx >= 0) evt("SIGNAL", TOPO_ID[selfIdx], signalName(sig));
}

void NodeController::applyRoute() {
    if (selfIdx < 0) return;
    if (own == Own::CANCELING) return;           // X blinkar, rör inte lamporna
    if (alarmMask == 0) {
        show(LedSignal::OFF);
        return;
    }
    RouteResult r = computeRoute((uint8_t)selfIdx, alarmMask);
    if (r.isBlocked) {
        show(LedSignal::CROSS);
    } else if (r.hasRoute) {
        show(r.signal);
        Serial.print("Vag ut: ");
        if (r.nextIdx < 0) {
            Serial.print("ut har");
        } else {
            Serial.print("via nod ");
            Serial.print((int)TOPO_ID[r.nextIdx]);
        }
        Serial.print(", ca ");
        Serial.print((unsigned long)(r.totalDm / 10));
        Serial.print(".");
        Serial.print((unsigned long)(r.totalDm % 10));
        Serial.println(" m");
    } else {
        show(LedSignal::OFF);
        Serial.println("INGEN VAG UT hittad (alla vagar blockerade)");
    }
}

void NodeController::printHello() {
    int id = selfIdx >= 0 ? (int)TOPO_ID[selfIdx] : 0;
    evt("HELLO", id);
    Serial.print("EVT STATE ");
    Serial.print(id);
    Serial.print(" ");
    bool any = false;
    for (int k = 0; k < TOPO_N; k++) {
        if ((alarmMask >> k) & 1UL) {
            if (any) Serial.print(",");
            Serial.print((int)TOPO_ID[k]);
            any = true;
        }
    }
    if (!any) Serial.print("-");
    Serial.println();
}

void NodeController::printStatus() {
    Serial.print("Nod ");
    Serial.print((int)(selfIdx >= 0 ? TOPO_ID[selfIdx] : 0));
    Serial.print(", larmande noder:");
    bool any = false;
    for (int k = 0; k < TOPO_N; k++) {
        if ((alarmMask >> k) & 1UL) {
            Serial.print(" ");
            Serial.print((int)TOPO_ID[k]);
            any = true;
        }
    }
    if (!any) Serial.print(" inga");
    Serial.println();
}

// ---- Eget larm ------------------------------------------------------------

void NodeController::onButtonPressed() {
    uint32_t now = millis();
    if (selfIdx < 0) {
        ledGuidance.setSignal(LedSignal::CROSS);
        return;
    }
    if (own == Own::NONE) {
        own = Own::ALARMING;
        setAlarm(selfIdx, true, now);
        lastAnnounce = now;
        Serial.println("Knapp tryckt: larmar");
        evt("ALARM_ON", TOPO_ID[selfIdx], "own");
        applyRoute();                                       // X tänds direkt
        if (radio) radio->sendAlert(TOPO_ID[selfIdx]);
    } else if (own == Own::ALARMING) {
        own = Own::CANCELING;                               // samma knapp igen: stäng av larmet
        cancelToggles = 0;
        xOn = false;
        lastToggle = now;
        ledGuidance.setSignal(LedSignal::OFF);
        Serial.println("Avstangning: X blinkar 3 ganger, sedan slacks larmet pa alla");
        evt("CANCEL_START", TOPO_ID[selfIdx]);
    }
}

void NodeController::updateOwn(uint32_t now) {
    if (own == Own::ALARMING) {
        if (timeReached(now, alarmUntil[selfIdx])) {        // 5 minuter slut
            own = Own::NONE;
            setAlarm(selfIdx, false, now);
            Serial.println("5 minuter har gatt, eget larm slut");
            evt("ALARM_OFF", TOPO_ID[selfIdx], "expire");
            applyRoute();
        } else if (timeReached(now, lastAnnounce + REANNOUNCE_MS)) {
            lastAnnounce = now;                             // ny signal så att alla noder säkert får larmet
            if (radio) radio->sendAlert(TOPO_ID[selfIdx]);
        }
    } else if (own == Own::CANCELING) {
        if (timeReached(now, lastToggle + CANCEL_BLINK_MS)) {
            lastToggle = now;
            xOn = !xOn;
            ledGuidance.setSignal(xOn ? LedSignal::CROSS : LedSignal::OFF);
            cancelToggles++;
            if (cancelToggles >= CANCEL_BLINKS * 2) {       // klar: släck mitt larm hos alla
                own = Own::NONE;
                setAlarm(selfIdx, false, now);
                if (radio) radio->sendCancel(TOPO_ID[selfIdx]);
                cancelResendPending = true;
                cancelResendAt = now + CANCEL_RESEND_MS;
                Serial.println("Avstangning klar");
                evt("ALARM_OFF", TOPO_ID[selfIdx], "own");
                applyRoute();
            }
        }
    }
    if (cancelResendPending && timeReached(now, cancelResendAt)) {
        cancelResendPending = false;
        if (radio && own == Own::NONE && selfIdx >= 0) radio->sendCancel(TOPO_ID[selfIdx]);
    }
}

// ---- Larm från andra noder ---------------------------------------------------

void NodeController::handleRadio(uint32_t now) {
    if (!radio || selfIdx < 0) return;
    RadioMsg m;
    while (radio->poll(m)) {
        int idx = topoIndexOfId(m.sender);
        if (idx < 0 || idx == selfIdx) continue;            // okänd avsändare eller eget eko
        bool active = (alarmMask >> idx) & 1UL;
        if (m.command == CMD_ALERT) {
            if (!active) {                                  // nytt larm (upprepningar förlänger inte tiden)
                setAlarm(idx, true, now);
                Serial.print("Larm fran nod ");
                Serial.println((int)m.sender);
                evt("ALARM_ON", m.sender, "radio");
                applyRoute();
            }
        } else if (m.command == CMD_CANCEL) {
            if (active) {
                setAlarm(idx, false, now);
                Serial.print("Avstangning fran nod ");
                Serial.println((int)m.sender);
                evt("ALARM_OFF", m.sender, "radio");
                applyRoute();
            }
        }
    }
}

void NodeController::expireAlarms(uint32_t now) {
    bool changed = false;
    for (int k = 0; k < TOPO_N; k++) {
        if (k == selfIdx) continue;                         // eget larm hanteras i updateOwn
        if (((alarmMask >> k) & 1UL) && timeReached(now, alarmUntil[k])) {
            alarmMask &= ~(1UL << k);
            evt("ALARM_OFF", TOPO_ID[k], "expire");
            changed = true;
        }
    }
    if (changed) {
        Serial.println("Ett larm har gatt ut (5 min)");
        applyRoute();
    }
}

// ---- Serial-kommandon ---------------------------------------------------------

void NodeController::finishCapture() {
    char cmd = capCmd;
    bool has = capHasDigit;
    uint32_t value = capValue;
    capCmd = 0;
    capValue = 0;
    capHasDigit = false;
    if (!has) {
        Serial.println("Ange ett nummer, t.ex. a9");
        return;
    }
    int idx = topoIndexOfId((uint8_t)(value > 255 ? 255 : value));
    if (idx < 0) {
        Serial.print("Nod ");
        Serial.print((unsigned long)value);
        Serial.println(" finns inte i topology.json");
        return;
    }
    if (cmd == 'a') {
        setAlarm(idx, true, millis());
        Serial.print("Simulerat larm fran nod ");
        Serial.println((unsigned long)value);
        evt("ALARM_ON", (int)value, "sim");
        applyRoute();
    } else if (cmd == 'd') {
        if (idx == selfIdx && own != Own::NONE) {
            Serial.println("Eget larm stangs av med knappen (b), inte med d");
            return;
        }
        setAlarm(idx, false, millis());
        Serial.print("Simulerat larm borttaget fran nod ");
        Serial.println((unsigned long)value);
        evt("ALARM_OFF", (int)value, "sim");
        applyRoute();
    } else if (cmd == 'n') {
        selfIdx = idx;
        own = Own::NONE;
        Serial.print("Det har kortet ar nu nod ");
        Serial.println((unsigned long)value);
        evt("HELLO", (int)value);
        applyRoute();
    }
}

void NodeController::handleChar(char c) {
    if (c == '\r' || c == '\n') {
        if (capCmd) finishCapture();
        return;
    }
    if (capCmd) {
        if (c >= '0' && c <= '9') {
            capValue = capValue * 10 + (uint32_t)(c - '0');
            if (capValue > 100000) capValue = 100000;
            capHasDigit = true;
            capLastMs = millis();
            return;
        }
        finishCapture();            // annat tecken avslutar numret, och tecknet tolkas nedan
    }

    switch (c) {
        case '0': setMode(NodeMode::STARTUP); break;
        case '1': setMode(NodeMode::NORMAL); break;
        case '2': setMode(NodeMode::ALARM); break;
        case '3': setMode(NodeMode::EVACUATION); break;
        case '4': setMode(NodeMode::ERROR); break;

        // LED-kommandon (manuell test)
        case 'x': ledGuidance.setSignal(LedSignal::CROSS); break;
        case 'r': ledGuidance.setSignal(LedSignal::RIGHT); break;
        case 'l': ledGuidance.setSignal(LedSignal::LEFT); break;
        case 'o': ledGuidance.setSignal(LedSignal::OFF); break;

        // Utrymningsvagar
        case 'a':
        case 'd':
        case 'n':
            capCmd = c;
            capValue = 0;
            capHasDigit = false;
            capLastMs = millis();
            break;
        case 'c':
            alarmMask = 0;
            own = Own::NONE;
            Serial.println("Alla larm rensade (lokalt)");
            if (selfIdx >= 0) evt("CLEAR", TOPO_ID[selfIdx]);
            applyRoute();
            break;
        case 'b':
            onButtonPressed();
            break;
        case 'h':
            printHello();
            break;
        case 's':
            printStatus();
            break;
        default:
            break;
    }
}

void NodeController::update() {
    uint32_t now = millis();

    // Knappen (debounce)
    bool raw = digitalRead(PIN_BUTTON);
    if (raw != lastRaw) {
        lastRaw = raw;
        changedAt = now;
    }
    if (timeReached(now, changedAt + DEBOUNCE_MS) && raw != stable) {
        stable = raw;
        if (stable == LOW) onButtonPressed();               // nedtryckt
    }

    handleRadio(now);
    updateOwn(now);
    expireAlarms(now);

    // Nummer som skrivs i Serial Monitor utan Enter raknas efter en kort paus
    if (capCmd && capHasDigit && timeReached(now, capLastMs + CAPTURE_TIMEOUT_MS)) {
        finishCapture();
    }
    while (Serial.available() > 0) {
        handleChar((char)Serial.read());
    }
}

void NodeController::setMode(NodeMode newMode) {
    currentMode = newMode;

    Serial.print("Nodens tillstand: ");
    Serial.println(modeToString(currentMode));
}

NodeMode NodeController::getMode() const {
    return currentMode;
}

const char* NodeController::modeToString(NodeMode mode) const {

    switch (mode) {

        case NodeMode::STARTUP:
            return "STARTUP";

        case NodeMode::NORMAL:
            return "NORMAL";

        case NodeMode::ALARM:
            return "ALARM";

        case NodeMode::EVACUATION:
            return "EVACUATION";

        case NodeMode::ERROR:
            return "ERROR";

        default:
            return "UNKNOWN";
    }
}
