# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot
**Domain:** Developer Tools / AI Coding Assistant
**Type:** Local Docker-based Single-User System for Unraid
**Status:** MVP + P1 Features Complete ✅

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt. Funktionsumfang und Bediengefühl an app.emergent.sh angelehnt, aber ohne Credit-System, ohne Kundenplattform und ohne öffentliche Hosting-Infrastruktur.

## User Persona
- **Primär:** Einzelentwickler, Hobby-Programmierer, Tech-Enthusiasten
- **Anwendungsfall:** KI-gestützte Softwareentwicklung lokal auf eigenem Server

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons, Prism.js
- **Backend:** FastAPI (Python), MongoDB 4.4, httpx
- **AI:** OpenAI GPT-4o mit Tool Calling
- **Version Control:** GitPython
- **Deployment:** Docker Compose
- **Design:** IBM Plex Sans + JetBrains Mono, Dark Theme (Zinc-950)

## Core Requirements

### ✅ Implemented (MVP + P1 - March 27, 2025)

#### 1. Start Screen
- [x] Zentraler Prompt-Bereich ("Was möchtest du bauen?")
- [x] Projekttyp-Auswahl (Full Stack App, Mobile App, Landing Page)
- [x] Aktuelle Projekte Übersicht
- [x] GitHub Import Button

#### 2. Workspace / Arbeitsbereich
- [x] Zweispaltiges Layout (Chat links, Preview rechts)
- [x] Agent Status Timeline (7 Agenten)
- [x] Chat mit AI Agent (Streaming Responses)
- [x] **KEIN Auto-Scroll** - Nutzer kontrolliert Scrollposition
- [x] "Zum Ende scrollen" Button
- [x] **Code-Generierung mit OpenAI Tool Calls**
- [x] File Explorer mit Tree-Struktur (Expand/Collapse)
- [x] **Code Editor mit Prism.js Syntax Highlighting**
- [x] Preview Panel
- [x] Logs Tab
- [x] Roadmap Tab

#### 3. GitHub Integration (VERBESSERT)
- [x] **Repository Dropdown** - lädt alle Repos des Users
- [x] **Branch Dropdown** - lädt Branches nach Repo-Auswahl
- [x] **Repo Info Box** - zeigt Name, öffentlich/privat Status
- [x] Zwei Modi: "Meine Repos" oder "URL eingeben"
- [x] Clone mit Token-Authentifizierung
- [x] Commit & Push API
- [x] Commit Button in UI

#### 4. AI Tool System
- [x] create_file - Neue Dateien erstellen
- [x] modify_file - Dateien bearbeiten
- [x] read_file - Dateien lesen
- [x] delete_file - Dateien löschen
- [x] list_files - Dateien auflisten
- [x] run_command - Shell-Befehle ausführen
- [x] create_roadmap - Roadmap-Einträge erstellen
- [x] update_roadmap_status - Roadmap-Status aktualisieren

#### 5. Docker Compose (NEU)
- [x] docker-compose.yml für Unraid
- [x] Backend Dockerfile
- [x] Frontend Dockerfile mit nginx
- [x] .env.example mit Konfiguration

### 🔲 Backlog (P2 - Low Priority)

- [ ] Echte Live-Preview mit Docker Container
- [ ] Multi-File Editor Tabs
- [ ] Ollama Integration (lokale LLMs als Fallback)
- [ ] WebSocket für Real-time Updates (statt Polling)
- [ ] Projekt-Templates
- [ ] Test-Runner Integration

## Testing Results
- **Backend:** 100% Tests bestanden
- **Frontend:** 95% Tests bestanden
- **Overall:** 97% Erfolgsrate

## Docker Deployment

```bash
# 1. .env Datei erstellen
cp .env.example .env
# Fülle OPENAI_API_KEY und GITHUB_TOKEN aus

# 2. Container starten
docker-compose up -d

# 3. ForgePilot öffnen
# http://localhost:3000
```

## API Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | /api/github/repos | Liste der GitHub Repos |
| GET | /api/github/branches?repo=user/repo | Branches eines Repos |
| POST | /api/github/import | Repository klonen |
| POST | /api/github/commit | Commit & Push |

## Next Action Items
1. ✅ Kein Auto-Scroll im Chat
2. ✅ GitHub Repos/Branches Dropdowns
3. ✅ Syntax Highlighting
4. ✅ Docker Compose für Unraid
5. ⏳ Echte Live-Preview
