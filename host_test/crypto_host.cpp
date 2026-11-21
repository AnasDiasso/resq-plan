// HMAC-SHA256 med OpenSSL för datortester (på ESP32 används mbedtls i src/crypto_esp.cpp).
#include "protocol.h"
#include <openssl/evp.h>
#include <openssl/hmac.h>

bool hmacSha256(const uint8_t *key, size_t keyLen, const uint8_t *msg, size_t msgLen, uint8_t out[32]) {
    unsigned int len = 32;
    return HMAC(EVP_sha256(), key, (int)keyLen, msg, msgLen, out, &len) != nullptr && len == 32;
}
