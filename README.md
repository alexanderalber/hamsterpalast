# Hamsterpalast

Mehrkammerhaus als Burg, für den Lasercutter. Haupthaus mit drei Kammern plus Turm
(Schlafkammer), ohne Boden, Deckel abnehmbar.

3D-Ansicht im Browser: **https://alber.me/hamsterpalast/**

`hamsterpalast.py` ohne Argumente ausführen (nur Standardbibliothek). Ergebnis in `docs/`:

- `svg/blatt_1.svg` … `svg/blatt_3.svg`: Schnittpläne, 600 x 400 mm
- `svg/vorschau.svg`: Frontansicht und Grundriss
- `model.js`: 3D-Daten für `index.html` (WebGL2, keine Bibliotheken, läuft auch per `file://`)

`docs/` ist die Quelle für GitHub Pages. Nach jeder Parameteränderung neu erzeugen und
`docs/` mit committen, sonst zeigt die Webseite den alten Stand.

## Farben in den SVGs

| Farbe | Bedeutung |
|---|---|
| rot `#ff0000` | schneiden |
| blau `#0000ff` | ritzen/gravieren (Mauerwerk, Torbogen, Fenster), schwach, schnell |
| grün | nur Beschriftung, Ebene **ausschalten** |

Gravur liegt auf der Außenseite: Teile mit der schönen Seite nach oben schneiden.
Reihenfolge in der Lasersoftware: Gravur, dann Innenschnitte, dann Außenkonturen.

## Vor dem Schneiden

1. Materialstärke messen, `T` oben im Skript setzen, neu erzeugen.
2. Nur die drei `Probe`-Teile schneiden (unten auf Blatt 2). Finger und Lasche sollen
   stramm, aber ohne Hammer passen. Zu locker: `KERF` erhöhen, zu stramm: senken.
3. Andere Plattengröße: `SHEET_W`, `SHEET_H`. Zwerghamster: `HAMSTER = "zwerg"`
   (kleinere Durchgänge).

## Material

Unbehandeltes Pappel- oder Birkensperrholz, 4 mm. Kein MDF (Bindemittel, quillt bei Urin).
Kein Lack, keine Beize. Kleber: wasserbasierter Holzleim, vor dem Einsetzen gut durchtrocknen
lassen. Rußige Brandkanten innen kurz anschleifen.

## Zusammenbau

1. Haupthaus: vorne, hinten, links, rechts über die Fingerzinken verleimen.
   Bei der rechten Wand ist „links = vorne“, Durchgang also hinten.
2. Trennwände von oben mit den Laschen in die Schlitze von Vorder- und Rückwand.
   Trennwand 1 (Durchgang hinten) neben Kammer 1, Trennwand 2 (Durchgang vorne) daneben.
   So entsteht ein Zickzackweg: Eingang, Kammer 1, 2, 3, Turm.
3. Auflageleisten innen an linke und rechte Wand leimen, Oberkante bündig mit den
   Trennwänden (140 mm). Beim Turm an die beiden Seitenwände, Oberkante 175 mm.
4. Turm wie das Haupthaus zusammensetzen, mit „Turm links“ an die rechte Hauswand,
   hinten bündig, damit die Durchgänge fluchten. Verleimen oder lose stellen.
5. Griffe in die Deckelschlitze leimen. Deckel liegen lose zwischen den Zinnen.

## Maße und Hamster-Hinweise

- Außen 500 x 200 mm, Haus 165 mm, Turm 200 mm hoch.
- Kammern innen ca. 115 x 192 mm, Turm 132 x 132 mm.
- Durchgänge Goldhamster 70 x 80 mm (Zwerg 55 x 65).
- Lüftung nur über 4 mm breite Schießscharten: zu schmal, um Kopf oder Pfote einzuklemmen.
- Ohne Boden: in die Einstreu stellen, der Hamster kann darunter graben, zum Kontrollieren
  einfach Deckel abheben.
- Turmdach liegt auf ca. 18 cm. Nichts danebenstellen, über das der Hamster aufs Dach
  klettern kann (Sturzhöhe).
