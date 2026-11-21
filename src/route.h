#pragma once
#include <stdint.h>
#include "led_guidance.h"

// Dijkstra: snabbaste vägen ut ur byggnaden, utan att passera larmande noder eller noder i larmande zoner.
// Inga Arduino-beroenden, så samma kod kan testas på en vanlig dator.

struct RouteResult {
    bool        hasRoute;   // false = ingen väg ut finns
    bool        isBlocked;  // noden själv larmar (visa X)
    LedSignal   signal;     // CROSS, LEFT eller RIGHT (OFF om ingen väg)
    int8_t      nextIdx;    // nästa nod på vägen, -1 = ut genom utgången här
    uint32_t    totalDm;    // total väg ut i decimeter
};

// blockedMask: bit k satt = nod med index k larmar. selfIdx: den här nodens index.
RouteResult computeRoute(uint8_t selfIdx, uint32_t blockedMask);

// Hjälpfunktioner
int  topoIndexOfId(uint8_t nodeId);    // -1 om ID saknas i topologin
