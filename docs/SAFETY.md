# Grenzen, Verantwortung und Risiken

Lag Check ist ein unabhängiges Open-Source-Community-Projekt. Die Software wird
gemäß MIT-Lizenz ohne Garantie bereitgestellt. Nutzung auf eigene Verantwortung,
soweit rechtlich zulässig; zwingende gesetzliche Ansprüche bleiben unberührt.
Diese Hinweise erweitern oder beschränken die MIT-Nutzungsrechte nicht.

## Was die App nicht tut

Keine Spielprozess-Handles, kein Lesen von Spielspeicher oder Spieldateien/logs,
keine Injection, Hooks, Overlays oder Anti-Cheat-Schnittstellen. Keine automatischen
Optimierungen, Registry-/TCP-Änderungen, Treiberinstallationen, Dienständerungen,
Neustarts oder Beendigungen fremder Prozesse. Die App startet nur ihren eigenen
Messprozess und begrenzte PowerShell-Helfer für Systeminformationen.

Die pro Prozess übergebene PowerShell-Option `-ExecutionPolicy Bypass` gilt nur für
diesen Aufruf; sie schreibt keine systemweite Ausführungsrichtlinie. Sie ist
notwendig, um die mitgelieferten lokalen Helferscripts ohne Installation zu starten.
Gruppenrichtlinien können dies weiterhin verhindern; Fehler werden protokolliert.

## Was trotzdem zu beachten ist

- Jeder Monitor benötigt CPU, RAM, Datenträgerplatz und gegebenenfalls Netzwerk.
  Das kann empfindliche Situationen beeinflussen. Vergleiche bei Bedarf Messungen
  mit und ohne Monitor; es gibt keine garantierte Lastobergrenze.
- Pings messen ICMP zu Referenzzielen, nicht den UDP-/TCP-Verkehr des Spiels.
  Firewalls, VPNs, Mehrwege-Routing und Router-Priorisierung beeinflussen Ergebnisse.
- Ein Sample pro Sekunde kann kurze Aussetzer übersehen. Keine FPS-/Frametime-
  Messung, keine DPC/ISR-Traces, kein Temperatur- oder Throttling-Nachweis.
- Windows-Counter können fehlen, zeitverzögert sein oder treiberabhängig andere
  Bedeutungen haben. Fehlende Daten sind keine Entwarnung.
- Hohe CPU/GPU-Last, Speicherbelegung, Nachladen oder Alt-Tab beweisen keinen Defekt.
- Kein Beweis einer Schuld des Spiels, Servers, Providers oder eines Treibers.
- Keine generelle Freigabe durch Anti-Cheat-/Spielehersteller. Beachte deren Regeln
  und die Richtlinien deines Arbeitsplatzes/Netzwerks. Das Projekt verspricht keine
  Unentdeckbarkeit, Umgehung oder Sperrfreiheit.
- Rohlogs können persönliche Daten enthalten. Nicht ungeprüft hochladen.

Keine riskanten Änderungen allein aufgrund einer Kategorie vornehmen. Wiederholte
Hardwarefehler sollten mit geeigneter fachlicher Unterstützung untersucht werden.

## Bezug und Integrität

Offizielle Projektquelle: https://github.com/Relis-lol/lag-check

Die portable Erstveröffentlichung ist unsigniert. Prüfe die ZIP-Prüfsumme aus dem
Release und die Herkunft. Eine Prüfsumme bestätigt die Übereinstimmung mit dem
veröffentlichten Artefakt, ist aber kein unabhängiges Sicherheitszertifikat.
Bei Warnungen nicht pauschal Schutzfunktionen deaktivieren; im Zweifel nicht starten.

## Deinstallation

Messung regulär stoppen und App schließen. Danach den entpackten Programmordner
entfernen. Die getrennten Sitzungen unter `%LOCALAPPDATA%\LagCheck` bleiben erhalten,
bis du sie selbst löschst. Kein Autostart, kein Dienst, keine Registry-Einträge.
