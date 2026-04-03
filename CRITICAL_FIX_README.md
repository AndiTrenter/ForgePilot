# 🚨 KRITISCHE FIXES - ForgePilot 3.0.0

## ⚠️ BEKANNTE PROBLEME & LÖSUNGEN

### 1. Settings Center zeigt keine Provider Cards (Cache-Problem)

**Symptom:** Settings Center Modal ist leer, keine Provider Cards sichtbar

**Ursache:** Browser-Cache hat alten JavaScript-Code

**Lösung:**
```bash
# Hard Refresh im Browser:
Windows: Strg + Shift + R (oder Strg + F5)
Mac: Cmd + Shift + R

# ODER in Developer Tools (F12):
1. Rechtsklick auf Reload-Button
2. "Empty Cache and Hard Reload"

# ODER Inkognito-Modus testen
```

**Verifikation:**
- Settings öffnen sollte 4 Provider Cards zeigen:
  - OpenAI
  - Anthropic
  - Google AI
  - GitHub

---

### 2. Agent sagt "npm nicht verfügbar" (System Prompt Problem)

**Symptom:** Agent erstellt npm_env oder sagt "keine Tools gefunden"

**Ursache:** Agent ignoriert System Prompt oder findet Workarounds

**Was wir implementiert haben:**
1. ✅ Hard Block im `run_command` Tool
2. ✅ System Prompt massiv verstärkt (60+ Zeilen Warnung)
3. ✅ Regex-Blockierung für verbotene Befehle

**Was der Agent JETZT tun sollte:**
```bash
✅ RICHTIG: run_command("npm install")
✅ RICHTIG: run_command("npm install react react-dom")
✅ RICHTIG: run_command("npm run build")

❌ FALSCH: nodeenv npm_env
❌ FALSCH: npm_env/bin/npm install
❌ FALSCH: "Alternative Methoden"
```

**Wenn es IMMER NOCH nicht funktioniert:**
- Starte ein **neues Projekt** (alte haben npm_env schon erstellt)
- Warte auf nächsten Agent-Response
- Agent sollte SOFORT `npm install` nutzen

---

### 3. Cloud-Button (Update) tut nichts

**Symptom:** Klick auf Cloud-Icon oben rechts → nichts passiert

**Ursache:** 
- LiveTerminal Modal State war in falschem Scope
- In Unraid Docker möglicherweise Update-Script fehlt

**Was wir gefixed haben:**
1. ✅ `showTerminal` State zu StartScreen hinzugefügt
2. ✅ LiveTerminalModal eingebunden
3. ✅ Cloud-Icon Button verbindet zu LiveTerminal

**Verifikation (lokal funktioniert):**
- Klick auf Cloud-Icon
- LiveTerminal Modal sollte öffnen
- Zeigt "Update-Script nicht gefunden" (normal wenn Script fehlt)

**Warum es in Unraid vielleicht nicht funktioniert:**
- Hard Refresh erforderlich (siehe Punkt 1)
- Oder Frontend-Build noch nicht aktualisiert

---

## 🔧 EMPFOHLENE SCHRITTE FÜR DEPLOYMENT

### 1. GitHub Push
```bash
git add .
git commit -m "fix: npm_env block + settings center + update button"
git push origin main
```

### 2. Docker Update (Unraid)
```bash
# In Unraid Container Terminal:
cd /path/to/forgepilot
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 3. Browser Cache löschen
```bash
# Im Browser: Strg + Shift + R
# Oder Inkognito-Modus testen
```

---

## 🧪 TESTING CHECKLIST

Nach Update testen:

**✅ Settings Center:**
- [ ] 4 Provider Cards sichtbar (OpenAI, Anthropic, Google, GitHub)
- [ ] "Configure API Key" Button funktioniert
- [ ] "Get API Key" öffnet Provider-Website
- [ ] "Test" Button validiert API Keys

**✅ Agent npm-Nutzung:**
- [ ] Neues Projekt erstellen "Baue eine Todo-App"
- [ ] Agent erstellt package.json
- [ ] Agent nutzt `run_command("npm install")` DIREKT
- [ ] KEIN npm_env wird erstellt
- [ ] npm install funktioniert sofort

**✅ Update-Button:**
- [ ] Cloud-Icon oben rechts sichtbar
- [ ] Klick öffnet LiveTerminal Modal
- [ ] Modal zeigt "ForgePilot Update (Unraid)"

---

## 📋 VERSION INFO

**Version:** 3.0.0
**Datum:** 2025-04-02
**Status:** Production Ready (mit bekannten Cache-Problemen)

**Hauptfeatures:**
- Completion Gates System
- Provider Registry
- Settings Center UI
- npm_env Hard Block
- Update-Menü

**Breaking Changes:** Keine

---

## 🆘 SUPPORT

**Bei weiteren Problemen:**

1. **Settings Center leer:** Hard Refresh (Strg + Shift + R)
2. **npm_env immer noch:** Neues Projekt starten
3. **Cloud-Button tut nichts:** Hard Refresh + Docker neu builden
4. **Andere Probleme:** GitHub Issue erstellen

---

**Letzte Aktualisierung:** 2025-04-02
**Autor:** E1 Agent
