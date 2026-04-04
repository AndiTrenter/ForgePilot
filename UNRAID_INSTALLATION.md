# 🚨 KRITISCHE UNRAID INSTALLATION - SCHRITT FÜR SCHRITT

**Problem behoben:** Frontend konnte Backend nicht erreichen, weil `REACT_APP_BACKEND_URL` zur Build-Zeit nicht korrekt gesetzt war.

---

## ✅ SO INSTALLIEREN SIE FORGEPILOT AUF UNRAID (NEU)

### Schritt 1: Repository klonen (falls noch nicht geschehen)
```bash
cd /mnt/user/appdata
git clone https://github.com/IHR-USERNAME/forgepilot.git
cd forgepilot
```

### Schritt 2: `.env` Datei anpassen (KRITISCH!)
```bash
nano .env
```

**Ändern Sie diese Zeile:**
```bash
# VORHER (falsch):
REACT_APP_BACKEND_URL=http://192.168.1.140:8001

# NACHHER (Ihre echte Unraid IP):
REACT_APP_BACKEND_URL=http://IHR_UNRAID_IP:8001
```

Beispiel: Wenn Ihre Unraid IP `192.168.1.50` ist:
```bash
REACT_APP_BACKEND_URL=http://192.168.1.50:8001
```

**Speichern:** `Ctrl + O` → `Enter` → `Ctrl + X`

---

### Schritt 3: Container bauen und starten
```bash
# Alte Container stoppen
docker-compose down

# NEU BAUEN (mit korrekter URL!)
docker-compose build --no-cache

# Container starten
docker-compose up -d

# Warten Sie 30 Sekunden
sleep 30

# Status prüfen
docker-compose ps
```

**Erwartete Ausgabe:**
```
forgepilot-mongodb    Healthy  
forgepilot-backend    Started
forgepilot-frontend   Started
```

---

### Schritt 4: Im Browser testen

1. Öffnen Sie: `http://IHR_UNRAID_IP:3000`
2. Klicken Sie auf das ⚙️ **Settings Icon** (oben rechts)
3. **Settings Center sollte jetzt alle 4 Provider-Karten anzeigen!**

---

## 🔍 Was war das Problem?

React-Apps mit `Create React App` (CRA) backen Umgebungsvariablen zur **BUILD-TIME** in den JavaScript-Code ein. Das bedeutet:

❌ **Falsch:** `.env` Datei NACH dem Build ändern  
✅ **Richtig:** `.env` VOR dem Build setzen → dann `docker-compose build`

**Vorher:**
```
Frontend Build → http://localhost:8001 eingebacken
Browser greift zu → http://192.168.1.140:3000
API Call → http://localhost:8001/api (❌ FALSCH - läuft nicht!)
```

**Nachher:**
```
.env → REACT_APP_BACKEND_URL=http://192.168.1.140:8001
Frontend Build → http://192.168.1.140:8001 eingebacken
Browser greift zu → http://192.168.1.140:3000
API Call → http://192.168.1.140:8001/api (✅ KORREKT!)
```

---

## 🆘 Troubleshooting

### Fehler: "Network Error" beim Laden der Provider
**Ursache:** Frontend nutzt immer noch falsche URL  
**Lösung:**
1. `.env` Datei prüfen: `cat .env | grep REACT_APP`
2. Neu bauen: `docker-compose build --no-cache frontend`
3. Neu starten: `docker-compose up -d`

### Fehler: Container startet nicht
**Lösung:** Logs prüfen:
```bash
docker-compose logs backend
docker-compose logs frontend
```

### Fehler: "Update-Script nicht gefunden"
**Ursache:** Alte Version läuft noch  
**Lösung:** `git pull origin main` → neu bauen (siehe Schritt 3)

---

## 📝 Nach erfolgreicher Installation

Wenn alles funktioniert:
1. ✅ Settings Center öffnet sich
2. ✅ Alle 4 Provider-Karten werden angezeigt  
3. ✅ "Configure API Key" Buttons funktionieren

**Dann können Sie:**
- OpenAI API Key konfigurieren
- Anthropic/Google Keys hinzufügen (optional)
- GitHub Token einrichten
- Mit dem Entwickeln beginnen! 🎉

---

**Erstellt:** 04. April 2026  
**Version:** 3.0.2
