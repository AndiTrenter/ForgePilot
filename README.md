# ForgePilot

Ein lokales AI-Entwicklungssystem für Unraid. Erstelle Software-Projekte per Chat - ForgePilot recherchiert, plant, programmiert, testet und debuggt automatisch.

## Features

- **Autonome KI-Entwicklung** - Agent arbeitet selbstständig bis fertig oder Frage nötig
- **Live-Preview** - Echte Vorschau deiner Projekte im Browser
- **7 spezialisierte Agenten** - Orchestrator, Planner, Coder, Reviewer, Tester, Debugger, Git
- **6 Projekt-Templates** - React, Vue.js, Node.js, Python FastAPI, Landing Page, Dashboard
- **GitHub Integration** - Import/Export von Repositories
- **Spracheingabe** - Mikrofon-Button für Sprachbefehle
- **Ollama Support** - Nutze lokale LLMs statt OpenAI

## Installation auf Unraid

### Option 1: Vorgebaute Docker Images (Empfohlen)

Nach dem Push zu GitHub werden die Docker Images automatisch gebaut.

1. **Repository klonen:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/forgepilot.git
   cd forgepilot
   ```

2. **Environment-Variablen konfigurieren:**
   ```bash
   cp .env.example .env
   nano .env  # Füge deinen OpenAI API Key ein
   ```

3. **docker-compose.unraid.yml anpassen:**
   ```bash
   # Ersetze YOUR_GITHUB_USERNAME mit deinem GitHub Benutzernamen
   sed -i 's/YOUR_GITHUB_USERNAME/dein-username/g' docker-compose.unraid.yml
   ```

4. **Docker Container starten:**
   ```bash
   docker-compose -f docker-compose.unraid.yml up -d
   ```

### Option 2: Lokal bauen

```bash
git clone https://github.com/YOUR_USERNAME/forgepilot.git
cd forgepilot
cp .env.example .env
# OPENAI_API_KEY eintragen
docker-compose up -d --build
```

### Zugriff

- **Frontend:** http://YOUR_UNRAID_IP:3000
- **Backend API:** http://YOUR_UNRAID_IP:8001

### GitHub Actions

Bei jedem Push zu `main` werden automatisch Docker Images gebaut:
- `ghcr.io/YOUR_USERNAME/forgepilot/forgepilot-backend:latest`
- `ghcr.io/YOUR_USERNAME/forgepilot/forgepilot-frontend:latest`

Für ein Release mit Version-Tag:
```bash
git tag v1.0.0
git push origin v1.0.0
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

## Konfiguration

### OpenAI

Für Cloud-basierte KI (empfohlen für beste Qualität):

1. Erstelle einen API Key: https://platform.openai.com/api-keys
2. Füge ihn in `backend/.env` ein:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

### Ollama (Lokal)

Für lokale LLMs ohne Cloud:

1. Installiere Ollama: https://ollama.com
2. Starte Ollama: `ollama serve`
3. Lade ein Modell: `ollama pull llama3`
4. Aktiviere Ollama in ForgePilot Einstellungen

### GitHub Integration

Für Repository Import/Export:

1. Erstelle einen Personal Access Token: https://github.com/settings/tokens
2. Füge ihn in `backend/.env` ein:
   ```
   GITHUB_TOKEN=github_pat_your-token-here
   ```

## Architektur

```
ForgePilot
├── frontend/          # React 19 + Tailwind CSS
│   ├── src/
│   │   ├── App.js
│   │   └── components/
│   └── Dockerfile
├── backend/           # FastAPI + MongoDB
│   ├── server.py
│   └── Dockerfile
├── docker-compose.yml # Für Unraid Deployment
└── workspaces/        # Generierte Projekte
```

## API Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | /api/projects | Liste aller Projekte |
| POST | /api/projects | Neues Projekt erstellen |
| POST | /api/projects/{id}/chat | Chat mit Agent (SSE) |
| GET | /api/projects/{id}/preview/{path} | Live-Preview |
| POST | /api/github/import | GitHub Repo importieren |

## Entwicklung

```bash
# Backend starten
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Frontend starten
cd frontend
yarn install
yarn start
```

## Lizenz

MIT License - Siehe LICENSE Datei
