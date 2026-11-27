// Datortest av hela larmkedjan: 18 noder med samma NodeController, route.cpp och protocol.cpp som kortet,
// ihopkopplade med en låtsasradio (broadcast, förlust, uppspelning, fel nyckel).
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <vector>
#include "Arduino.h"
#include "node_controller.h"
#include "route.h"
#include "topology.h"

static int fails = 0;
static int checks = 0;
#define CHECK(cond, ...) do { checks++; if (!(cond)) { fails++; printf("FEL: "); printf(__VA_ARGS__); printf("\n"); } } while (0)

// ---------- Låtsasradio ----------
struct Net;
struct FakeRadio : IRadio {
    Net *net;
    AlarmCodec codec;
    std::deque<std::vector<uint8_t>> inbox;
    FakeRadio(Net *n, const uint8_t *key) : net(n), codec(key) {}
    void sendAlert(uint8_t sender) override;
    void sendCancel(uint8_t sender) override;
    bool poll(RadioMsg &out) override {
        while (!inbox.empty()) {
            std::vector<uint8_t> pkt = inbox.front();
            inbox.pop_front();
            if (codec.decode(pkt.data(), (int)pkt.size(), out)) return true;   // samma kontroll som på kortet
        }
        return false;
    }
};

struct Net {
    std::vector<FakeRadio *> radios;
    double dropProb = 0.0;                          // sannolikhet att en enskild kopia försvinner
    std::vector<std::vector<uint8_t>> sent;         // alla skickade paket (för uppspelningstest)
    void broadcast(FakeRadio *from, const AlarmPacket &p) {
        std::vector<uint8_t> bytes((const uint8_t *)&p, (const uint8_t *)&p + sizeof(p));
        sent.push_back(bytes);
        for (int rep = 0; rep < 3; rep++) {         // som kortet: tre kopior av samma paket
            for (FakeRadio *r : radios) {
                if (r == from) continue;
                if ((double)rand() / RAND_MAX < dropProb) continue;
                r->inbox.push_back(bytes);
            }
        }
    }
};

static uint32_t nextNonce() { uint32_t n = (uint32_t)rand() * 2654435761u; return n ? n : 1; }
void FakeRadio::sendAlert(uint8_t sender)  { AlarmPacket p; codec.encode(CMD_ALERT, sender, nextNonce(), p);  net->broadcast(this, p); }
void FakeRadio::sendCancel(uint8_t sender) { AlarmPacket p; codec.encode(CMD_CANCEL, sender, nextNonce(), p); net->broadcast(this, p); }

// ---------- Hjälp ----------
static const uint8_t KEY[16] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16};
static const uint8_t BAD_KEY[16] = {9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9};

struct World {
    Net net;
    std::vector<NodeController *> nodes;
    std::vector<FakeRadio *> radios;
    World(double drop = 0.0) {
        net.dropProb = drop;
        for (int k = 0; k < TOPO_N; k++) {
            FakeRadio *r = new FakeRadio(&net, KEY);
            NodeController *n = new NodeController();
            n->setRadio(r);
            n->begin(TOPO_ID[k]);
            net.radios.push_back(r);
            radios.push_back(r);
            nodes.push_back(n);
        }
    }
    void run(uint32_t ms) {                          // steg om 10 ms
        for (uint32_t t = 0; t < ms; t += 10) {
            g_ms += 10;
            for (NodeController *n : nodes) n->update();
        }
    }
    int idxOf(int id) { return topoIndexOfId((uint8_t)id); }
    void press(int id) { nodes[idxOf(id)]->onButtonPressed(); }
};

static uint32_t maskOf(std::initializer_list<int> ids) {
    uint32_t m = 0;
    for (int id : ids) m |= 1UL << topoIndexOfId((uint8_t)id);
    return m;
}
static const char *name(LedSignal s) {
    return s == LedSignal::OFF ? "OFF" : s == LedSignal::CROSS ? "X" : s == LedSignal::LEFT ? "LEFT" : "RIGHT";
}

// Alla noder ska visa precis det motorn räknar fram för den givna larmmängden
static void expectAll(World &w, uint32_t mask, const char *what) {
    for (int k = 0; k < TOPO_N; k++) {
        LedSignal want = mask ? computeRoute((uint8_t)k, mask).signal : LedSignal::OFF;
        LedSignal got = w.nodes[k]->signal();
        CHECK(got == want, "%s: nod %d visar %s, väntade %s", what, TOPO_ID[k], name(got), name(want));
        CHECK(w.nodes[k]->alarms() == mask, "%s: nod %d har larmmängd %08x, väntade %08x", what, TOPO_ID[k], w.nodes[k]->alarms(), mask);
    }
}

int main() {
    srand(7);
    // ===== 1. Larm, andra larm, avstängning, utgång =====
    {
        World w;
        w.run(100);
        expectAll(w, 0, "start");

        w.press(2);                       // nod 2 larmar
        w.run(200);
        expectAll(w, maskOf({2}), "larm nod 2");
        CHECK(w.nodes[w.idxOf(2)]->signal() == LedSignal::CROSS, "nod 2 ska visa X");
        CHECK(w.nodes[w.idxOf(1)]->signal() == LedSignal::CROSS, "nod 1 ska visa X (samma trapphus som nod 2)");
        CHECK(w.nodes[w.idxOf(3)]->signal() == LedSignal::CROSS, "nod 3 ska visa X (samma trapphus som nod 2)");
        CHECK(w.nodes[w.idxOf(4)]->signal() == LedSignal::LEFT, "nod 4 (utgång) ska visa ut (grön)");

        w.press(9);                       // ett andra larm
        w.run(200);
        expectAll(w, maskOf({2, 9}), "larm nod 2 och 9");

        w.press(2);                       // nod 2 stänger av: blinkar 3 gånger
        int xOnCount = 0;
        LedSignal prev = w.nodes[w.idxOf(2)]->signal();
        for (int i = 0; i < 160; i++) {   // 1,6 s
            w.run(10);
            LedSignal s = w.nodes[w.idxOf(2)]->signal();
            if (s == LedSignal::CROSS && prev != LedSignal::CROSS) xOnCount++;
            prev = s;
        }
        CHECK(xOnCount == 3, "X ska blinka 3 gånger, blinkade %d", xOnCount);
        w.run(300);
        expectAll(w, maskOf({9}), "efter avstängning av nod 2");

        w.press(9);
        w.run(2000);
        expectAll(w, 0, "efter avstängning av nod 9");
    }

    // ===== 2. Larmet går ut efter 5 minuter =====
    {
        World w;
        w.press(6);
        w.run(1000);
        expectAll(w, maskOf({6}), "larm nod 6");
        w.run(5 * 60 * 1000 + 2000);
        expectAll(w, 0, "5 minuter senare");
    }

    // ===== 3. Förlorade paket: upprepningen var 10:e sekund ska hjälpa =====
    {
        World w(0.6);                     // 60 % av alla kopior försvinner
        w.press(7);
        w.run(60 * 1000);
        expectAll(w, maskOf({7}), "60 % paketförlust, efter 60 s");
    }

    // ===== 4. Fel nyckel ignoreras =====
    {
        World w;
        FakeRadio intruder(&w.net, BAD_KEY);
        AlarmPacket p;
        intruder.codec.encode(CMD_ALERT, 5, 12345, p);
        w.net.broadcast(&intruder, p);
        w.run(500);
        expectAll(w, 0, "paket med fel nyckel");
    }

    // ===== 5. Uppspelning av inspelat paket ignoreras =====
    {
        World w;
        w.press(2);
        w.run(300);
        std::vector<uint8_t> recorded = w.net.sent.front();   // nod 2:s ALERT
        w.press(2);
        w.run(2500);
        expectAll(w, 0, "efter avstängning");
        for (FakeRadio *r : w.radios) r->inbox.push_back(recorded);   // någon spelar upp det gamla larmet
        w.run(300);
        expectAll(w, 0, "uppspelat ALERT");
    }

    // ===== 6. Okänd avsändare och förvanskade paket =====
    {
        World w;
        FakeRadio ok(&w.net, KEY);
        AlarmPacket p;
        ok.codec.encode(CMD_ALERT, 99, 777, p);              // rätt nyckel men nod 99 finns inte
        w.net.broadcast(&ok, p);
        AlarmPacket q;
        ok.codec.encode(CMD_ALERT, 4, 778, q);
        q.sender = 5;                                       // ändrat efter signering
        w.net.broadcast(&ok, q);
        std::vector<uint8_t> shortPkt(5, 0);
        for (FakeRadio *r : w.radios) r->inbox.push_back(shortPkt);
        w.run(500);
        expectAll(w, 0, "okänd avsändare och trasiga paket");
    }

    // ===== 7. Serial-kommandon och lampor på ett kort (utan radio) =====
    {
        g_ms = 1000000;
        NodeController n;
        n.begin(1);
        auto type = [&](const char *s, uint32_t adv = 60) { g_serialIn = s; g_ms += adv; n.update(); };
        auto pins = [&](int x, int l, int r) { return g_pin[2] == x && g_pin[23] == l && g_pin[22] == r; };
        CHECK(pins(0, 0, 0), "start: lamporna ska vara släckta");
        type("n10\n"); type("a9\n");            CHECK(pins(0, 1, 0), "n10, a9 -> vänster (grön)");
        type("c");                              CHECK(pins(0, 0, 0), "c rensar");
        type("n3\n"); type("a2\n");             CHECK(pins(1, 0, 0), "n3, a2 -> X (samma trapphus)");
        type("c"); type("n7\n"); type("a2\n");  CHECK(pins(0, 1, 0), "n7, a2 -> vänster (grön, mot nod 8)");
        type("c"); type("n9\n"); type("a9\n");  CHECK(pins(1, 0, 0), "n9, a9 -> X");
        type("c"); type("n7\n"); type("a2\n"); type("a8\n"); CHECK(pins(0, 0, 0), "n7, larm 2 och 8 -> ingen väg");
        type("c"); type("n10"); g_ms += 900; type("", 0); type("a9"); g_ms += 900; type("", 0);
        CHECK(pins(0, 1, 0), "tal utan Enter räknas efter tidsgräns");
        type("c"); type("a99\n");               CHECK(pins(0, 0, 0), "okänt id ignoreras");
        type("x"); CHECK(pins(1, 0, 0), "x");  type("l"); CHECK(pins(0, 1, 0), "l");
        type("r"); CHECK(pins(0, 0, 1), "r");  type("o"); CHECK(pins(0, 0, 0), "o");
    }

    printf("%d kontroller, %d fel\n", checks, fails);
    printf(fails ? "FEL\n" : "ALLA OK\n");
    return fails ? 1 : 0;
}
