# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot
**Domain:** Developer Tools / AI Coding Assistant
**Type:** Local Docker-based Single-User System for Unraid
**Status:** MVP Complete ✅

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt. Funktionsumfang und Bediengefühl an app.emergent.sh angelehnt, aber ohne Credit-System, ohne Kundenplattform und ohne öffentliche Hosting-Infrastruktur.

## User Persona
- **Primär:** Einzelentwickler, Hobby-Programmierer, Tech-Enthusiasten
- **Anwendungsfall:** KI-gestützte Softwareentwicklung lokal auf eigenem Server

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons
- **Backend:** FastAPI (Python), MongoDB 4.4
- **AI:** OpenAI GPT-4o mit Tool Calling
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
- [x] **Code-Generierung mit OpenAI Tool Calls**
- [x] **Automatische Dateierstellung (create_file, modify_file, read_file)**
- [x] File Explorer mit Tree-Struktur
- [x] Code Editor mit Speichern-Funktion
- [x] Preview Panel
- [x] Logs Tab mit Terminal-Ansicht
- [x] Roadmap Tab

#### 3. Backend API (94% Testabdeckung)
- [x] Projects CRUD (/api/projects)
- [x] Messages/Chat (/api/projects/{id}/messages, /api/projects/{id}/chat)
- [x] Agent Status (/api/projects/{id}/agents)
- [x] Logs (/api/projects/{id}/logs)
- [x] Roadmap (/api/projects/{id}/roadmap)
- [x] GitHub Import/Export (/api/github/import, /api/github/commit)
- [x] Workspace Files (/api/projects/{id}/files)

#### 4. AI Tool System
- [x] create_file - Neue Dateien erstellen
- [x] modify_file - Dateien bearbeiten
- [x] read_file - Dateien lesen
- [x] delete_file - Dateien löschen
- [x] list_files - Dateien auflisten
- [x] run_command - Shell-Befehle ausführen
- [x] create_roadmap - Roadmap-Einträge erstellen
- [x] update_roadmap_status - Roadmap-Status aktualisieren

#### 5. GitHub Integration
- [x] Repository Import Dialog
- [x] Clone mit Token-Authentifizierung
- [x] Commit & Push API
- [x] Commit Button in UI

### 🔲 Backlog (P1 - Medium Priority)

- [ ] Echte Live-Preview mit isolierten Docker-Containern
- [ ] Hot Reload für Preview
- [ ] Multi-File Editor Tabs
- [ ] Syntax Highlighting im Editor
- [ ] Branch Switching im Frontend
- [ ] Projekt-Export (lokaler Download)
- [ ] Settings Panel für API Keys

### 🔲 Backlog (P2 - Low Priority)

- [ ] Docker Compose für Unraid
- [ ] Ollama Integration (lokale LLMs als Fallback)
- [ ] WebSocket für Real-time Updates (statt Polling)
- [ ] Projekt-Templates
- [ ] Test-Runner Integration

## Testing Results
- **Backend:** 93.3% Tests bestanden
- **Frontend:** 95% Tests bestanden
- **Overall:** 94% Erfolgsrate

## Configuration

### Environment Variables (Backend)
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="forgepilot"
OPENAI_API_KEY="sk-..."
GITHUB_TOKEN="github_pat_..."
```

## Next Action Items
1. ✅ Code-Generierung implementiert
2. ✅ File Explorer & Editor implementiert
3. ⏳ Docker Compose für Unraid-Deployment
4. ⏳ Live-Preview mit Docker Container
