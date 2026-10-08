# Bedienung

## Vor dem Spielen

Entpacke die Release-ZIP vollständig und öffne `LagCheck.exe`.
Auf der Seite **Messung** siehst du zunächst Striche: Es werden noch keine Daten
erfasst. Erst **Messung starten** beginnt die Aufzeichnung.

- **Netzwerkproben**: prüft Router sowie Cloudflare und Google ungefähr jede Sekunde.
  Ausschalten bedeutet, dass keine Netzwerk-Ursache eingeordnet werden kann.
- **Windows-Ereignisse**: liest beim Stop das Systemprotokoll nur für die Messdauer.
- **Ich tabbe häufig raus**: berücksichtigt deinen Hinweis bei GPU-Einbrüchen.
  Die App erkennt keinen Fensterfokus des Spiels und überwacht keine Eingaben.

Diese Optionen gelten jeweils für die ganze Sitzung und sind währenddessen gesperrt.
Andere Programme dürfen weiterlaufen. Lag Check ordnet ihnen keine Last zu.

## Bei einem Ruckler

Wechsle bei Bedarf zur App und klicke einen Marker:

| Button | Wann verwenden? |
|---|---|
| Bild hängt / F6 | Das Bild friert ein oder stottert sichtbar. |
| Zurückgesetzt / Welt steht / F7 | Du kannst dich bewegen, wirst aber zurückgesetzt; andere Figuren stehen. |
| Anderer Ruckler / F8 | Du bist unsicher oder möchtest einen allgemeinen Zeitpunkt markieren. |

F6–F8 funktionieren ausschließlich im App-Fenster. Es gibt keine globale
Tastenerfassung. Die Markierung erfolgt beim Klick/Tastendruck; Reaktionszeit und
Alt-Tab verzögern sie gegenüber dem wirklichen Beginn. Die Auswertung betrachtet
jeweils 10 Sekunden davor und danach. Kurz nach dem Marker nicht hart schließen.

## Stop und Ergebnisse

**Stoppen & auswerten** wartet bei einem frischen Marker nötigenfalls den Rest des
10-Sekunden-Nachher-Fensters ab. Danach werden Daten geschlossen, Systemereignisse
gelesen und Ergebnisse angezeigt. Das kann einige Sekunden dauern.

Wähle unter **Ergebnisse** eine Sitzung. Du kannst die Erklärung in der App lesen,
den lokalen Browserbericht öffnen oder eine datensparsame Zusammenfassung speichern.
Ein „PC-Hinweis“ bedeutet zeitliche Nähe einer Auffälligkeit, keinen bewiesenen
Hardwaredefekt. „Spielroute / Server“ ist eine unbestätigte Möglichkeit.

Wenn kein echter großer Lag aufgetreten ist, liefert die Sitzung keine belastbare
Diagnose für einen früheren großen Lag. Es gibt keine automatische Reparatur.

## Daten verwalten

Alle Sitzungen bleiben in `%LOCALAPPDATA%\LagCheck\sessions`.
**Datenordner** öffnet den Explorer. Entferne alte Sitzungen bei gestoppter Messung
manuell, wenn du sie nicht mehr brauchst. Keine automatische Löschung.

Ein Stromausfall oder erzwungenes Beenden kann die letzte Zeile oder Auswertung
unvollständig lassen. Die App kennzeichnet solche Sitzungen als unvollständig.
Die gespeicherten Rohdaten bleiben erhalten. Die erste Version hat keine
automatische Wiederherstellung einer abgebrochenen Sitzung.

## Fehlende Werte / Startprobleme

Ein Strich ist ein fehlender Wert, keine gemessene Null. GPU-Counter fehlen bei
manchen Treibern/VMs. Blockierte ICMP-Antworten sind keine automatische Diagnose
einer kaputten Verbindung. Bei einem Startfehler liegt `worker.log` im Datenordner;
dieses Protokoll vor einer Weitergabe auf persönliche Daten prüfen.

Bitte keine Windows-Schutzfunktionen abschalten oder als Standardlösung höhere
Rechte vergeben. Nutze bei Unsicherheit die Quellcode-Version oder melde einen
Fehler ohne Rohprotokolle.
