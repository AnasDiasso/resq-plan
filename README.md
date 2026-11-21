# resq_led: utrymningspilar med Dijkstra och ESP-NOW

Varje nod har tre lampor: röd **X** (GPIO2), grön pil **LEFT** (GPIO23) och gul pil **RIGHT** (GPIO22), samt en knapp (GPIO4 till GND).
Noden vet var den sitter i byggnaden (`topology.json`) och räknar själv ut **snabbaste vägen ut** med Dijkstra,
utan att gå genom noder som larmar. Den som larmar visar X. Alla andra visar pilen mot närmaste utgång.

## Snabbstart: ett kort + gränssnittet
Målet: du trycker på knappen på kortet, kortets röda lampa (X) tänds, och noden larmar på kartan i webbläsaren.
1. Skapa `.env`: `python3 tools/setup.py 2` (byt 2 mot nodens nummer på kartan). Det skapar nyckel och kanal åt dig.
2. Öppna mappen i VS Code (PlatformIO), koppla kortet med USB och klicka **Upload** (pilen). Håll in **BOOT** om det hänger på "Connecting...".
3. Stäng Serial Monitor om den är öppen (bara ett program kan använda USB-porten).
4. `pip install pyserial` (en gång), och starta sedan gränssnittet: `python3 sim/server.py --port auto`. Skriver den "Hittade inget kort" kan du ange porten själv: `--port COM3` (Mac: `/dev/cu.usbserial-...`, Linux: `/dev/ttyUSB0`).
5. Öppna http://127.0.0.1:8000. Under "Riktiga kort" ska det stå `nod 2` (kortet presenterar sig när anslutningen öppnas, det tar någon sekund).
6. Tryck på knappen på kortet: röda X tänds på kortet, och på kartan syns larmet på nod 2. De andra noderna på kartan visar sina pilar. Tryck igen för att stänga av. Du kan också klicka på noden på kartan, det är samma sak som att trycka på knappen.

Ska flera kort kopplas till samma dator: kör `python3 tools/setup.py <nr>` före varje uppladdning. Nyckeln och kanalen behålls, så alla kort får samma.

## Kom igång
1. Öppna mappen `resq_led` i VS Code (PlatformIO).
2. Skapa `.env`: `cp .env.example .env` och fyll i:
   - `NODE_ID`: kortets nummer i `topology.json` (olika för varje kort).
   - `ESPNOW_CHANNEL`: Wi-Fi-kanal 1-13, **samma på alla kort** (standard 1).
   - `GROUP_KEY`: gruppnyckel, **samma på alla kort**. Skapa med `python3 -c "import secrets; print(secrets.token_hex(16))"`.
3. Ladda upp med pilen i PlatformIOs blå lista. Håll in **BOOT** på kortet om det hänger på "Connecting...".
4. Öppna Serial Monitor (115200). Du ser `ESP-NOW klar. MAC: ...` och `Jag ar nod <nr>`.
5. För nästa kort: ändra bara `NODE_ID` i `.env` och ladda upp igen.

Vid bygget skapar `scripts/load_env.py` filen `include/secrets.h` av `.env`, och bygget stoppas med ett tydligt fel om något saknas, står kvar som `CHANGE_ME` eller om `NODE_ID` inte finns i `topology.json`.

## Så fungerar larmet
- **Tryck på knappen** på nod X: X-lampan tänds och noden skickar ett signerat larm med sitt nummer till alla (ESP-NOW broadcast, ingen router behövs).
- **Alla andra noder** tar emot larmet, räknar ut snabbaste vägen ut utan att passera X och tänder rätt pil.
- **Tryck igen** på samma knapp: X blinkar 3 gånger, sedan skickas en avstängning och nod X:s larm släcks hos alla. Avstängningen skickas en gång till efter 2 sekunder.
- **Flera larm** samtidigt fungerar. Varje larm gäller i 5 minuter.
- **Missade paket:** broadcast har ingen kvittens. Därför skickas varje meddelande i tre kopior, och en larmande nod upprepar sitt larm var 10:e sekund så att noder som missat det hinner ikapp. Upprepningarna förlänger inte tiden de andra noderna visar larmet.
- **Signering:** varje paket (14 byte) har nodens nummer, ett slumptal och en HMAC-SHA256 med gruppnyckeln. Paket med fel nyckel, ändrat innehåll, okänt nodnummer eller en dubblett kastas.

## Testa med Serial (ett kort)
| Kommando | Gör |
|---|---|
| `n10` + Enter | Låt kortet vara nod 10 (test) |
| `a9` + Enter | Simulera lokalt att nod 9 larmar. Kortet visar sin pil, och Serial skriver vägen och längden |
| `c` | Rensa alla larm |
| `s` | Visa status |
| knappen | Larma på riktigt (skickas till alla kort). Tryck igen för att stänga av |
| `x`, `l`, `r`, `o` | Tänd X, vänster, höger, släck (lamptest) |
| `0`-`4` | Lägen (skriver bara ut) |

Kommandona simulerar bara lokalt och skickas inte till andra kort. Skriv numret och tryck Enter, eller vänta en sekund efter sista siffran.
Exempel: `n13`, Enter, `a9`, Enter. Kortet är nod 13 och larmet kommer från nod 9, så den gröna pilen tänds (mot trapphuset till höger).
Byt `n` och testa alla noder på kartan med samma kort. Bilderna i `docs/scenarier/` visar vad varje nod ska visa.

## Kartan: topology.json
Det är den enda filen du redigerar. `scripts/gen_topology.py` gör om den till `include/topology.h` vid varje bygge och stoppar bygget med ett tydligt fel om något är fel.
- `nodes`: `id`, `name`, `floor`, `x` och `y` (pixel i `docs/karta.png`, bara för bilder), och `exit_m` + `exit_lamp` för utgångar.
- `edges`: riktade kanter `from -> to` med `m` (meter) och `lamp` (vilken pil på `from` som pekar mot `to`).

**Avstånden är uppskattade ur kartbilden.** Skalan är 0,05 m per pixel och en trappa är 12 m. Ersätt med riktiga mått i `topology.json`. `tools/make_topology.py` visar hur siffrorna togs fram.

## Så är kartan tolkad (rätta i topology.json)
1. **Utgångar** är nod 1 och nod 4: entréplanet. Lampan "ut" där är grön (LEFT), enligt bildens trianglar.
2. **Trapporna går ner** mot entréplanet: 3 -> 2 -> 1 och 6 -> 5 -> 4. Vilken lampa som pekar ner avgörs av bildens trianglar (se punkt 6).
3. **Korridoren och rummen** (nod 7-16) ligger på samma plan som nod 3 och 6. Korridoren kopplar ihop de två trapphusen: nod 3 <-> 7 och nod 13 <-> 6. Lamporna där följer bildens trianglar.
4. **Ingen väg över mitten.** Den vita ytan mellan trapphusen är ett tomrum, så det finns ingen väg mellan vänster och höger trapphus på plan 1 och 2.
5. **Rummen** i söder (nod 14, 15, 16) pekar bara ut mot korridoren. Ingen väg leder in i dem.
6. **Lamporna följer bildens orange trianglar.** På varje nod är den **vänstra triangeln LEFT (grön, GPIO23)** och den högra **RIGHT (gul, GPIO22)**. `python3 tools/extract_lamps.py` läser `docs/karta.png`, hittar trianglarna och korsen, väljer för varje väg den triangel som pekar närmast riktningen mot grannen och skriver om `lamp` i `topology.json`. Den skriver också `sim/lamps.json` (för simulatorn) och `docs/lampor_per_nod.md` (kopplingstabell). Där en triangel inte pekar mot grannen (nod 3, 6, 7, 8, 9, 11, 13, 14, 15, 16) är valet osäkert och markerat i tabellen: rita om pilen i bilden eller ändra `lamp` för hand. **Ändras lamporna måste korten laddas upp på nytt.** Varje nod har bara två pilar, så varje granne måste ha sin egen. Generatorn varnar annars.
7. **Zoner** (valfritt `zone` i `topology.json`) kan stänga flera noder samtidigt när en larmar. De används inte just nu.

## Simulator: karta i webbläsaren (Python)
En karta som visar vad som händer mellan noderna. Trycker du på knappen på ett riktigt kort tänds X på kortet **och** på kartan, på den position noden har. De andra noderna på kartan är virtuella och tänder sina trianglar enligt samma vägval som kortet (`sim/routing.py` är testad mot C++-koden). Du kan också klicka på valfri nod på kartan för att larma eller stänga av den.

**Utan kort (bara simulering):**
```
python3 sim/server.py
```
Öppna sedan http://127.0.0.1:8000. Simulatorn visar `docs/karta_ren.png`: din karta utan trianglar, kryss och blå prickar, så att den ritar dem själv. Skapa om den efter att du bytt `docs/karta.png`: `python3 tools/make_clean_map.py` (fyller i bakgrunden automatiskt, så små suddiga fläckar kan synas vid väggar). Finns den inte används originalkartan.

**3D-vy:** knappen uppe till höger på kartan växlar mellan platt karta och våningarna som plan under varandra (plan 3 överst, entréplanet längst ner). Trapphusen ritas som tunna streckade linjer bakom plattorna, som går ner genom alla våningar, våningen med larm får röd glöd och skylt, och reglaget "lutning" ändrar vinkeln. Vägen ut ritas genom trapphusen. Allt annat (lampor, larmvågor, drag av noder, gropar) fungerar likadant. Valet sparas i webbläsaren. Plattornas gränser i bilden står i `SL` i `sim/web/index.html` om du byter karta.

Animationer: röda krysset pulserar, larmet sprider sig som röda ringar från larmande noder, och när du håller musen över en nod löper en puls längs vägen ut (avstängt om datorn är inställd på minskad rörelse).

**Flytta noder:** dra en nod bort från sin plats så tas den bort och lämnar en grop ("saknas"). Den tänds inte, kan inte larma och tar inte emot larm. Dra tillbaka den från rutan "Lösa noder" och släpp på gropen för att sätta dit den igen. En nod kan bara sättas tillbaka på sin egen plats (id hör ihop med kortet). Övriga noders vägval ändras inte när en nod saknas, eftersom kortens karta är fast och grannsystemet inte finns än. Riktiga kort kan inte dras bort.

Kartans orange trianglar täcks av grå (släckt), grön (LEFT tänd) eller gul (RIGHT tänd), och krysset är grått eller rött.

**Med ett eller flera riktiga kort:**
1. `pip install pyserial` (behövs bara för USB-kopplingen).
2. Koppla kortet med USB. Stäng PlatformIOs Serial Monitor, eftersom bara ett program kan använda porten.
3. Hitta porten: `python3 sim/server.py` listar portarna om pyserial finns (Windows: `COM3`, macOS: `/dev/cu.usbserial-...`, Linux: `/dev/ttyUSB0`).
4. Starta: `python3 sim/server.py --port COM3` (flera kort: `--port COM3 --port COM5`).

Kartan visar:
- **Rött kryss** på noder som larmar, **gröna och gula pilar** som kortet visar, och **UT** vid utgångarna.
- **Blå ring** runt noder med riktigt kort. Ringen blir **grön** när kortets lampor stämmer med simuleringen, och **röd** om kortet visar något annat.
- Håll muspekaren över en nod: väg ut, avstånd och plan. Hela vägen ritas på kartan.
- Klicka på en virtuell nod: larmet skickas även till de riktiga korten via USB, så att deras lampor följer med. Klicka på en nod med riktigt kort: det är som att trycka på kortets knapp, och larmet skickas över ESP-NOW till övriga kort.
- Till höger: larm just nu, anslutna kort och en händelselogg.

**Så pratar kortet med Python:** kortet skriver rader som `EVT ALARM_ON 3 own` och `EVT SIGNAL 3 X` på Serial, och tar emot kommandona `b` (tryck knappen), `a<nr>`, `d<nr>` och `c`. Du kan använda samma kommandon i Serial Monitor.

**Att veta:**
- Larm från **virtuella** noder skickas bara till de kort som är anslutna till datorn via USB. Andra kort som inte sitter i datorn hör dem inte, eftersom de inte går över ESP-NOW.
- Kartan servas bara på den här datorn (127.0.0.1) och har ingen inloggning. Lägg inte ut den på ett öppet nät.
- Kortet startar om när porten öppnas. Det är normalt. Simulatorn ger kortet sina larm igen efteråt.
- `python3 sim/test_sim.py` testar simulatorn mot noden. Där körs samma C++-kod som kortet kör, som ett vanligt program (`host_test/node_host`).

## Begränsningar
- **Ingen loggning mot servern än.** Python-servern (`resq.zip`) tar emot händelser över Wi-Fi/HTTP, men den är inte inkopplad i det här projektet.
- **Gemensam nyckel:** alla noder har samma `GROUP_KEY`. Den som kommer åt ett kort kan läsa ut den ur flashminnet och skicka larm som vilken nod som helst.
- **Uppspelning:** skyddet mot uppspelning kommer ihåg de senaste 32 paketen. Ett inspelat larm som spelas upp efter längre tid kan godkännas och ge ett falskt larm i högst 5 minuter. Det går att stänga av från nod X:s knapp.
- **Missad avstängning:** om en nod missar båda avstängningarna visar den larmet tills de 5 minuterna är slut.
- Varje nod har bara två pilar. Har en nod fler än två vägar kan den bara visa två riktningar.
- Finns ingen väg ut (alla vägar blockerade) släcks pilarna. Nodens X-lampa lyser bara hos den som själv larmar.
- **Ström:** Wi-Fi-radion måste vara på hela tiden för att ta emot larm, så räkna med ca 80-100 mA per nod (klockan är satt till 80 MHz).
- Det här är ett hobbysystem. Det ersätter inte certifierad utrymningsskyltning eller brandlarm.

## Test
- `./host_test/run_sim.sh`: bygger och kör testerna på datorn. Där körs samma kod som på kortet (`node_controller`, `route`, `protocol`) i ett nät med alla 16 noder och en låtsasradio. Det testar larm, två larm samtidigt, avstängning med blinkning, 5-minuters-utgång, 60 % paketförlust, fel nyckel, uppspelning, okänd avsändare och trasiga paket, samt Serial-kommandon och lampor. Signaturen kontrolleras mot Python.
- `python3 sim/test_sim.py`: testar simulatorn och Python-vägvalet mot C++-koden (se Simulator ovan).
- `python3 sim/test_serial.py`: testar USB-kopplingen med en virtuell serieport (Linux/macOS, kräver pyserial).
- `python3 host_test/compare.py`: jämför vägvalet mot en oberoende Python-referens (437 scenarier).
- `python3 tools/render_map.py ut.png 9`: ritar kartan för ett larm.
- Testerna kräver `g++` och OpenSSL-utvecklingsfiler (`libssl-dev`) på datorn.
