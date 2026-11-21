// Värdtest: kör samma route.cpp som noden på en vanlig dator.
// Utdata: en rad per nod och scenario:  SCEN <namn> | <id> <läge> <nästa-id|UT|-> <meter>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "route.h"
#include "topology.h"

int main(int argc, char **argv) {
    // argumenter: larm-id:n, t.ex.  sim 9 12
    uint32_t mask = 0;
    for (int i = 1; i < argc; i++) {
        int k = topoIndexOfId((uint8_t)atoi(argv[i]));
        if (k < 0) { fprintf(stderr, "okänt id %s\n", argv[i]); return 2; }
        mask |= 1UL << k;
    }
    for (int k = 0; k < TOPO_N; k++) {
        RouteResult r = computeRoute((uint8_t)k, mask);
        const char *mode = r.isBlocked ? "X" : (!r.hasRoute ? "INGEN" : (r.signal == LedSignal::LEFT ? "LEFT" : "RIGHT"));
        char next[8];
        if (r.isBlocked || !r.hasRoute) strcpy(next, "-");
        else if (r.nextIdx < 0) strcpy(next, "UT");
        else snprintf(next, sizeof next, "%d", TOPO_ID[r.nextIdx]);
        printf("%d %s %s %.1f\n", TOPO_ID[k], mode, next, r.totalDm / 10.0);
    }
    return 0;
}
