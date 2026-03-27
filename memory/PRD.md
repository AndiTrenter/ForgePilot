# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot  
**Domain:** Developer Tools / AI Coding Assistant  
**Type:** Local Docker-based Single-User System for Unraid  
**Status:** ✅ FEATURE-COMPLETE & TESTED
**Last Updated:** 4. Dezember 2025

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt.

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons, Prism.js
- **Backend:** FastAPI, MongoDB 4.4, httpx, DuckDuckGo Search
- **AI:** OpenAI GPT-4o mit Tool Calling (13 Tools)
- **Deployment:** Docker Compose für Unraid

## ✅ All Implemented Features

### P0 (Core Features)
- [x] Projekt erstellen per Chat
- [x] Autonomer AI-Workflow (coden, testen, debuggen)
- [x] Live-Preview für HTML/CSS/JS
- [x] GitHub Import/Export
- [x] 7 spezialisierte Agenten

### P1 (High Priority)
- [x] Made with Emergent Badge entfernt
- [x] Preview-Panel Toggle (schließen/öffnen)
- [x] Scroll-Problem behoben
- [x] Mikrofon-Button für Spracheingabe
- [x] Live-Aktivitätsanzeige
- [x] Projekt-Zusammenfassung
- [x] Multi-Tab Editor
- [x] Ollama Settings UI
- [x] **Settings-Modal für API Keys (NEU)**
  - OpenAI API Key eingeben & speichern
  - GitHub Token eingeben & speichern
  - Keys persistent in MongoDB
  - Zugänglich von StartScreen & Workspace

### P2 (Medium Priority) - ✅ ERLEDIGT
- [x] **6 Projekt-Templates:**
  - React App (⚛️)
  - Vue.js App (💚)
  - Node.js API (🟢)
  - Python FastAPI (🐍)
  - Landing Page (🚀)
  - Dashboard (📊)
- [x] **8 Tastaturkürzel:**
  - Ctrl+S - Datei speichern
  - Ctrl+Shift+S - Alle Dateien speichern
  - Ctrl+P - Preview ein/aus
  - Ctrl+B - Datei-Explorer ein/aus
  - Ctrl+K - Chat fokussieren
  - Ctrl+W - Tab schließen
  - Ctrl+Shift+R - Preview neu laden
  - Ctrl+, - Einstellungen öffnen

### P3 (Low Priority) - ✅ ERLEDIGT
- [x] Komponenten refactored in separate Dateien:
  - /components/common.jsx (Tooltip, Logo, LoadingScreen)
  - /components/api.js (API Funktionen)
  - /components/AgentComponents.jsx (Agent UI)
  - /components/EditorComponents.jsx (Editor, FileTree, Chat)
  - /components/templates.js (Template-Definitionen)
  - /components/shortcuts.js (Keyboard Shortcuts)

## Test Results (Iteration 5)

| Kategorie | Ergebnis |
|-----------|----------|
| Backend | 100% Pass |
| Frontend | 100% Pass |
| Templates | 6/6 funktionieren |
| Shortcuts | 8/8 angezeigt |

## API Endpoints (Alle getestet ✅)

- GET /api/ - API Status
- GET /api/projects - Projektliste
- POST /api/projects - Neues Projekt
- GET/DELETE /api/projects/{id}
- POST /api/projects/{id}/chat - Chat (SSE)
- GET /api/projects/{id}/messages
- GET /api/projects/{id}/agents
- GET /api/projects/{id}/files
- PUT /api/projects/{id}/files
- GET /api/projects/{id}/preview/{path}
- GET /api/projects/{id}/preview-info
- POST /api/projects/{id}/push
- GET /api/projects/{id}/roadmap
- GET /api/projects/{id}/logs
- GET /api/github/repos
- GET /api/github/branches
- POST /api/github/import
- GET /api/ollama/status
- POST /api/ollama/enable
- GET /api/settings - Aktuelle Settings (ohne Keys zu exponieren)
- PUT /api/settings - Settings aktualisieren
- DELETE /api/settings/openai-key - OpenAI Key löschen
- DELETE /api/settings/github-token - GitHub Token löschen

## Future Backlog

- [ ] Echte Docker-Container für Node.js/Python Projekte
- [ ] Mehrere Ollama-Modelle zur Auswahl
- [ ] Projekt-Export als ZIP
- [ ] Versionsverlauf für Dateien
- [ ] Weitere Templates (Svelte, Angular, Django)

## Changelog

### 4. Dezember 2025 - SETTINGS FEATURE COMPLETE
- ✅ Settings-Modal mit 3 Tabs (API Keys, LLM, Tastatur)
- ✅ OpenAI API Key & GitHub Token persistent in MongoDB
- ✅ Settings-Button auf StartScreen & Workspace
- ✅ Backend lädt Settings beim Start aus DB
- ✅ Alle API Endpoints getestet (iteration_7.json: 100% Pass)

### 27. März 2026 - P2/P3 COMPLETE
- ✅ 6 Projekt-Templates auf Homepage
- ✅ 8 Tastaturkürzel implementiert
- ✅ Komponenten in separate Dateien refactored
- ✅ Settings-Modal erweitert mit Shortcuts-Anzeige

### 27. März 2026 - P1 COMPLETE
- ✅ Preview-Panel Toggle
- ✅ Scroll-Fix
- ✅ Mikrofon-Button
- ✅ Made with Emergent Badge entfernt

### 26. März 2026
- ✅ Live-Aktivitätsanzeige
- ✅ Multi-Tab Editor
- ✅ Ollama Settings UI
- ✅ Projekt-Zusammenfassung

### 25. März 2026
- ✅ MVP erstellt
- ✅ Workspace Split-Pane UI
- ✅ Agent Status Timeline

## Project Structure

```
/app/
├── backend/
│   ├── server.py              # FastAPI Application
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.js             # Main React App
│   │   ├── App.css
│   │   └── components/
│   │       ├── index.js       # Re-exports
│   │       ├── common.jsx     # Tooltip, Logo
│   │       ├── api.js         # API Functions
│   │       ├── AgentComponents.jsx
│   │       ├── EditorComponents.jsx
│   │       ├── templates.js   # 6 Templates
│   │       └── shortcuts.js   # Keyboard Shortcuts
│   └── package.json
├── workspaces/                # Project files
├── docker-compose.yml
└── memory/
    └── PRD.md
```

## 🎉 PROJECT COMPLETE

ForgePilot ist vollständig implementiert und getestet. Alle P0, P1, P2 und P3 Aufgaben sind erledigt.
