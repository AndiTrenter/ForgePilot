# ForgePilot v3.0 - Deployment-Leitfaden

## 🚀 SCHNELLSTART

### 1. Update via Unraid Update-Mechanismus

**Auf Ihrem Unraid-System:**
1. ForgePilot öffnen
2. Update-Banner erscheint (Version 3.0.0)
3. Klick auf **"Jetzt updaten"** 
4. Live-Terminal zeigt Docker-Pull
5. Nach Neustart: Neue Architektur aktiv

### 2. Manuelle Installation (falls nötig)

```bash
cd /mnt/user/appdata/forgepilot
bash update.sh
```

---

## ✅ NACH DEM UPDATE

### Neue Features verfügbar:

**1. Settings-Center (UI)**
- Öffnen via Settings-Icon
- Alle Provider auf einen Blick
- **Direct Links** zu Key-Erstellungsseiten
- Test-Connection-Buttons

**2. Quality-Gates (Backend)**
- Tasks werden automatisch geprüft
- Keine "Fake-Fertig"-Meldungen mehr
- Evidence wird gesammelt

**3. Intelligentes Model-Routing**
- System wählt optimales LLM
- Cost-optimiert
- Priority-based

**4. Tech-Stack-Detection**
- "Baue ein Browser-Spiel" → Automatisch Vite + React
- "Erstelle ein Dashboard" → Automatisch Next.js + DB
- Keine manuelle Stack-Auswahl nötig

**5. Discovery-Phase**
- System analysiert Anforderungen strukturiert
- Stellt kritische Fragen
- Dokumentiert Annahmen

---

## 🔧 KONFIGURATION

### Provider einrichten:

**1. OpenAI (empfohlen):**
```
1. Settings-Center öffnen
2. OpenAI-Card finden
3. "Get API Key" klicken → platform.openai.com/api-keys
4. Key kopieren
5. In Settings einfügen
6. "Test" klicken → Erfolg!
```

**2. Anthropic (optional):**
```
"Get API Key" → console.anthropic.com/settings/keys
```

**3. Google AI (optional):**
```
"Get API Key" → aistudio.google.com/apikey
```

**4. GitHub (für Code-Push):**
```
"Get API Key" → github.com/settings/tokens/new
Permissions: repo, workflow
```

---

## 📊 SYSTEM-ÜBERSICHT

### Neue Architektur:

**Backend:**
- ✅ Modulares System (35+ Dateien statt Monolith)
- ✅ State Machine erzwingt valide Abläufe
- ✅ Completion Gates verhindern Qualitätsprobleme
- ✅ API v1 (moderne REST-Endpoints)
- ⚠️  Legacy API läuft parallel (Backward-Compatible)

**Frontend:**
- ✅ Settings-Center-Komponente
- ⚠️  App.js wird in späteren Updates aufgesplittet

**Datenbank:**
- ✅ Neue Collections: `tasks`, `evidence`
- ✅ Bestehende Collections bleiben erhalten

---

## 🧪 TESTING

### Test 1: Provider-Configuration
```
1. Settings öffnen
2. OpenAI-Provider konfigurieren
3. "Test" klicken
4. Erwartung: ✅ Success
```

### Test 2: Neues Projekt mit Detection
```
1. "Neues Projekt"
2. Input: "Erstelle ein Super Mario Browser-Spiel"
3. System erkennt automatisch: Vite + React
4. Projekt wird mit richtigem Stack erstellt
```

### Test 3: Task mit Quality-Gates
```
1. Task erstellen
2. Versuche "Complete" OHNE Tests
3. Erwartung: ❌ GateViolationError
4. Nach Tests: ✅ Complete erlaubt
```

---

## 🐛 TROUBLESHOOTING

### Problem: "Provider not configured"
**Lösung:**
```
Settings → Provider → Get API Key → Konfigurieren
```

### Problem: "Task completion blocked"
**Bedeutung:** Quality-Gates nicht erfüllt
**Lösung:**
```
1. Build ausführen
2. Tests ausführen
3. Lint ausführen
4. Dann erneut "Complete"
```

### Problem: "Legacy routes not working"
**Lösung:**
```
System läuft im Hybrid-Modus.
Alte Routes: /api/projects (funktioniert)
Neue Routes: /api/v1/tasks (zusätzlich)
```

---

## 📈 ROADMAP

**✅ Update 1 (JETZT):** Foundation + Core
**🔄 Update 2 (geplant):** Complete Environment-Provisioning
**🔄 Update 3 (geplant):** Complete Agent-Orchestration
**🔄 Update 4 (geplant):** Frontend-Modernisierung
**🔄 Update 5 (geplant):** Legacy-Migration abschließen

---

## 💡 BEST PRACTICES

### 1. Provider zuerst konfigurieren
```
Ohne API-Keys kann das System nicht arbeiten.
→ Settings-Center öffnen
→ Mindestens OpenAI konfigurieren
```

### 2. Discovery-Phase nutzen
```
Statt "Baue X" → "Baue ein X mit Y-Features, für Z-Benutzer"
System analysiert besser und stellt gezielte Fragen
```

### 3. Quality-Gates verstehen
```
Gates = Qualitätssicherung
Wenn Task nicht "Complete" geht → Prüfen was fehlt
```

### 4. Model-Routing vertrauen
```
System wählt automatisch optimales Model
Hohe Priorität → Starkes Model
Budget-Limit → Günstiges Model
```

---

## 🆘 SUPPORT

**Dokumentation:**
- `/app/TRANSFORMATION_COMPLETE.md` - Vollständige Feature-Liste
- `/app/SYSTEM_TRANSFORMATION_PLAN.md` - Architektur-Details

**Logs:**
```bash
# Backend-Logs
tail -f /var/log/supervisor/backend.out.log

# Frontend-Logs
tail -f /var/log/supervisor/frontend.out.log
```

**System-Status:**
```bash
sudo supervisorctl status
```

---

## ✅ CHECKLISTE NACH UPDATE

- [ ] Update erfolgreich
- [ ] Frontend lädt
- [ ] Backend erreichbar
- [ ] Settings-Center öffnet
- [ ] Mindestens 1 Provider konfiguriert
- [ ] Test-Connection erfolgreich
- [ ] Neues Projekt erstellen funktioniert
- [ ] Tech-Stack wird automatisch erkannt

**Wenn alle Checkboxen ✅ → System läuft perfekt!**

---

**Version:** 3.0.0  
**Release-Datum:** 2026-04-02  
**Breaking Changes:** Keine (Hybrid-Modus)
