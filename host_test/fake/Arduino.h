#pragma once
// Låtsas-Arduino för datortester: tid, pinnar och Serial.
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <string>
#define OUTPUT 1
#define INPUT_PULLUP 2
#define HIGH 1
#define LOW 0
void pinMode(uint8_t, uint8_t);
void digitalWrite(uint8_t, uint8_t);
int digitalRead(uint8_t);
void delay(unsigned long);
unsigned long millis();
struct FakeSerial {
    void begin(unsigned long);
    void println();
    void println(const char *);
    void println(int);
    void println(unsigned long);
    void print(const char *);
    void print(int);
    void print(unsigned long);
    void print(unsigned int);
    int available();
    int read();
};
extern FakeSerial Serial;
extern std::string g_serialIn;   // text som "skrivs" i Serial Monitor
extern uint32_t g_ms;            // låtsastid
extern int g_pin[40];            // senaste värdet per pinne
extern bool g_verbose;           // skriv ut Serial-text
