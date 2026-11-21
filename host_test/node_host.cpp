// Kör noden (samma NodeController, route och topologi som på kortet) som ett vanligt program.
// Serial = stdin/stdout. Används för att testa sim/server.py utan riktigt kort.
//   node_host <nod-id>
#include <cstdlib>
#include <unistd.h>
#include "Arduino.h"
#include "node_controller.h"

int main(int argc, char **argv) {
    int id = argc > 1 ? atoi(argv[1]) : 1;
    NodeController node;
    node.begin((uint8_t)id);
    for (;;) {
        node.update();
        usleep(5000);
    }
}
