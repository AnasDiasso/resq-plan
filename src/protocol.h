#pragma once
#include <stdint.h>
#include <stddef.h>

// Larmpaket över ESP-NOW (broadcast). Samma kod används på noden och i datortesterna.
//   command  1 = ALERT (jag larmar), 2 = CANCEL (jag stänger av mitt larm)
//   sender   nodens nummer (NODE_ID) i topology.json
//   nonce    slumptal per sändning (skyddar mot uppspelning, och dubbletter kastas)
//   tag      HMAC-SHA256(GRUPPNYCKEL, command + sender + nonce), avkortad till 8 byte

enum : uint8_t {
    CMD_ALERT  = 1,
    CMD_CANCEL = 2
};

static const int TAG_LEN = 8;

struct __attribute__((packed)) AlarmPacket {
    uint8_t  command;
    uint8_t  sender;
    uint32_t nonce;
    uint8_t  tag[TAG_LEN];
};
static const size_t ALARM_PACKET_LEN = sizeof(AlarmPacket);   // 14 byte

struct RadioMsg {           // ett kontrollerat och godkänt meddelande
    uint8_t command;
    uint8_t sender;
};

// Plattformsberoende: HMAC-SHA256. På ESP32 med mbedtls (crypto_esp.cpp), på datorn med OpenSSL.
bool hmacSha256(const uint8_t *key, size_t keyLen, const uint8_t *msg, size_t msgLen, uint8_t out[32]);

class AlarmCodec {
public:
    explicit AlarmCodec(const uint8_t *key16);

    // Bygger ett signerat paket. nonce får inte vara 0.
    bool encode(uint8_t command, uint8_t sender, uint32_t nonce, AlarmPacket &out) const;

    // Kontrollerar längd, kommando, signatur och dubblett/uppspelning. true = godkänt och nytt.
    bool decode(const uint8_t *data, int len, RadioMsg &out);

private:
    uint8_t key[16];
    static const int HISTORY = 32;
    uint64_t seen[HISTORY];
    int seenIndex;

    bool computeTag(uint8_t command, uint8_t sender, uint32_t nonce, uint8_t tagOut[TAG_LEN]) const;
    bool alreadySeen(uint8_t sender, uint32_t nonce) const;
    void remember(uint8_t sender, uint32_t nonce);
};
