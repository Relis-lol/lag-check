# Messquellen und Interpretation

Alle englischen PDH-Counterpfade stehen in `lagcheck/native.py` unter `COUNTERS`.
`PdhAddEnglishCounterW` funktioniert auch auf lokalisiertem Windows. Es werden
keine Counter registriert oder Systemeinstellungen geschrieben.

| Messung | Quelle / Definition |
|---|---|
| CPU / logische Kerne | `Processor(*)\% Processor Time` |
| Grober CPU-Takt | `Processor Information(_Total)\Processor Frequency` |
| RAM | `GlobalMemoryStatusEx`, Gesamtmenge und verfügbar; Belegungsanteil berechnet |
| Commit | `Memory\Committed Bytes`, `Commit Limit`, `% Committed Bytes In Use` |
| Paging | `Memory\Pages Input/sec` und `Pages Output/sec`; auch dateibasierte Seiten |
| Pagefile-Belegung | `Paging File(_Total)\% Usage`; keine exklusive Pagefile-I/O-Messung |
| Datenträger | `PhysicalDisk(*)`: 100 minus `% Idle Time` (auf 0–100 begrenzt), Bytes/s, momentane Queue und Antwortzeit |
| Netzwerk | `Network Interface(*)`: RX/TX Bytes/s, kumulative Fehler/Discards |
| TCP-Neusendungen | `TCPv4` und `TCPv6\Segments Retransmitted/sec`; systemweit |
| Adapterstatus | `GetIfTable`; keine Paketmitschnitte |
| Gateway | `Get-NetRoute` plus `Get-NetIPInterface`, verbundene IPv4-Default-Route mit niedrigster Gesamtmetrik; alle 30 s |
| Ping | `IcmpSendEcho`, 800 ms Timeout, unabhängige Threads pro Ziel |
| GPU | `GPU Engine(*)\Utilization Percentage`: Summe der Prozessinstanzen je Hardware-Engine, danach Maximum der Engines; 3D/Copy separat |
| VRAM | `GPU Adapter Memory(*)\Dedicated Usage`; pro Adapter und als Summe, kein verlässliches Kapazitätslimit |
| Windows-Ereignisse | `Get-WinEvent`, System-Protokoll nur im Messzeitraum; Warnungen/Fehler sowie ausgewählte Hardware-/Netzwerkprovider |

Die Rohdateien enthalten die zusätzlichen Counter auch dann, wenn die Oberfläche
nur die wichtigsten Werte zeigt. Ein fehlender Wert bleibt leer. Temperaturen,
GPU-Takt, Framezeiten und Auslastung einzelner Spielprozesse sind nicht enthalten.

## Zeit und Abdeckung

CSV: UTC mit Millisekunden. Oberfläche: lokale Windows-Zeit. Monotone Zeit und
Intervalllänge werden zusätzlich erfasst. Der Systemtimestamp bezeichnet den
Abfragebeginn; Counter beschreiben überwiegend das davorliegende Zeitintervall.
Millise­kunden im Timestamp bedeuten keine millisekundengenaue Ursachenmessung.

Die Analyse betrachtet ±10 Sekunden. Für einen unauffälligen Ping-Befund werden
mindestens 16 erfolgreiche Proben benötigt, eine Abdeckung bis mindestens −8/+8 s,
keine Lücke über 2,5 s, keine Fehler und eine brauchbare Baseline. Ein Gateway-Wechsel
im Fenster verhindert „unauffällig“. Zeitumstellungen/Suspend können die zeitliche
Zuordnung stören; keine Entwarnung aus lückenhaften Daten ableiten.

## Baselines und Hinweise

- Ping-Baseline: Median erfolgreicher Proben derselben Sitzung und desselben
  Zielwerts, außerhalb aller Markerfenster; mindestens 10 Werte. Spike bei mehr
  als Baseline + 100 ms. Ohne erfolgreiche Baseline kann ICMP generell blockiert sein.
- Hardware-Baseline: Median/P95/Maximum außerhalb aller Markerfenster.
- CPU, RAM, Commit oder Datenträger ab 95 %, einzelner Kern ab 99 %: Hinweis,
  keine bewiesene Ursache. GPU ab 95 % ist lediglich eine Notiz über hohe Last.
- Dynamische Schwellen: mindestens dreimal P95 bei mindestens 10 Baselinewerten;
  zusätzlich Untergrenze Queue 2, Antwortzeit 50 ms, Pages Input 1.000/s,
  TCP-Neusendungen 10/s.
- GPU-Abfall um mindestens 50 Prozentpunkte: Notiz, allein keine Einstufung als
  Hardwarefehler. Bei angegebenem Alt-Tab wird dieser Zusammenhang ausdrücklich erwähnt.
- Adapterfehler: nur positive Differenzen, keine alten kumulativen Fehler zählen.
- Hardware-/Treiberereignisse: enge Liste relevanter Provider und IDs für die
  Kategorie; andere Systemereignisse bleiben im lokalen CSV für manuelle Prüfung.

Kategorien priorisieren lokale Ping-Probleme, dann externe Ping-Probleme, dann
zeitgleiche PC-Auffälligkeiten. Alle weiteren Beobachtungen bleiben im Bericht.
Eine Server-/Spielroute-Möglichkeit wird nur bei RUBBERBAND, drei sauberen
Referenzmessungen und vollständigem Systemfenster genannt. Fehlende einzelne
Hardwarezähler bleiben trotzdem eine Grenze; es handelt sich um keinen Ausschluss
aller lokalen Ursachen. IPv6-Verbindungen, spezifische VPN-Routen und Spielverkehr
werden durch diese drei IPv4-Proben nicht vollständig abgebildet.

## Primärquellen

- [Windows PDH-Abfrage](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhcollectquerydata)
- [Englische Counterpfade](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddenglishcounterw)
- [Systemspeicherstatus](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex)
- [ICMP Echo](https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpsendecho)
- [Windows-Ereignisse](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent)
