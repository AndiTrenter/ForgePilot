# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot
**Domain:** Developer Tools / AI Coding Assistant
**Type:** Local Docker-based Single-User System for Unraid

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt. Funktionsumfang und Bediengefühl an app.emergent.sh angelehnt, aber ohne Credit-System, ohne Kundenplattform und ohne öffentliche Hosting-Infrastruktur.

## User Persona
- **Primär:** Einzelentwickler, Hobby-Programmierer, Tech-Enthusiasten
- **Anwendungsfall:** KI-gestützte Softwareentwicklung lokal auf eigenem Server

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons
- **Backend:** FastAPI (Python), MongoDB 4.4
- **AI:** OpenAI GPT-4o
- **Version Control:** GitPython
- **Design:** IBM Plex Sans + JetBrains Mono, Dark Theme (Zinc-950)

## Core Requirements

### ✅ Implemented (MVP - March 27, 2025)

#### 1. Start Screen
- [x] Zentraler Prompt-Bereich ("Was möchtest du bauen?")
- [x] Projekttyp-Auswahl (Full Stack App, Mobile App, Landing Page)
- [x] Aktuelle Projekte Übersicht
- [x] GitHub Import Button

#### 2. Workspace / Arbeitsbereich
- [x] Zweispaltiges Layout (Chat links, Preview rechts)
- [x] Agent Status Timeline (Orchestrator, Planner, Coder, Reviewer, Tester, Debugger, Git)
- [x] Chat mit AI Agent (Streaming Responses)
- [x] Preview Panel mit Mock Browser
- [x] Logs Tab mit Terminal-Ansicht

#### 3. Backend API
- [x] Projects CRUD (/api/projects)
- [x] Messages/Chat (/api/projects/{id}/messages, /api/projects/{id}/chat)
- [x] Agent Status (/api/projects/{id}/agents)
- [x] Logs (/api/projects/{id}/logs)
- [x] Roadmap (/api/projects/{id}/roadmap)
- [x] GitHub Import/Export (/api/github/import, /api/github/commit)
- [x] Workspace Files (/api/projects/{id}/files)

#### 4. GitHub Integration
- [x] Repository Import Dialog
- [x] Clone mit Token-Authentifizierung
- [x] Commit & Push API

#### 5. UI/UX
- [x] Dark Theme (Zinc-950 Palette)
- [x] IBM Plex Sans + JetBrains Mono Fonts
- [x] Responsive Design
- [x] Animationen (Fade-in, Pulse für aktive Agenten)

### 🔲 Backlog (P0 - High Priority)

#### Agent System (vollständige Implementierung)
- [ ] Orchestrator Agent - Gesamtprozess-Steuerung
- [ ] Planner Agent - Anforderungsanalyse, Strategie, Roadmap
- [ ] Coder Agent - Code-Generierung in isolierten Workspaces
- [ ] Reviewer Agent - Code-Review, Qualitätsprüfung
- [ ] Test Agent - Automatisierte Tests
- [ ] Debugger Agent - Log-Analyse, Fehlerbehebung
- [ ] Git Agent - Versionskontrolle

#### Preview System
- [ ] Echte Live-Preview mit isolierten Containern
- [ ] Hot Reload für Preview
- [ ] Port Management für Preview Container

#### Workspace Management
- [ ] File Explorer im Frontend
- [ ] Code Editor Integration
- [ ] Multi-File Editing

### 🔲 Backlog (P1 - Medium Priority)

- [ ] Roadmap Visualization
- [ ] Automatisierte Tests mit Playwright
- [ ] Build-Logs Streaming
- [ ] Branch Switching im Frontend
- [ ] Projekt-Export (lokaler Download)
- [ ] Settings Panel für API Keys

### 🔲 Backlog (P2 - Low Priority)

- [ ] Docker Compose für Unraid
- [ ] Ollama Integration (lokale LLMs)
- [ ] WebSocket für Real-time Updates
- [ ] Multi-Tab Support
- [ ] Projekt-Templates

## API Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | /api/ | API Status |
| GET | /api/projects | Liste aller Projekte |
| POST | /api/projects | Neues Projekt erstellen |
| GET | /api/projects/{id} | Projekt Details |
| DELETE | /api/projects/{id} | Projekt löschen |
| GET | /api/projects/{id}/messages | Chat-Nachrichten |
| POST | /api/projects/{id}/chat | Chat mit AI (SSE) |
| GET | /api/projects/{id}/agents | Agent Status |
| GET | /api/projects/{id}/logs | Logs |
| GET | /api/projects/{id}/roadmap | Roadmap Items |
| POST | /api/github/import | GitHub Repo importieren |
| POST | /api/github/commit | Commit & Push |
| GET | /api/projects/{id}/files | Workspace Dateien |

## Configuration

### Environment Variables (Backend)
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="forgepilot"
OPENAI_API_KEY="sk-..."
GITHUB_TOKEN="github_pat_..."
```

### Environment Variables (Frontend)
```
REACT_APP_BACKEND_URL=https://...
```

## Design Guidelines
- **Color Palette:** Zinc-950 (Background), Zinc-900 (Surface), Blue-500 (Processing), Emerald-500 (Success), Rose-500 (Error)
- **Typography:** IBM Plex Sans (Headings/Body), JetBrains Mono (Code)
- **Border Radius:** 0.25rem
- **Spacing:** Generous (p-6, p-8)

## Next Action Items
1. Implementierung der echten Agent-Logik mit Tool-Calls
2. Live-Preview mit Docker Container
3. File Explorer und Code Editor
4. Docker Compose Setup für Unraid
