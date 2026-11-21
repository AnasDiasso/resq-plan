# Lampor per nod (kopplingstabell)

Skapad av `tools/extract_lamps.py` ur kartbilden. Varje nod har två pilar (trianglar) i bilden.
På varje nod är den **vänstra triangeln** den gröna pilen (LEFT, GPIO23) och den **högra** den gula pilen
(RIGHT, GPIO22). Tabellen visar åt vilket håll respektive triangel pekar i bilden, och hur många grader fel
den pekar mot det den ska visa (0° är rakt åt rätt håll). **Osäker** betyder mer än 60° fel: ingen av
trianglarna pekar åt grannen (t.ex. vid trapphusen). Rita om pilen i bilden eller välj lampa för hand i `topology.json`.

| Nod | Namn | Grön pil (LEFT) pekar | fel | Gul pil (RIGHT) pekar | fel | |
|---|---|---|---|---|---|---|
| 1 | Trapphus vä plan 1 (entré) | upp | 0° | ner | - |  |
| 2 | Trapphus vä plan 2 | upp | 0° | ner | - |  |
| 3 | Trapphus vä plan 3 | höger | 83° | vänster | 92° | **osäker** |
| 4 | Trapphus hö plan 1 (entré) | upp | 0° | ner | - |  |
| 5 | Trapphus hö plan 2 | upp | 0° | ner | - |  |
| 6 | Trapphus hö plan 3 | höger | 77° | vänster | 93° | **osäker** |
| 7 | Korridor/rum plan 3 – korridor vä (B1) | höger | 56° | vänster | 85° | **osäker** |
| 8 | Korridor/rum plan 3 – dörr 1 (B2) | upp | 34° | ner | 90° | **osäker** |
| 9 | Korridor/rum plan 3 – dörr 2 (B3) | upp | 52° | ner | 87° | **osäker** |
| 10 | Korridor/rum plan 3 – korridor mitt (B4) | höger | 46° | vänster | 38° |  |
| 11 | Korridor/rum plan 3 – dörr 3 (B5) | upp | 45° | ner | 87° | **osäker** |
| 12 | Korridor/rum plan 3 – dörr 4 (B6) | höger | 9° | vänster | 2° |  |
| 13 | Korridor/rum plan 3 – korridor hö (B7) | upp | 13° | ner | 101° | **osäker** |
| 14 | Korridor/rum plan 3 – rum söder 1 (B8) | höger | - | vänster | 80° | **osäker** |
| 15 | Korridor/rum plan 3 – rum söder 2 (B9) | höger | 83° | vänster | - | **osäker** |
| 16 | Korridor/rum plan 3 – rum söder 3 (B10) | höger | 71° | vänster | - | **osäker** |
