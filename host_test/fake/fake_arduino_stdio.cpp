// Låtsas-Arduino som pratar Serial över stdin/stdout med riktig klocka. Används av node_host.
#include "Arduino.h"
#include <cstdio>
#include <ctime>
#include <poll.h>
#include <unistd.h>
FakeSerial Serial;
std::string g_serialIn;
uint32_t g_ms = 0;
int g_pin[40];
bool g_verbose = true;
void pinMode(uint8_t, uint8_t) {}
void digitalWrite(uint8_t p, uint8_t v) { g_pin[p] = v; }
int digitalRead(uint8_t) { return HIGH; }
void delay(unsigned long ms) { usleep(ms * 1000); }
unsigned long millis() {
    timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (unsigned long)(ts.tv_sec * 1000UL + ts.tv_nsec / 1000000UL);
}
void FakeSerial::begin(unsigned long) {}
void FakeSerial::println() { printf("\n"); fflush(stdout); }
void FakeSerial::println(const char *s) { printf("%s\n", s); fflush(stdout); }
void FakeSerial::println(int v) { printf("%d\n", v); fflush(stdout); }
void FakeSerial::println(unsigned long v) { printf("%lu\n", v); fflush(stdout); }
void FakeSerial::print(const char *s) { printf("%s", s); }
void FakeSerial::print(int v) { printf("%d", v); }
void FakeSerial::print(unsigned long v) { printf("%lu", v); }
void FakeSerial::print(unsigned int v) { printf("%u", v); }
int FakeSerial::available() {
    pollfd p = {0, POLLIN, 0};
    while (poll(&p, 1, 0) > 0 && (p.revents & POLLIN)) {
        char buf[256];
        ssize_t n = ::read(0, buf, sizeof buf);
        if (n <= 0) break;
        g_serialIn.append(buf, (size_t)n);
        p.revents = 0;
    }
    return (int)g_serialIn.size();
}
int FakeSerial::read() { int c = (unsigned char)g_serialIn[0]; g_serialIn.erase(0, 1); return c; }
