#include "Arduino.h"
#include <cstdio>
FakeSerial Serial;
std::string g_serialIn;
uint32_t g_ms = 1000;
int g_pin[40];
bool g_verbose = false;
void pinMode(uint8_t, uint8_t) {}
void digitalWrite(uint8_t p, uint8_t v) { g_pin[p] = v; }
int digitalRead(uint8_t) { return HIGH; }
void delay(unsigned long) {}
unsigned long millis() { return g_ms; }
void FakeSerial::begin(unsigned long) {}
void FakeSerial::println() { if (g_verbose) printf("\n"); }
void FakeSerial::println(const char *s) { if (g_verbose) printf("%s\n", s); }
void FakeSerial::println(int v) { if (g_verbose) printf("%d\n", v); }
void FakeSerial::println(unsigned long v) { if (g_verbose) printf("%lu\n", v); }
void FakeSerial::print(const char *s) { if (g_verbose) printf("%s", s); }
void FakeSerial::print(int v) { if (g_verbose) printf("%d", v); }
void FakeSerial::print(unsigned long v) { if (g_verbose) printf("%lu", v); }
void FakeSerial::print(unsigned int v) { if (g_verbose) printf("%u", v); }
int FakeSerial::available() { return (int)g_serialIn.size(); }
int FakeSerial::read() { int c = (unsigned char)g_serialIn[0]; g_serialIn.erase(0, 1); return c; }
