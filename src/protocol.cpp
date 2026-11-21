#include "protocol.h"
#include <string.h>

AlarmCodec::AlarmCodec(const uint8_t *key16) : seenIndex(0) {
    memcpy(key, key16, sizeof(key));
    memset(seen, 0, sizeof(seen));
}

bool AlarmCodec::computeTag(uint8_t command, uint8_t sender, uint32_t nonce, uint8_t tagOut[TAG_LEN]) const {
    uint8_t msg[6];
    msg[0] = command;
    msg[1] = sender;
    memcpy(&msg[2], &nonce, 4);
    uint8_t full[32];
    if (!hmacSha256(key, sizeof(key), msg, sizeof(msg), full)) return false;
    memcpy(tagOut, full, TAG_LEN);
    return true;
}

bool AlarmCodec::encode(uint8_t command, uint8_t sender, uint32_t nonce, AlarmPacket &out) const {
    if (nonce == 0) return false;               // 0 betyder "tom plats" i historiken
    out.command = command;
    out.sender = sender;
    out.nonce = nonce;
    return computeTag(command, sender, nonce, out.tag);
}

bool AlarmCodec::alreadySeen(uint8_t sender, uint32_t nonce) const {
    uint64_t id = ((uint64_t)sender << 32) | nonce;
    for (int i = 0; i < HISTORY; i++) {
        if (seen[i] == id) return true;
    }
    return false;
}

void AlarmCodec::remember(uint8_t sender, uint32_t nonce) {
    seen[seenIndex] = ((uint64_t)sender << 32) | nonce;
    seenIndex = (seenIndex + 1) % HISTORY;
}

bool AlarmCodec::decode(const uint8_t *data, int len, RadioMsg &out) {
    if (len != (int)ALARM_PACKET_LEN) return false;
    AlarmPacket in;
    memcpy(&in, data, sizeof(in));
    if (in.command != CMD_ALERT && in.command != CMD_CANCEL) return false;
    if (in.sender == 0 || in.nonce == 0) return false;

    uint8_t expected[TAG_LEN];
    if (!computeTag(in.command, in.sender, in.nonce, expected)) return false;
    uint8_t diff = 0;
    for (int i = 0; i < TAG_LEN; i++) diff |= expected[i] ^ in.tag[i];   // konstant tid
    if (diff != 0) return false;                                          // fel nyckel eller ändrat paket

    if (alreadySeen(in.sender, in.nonce)) return false;                   // dubblett eller uppspelning
    remember(in.sender, in.nonce);

    out.command = in.command;
    out.sender = in.sender;
    return true;
}
