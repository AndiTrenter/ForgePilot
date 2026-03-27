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

### Voraussetzungen

- Unraid 6.x oder höher
- Docker und Docker Compose
- OpenAI API Key (oder Ollama für lokale LLMs)

### Schnellstart

1. **Repository klonen:**
   ```bash
   git clone https://github.com/your-username/forgepilot.git
   cd forgepilot
   ```

2. **Environment-Variablen konfigurieren:**
   ```bash
   cp backend/.env.example backend/.env
   # Bearbeite backend/.env und füge deinen OpenAI API Key ein
   ```

3. **Docker Container starten:**
   ```bash
   docker-compose up -d
   ```

4. **Öffne ForgePilot:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001

### Unraid Community Applications

Alternativ kannst du ForgePilot über die Unraid Community Applications installieren:

1. Öffne "Apps" in Unraid
2. Suche nach "ForgePilot"
3. Klicke "Install"
4. Konfiguriere deinen OpenAI API Key
5. Fertig!

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
