# 🎯 ForgePilot Master Agent System

## Übersicht

Das Master Agent System implementiert ein mehrstufiges Qualitätskontrollsystem für die autonome Code-Generierung. Der "Master Agent" überwacht und validiert die Arbeit aller spezialisierten Agents in jeder Phase.

## Konzept

Statt dass ein einzelner Agent durchläuft und am Ende hofft, dass alles funktioniert, arbeitet das System in **kontrollierten Phasen** mit **Qualitätschecks nach jedem Schritt**.

## System-Architektur

```
┌─────────────────────────────────────────────────┐
│           MASTER AGENT (Supervisor)              │
│  Überwacht alle Phasen und führt Quality Checks │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
  ┌─────────┐   ┌─────────┐   ┌─────────┐
  │ PLANNER │   │  CODER  │   │ TESTER  │
  └─────────┘   └─────────┘   └─────────┘
        │             │             │
        ▼             ▼             ▼
  ┌─────────┐   ┌─────────┐   ┌─────────┐
  │REVIEWER │   │DEBUGGER │   │   GIT   │
  └─────────┘   └─────────┘   └─────────┘
```

## Phasen-Ablauf

### PHASE 1: PLANNER AGENT
**Verantwortlich**: Recherche und Planung

**Aufgaben**:
- Web-Suche nach Best Practices
- Detaillierte Roadmap erstellen
- ALLE benötigten Komponenten planen

**Master Check**:
- ✅ Ist die Planung vollständig?
- ✅ Fehlt etwas Kritisches?
- ✅ Sind alle Abhängigkeiten berücksichtigt?

### PHASE 2: CODER AGENT
**Verantwortlich**: Code-Implementierung

**Aufgaben**:
- Vollständigen, funktionierenden Code schreiben
- KEINE Platzhalter oder TODOs
- KEINE Kommentare wie "hier Code einfügen"

**Master Check (nach JEDER Datei)**:
- ✅ Datei mit `read_file` überprüfen
- ✅ Ist der Code vollständig?
- ✅ Fehlen Funktionen oder Imports?
- ✅ Bei Unvollständigkeit → `modify_file` zur Vervollständigung

### PHASE 3: TESTER AGENT
**Verantwortlich**: Code-Validierung

**Aufgaben**:
- `test_code` mit `type="syntax"` für alle Dateien
- `test_code` mit `type="run"` ausführen
- Bei Spielen: `verify_game` PFLICHT

**Master Check**:
- ✅ Alle Syntax-Tests bestanden?
- ✅ Run-Tests erfolgreich?
- ✅ Game-Verifikation OK (falls Spiel)?

### PHASE 4: REVIEWER AGENT
**Verantwortlich**: Finale Qualitätskontrolle

**Aufgaben**:
- JEDE erstellte Datei mit `read_file` lesen
- Prüfen auf Vollständigkeit, Fehler, fehlende Features

**Master Check**:
- ✅ Entspricht der Code den Anforderungen?
- ✅ Sind alle Funktionen implementiert?
- ✅ Code ist lesbar und strukturiert?

### PHASE 5: DEBUGGER AGENT (falls nötig)
**Verantwortlich**: Fehlerbehebung

**Aufgaben**:
- Alle gefundenen Probleme beheben
- Tests wiederholen
- Iterieren bis alle Tests grün sind

**Master Check**:
- ✅ Sind alle Probleme behoben?
- ✅ Neue Tests bestanden?

## Qualitäts-Standards

### Minimale Anforderungen für "fertig"
- [ ] `index.html` existiert und ist valide
- [ ] Alle Scripts sind eingebunden
- [ ] Keine Syntax-Fehler
- [ ] Event-Listener für Benutzerinteraktion vorhanden
- [ ] Alle Kern-Funktionen implementiert
- [ ] Code ist lesbar und strukturiert

### Zusätzlich für Spiele
- [ ] Game-Loop (requestAnimationFrame/setInterval) implementiert
- [ ] Tastatur/Maus-Steuerung funktioniert
- [ ] Spiellogik vollständig (Bewegung, Kollision, Punkte)
- [ ] Visuelles Feedback für Spieler
- [ ] Start/Neustart möglich
- [ ] `verify_game` Tool erfolgreich durchlaufen

## Master Check Regeln

### Nach JEDER erstellten Datei:
1. **Lesen**: Datei mit `read_file` öffnen
2. **Prüfen**: Ist sie vollständig? Fehlt Code?
3. **Korrigieren**: Wenn unvollständig → `modify_file`
4. **Wiederholen**: Bis die Datei KOMPLETT ist

### BEVOR `mark_complete` aufgerufen wird:
1. `test_code type="syntax"` → muss bestehen
2. `test_code type="run"` → muss bestehen
3. Bei Spielen: `verify_game` → muss bestehen
4. ALLE Dateien lesen und prüfen

### WENN Tests fehlschlagen:
- ❌ **NICHT** `mark_complete` aufrufen!
- 🔧 Fehler beheben und erneut testen
- ✅ Erst bei ALLEN grünen Tests weitermachen

## Vorteile des Master Agent Systems

### 1. Höhere Code-Qualität
Durch kontinuierliche Überprüfung in jeder Phase werden Fehler früh erkannt und behoben.

### 2. Vollständigkeit garantiert
Der Master Agent stellt sicher, dass kein Code unvollständig bleibt oder Platzhalter enthält.

### 3. Systematisches Vorgehen
Klare Phasen-Struktur verhindert chaotisches Hin-und-Her-Springen.

### 4. Automatische Selbstkorrektur
Der Agent korrigiert sich selbst, wenn er Fehler oder Unvollständigkeiten entdeckt.

### 5. Transparenz
Jede Phase ist dokumentiert und nachvollziehbar im Agenten-Feed.

## Tools des Master Agents

| Tool | Verwendung | Pflicht? |
|------|------------|----------|
| `web_search` | Recherche BEVOR Code geschrieben wird | Empfohlen |
| `create_roadmap` | Fortschritt tracken | Ja |
| `update_roadmap_status` | Status aktualisieren | Ja |
| `create_file` | Neue Dateien erstellen | Ja |
| `modify_file` | Dateien ändern | Ja |
| `read_file` | Dateien überprüfen | **PFLICHT nach jedem create/modify** |
| `test_code` | Code testen | **PFLICHT vor mark_complete** |
| `verify_game` | Spiele validieren | **PFLICHT für Spiele** |
| `debug_error` | Fehler analysieren | Bei Bedarf |
| `ask_user` | Bei Unklarheiten | Bei Bedarf |
| `mark_complete` | Projekt abschließen | **NUR nach allen Checks** |

## Implementierung (server.py)

Der Master Agent ist im System-Prompt in `run_autonomous_agent()` implementiert:

```python
system_prompt = f"""Du bist ForgePilot, ein autonomer KI-Entwicklungsassistent mit einem MASTER-AGENT System.

═══════════════════════════════════════════════════════════════════════════════
                           MASTER AGENT PROTOKOLL
═══════════════════════════════════════════════════════════════════════════════

Du arbeitest in PHASEN. Jede Phase wird von einem spezialisierten "Agent" ausgeführt,
und nach jeder Phase führt der MASTER eine Qualitätskontrolle durch.

[... detaillierte Anweisungen für jede Phase ...]
"""
```

## Beispiel-Ablauf (Tetris-Spiel)

```
1️⃣ PLANNER
   - Web-Suche: "Tetris best practices JavaScript"
   - Roadmap: HTML, CSS, JavaScript, Game-Loop, Collision Detection
   ✅ Master Check: Vollständig

2️⃣ CODER
   - create_file: index.html
   - read_file: index.html → ✅ vollständig
   - create_file: style.css
   - read_file: style.css → ✅ vollständig
   - create_file: script.js
   - read_file: script.js → ❌ Game-Loop fehlt!
   - modify_file: script.js (Game-Loop hinzufügen)
   - read_file: script.js → ✅ vollständig
   ✅ Master Check: Alle Dateien komplett

3️⃣ TESTER
   - test_code type="syntax" → ✅ OK
   - test_code type="run" → ✅ OK
   - verify_game type="tetris" → ✅ Spielbar
   ✅ Master Check: Alle Tests bestanden

4️⃣ REVIEWER
   - read_file: index.html → ✅ OK
   - read_file: style.css → ✅ OK
   - read_file: script.js → ✅ OK
   ✅ Master Check: Code erfüllt Anforderungen

5️⃣ FERTIG
   - mark_complete ✅
```

## Monitoring

Der Agent-Fortschritt wird in der UI im "Agent Activity Feed" angezeigt:
- Aktuelle Phase
- Aktuelles Tool
- Iteration-Counter
- Tool-Ergebnisse

## Anpassungen

### System-Prompt anpassen
Die Master Agent Logik befindet sich in `/app/backend/server.py` in der Funktion `run_autonomous_agent()`.

### Neue Phasen hinzufügen
Ergänze neue Agent-Typen im System-Prompt und in der `AgentStatus` Liste.

### Qualitäts-Standards ändern
Passe die "QUALITÄTS-STANDARDS" Sektion im System-Prompt an.

## Best Practices

### Für Entwickler
1. **Nicht übersteuern**: Lass den Master Agent seine Arbeit machen
2. **Klare Anforderungen**: Je präziser die User-Anfrage, desto besser
3. **Geduld**: Der Master Agent braucht mehr Iterationen, produziert aber bessere Ergebnisse

### Für Agent-Entwicklung
1. **Früh prüfen**: Nach jeder Datei sofort `read_file`
2. **Nicht weitermachen** bei fehlgeschlagenen Tests
3. **Dokumentieren**: Jeder Schritt sollte im Log erscheinen

---

**Entwickelt für ForgePilot v1.1.0+**
**Basierend auf dem "Agent Supervisor" Pattern**
