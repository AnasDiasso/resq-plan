// Skriver ut paketet som C++-koden bygger, så att Python kan kontrollera signaturen oberoende.
#include <cstdio>
#include <cstdlib>
#include "protocol.h"
int main(int, char **argv) {
    uint8_t key[16];
    for (int i = 0; i < 16; i++) key[i] = (uint8_t)(i * 17);
    AlarmCodec c(key);
    AlarmPacket p;
    c.encode((uint8_t)atoi(argv[1]), (uint8_t)atoi(argv[2]), (uint32_t)strtoul(argv[3], 0, 10), p);
    const uint8_t *b = (const uint8_t *)&p;
    for (size_t i = 0; i < sizeof(p); i++) printf("%02x", b[i]);
    printf("\n");
}
