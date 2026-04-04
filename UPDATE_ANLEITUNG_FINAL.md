# 🚀 UPDATE-ANLEITUNG FINAL v3.0.3

**WICHTIG:** `docker-compose restart` lädt NICHT das neue Image!

---

## ❌ FALSCH (lädt altes Image):
```bash
docker-compose build backend
docker-compose restart backend  # ❌ Startet alten Container neu!
```

## ✅ RICHTIG (lädt neues Image):
```bash
docker-compose build backend
docker-compose up -d backend    # ✅ Startet NEUEN Container!
```

---

## 📋 KOMPLETTE UPDATE-PROZEDUR

### Auf Unraid ausführen:

```bash
cd /mnt/user/appdata/forgepilot

# 1. Code von GitHub holen
git pull origin main

# 2. Prüfen ob updater-service.sh vorhanden ist
ls -la updater-service.sh
# Sollte zeigen: -rwxr-xr-x ... updater-service.sh

# 3. Container neu bauen
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 4. Warten (Build kann 5-7 Minuten dauern)
sleep 60

# 5. Status prüfen
docker-compose ps
```

**Erwartete Ausgabe (Schritt 5):**
```
forgepilot-mongodb     Healthy
forgepilot-backend     Started
forgepilot-frontend    Started
```

---

## 🧪 NACH DEM UPDATE TESTEN:

### 1. Version prüfen
- Browser: `http://192.168.1.140:3000`
- Oben links im Logo sollte stehen: **"ForgePilot v3.0.3"**

### 2. Settings Center
- Klick auf ⚙️ Icon (oben rechts)
- Alle 4 Provider-Karten sollten sichtbar sein

### 3. Update-Funktion
- Im Settings Center zu "System" scrollen
- "Update ForgePilot" Button klicken
- **Sollte jetzt funktionieren!**

---

## 🐛 TROUBLESHOOTING

### Update-Button zeigt Fehler
**Symptom:** "Update-Script nicht gefunden"

**Ursache:** Backend läuft mit altem Code

**Lösung:**
```bash
cd /mnt/user/appdata/forgepilot

# Backend NEU STARTEN (nicht restart!)
docker-compose up -d backend --force-recreate

# Warten
sleep 10

# Logs prüfen
docker-compose logs backend | grep -i "update"
```

### Version wird nicht angezeigt
**Ursache:** Frontend läuft mit altem Code

**Lösung:**
```bash
docker-compose build --no-cache frontend
docker-compose up -d frontend --force-recreate
```

### Orchestrator kann npm nicht nutzen
**Ursache:** Backend ohne Node.js gebaut

**Lösung:**
```bash
# Prüfen ob Node.js im Backend ist
docker exec forgepilot-backend node --version
# Sollte zeigen: v20.x.x

# Falls nicht:
docker-compose build --no-cache backend
docker-compose up -d backend --force-recreate
```

---

## 📊 UNTERSCHIED: restart vs up -d

| Befehl | Was passiert | Wann verwenden |
|--------|--------------|----------------|
| `docker-compose restart` | Stoppt und startet den **existierenden** Container neu | Config-Änderungen (.env) |
| `docker-compose up -d` | Erstellt **neuen** Container mit neuem Image | Nach Code-Änderungen |
| `docker-compose up -d --force-recreate` | Erzwingt Neuerstellen des Containers | Bei hartnäckigen Problemen |

---

## 🎯 WICHTIGSTE REGEL:

**Nach jedem `git pull` und `docker-compose build`:**
```bash
docker-compose up -d
```

**NICHT:**
```bash
docker-compose restart  # ❌
```

---

**Version:** 3.0.3  
**Datum:** 04. April 2026  
**Status:** PRODUKTIONSREIF ✅
