#include "route.h"
#include "topology.h"

static const uint32_t INF = 0xFFFFFFFFu;

int topoIndexOfId(uint8_t nodeId) {
    for (int k = 0; k < TOPO_N; k++) {
        if (TOPO_ID[k] == nodeId) return k;
    }
    return -1;
}

RouteResult computeRoute(uint8_t selfIdx, uint32_t blockedMask) {
    RouteResult r;
    r.hasRoute = false;
    r.isBlocked = false;
    r.signal = LedSignal::OFF;
    r.nextIdx = -1;
    r.totalDm = 0;

    if (selfIdx >= TOPO_N) return r;

    if (blockedMask & (1UL << selfIdx)) {      // jag larmar själv: X-lampan
        r.isBlocked = true;
        r.signal = LedSignal::CROSS;
        return r;
    }

    // Larm stänger hela sin zon (t.ex. ett trapphus): inga pilar leder dit, och utgångar där räknas inte.
    uint32_t zoneBlocked = 0;
    for (int k = 0; k < TOPO_N; k++) {
        if ((blockedMask >> k) & 1UL) zoneBlocked |= TOPO_ZONE_MASK[k];
    }
    blockedMask = zoneBlocked;      // härifrån betyder "blockerad" = stängd (larm eller stängd zon)

    // Dijkstra från "utanför byggnaden". dist[v] = kortaste väg från v till utsidan.
    // Utgångsnoder startar med sin utgångssträcka. Kanterna är riktade (från -> till),
    // så vi går baklänges: när noden u är klar relaxeras alla v som har kanten v -> u.
    uint32_t dist[TOPO_N];
    bool done[TOPO_N];
    for (int k = 0; k < TOPO_N; k++) {
        bool blocked = (blockedMask >> k) & 1UL;
        dist[k] = (!blocked && TOPO_EXIT_DM[k] > 0) ? TOPO_EXIT_DM[k] : INF;
        done[k] = false;
    }

    for (int iter = 0; iter < TOPO_N; iter++) {
        int u = -1;
        uint32_t best = INF;
        for (int k = 0; k < TOPO_N; k++) {
            if (!done[k] && dist[k] < best) { best = dist[k]; u = k; }
        }
        if (u < 0) break;
        done[u] = true;
        for (int e = 0; e < TOPO_E; e++) {
            if (TOPO_E_TO[e] != u) continue;
            int v = TOPO_E_FROM[e];
            if ((blockedMask >> v) & 1UL) continue;      // går inte genom larmande noder
            uint32_t cand = dist[u] + TOPO_E_DM[e];
            if (cand < dist[v]) dist[v] = cand;
        }
    }

    // Välj bästa utgående val för den här noden: antingen ut här eller till en granne.
    uint32_t bestTotal = INF;
    int8_t bestNext = -1;
    uint8_t bestLamp = 0;

    if (TOPO_EXIT_DM[selfIdx] > 0 && !((blockedMask >> selfIdx) & 1UL)) {
        bestTotal = TOPO_EXIT_DM[selfIdx];
        bestNext = -1;
        bestLamp = TOPO_EXIT_LAMP[selfIdx];
    }
    for (int e = 0; e < TOPO_E; e++) {
        if (TOPO_E_FROM[e] != selfIdx) continue;
        int to = TOPO_E_TO[e];
        if ((blockedMask >> to) & 1UL) continue;
        if (dist[to] == INF) continue;
        uint32_t total = TOPO_E_DM[e] + dist[to];
        if (total < bestTotal) {
            bestTotal = total;
            bestNext = (int8_t)to;
            bestLamp = TOPO_E_LAMP[e];
        }
    }

    if (bestTotal == INF) return r;           // ingen väg ut

    r.hasRoute = true;
    r.signal = (bestLamp == 0) ? LedSignal::LEFT : LedSignal::RIGHT;
    r.nextIdx = bestNext;
    r.totalDm = bestTotal;
    return r;
}
