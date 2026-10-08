# Mitmachen

Danke für Verbesserungen! Bitte zuerst ein Issue mit klarer Beschreibung anlegen,
wenn sich Verhalten oder Datenschutz wesentlich ändern soll. Fehlerberichte
brauchen keine persönlichen Rohdaten. Nutze die Issue-Vorlage und höchstens den
geprüften datensparsamen Export.

## Lokal entwickeln

Python 3.12+, Windows für die tatsächliche Messung. Die reine Auswertung und ihre
Tests sind plattformunabhängig. Keine Laufzeitpakete erforderlich.

```powershell
py -3 -m unittest discover -s tests -v
py -3 scripts/check_publish.py
py -3 run.py
```

Für EXE-Builds eine isolierte virtuelle Umgebung und `requirements-build.txt`
verwenden. Keine privaten Sessions als Fixtures einchecken; Tests erzeugen klar
synthetische Daten in temporären Verzeichnissen.

## Grenzen für Beiträge

- Systembeobachtung, keine Game-/Anti-Cheat-Integration und keine Optimierer.
- Fehlende Werte bleiben fehlend; keine simulierten Messwerte in echten Sessions.
- Verständliche, vorsichtige Erklärungen. Korrelation ist keine Diagnose.
- Keine Telemetrie oder Uploads. Export nur per Positivliste.
- Änderungen an Analyse, Export und Worker-Lebenszyklus mit passenden Tests belegen.
- Tastaturbedienung, deutsche Texte und einen aufgeräumten UI-Fehlerzustand beachten.

Mit einem Beitrag bestätigst du, dass du ihn unter der MIT-Lizenz des Projekts
beisteuern darfst. Keine zusätzliche Rechteübertragung oder CLA erforderlich.
Diskussionen bitte respektvoll, sachlich und ohne persönliche Daten führen.
