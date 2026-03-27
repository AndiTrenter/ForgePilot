# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot  
**Domain:** Developer Tools / AI Coding Assistant  
**Type:** Local Docker-based Single-User System for Unraid  
**Status:** Feature-Complete ✅

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt.

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons, Prism.js
- **Backend:** FastAPI, MongoDB 4.4, httpx, DuckDuckGo Search
- **AI:** OpenAI GPT-4o mit Tool Calling (10 Tools)
- **Deployment:** Docker Compose für Unraid

## ✅ Implemented Features

### 1. Intelligente Code-Entwicklung
- [x] **Web Research** - Sucht automatisch nach Best Practices vor der Implementierung
- [x] **Code-Generierung** mit OpenAI Tool Calls
- [x] **10 AI Tools:** create_file, modify_file, read_file, delete_file, list_files, run_command, create_roadmap, update_roadmap_status, web_search, mark_ready_for_push

### 2. Live-Preview System
- [x] **Echte Live-Preview** im iframe - zeigt laufende HTML/CSS/JS Projekte
- [x] Automatische Erkennung von Entry Points (index.html, etc.)
- [x] "Preview öffnen" Button für externe Ansicht
- [x] Refresh bei Dateiänderungen

### 3. GitHub Workflow
- [x] **Repository Dropdown** - lädt alle User-Repos
- [x] **Branch Dropdown** - lädt Branches nach Repo-Auswahl
- [x] **Ready for Push** Status - Agent markiert wenn fertig
- [x] Push-Button erscheint wenn Projekt bereit ist

### 4. User Experience
- [x] **Tooltips auf allen Buttons** - erscheinen nach 2-3 Sekunden Hover
- [x] Einfache Erklärungen für jeden Button
- [x] Verschwinden bei Klick oder Mouse-Leave
- [x] Chat ohne Auto-Scroll
- [x] File Explorer mit Tree-Struktur
- [x] Code Editor mit Syntax Highlighting

### 5. Agent System (7 Agenten)
- [x] Orchestrator - Koordiniert alle Agenten
- [x] Planner - Plant Architektur und Roadmap
- [x] Coder - Schreibt und generiert Code
- [x] Reviewer - Überprüft Code-Qualität
- [x] Tester - Führt Tests durch
- [x] Debugger - Analysiert Fehler
- [x] Git - Verwaltet Versionskontrolle

### 6. Docker Deployment
- [x] docker-compose.yml für Unraid
- [x] Backend Dockerfile
- [x] Frontend Dockerfile mit nginx
- [x] .env.example mit Konfiguration

## Testing Results
- **Backend:** 100%
- **Frontend:** 100%
- **Overall:** 100% Erfolgsrate

## Workflow

```
1. Projekt beschreiben
   ↓
2. Agent recherchiert Best Practices (Web Search)
   ↓
3. Agent erstellt Roadmap
   ↓
4. Agent generiert Code
   ↓
5. Live-Preview testen
   ↓
6. Agent markiert als "Ready for Push"
   ↓
7. Push zu GitHub
   ↓
8. Deployment in reale Umgebung
```

## API Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | /api/projects/{id}/preview/{path} | Serviert Preview-Dateien |
| GET | /api/projects/{id}/preview-info | Preview-Status |
| POST | /api/projects/{id}/push | Push zu GitHub |
| GET | /api/github/repos | Liste der Repos |
| GET | /api/github/branches | Branches eines Repos |

## Next Steps
- Echte Docker-Container für komplexere Projekte (Node.js, Python)
- Multi-Tab Editor Support
- Ollama Integration für lokale LLMs
