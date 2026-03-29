# 🚀 ForgePilot Auto-Update System

## Übersicht

Das Auto-Update System ermöglicht es Benutzern, Updates direkt aus der ForgePilot-UI mit einem Klick zu installieren, ohne manuelle Terminal-Befehle ausführen zu müssen.

## Architektur

### 1. Frontend (App.js)
- **Update-Banner**: Wird oben angezeigt, wenn ein Update verfügbar ist
- **Update-Button**: Startet das automatische Update
- **Auto-Reload**: Nach erfolgreichem Update wird die Seite nach 35 Sekunden automatisch neu geladen

### 2. Backend (server.py)
- **Endpoint**: `POST /api/update/install`
- **Funktion**: Erstellt eine Trigger-Datei `/app/workspaces/.update_trigger`
- **Response**: 
  - `triggered: true` → Auto-Update wird ausgeführt
  - `triggered: false` → Fallback auf manuelle Anweisungen

### 3. Updater Service (docker-compose.unraid.yml)
- **Container**: `forgepilot-updater`
- **Image**: `docker:24-cli`
- **Volumes**:
  - `/var/run/docker.sock` → Ermöglicht Docker-Befehle von innen
  - `workspaces:/app/workspaces` → Zugriff auf Trigger-Datei
- **Funktion**: Überwacht Trigger-Datei und führt Update durch

## Update-Ablauf

```
1. Benutzer klickt "Jetzt updaten" im UI
   ↓
2. Frontend ruft POST /api/update/install auf
   ↓
3. Backend erstellt /app/workspaces/.update_trigger
   ↓
4. Updater Service erkennt Trigger-Datei
   ↓
5. Updater Service führt aus:
   - docker pull ghcr.io/anditrenter/forgepilot/forgepilot-backend:latest
   - docker pull ghcr.io/anditrenter/forgepilot/forgepilot-frontend:latest
   - docker stop forgepilot-frontend forgepilot-backend
   - docker rm forgepilot-frontend forgepilot-backend
   - docker-compose up -d backend frontend
   ↓
6. Frontend lädt automatisch nach 35 Sekunden neu
   ↓
7. Neue Version ist aktiv! ✅
```

## Vorteile

✅ **1-Klick-Update**: Kein SSH oder Terminal notwendig
✅ **Automatischer Neustart**: Container werden automatisch neu gestartet
✅ **Fallback**: Bei Problemen werden manuelle Anweisungen angezeigt
✅ **Feedback**: Benutzer sieht Status-Updates während des Prozesses
✅ **Auto-Reload**: Seite wird automatisch neu geladen nach Update

## Wichtige Dateien

| Datei | Funktion |
|-------|----------|
| `/app/frontend/src/App.js` | Update-UI und `handleInstallUpdate` Funktion |
| `/app/backend/server.py` | `/api/update/install` Endpoint |
| `/app/docker-compose.unraid.yml` | Updater Service Definition |
| `/app/updater-service.sh` | Standalone Update-Script (Alternative) |

## Testen

### Lokal testen (Entwicklung)
```bash
# 1. Update-Check simulieren
curl -X POST http://localhost/api/update/check

# 2. Update installieren (erstellt Trigger-Datei)
curl -X POST http://localhost/api/update/install

# 3. Trigger-Datei prüfen
ls -la /app/workspaces/.update_trigger
```

### In Produktion (Unraid)
1. Neue Version in GitHub pushen
2. GitHub Actions baut neue GHCR Images
3. ForgePilot UI zeigt Update-Banner
4. Auf "Jetzt updaten" klicken
5. Warten bis Update abgeschlossen ist (~30 Sekunden)
6. Seite wird automatisch neu geladen

## Fehlerbehebung

### Update-Button reagiert nicht
→ Browser-Konsole prüfen (F12)
→ Backend-Logs prüfen: `docker logs forgepilot-backend`

### Updater Service läuft nicht
→ Prüfen: `docker ps | grep updater`
→ Logs: `docker logs forgepilot-updater`

### Docker Socket Fehler
→ Prüfen ob Volume gemountet ist:
```bash
docker inspect forgepilot-updater | grep docker.sock
```

### Trigger-Datei wird nicht erkannt
→ Workspaces Volume prüfen:
```bash
docker volume inspect forgepilot_workspaces
```

## Sicherheit

⚠️ **Docker Socket**: Der Updater Service hat Zugriff auf den Docker Socket. Dies ist notwendig für Container-Management, sollte aber nur in vertrauenswürdigen Umgebungen verwendet werden.

✅ **Isolierung**: Der Updater läuft in einem separaten Container
✅ **Nur GHCR Images**: Nur offizielle Images von GitHub werden gepullt
✅ **Keine Root-Befehle**: Normale Docker-Befehle, kein sudo

## Erweiterungen

### Alternative Update-Methoden
1. **Manuell via Script**: `./update.sh`
2. **Manuell via Docker Compose**:
   ```bash
   docker-compose -f docker-compose.unraid.yml pull
   docker-compose -f docker-compose.unraid.yml down
   docker-compose -f docker-compose.unraid.yml up -d
   ```

---

**Entwickelt für ForgePilot v1.1.0+**
