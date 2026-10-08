# Lag Check

**Ruckler verstehen. Ohne auf dein Spiel zuzugreifen.**

Eine kleine, unabhängige Windows-App für sporadische Freezes, Ruckler und
Rubberbanding. Starte eine Messung, markiere den bemerkten Ruckler und lies danach
die verständliche Auswertung. Kein Konto, keine Telemetrie, kein Optimierer.

[Windows-Version herunterladen](https://github.com/Relis-lol/lag-check/releases/latest)
· [Bedienung](docs/USAGE.md) · [Datenschutz](docs/PRIVACY.md)
· [Grenzen und Risiken](docs/SAFETY.md) · [Technische Quellen](docs/MEASUREMENTS.md)

## In drei Schritten

1. **ZIP entpacken**, den gesamten Ordner behalten und `LagCheck.exe` öffnen.
2. **Messung starten**, wie gewohnt spielen und bei einem Lag **Bild hängt**,
   **Zurückgesetzt / Welt steht** oder **Anderer Ruckler** anklicken.
3. **Stoppen & auswerten**. Unter **Ergebnisse** stehen die Beobachtungen in
   verständlicher Sprache. Der lesbare Bericht öffnet sich auf Wunsch im Browser.

Alt-Tab ist erlaubt. Lass **Ich tabbe häufig raus** eingeschaltet.
Die Tasten F6/F7/F8 setzen Marker **nur bei aktivem App-Fenster**; keine globalen
Hotkeys, kein Overlay und keine Interaktion mit dem Spiel.

## Was du bekommst

- Start-/Stop-Buttons, Live-Karten und einen Verlauf für CPU, GPU und RAM.
- Drei Lag-Marker, lokale Sitzungshistorie und einen HTML-/Textbericht.
- Einsekunden-Messungen von CPU/Kernen, RAM/Commit, Datenträger, Netzwerk und
  verfügbaren GPU-Leistungszählern.
- Optionale ICMP-Proben zum aktiven IPv4-Default-Gateway und zwei öffentlichen
  Referenzzielen. Optionale Windows-Systemereignisse im Messzeitraum.
- Eine vorsichtige Einordnung: lokales Netz, Internetweg, PC-Auffälligkeit,
  offene Spielroute-/Servermöglichkeit oder Ursache unbekannt.
- **Datensparsamer Export**: neue JSON-Zusammenfassung aus ausgewählten Zahlen
  und Kategorien, ohne IPs, Gerätenamen, Pfade, Eventtexte oder absolute Zeiten.

**Die Software liefert Hinweise, keine bewiesene Ursache.** Hohe Spielelast,
Nachladen und Alt-Tab können auffällige Werte erzeugen. Ein sauberer Ping zu einem
Referenzziel beweist nicht, dass die Verbindung zum Spielserver störungsfrei ist.

## Anforderungen

- Windows 10/11 **64 Bit**, normale Desktop-Benutzersitzung.
- Portable ZIP: kein Python und keine Installation nötig. Den `_internal`-Ordner
  neben der EXE belassen.
- Aus dem Quellcode: Python **3.12 oder neuer**, inklusive Tkinter, sowie
  Windows PowerShell 5.1. Keine externen Python-Laufzeitpakete nötig.
- Kein Administrator erforderlich. Nicht verfügbare Counter werden als fehlend
  behandelt; GPU-Werte hängen vom Windows-Treiber ab.
- Freier Platz für lokale Sitzungen; je nach Hardware einige Dutzend MB pro Stunde.

Temperatur, GPU-Takt, ein zuverlässiges VRAM-Limit und FPS/Frametimes werden nicht
erfasst. Aktuell deutsche Oberfläche, IPv4-Ping, kein Linux/macOS/ARM-Build.

## Datenschutz und Sicherheit

Rohdaten liegen ausschließlich in `%LOCALAPPDATA%\LagCheck`. **Rohprotokolle können
lokale IPs, Adapterbezeichnungen, Zeitpunkte und Windows-Ereignistexte enthalten.**
Keine echten Sitzungen gehören in GitHub-Issues oder Pull Requests.
Zum Teilen ausschließlich den datensparsamen Export verwenden und ihn vorher prüfen.

Bei aktivierten Netzwerkproben erzeugt die App etwa drei kleine ICMP-Proben pro
Sekunde. Die Referenzziele sind die öffentlichen Dienste von Cloudflare und Google;
sie sehen technisch die Absenderadresse. Die öffentlich dokumentierten Zieladressen
im Quellcode sind keine persönlichen Messdaten. Netzwerkproben lassen sich vor
dem Start ausschalten. Keine Uploads, Analyse-Tracker oder Update-Anfragen.

Keine Injection, kein Lesen von Spielspeicher, keine Spieldateien/-logs, keine
Hooks/Overlays, keine Anti-Cheat-Schnittstellen, keine Registry-/TCP-Optimierungen,
kein Beenden oder Neustarten fremder Prozesse. Details: [Sicherheitsgrenzen](docs/SAFETY.md).

**Benutzung auf eigene Verantwortung und ohne Garantie, soweit gesetzlich zulässig.**
Die MIT-Lizenz gilt für den Projektcode. Gesetzlich zwingende Rechte bleiben
unberührt. Lag Check ist kein offizielles Tool eines Spieleherstellers und keine
Zusage, dass ein bestimmter Anti-Cheat-Anbieter es erlaubt.

Die erste portable Veröffentlichung ist **nicht digital signiert**. Prüfe Herkunft
und SHA-256-Prüfsumme. Bei Zweifeln nicht ausführen; Schutzsoftware nicht abschalten.

## Aus dem Quellcode starten

```powershell
git clone https://github.com/Relis-lol/lag-check.git
cd lag-check
py -3 run.py
```

Alternativ `start.cmd` doppelklicken. Eine Messung startet erst nach Klick auf
**Messung starten**. Das Schließen während einer Messung bietet einen regulären
Stop mit Auswertung an; Minimieren lässt die Messung weiterlaufen.

## Entwicklung und Build

```powershell
py -3 -m unittest discover -s tests -v
py -3 scripts/check_publish.py
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-build.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm LagCheck.spec
```

Ergebnis: `dist\LagCheck\LagCheck.exe`. Die GitHub-Actions-Pipeline prüft Tests,
Publikationshygiene und einen echten Windows-Messlauf; anschließend baut sie die
portable ZIP samt Lizenzen und Prüfsumme auf einem frischen GitHub-Runner.

Siehe [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) und
[CHANGELOG.md](CHANGELOG.md). Beiträge sind willkommen, die Beobachtung und
Verständlichkeit verbessern, ohne Spiele anzufassen oder Datenschutz zu schwächen.

## Lizenz

[MIT](LICENSE), Copyright 2026 Relis-lol und Mitwirkende.
Python/Tcl/Tk und Build-Komponenten behalten ihre eigenen Lizenzen. Die portable
ZIP enthält die zugehörigen Lizenztexte unter `third-party-licenses`.
