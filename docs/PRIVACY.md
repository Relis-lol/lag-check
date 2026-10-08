# Datenschutz

Lag Check hat keinen Server, kein Benutzerkonto, keine Telemetrie, keine
Crash-Uploads und keine automatische Update-Prüfung. Alle Auswertungen finden
auf deinem Rechner statt. Ein Browserbericht lädt keine externen Inhalte.

## Netzwerkverkehr

Bei aktivierten Netzwerkproben sendet die App ICMP-Echo-Proben an das aktive
IPv4-Default-Gateway sowie öffentliche Referenzziele von Cloudflare und Google.
Die Ziele sehen technisch die Quelladresse der Verbindung. Die App ermittelt
keine öffentliche IP über einen separaten Webdienst. Proben sind optional.
„Passiv“ bedeutet beobachtend gegenüber dem Spiel/System, nicht vollständig
verkehrsfrei: Ping ist absichtlich erzeugter Diagnoseverkehr.

## Lokale Rohdaten

Gespeichert werden Zeitstempel, Leistungswerte, ausgewählte Netzwerkinformationen,
manuelle Marker und optional Systemereignisse. Darin können lokale Gateway-IPs,
Adapternamen, Interface-IDs, Laufwerksbezeichnungen, lokale Dateipfade und
Windows-Ereignismeldungen vorkommen. Sie sind **nicht zum öffentlichen Teilen gedacht**.

GPU-Engine-Counter werden von Windows teils mit Prozesskennungen bereitgestellt.
Die App fasst diese vor dem Speichern nach Hardware-Engine zusammen, öffnet keine
Spielprozesse und liest keine Speicherinhalte. Die eigene Speichernutzung wird
als Working Set des eigenen Monitors erfasst.

Speicherort: `%LOCALAPPDATA%\LagCheck`. Dateien werden nicht verschlüsselt und
nicht automatisch gelöscht; lokale Kontorechte und Backups gelten wie bei anderen
Benutzerdateien. Die App importiert oder veröffentlicht keine alten Diagnosesitzungen.

## Datensparsamer Export

Der Export wird aus einer **festen Positivliste** neu aufgebaut. Er enthält nur:

- Messdauer, Anzahl der Samples;
- aggregierte Ping-Statistik je abstrakter Zielbezeichnung;
- Markertyp, Kategorie, numerische Auffälligkeiten und relative Sekundenabstände.

Keine Kopie der Rohdaten und keine einfache Regex-Schwärzung. IPs, Zielwerte,
Host-/Gerätenamen, Pfade, Eventtexte, Freitexte und absolute Zeitstempel werden
nicht übernommen. Trotzdem vor dem Teilen prüfen: Auch Leistungsdaten verraten
etwas über das System und die Sitzung. Die App speichert den Export lokal und
verschickt ihn nicht selbst.

## Öffentliches Repository und Releases

Private Messdaten, Entwicklungsprotokolle, Umgebungsdateien und Builds sind durch
`.gitignore` ausgeschlossen. Ein zusätzlicher Veröffentlichungscheck prüft
getrackte Dateien auf Rohdaten, private IP-Literale, lokale Benutzerpfade und
übliche Token-/Schlüsselmuster. Diese Checks ergänzen eine Sichtprüfung und
garantieren keine Erkennung beliebiger Geheimnisse.

Die portable Release-Datei wird auf GitHub Actions aus dem geprüften Quellcode
gebaut. Sie enthält keine Sitzung vom Rechner der Entwickler.
