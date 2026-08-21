# LOCAL_AI_SETUP_CHECKLIST.md – Manuelle Verifikation der automatisierten
lokalen KI-Einrichtung (§68)

Diese Checkliste prüft den kompletten automatisierten Ablauf `Hardware erkennen →
Modell empfehlen → Ollama installieren → Modell herunterladen → Health Check → bereit`
auf einem echten Windows-Rechner. Die zugrunde liegende Logik ist durch
Unit-/Integrationstests mit Fakes abgesichert (siehe `tests/test_local_ai_*.py`) - diese
Checkliste prüft den ECHTEN Ablauf gegen ein echtes System, wie er in
ARCHITECTURE.md §66 für den KI-Kernpfad bereits einmal durchgeführt wurde.

**WICHTIG (CLAUDE.md-Grundregel):** Ausschließlich synthetische Testdaten verwenden -
niemals echte Mandantendaten. Ein frischer/isolierter Rechner (oder eine VM) wird
empfohlen, damit "Ollama bereits installiert" vs. "Ollama fehlt" beide Pfade sauber
geprüft werden können.

---

## A. Ausgangszustand (frischer Rechner ohne Ollama)

- [ ] Windows 10/11 (64-Bit), Lexoron-Projekt/-Installation vorhanden
- [ ] `ollama --version` liefert "command not found" (Ollama NICHT installiert)
- [ ] `.env`: `LOCAL_AI_ENABLED` fehlt oder `false`

## B. Hardware-Erkennung & Empfehlung

- [ ] `LocalAiSetupService().get_recommendation()` liefert ein `HardwareProfile` ohne
      Absturz, auch wenn einzelne Werte nicht ermittelbar sind
- [ ] Angezeigte Hardwareklasse plausibel (RAM/CPU/GPU stimmen mit Task-Manager/
      Systeminformationen überein)
- [ ] Primärempfehlung + mind. eine Alternative vorhanden, mit menschenlesbarer
      Begründung (keine rohen Zahlen/Ports/Modell-IDs ohne Kontext)

## C. Automatisierte Einrichtung (`LocalAiSetupService.run_setup`)

- [ ] Ollama-Installer wird von der offiziellen Quelle geladen (`ollama.com/download/...`
      → Weiterleitung auf `github.com/ollama/ollama/releases`, HTTPS)
- [ ] Installation läuft unbeaufsichtigt durch (keine Dialoge, die auf Klicks warten)
- [ ] `ollama --version` liefert danach eine Versionsnummer
- [ ] Empfohlenes Modell wird heruntergeladen (Fortschritt in den Logs sichtbar)
- [ ] Nach Abschluss: `ollama list` zeigt das erwartete Modell
- [ ] Health Check erfolgreich (`OllamaLocalLLMProvider.check_health()`:
      `reachable=True`, `model_available=True`)
- [ ] `.env` enthält danach `LOCAL_AI_ENABLED=true` und `OLLAMA_MODEL=<gewähltes Modell>`
- [ ] KEIN anderer `.env`-Wert wurde verändert (insbesondere `SESSION_SECRET_KEY`
      unverändert)

## D. Automatischer Start / Statusprüfung

- [ ] Lexoron-Prozess neu starten
- [ ] `LocalAiSetupService().get_status()` liefert `LocalAiState.READY`, OHNE dass der
      Benutzer Ollama manuell startet
- [ ] Rechner neu starten, Ollama-Tray-Prozess prüfen (sollte laut offiziellem
      Installer automatisch mitstarten) - Status danach weiterhin `READY`
- [ ] Falls Ollama nach einem Neustart NICHT automatisch läuft: Status meldet
      `RUNTIME_UNREACHABLE` (nicht fälschlich `READY` oder `RUNTIME_MISSING`)

## E. Negativfälle (jeweils einzeln, Zustand danach zurücksetzen)

- [ ] Ollama-Prozess manuell beenden → `get_status()` meldet `RUNTIME_UNREACHABLE`
- [ ] Modell manuell entfernen (`ollama rm <modell>`) → `get_status()` meldet
      `MODEL_MISSING`
- [ ] `LOCAL_AI_ENABLED=false` setzen → `get_status()` meldet `DISABLED`
- [ ] Setup mit absichtlich zu wenig freiem Speicherplatz (z. B. auf einem fast vollen
      Laufwerk) starten → Download startet NICHT, verständliche Fehlermeldung

## F. End-zu-Ende (produktiver Pfad)

- [ ] Mit `LOCAL_AI_ENABLED=true`: einen Testentwurf über `DraftingService` erzeugen
      (ausschließlich synthetische Aktendaten) - Presidio → Ollama → Claude → lokale
      Rekonstruktion läuft real durch (wie in ARCHITECTURE.md §66 bereits einmal
      verifiziert)
- [ ] Reale Latenz erneut dokumentieren (variiert je nach Hardware - siehe §66 für den
      Referenzwert einer CPU-only-Legacy-Maschine)

---

**Ergebnis festhalten:** Datum, Windows-Version, Hardwareklasse, gewähltes Modell,
Ergebnis pro Abschnitt (bestanden/fehlgeschlagen mit konkreter Fehlermeldung). Nichts als
"verifiziert" vermerken, was nicht tatsächlich auf einem echten Rechner durchlaufen wurde.
