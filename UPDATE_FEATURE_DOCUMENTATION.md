# ForgePilot Live-Update Feature

## 🎯 Überblick

Der **Update-Button** öffnet jetzt ein **Live-Terminal-Fenster**, das das Update-Script (`/mnt/user/appdata/forgepilot/update.sh`) in Echtzeit ausführt und die gesamte Ausgabe anzeigt - genau wie in Ihrem Screenshot!

## ✨ Features

### 1. **Live-Terminal-Modal**
- Öffnet sich beim Klick auf "Jetzt updaten"
- Zeigt alle Update-Ausgaben in Echtzeit (Docker-Pulls, Layer-Downloads, etc.)
- Automatisches Scrollen zum neuesten Output
- Farbcodierte Ausgabe:
  - 🔵 **Blau** - Info-Nachrichten
  - 🟢 **Grün** - Erfolgs-Nachrichten
  - 🔴 **Rot** - Fehler-Nachrichten
  - ⚪ **Weiß** - Standard-Output

### 2. **Server-Sent Events (SSE)**
- Streaming-Verbindung vom Backend zum Frontend
- Kein Polling erforderlich
- Minimale Latenz
- Automatische Wiederverbindung bei Verbindungsabbruch

### 3. **User Experience**
- **Während des Updates:**
  - Badge "Läuft..." mit Spinner
  - Live-Output im Terminal-Fenster
  - Automatisches Scrollen
  
- **Nach dem Update:**
  - "Update abgeschlossen"-Nachricht
  - Schließen-Button erscheint
  - Klick außerhalb des Modals schließt es

## 🔧 Technische Implementation

### Backend (`/app/backend/server.py`)

**Neuer Endpoint:** `GET /api/update/execute-live`

```python
@api_router.get("/update/execute-live")
async def execute_update_live():
    """Execute update script with live output streaming"""
    # Führt das Script aus: /mnt/user/appdata/forgepilot/update.sh
    # Streamt die Ausgabe Zeile für Zeile als Server-Sent Events
```

**Funktionsweise:**
1. Prüft ob Update-Script existiert
2. Führt Script mit `asyncio.create_subprocess_exec` aus
3. Liest stdout/stderr Zeile für Zeile
4. Sendet jede Zeile als SSE-Event an Frontend
5. Schließt Stream nach Completion

### Frontend (`/app/frontend/src/App.js`)

**Neue Komponente:** `LiveTerminalModal`

```javascript
const LiveTerminalModal = ({ isOpen, onClose, title }) => {
  // Verwendet EventSource für SSE
  // Zeigt Terminal-Output in Echtzeit
  // Auto-Scroll zu neuesten Logs
}
```

**Integration in UpdateBanner:**
- Button "Jetzt updaten" öffnet Terminal-Modal
- Icon: `MonitorPlay` (Monitor mit Play-Symbol)
- Modal übernimmt die Update-Ausführung

## 📋 Verwendung

### Für den Endnutzer:

1. **Update verfügbar?** → Banner erscheint oben
2. **Klick auf "Jetzt updaten"** → Terminal-Modal öffnet sich
3. **Live-Output sehen** → Alle Docker-Pulls, Downloads, etc. werden angezeigt
4. **Warten bis fertig** → "Update abgeschlossen" erscheint
5. **Modal schließen** → Klick auf "Schließen" oder außerhalb

### Beispiel-Output im Terminal:

```
ForgePilot Update Script
Starte Update...

Aktuelle Version: 2.5.6
Prüfe auf Updates...
Neueste Version: 2.9.0

Starte Update auf Version 2.9.0...

[1/4] Lade neue Images herunter...
[+] Pulling 22/25
✓ updater Pulled
:: backend 11 layers [░░░░░░░░░░░] 96.93MB/242.9MB Pulling
✓ ec781dee3f47 Already exists
✓ 6944007a5b45 Already exists
✓ e35b92e2619d Already exists
✓ 7524aba7408c Already exists
✓ 5b81680ca588 Pull complete
✓ 681db0298290 Pull complete
✓ a30d99abeb74 Pull complete
:: 4820f231f413 Extracting [==================>] 96.93MB/242.9MB
✓ 5a8c2c075968 Download complete
:: 871ec4e9668d Verifying Checksum
✓ 733720728836 Download complete
✓ frontend 10 layers [░░░░░░░░░░░] 0B/0B Pulled
✓ mongodb Pulled

✅ Update erfolgreich abgeschlossen!
```

## 🎨 UI-Design

### Terminal-Modal Design:
- **Header:** Terminal-Icon + Titel "ForgePilot Update"
- **Body:** Schwarzer Hintergrund mit Monospace-Font (wie echtes Terminal)
- **Footer:** Status-Text + Schließen-Button (nur wenn fertig)
- **Größe:** 80% Viewport-Höhe, max-width: 4xl
- **Farben:** Zinc-950 (sehr dunkel) für authentisches Terminal-Feeling

### Update-Button Design:
- **Icon:** `MonitorPlay` (Monitor mit Play-Symbol)
- **Text:** "Jetzt updaten"
- **Style:** Weißer Button auf blau-violettem Banner
- **Hover:** Helleres Weiß

## 🔄 Update-Flow

```
User klickt "Jetzt updaten"
         ↓
Modal öffnet sich
         ↓
EventSource connected zu /api/update/execute-live
         ↓
Backend führt update.sh aus
         ↓
Jede Zeile wird gestreamt
         ↓
Frontend zeigt Zeile im Terminal
         ↓
Update fertig
         ↓
"Done"-Event schließt Stream
         ↓
User kann Modal schließen
```

## 🐛 Error Handling

### Mögliche Fehler:
1. **Script nicht gefunden** → Zeigt Fehler im Terminal
2. **Verbindung unterbrochen** → Zeigt "Verbindung zum Server unterbrochen"
3. **Script-Fehler (Exit Code ≠ 0)** → Zeigt "Update mit Fehler beendet"

### Alle Fehler werden im Terminal angezeigt (rot gefärbt)

## 📁 Geänderte Dateien

1. **`/app/backend/server.py`**
   - Neuer Endpoint: `GET /api/update/execute-live`
   - SSE-Streaming-Implementation

2. **`/app/frontend/src/App.js`**
   - Neue Komponente: `LiveTerminalModal`
   - Updated: `UpdateBanner` Component
   - Neues Icon importiert: `MonitorPlay`

## ✅ Testing

**Backend-Test (in Unraid):**
```bash
# Test ob Script existiert
ls -la /mnt/user/appdata/forgepilot/update.sh

# API-Test (EventSource)
curl -N https://YOUR-DOMAIN/api/update/execute-live
```

**Frontend-Test:**
1. Update-Banner sollte erscheinen wenn Update verfügbar
2. Klick auf "Jetzt updaten"
3. Terminal-Modal öffnet sich
4. Live-Output sollte erscheinen
5. Nach Completion: Modal kann geschlossen werden

## 🚀 Next Steps

In der Produktions-Umgebung (Unraid):
1. Script-Pfad ist korrekt: `/mnt/user/appdata/forgepilot/update.sh`
2. Update-Check zeigt neue Version an
3. "Jetzt updaten"-Button erscheint
4. Terminal-Modal zeigt Live-Output wie im Screenshot

## 💡 Hinweise

- **Auto-Reload:** Nach erfolgreichem Update lädt sich die Seite automatisch neu
- **Performance:** SSE ist sehr effizient, kein Overhead durch Polling
- **Mobile:** Modal ist responsive und funktioniert auch auf kleineren Bildschirmen
- **Accessibility:** Terminal-Output ist selectable und copyable
