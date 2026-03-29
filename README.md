# ForgePilot

Ein lokales AI-Entwicklungssystem für Unraid. Erstelle Software-Projekte per Chat - ForgePilot recherchiert, plant, programmiert, testet und debuggt automatisch.

## Features

- **Autonome KI-Entwicklung** - Agent arbeitet selbstständig bis fertig oder Frage nötig
- **Live-Preview** - Echte Vorschau deiner Projekte im Browser
- **7 spezialisierte Agenten** - Orchestrator, Planner, Coder, Reviewer, Tester, Debugger, Git
- **6 Projekt-Templates** - React, Vue.js, Node.js, Python FastAPI, Landing Page, Dashboard
- **GitHub Integration** - Import/Export von Repositories
- **Spracheingabe** - Mikrofon-Button für Sprachbefehle
- **Ollama Support** - Nutze lokale LLMs (llama3, mistral, codellama) statt OpenAI
- **Auto-Fallback** - Automatischer Wechsel zwischen Ollama und OpenAI
- **Update-System** - Automatische Update-Erkennung und Installation über die UI

## Installation auf Unraid

### Schnellstart mit GHCR Images (Empfohlen)

```bash
# 1. Repository klonen
git clone https://github.com/AndiTrenter/ForgePilot.git
cd ForgePilot

# 2. .env erstellen
cp .env.example .env
nano .env  # Mindestens OPENAI_API_KEY eintragen

# 3. Container starten
docker-compose -f docker-compose.unraid.yml up -d

# 4. Öffne http://YOUR_UNRAID_IP:3000
```

### Environment-Variablen

Erstelle eine `.env` Datei im Projektverzeichnis:

```bash
# Erforderlich
OPENAI_API_KEY=sk-proj-...

# Optional - GitHub Integration
GITHUB_TOKEN=github_pat_...

# Optional - Ollama (lokale LLM)
OLLAMA_URL=http://192.168.1.140:11434
OLLAMA_MODEL=llama3

# LLM Provider: auto (empfohlen), openai, ollama
LLM_PROVIDER=auto
```

## LLM Provider Konfiguration

ForgePilot unterstützt drei Modi für die KI:

### Auto (Empfohlen)
```bash
LLM_PROVIDER=auto
```
- Nutzt Ollama wenn verfügbar
- Fällt automatisch auf OpenAI zurück
- Beste Kombination aus Kosten und Verfügbarkeit

### OpenAI Only
```bash
LLM_PROVIDER=openai
```
- Nutzt nur OpenAI GPT-4o
- Benötigt gültigen API Key
- Beste Qualität, aber kostenpflichtig

### Ollama Only
```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://192.168.1.140:11434
OLLAMA_MODEL=llama3
```
- Nutzt nur lokales Ollama
- Kostenlos, aber benötigt lokale Hardware
- Gut für einfachere Aufgaben

## Ollama Setup

1. **Ollama installieren:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Ollama starten:**
   ```bash
   ollama serve
   ```

3. **Modell laden:**
   ```bash
   ollama pull llama3
   # oder für Code: ollama pull codellama
   ```

4. **ForgePilot konfigurieren:**
   - Einstellungen öffnen (Ctrl+,)
   - Tab "LLM" wählen
   - Ollama URL eintragen: `http://192.168.x.x:11434`
   - "Test" klicken um Verbindung zu prüfen
   - Provider auf "Ollama" oder "Auto" setzen

## Update-System

ForgePilot kann automatisch nach Updates suchen und diese installieren.

### Update durchführen

**Empfohlen: Update-Script verwenden**
```bash
cd /pfad/zu/forgepilot
./update.sh
```

Das Script macht automatisch:
1. Prüft auf neue Version
2. Lädt neue Images herunter
3. Stoppt alte Container
4. Entfernt alte Container
5. Startet neue Container
6. Verifiziert die Installation

**Weitere Optionen:**
```bash
./update.sh --check   # Nur prüfen ob Update verfügbar
./update.sh --force   # Update erzwingen
```

### Manuelles Update
```bash
cd /pfad/zu/forgepilot
docker-compose -f docker-compose.unraid.yml pull
docker-compose -f docker-compose.unraid.yml down
docker-compose -f docker-compose.unraid.yml up -d
```

### Rollback
Falls ein Update Probleme verursacht:
```bash
# Zur vorherigen Version zurückkehren
docker pull ghcr.io/anditrenter/forgepilot/forgepilot-backend:v1.0.0
docker pull ghcr.io/anditrenter/forgepilot/forgepilot-frontend:v1.0.0
docker-compose -f docker-compose.unraid.yml up -d
```

## Tastaturkürzel

| Kürzel | Aktion |
|--------|--------|
| Ctrl+S | Datei speichern |
| Ctrl+Shift+S | Alle Dateien speichern |
| Ctrl+P | Preview ein/aus |
| Ctrl+B | Datei-Explorer ein/aus |
| Ctrl+K | Chat fokussieren |
| Ctrl+W | Tab schließen |
| Ctrl+Shift+R | Preview neu laden |
| Ctrl+, | Einstellungen |

## Projekt-Templates

| Template | Beschreibung |
|----------|--------------|
| ⚛️ React App | Moderne React-Anwendung mit Hooks |
| 💚 Vue.js App | Reaktive Vue.js 3 mit Composition API |
| 🟢 Node.js API | Express.js REST API mit CRUD |
| 🐍 Python FastAPI | FastAPI mit Pydantic Models |
| 🚀 Landing Page | Marketing-Landingpage mit Tailwind |
| 📊 Dashboard | Admin-Dashboard mit Charts |

## API Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | /api/ | API Status & Version |
| GET | /api/health | Health Check |
| GET | /api/version | App Version |
| GET | /api/llm/status | LLM Status (Provider, Ollama Verfügbarkeit) |
| GET | /api/settings | Aktuelle Einstellungen |
| PUT | /api/settings | Einstellungen speichern |
| GET | /api/update/status | Update Status |
| POST | /api/update/check | Nach Updates suchen |
| GET | /api/projects | Liste aller Projekte |
| POST | /api/projects | Neues Projekt erstellen |
| POST | /api/projects/{id}/chat | Chat mit Agent (SSE) |
| GET | /api/projects/{id}/preview/{path} | Live-Preview |
| POST | /api/github/import | GitHub Repo importieren |

## Architektur

```
ForgePilot
├── frontend/               # React 19 + Tailwind CSS
│   ├── src/
│   │   ├── App.js          # Hauptkomponente
│   │   └── components/
│   │       ├── api.js      # API Client (nutzt /api relativ)
│   │       └── ...
│   ├── nginx.conf          # Reverse Proxy für /api
│   └── Dockerfile
├── backend/                # FastAPI + MongoDB
│   ├── server.py           # API Server
│   └── Dockerfile
├── docker-compose.yml      # Lokales Bauen
├── docker-compose.unraid.yml  # GHCR Images für Unraid
├── VERSION                 # App-Version
└── workspaces/             # Generierte Projekte
```

## Entwicklung

```bash
# Backend starten
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Frontend starten (separates Terminal)
cd frontend
yarn install
yarn start
```

## Troubleshooting

### Frontend zeigt "Backend nicht erreichbar"
1. Prüfe ob alle Container laufen: `docker ps`
2. Prüfe Backend-Logs: `docker logs forgepilot-backend`
3. Prüfe Netzwerk: `docker network inspect forgepilot_forgepilot-network`

### Ollama wird nicht erkannt
1. Prüfe Ollama-URL in Einstellungen
2. Teste von Backend aus: `curl http://OLLAMA_IP:11434/api/tags`
3. Stelle sicher dass Ollama auf 0.0.0.0 hört, nicht nur localhost

### Settings speichern schlägt fehl
- Keys aus .env werden als read-only behandelt
- Nur Keys die NICHT in .env stehen können über UI geändert werden
- Bei .env Änderungen: Container neu starten

## Lizenz

MIT License - Siehe LICENSE Datei
