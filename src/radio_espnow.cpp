#ifdef ARDUINO
#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include "radio_espnow.h"

static const int SEND_REPEATS = 3;          // broadcast har ingen kvittens, så skicka några gånger
static const int SEND_GAP_MS = 15;
static const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// Inkorg: callbacken körs i Wi-Fi-tråden, så meddelandena läggs i en liten kö som loop() tömmer.
static const int RING = 16;
static RadioMsg ring[RING];
static volatile int ringHead = 0;
static volatile int ringTail = 0;
static portMUX_TYPE ringMux = portMUX_INITIALIZER_UNLOCKED;
static EspNowRadio *instance = nullptr;

static const uint8_t ZERO_KEY[16] = {0};

EspNowRadio::EspNowRadio() : codec(ZERO_KEY) {}

// Signaturen skiljer sig mellan ESP32 Arduino core 2.x och 3.x
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onRecv(const esp_now_recv_info_t *, const uint8_t *data, int len) {
#else
static void onRecv(const uint8_t *, const uint8_t *data, int len) {
#endif
    if (instance) instance->handleReceive(data, len);
}

void EspNowRadio::handleReceive(const uint8_t *data, int len) {
    RadioMsg m;
    if (!codec.decode(data, len, m)) return;        // fel storlek, fel nyckel eller dubblett
    portENTER_CRITICAL(&ringMux);
    int next = (ringHead + 1) % RING;
    if (next != ringTail) {                          // full kö: släpp meddelandet
        ring[ringHead] = m;
        ringHead = next;
    }
    portEXIT_CRITICAL(&ringMux);
}

bool EspNowRadio::poll(RadioMsg &out) {
    bool got = false;
    portENTER_CRITICAL(&ringMux);
    if (ringTail != ringHead) {
        out = ring[ringTail];
        ringTail = (ringTail + 1) % RING;
        got = true;
    }
    portEXIT_CRITICAL(&ringMux);
    return got;
}

bool EspNowRadio::begin(uint8_t channel, const uint8_t *groupKey) {
    codec = AlarmCodec(groupKey);
    instance = this;

    WiFi.mode(WIFI_STA);          // station-läge, ingen router
    WiFi.disconnect();

    // Lås alla noder till samma kanal
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);

    if (esp_now_init() != ESP_OK) {
        Serial.println("Fel vid start av ESP-NOW!");
        return false;
    }
    esp_now_register_recv_cb(onRecv);

    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, BROADCAST, 6);
    peer.channel = channel;
    peer.encrypt = false;
    if (esp_now_add_peer(&peer) != ESP_OK) {
        Serial.println("Kunde inte lägga till broadcast-peer!");
        return false;
    }
    return true;
}

void EspNowRadio::sendCommand(uint8_t command, uint8_t sender) {
    uint32_t nonce = esp_random();
    if (nonce == 0) nonce = 1;
    AlarmPacket pkt;
    if (!codec.encode(command, sender, nonce, pkt)) {
        Serial.println("Kunde inte signera paketet, skickar inte.");
        return;
    }
    for (int i = 0; i < SEND_REPEATS; i++) {
        esp_now_send(BROADCAST, (const uint8_t *)&pkt, sizeof(pkt));
        delay(SEND_GAP_MS);
    }
}

void EspNowRadio::sendAlert(uint8_t sender)  { sendCommand(CMD_ALERT, sender); }
void EspNowRadio::sendCancel(uint8_t sender) { sendCommand(CMD_CANCEL, sender); }
#endif
