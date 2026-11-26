#include <Arduino.h>

// HMMD mmWave (24 GHz) – närvaro eller ingen närvaro
// Koppling: sensor TX -> G16, sensor RX -> G17, 3V3 -> 3V3, GND -> GND

const unsigned long HOLD_MS = 10000;   // NÄRVARO hålls kvar 10 s efter senaste rörelse

// ---- Räckvidd: rörelse längre bort än så ignoreras ----
const int MAX_DISTANCE_CM = 10000; //

// ---- Känslighet: hur mycket över det normala bruset som räknas som rörelse ----
const float SENSITIVITY_FACTOR = 1.3;   // högre = mindre känslig
const int   SENSITIVITY_MARGIN = 8;    // högre = mindre känslig

int minZone, maxZone;              // räknas ut från MAX_DISTANCE_CM (0,7 m per zon)

HardwareSerial Radar(2);

float normal[16];          // normal nivå (brus) per zon – lärs in automatiskt
float level[16];           // nuvarande nivå per zon (utjämnad)
bool started = false;
unsigned long lastSeen = 0, lastData = 0;
int previousPresence = -1;

// Läser en mätning från sensorn: energi i 16 zoner (0,7 m per zon)
bool readRadar(int energy[16]) {
  static uint8_t buf[64];
  static int len = 0;
  while (Radar.available()) {
    uint8_t b = Radar.read();
    if (len == 0 && b != 0xF4) continue;
    buf[len++] = b;
    if (len == 4 && !(buf[1] == 0xF3 && buf[2] == 0xF2 && buf[3] == 0xF1)) { len = 0; continue; }
    if (len < 6) continue;
    int total = 6 + (buf[4] | (buf[5] << 8)) + 4;
    if (total > 64 || total < 45) { len = 0; continue; }
    if (len < total) continue;
    len = 0;
    if (buf[total - 4] != 0xF8 || buf[total - 1] != 0xF5) continue;
    for (int z = 0; z < 16; z++) energy[z] = buf[9 + 2 * z] | (buf[10 + 2 * z] << 8);
    lastData = millis();
    return true;
  }
  return false;
}

// Ber sensorn skicka energi per zon
void startReportMode(uint8_t mode) {
  uint8_t a[] = {0xFD,0xFC,0xFB,0xFA, 0x04,0x00, 0xFF,0x00, 0x01,0x00, 0x04,0x03,0x02,0x01};
  uint8_t b[] = {0xFD,0xFC,0xFB,0xFA, 0x08,0x00, 0x12,0x00, 0x00,0x00, mode,0x00,0x00,0x00, 0x04,0x03,0x02,0x01};
  uint8_t c[] = {0xFD,0xFC,0xFB,0xFA, 0x02,0x00, 0xFE,0x00, 0x04,0x03,0x02,0x01};
  Radar.write(a, sizeof(a)); delay(100);
  Radar.write(b, sizeof(b)); delay(100);
  Radar.write(c, sizeof(c)); delay(100);
}

void setup() {
  Serial.begin(115200);
  Radar.begin(115200, SERIAL_8N1, 16, 17);
  // Zon z täcker z*70 till (z+1)*70 cm
  minZone = 1;                                          // 0-70 cm brusar alltid och hoppas över
  maxZone = constrain((MAX_DISTANCE_CM - 1) / 70, 1, 15);
  Serial.println("HMMD mmWave startad");
  Serial.printf("Räknar rörelse upp till %d cm\n", (maxZone + 1) * 70);
}

void loop() {
  // Ingen data? Be sensorn skicka energi per zon (var 5:e sekund)
  static unsigned long lastTry = 0;
  static bool modeA = true;
  if (millis() - lastData > 3000 && millis() - lastTry > 5000) {
    lastTry = millis();
    startReportMode(modeA ? 0x04 : 0x64);
    modeA = !modeA;
  }

  int energy[16];
  if (readRadar(energy)) {
    bool moving = false;
    for (int z = minZone; z <= maxZone; z++) {       // bara zonerna inom räckvidden
      if (!started) { normal[z] = energy[z]; level[z] = energy[z]; }
      level[z] += (energy[z] - level[z]) * 0.2;      // utjämnad nivå (ca 0,5 s)
      if (level[z] > normal[z] * SENSITIVITY_FACTOR + SENSITIVITY_MARGIN) moving = true;   // tydligt över det normala = rörelse
    }
    started = true;

    if (moving) lastSeen = millis();
    else for (int z = minZone; z <= maxZone; z++)    // ingen rörelse: lär in det normala långsamt
      normal[z] += (level[z] - normal[z]) * 0.002;
  }

  // NÄRVARO = rörelse de senaste 10 sekunderna
  int presence = (lastSeen > 0 && millis() - lastSeen < HOLD_MS) ? HIGH : LOW;

  if (presence != previousPresence) {
    Serial.println(presence == HIGH ? "NARVARO" : "INGEN NARVARO");
    previousPresence = presence;
  }

  delay(5);
}