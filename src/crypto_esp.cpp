// HMAC-SHA256 på ESP32 (mbedtls ingår i Arduino-ESP32). På datorn används crypto_host.cpp i stället.
#ifdef ARDUINO
#include "protocol.h"
#include "mbedtls/md.h"

bool hmacSha256(const uint8_t *key, size_t keyLen, const uint8_t *msg, size_t msgLen, uint8_t out[32]) {
    const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    return mbedtls_md_hmac(info, key, keyLen, msg, msgLen, out) == 0;
}
#endif
