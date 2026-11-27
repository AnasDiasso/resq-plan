#pragma once

// HMMD mmWave (24 GHz) – närvaro eller ingen närvaro
// Koppling: sensor TX -> G16, sensor RX -> G17, 3V3 -> 3V3, GND -> GND

void mmwave_setup();
void mmwave_update();
bool mmwave_present();
