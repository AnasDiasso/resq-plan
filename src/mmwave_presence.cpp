#include <Arduino.h>
#include "mmwave_presence.h"

// HMMD mmWave (24 GHz) – närvaro eller ingen närvaro
// Koppling: sensor TX -> G16, sensor RX -> G17, 3V3 -> 3V3, GND -> GND

static const unsigned long HOLD_MS = 5000; // NÄRVARO hålls kvar 5 s efter senaste rörelse

// ---- Räckvidd: rörelse längre bort än så ignoreras ----
static const int MAX_DISTANCE_CM = 10000;

// ---- Känslighet: hur mycket över det normala bruset som räknas som rörelse ----
static const float SENSITIVITY_FACTOR = 1.3; // högre = mindre känslig
static const int SENSITIVITY_MARGIN = 8;     // högre = mindre känslig

static HardwareSerial Radar(2);

static int minZone, maxZone; // räknas ut från MAX_DISTANCE_CM (0,7 m per zon)
static float normal[16];     // normal nivå (brus) per zon – lärs in automatiskt
static float level[16];      // nuvarande nivå per zon (utjämnad)
static bool started = false;
static unsigned long lastSeen = 0, lastData = 0;
static int previousPresence = -1;

// Kommandosekvens till sensorn – ett kommando per 100 ms, utan delay
static int cmdStep = 0; // 0 = inget pågår, 1-3 = nästa kommando
static unsigned long cmdTime = 0, lastTry = 0;
static uint8_t cmdMode = 0x04;
static bool modeA = true;

// Läser en mätning från sensorn: energi i 16 zoner (0,7 m per zon)
static bool readRadar(int energy[16])
{
  static uint8_t buf[64];
  static int len = 0;
  while (Radar.available())
  {
    uint8_t b = Radar.read();
    if (len == 0 && b != 0xF4)
      continue;
    buf[len++] = b;
    if (len == 4 && !(buf[1] == 0xF3 && buf[2] == 0xF2 && buf[3] == 0xF1))
    {
      len = 0;
      continue;
    }
    if (len < 6)
      continue;
    int total = 6 + (buf[4] | (buf[5] << 8)) + 4;
    if (total > 64 || total < 45)
    {
      len = 0;
      continue;
    }
    if (len < total)
      continue;
    len = 0;
    if (buf[total - 4] != 0xF8 || buf[total - 1] != 0xF5)
      continue;
    for (int z = 0; z < 16; z++)
      energy[z] = buf[9 + 2 * z] | (buf[10 + 2 * z] << 8);
    lastData = millis();
    return true;
  }
  return false;
}

// Ber sensorn skicka energi per zon – blockerar aldrig
static void reportModeUpdate()
{
  // Ingen data på 3 s? Starta kommandosekvensen (högst var 5:e sekund)
  if (cmdStep == 0 && millis() - lastData > 3000 && millis() - lastTry > 5000)
  {
    lastTry = millis();
    cmdMode = modeA ? 0x04 : 0x64;
    modeA = !modeA;
    cmdStep = 1;
  }
  if (cmdStep == 0 || millis() - cmdTime < 100)
    return;

  uint8_t a[] = {0xFD, 0xFC, 0xFB, 0xFA, 0x04, 0x00, 0xFF, 0x00, 0x01, 0x00, 0x04, 0x03, 0x02, 0x01};
  uint8_t b[] = {0xFD, 0xFC, 0xFB, 0xFA, 0x08, 0x00, 0x12, 0x00, 0x00, 0x00, cmdMode, 0x00, 0x00, 0x00, 0x04, 0x03, 0x02, 0x01};
  uint8_t c[] = {0xFD, 0xFC, 0xFB, 0xFA, 0x02, 0x00, 0xFE, 0x00, 0x04, 0x03, 0x02, 0x01};
  if (cmdStep == 1)
    Radar.write(a, sizeof(a));
  if (cmdStep == 2)
    Radar.write(b, sizeof(b));
  if (cmdStep == 3)
    Radar.write(c, sizeof(c));
  cmdTime = millis();
  cmdStep = (cmdStep == 3) ? 0 : cmdStep + 1;
}

void mmwave_setup()
{
  Radar.begin(115200, SERIAL_8N1, 16, 17);
  // Zon z täcker z*70 till (z+1)*70 cm
  minZone = 1; // 0-70 cm brusar alltid och hoppas över
  maxZone = constrain((MAX_DISTANCE_CM - 1) / 70, 1, 15);
  Serial.println("HMMD mmWave startad");
  Serial.printf("Räknar rörelse upp till %d cm\n", (maxZone + 1) * 70);
}

void mmwave_update()
{
  reportModeUpdate();

  int energy[16];
  if (readRadar(energy))
  {
    bool moving = false;
    for (int z = minZone; z <= maxZone; z++)
    { // bara zonerna inom räckvidden
      if (!started)
      {
        normal[z] = energy[z];
        level[z] = energy[z];
      }
      level[z] += (energy[z] - level[z]) * 0.2; // utjämnad nivå (ca 0,5 s)
      if (level[z] > normal[z] * SENSITIVITY_FACTOR + SENSITIVITY_MARGIN)
        moving = true;
    }
    started = true;

    if (moving)
      lastSeen = millis();
    else
      for (int z = minZone; z <= maxZone; z++) // ingen rörelse: lär in det normala långsamt
        normal[z] += (level[z] - normal[z]) * 0.002;
  }

  // Skriv ut när statusen ändras
  int presence = mmwave_present() ? HIGH : LOW;
  if (presence != previousPresence)
  {
    Serial.println(presence == HIGH ? "NARVARO" : "INGEN NARVARO");
    previousPresence = presence;
  }
}

// NÄRVARO = rörelse de senaste 10 sekunderna
bool mmwave_present()
{
  return lastSeen > 0 && millis() - lastSeen < HOLD_MS;
}