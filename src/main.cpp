#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h" // NODE_ID, ESPNOW_CHANNEL, GROUP_KEY (skapas av scripts/load_env.py från .env)
#include "node_controller.h"
#include "radio_espnow.h"
#include "mmwave_presence.h"

static const uint32_t CPU_FREQ_MHZ = 80; // lägsta frekvens där Wi-Fi/ESP-NOW fungerar, sparar ström

NodeController node;
EspNowRadio radio;

void setup()
{
    setCpuFrequencyMhz(CPU_FREQ_MHZ);
    Serial.begin(115200);
    delay(500);

    if (radio.begin(ESPNOW_CHANNEL, GROUP_KEY))
    {
        node.setRadio(&radio);
        Serial.print("ESP-NOW klar. MAC: ");
        Serial.println(WiFi.macAddress());
    }
    else
    {
        Serial.println("ESP-NOW startade inte. Noden körs bara lokalt.");
    }
    node.begin(NODE_ID);
    mmwave_setup();
}

void loop()
{
    node.update();
    mmwave_update();
}
