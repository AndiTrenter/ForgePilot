# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot  
**Domain:** Developer Tools / AI Coding Assistant  
**Type:** Local Docker-based Single-User System for Unraid  
**Status:** Feature-Complete ✅
**Last Updated:** 27. März 2026

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt. Der Agent soll autonom arbeiten (coden, testen, debuggen) bis er fertig ist oder eine Frage hat.

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons, Prism.js
- **Backend:** FastAPI, MongoDB 4.4, httpx, DuckDuckGo Search
- **AI:** OpenAI GPT-4o mit Tool Calling (13 Tools)
- **Deployment:** Docker Compose für Unraid

## ✅ Implemented Features

### 1. Intelligente Code-Entwicklung
- [x] **Web Research** - Sucht automatisch nach Best Practices vor der Implementierung
- [x] **Code-Generierung** mit OpenAI Tool Calls
- [x] **Autonomer Workflow** - Agent arbeitet selbstständig bis fertig oder Frage nötig
- [x] **13 AI Tools:** create_file, modify_file, read_file, delete_file, list_files, run_command, create_roadmap, update_roadmap_status, web_search, test_code, debug_error, ask_user, mark_complete

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
- [x] Chat ohne Auto-Scroll
- [x] File Explorer mit Tree-Struktur
- [x] Code Editor mit Syntax Highlighting
- [x] **"Made with Emergent" Badge entfernt**

### 5. Agent System (7 Agenten)
- [x] Orchestrator - Koordiniert alle Agenten
- [x] Planner - Plant Architektur und Roadmap
- [x] Coder - Schreibt und generiert Code
- [x] Reviewer - Überprüft Code-Qualität
- [x] Tester - Führt Tests durch
- [x] Debugger - Analysiert Fehler
- [x] Git - Verwaltet Versionskontrolle

### 6. **NEU: Live-Aktivitätsanzeige**
- [x] **Agent Activity Feed** - Zeigt in Echtzeit was der Agent gerade macht
- [x] Farbcodierte Agenten (Coder=grün, Planner=blau, Debugger=rot, etc.)
- [x] Detaillierte Aktionsbeschreibungen (erstellt Datei, bearbeitet, testet, etc.)
- [x] Zeitstempel für jede Aktion
- [x] Handoff-Anzeige zwischen Agenten (z.B. "Debugger übernimmt...")
- [x] Fehler- und Erfolgs-Visualisierung
- [x] Auto-Scroll im Activity Feed

### 7. **NEU: Multi-Tab Editor**
- [x] Mehrere Dateien gleichzeitig öffnen
- [x] Tabs mit Close-Button (X)
- [x] Aktiver Tab hervorgehoben
- [x] Unsaved-Indicator (gelber Punkt) bei geänderten Dateien
- [x] "Alle speichern" Button für mehrere geänderte Dateien

### 8. **NEU: Ollama Settings UI**
- [x] Settings Modal mit LLM-Auswahl
- [x] Toggle zwischen OpenAI GPT-4o und Ollama (lokal)
- [x] Ollama Status-Anzeige (Verfügbar/Nicht verbunden)
- [x] Setup-Anleitung für Ollama

### 9. **NEU: Projekt-Zusammenfassung**
- [x] Erscheint wenn Projekt für Push bereit ist
- [x] Zeigt Commit-Message
- [x] Liste der getesteten Features
- [x] Direkte Push- und Preview-Buttons

### 10. Docker Deployment
- [x] docker-compose.yml für Unraid
- [x] Backend Dockerfile
- [x] Frontend Dockerfile mit nginx
- [x] .env.example mit Konfiguration

## Workflow

```
1. Projekt beschreiben
   ↓
2. Agent recherchiert Best Practices (Web Search)
   ↓
3. Agent erstellt Roadmap
   ↓
4. Agent generiert Code (Live-Aktivität zeigt jeden Schritt)
   ↓
5. Agent testet automatisch
   ↓
6. Bei Fehlern: Debugger übernimmt und korrigiert
   ↓
7. Live-Preview testen
   ↓
8. Agent markiert als "Ready for Push"
   ↓
9. Zusammenfassung erscheint mit getesteten Features
   ↓
10. Push zu GitHub
```

## API Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | /api/ | API Status |
| GET | /api/projects | Liste aller Projekte |
| POST | /api/projects | Neues Projekt erstellen |
| GET | /api/projects/{id} | Projekt-Details |
| DELETE | /api/projects/{id} | Projekt löschen |
| POST | /api/projects/{id}/chat | Chat (SSE Streaming) |
| GET | /api/projects/{id}/messages | Nachrichten abrufen |
| GET | /api/projects/{id}/agents | Agent-Status |
| GET | /api/projects/{id}/files | Dateiliste/Inhalt |
| PUT | /api/projects/{id}/files | Datei speichern |
| GET | /api/projects/{id}/preview/{path} | Preview-Dateien |
| GET | /api/projects/{id}/preview-info | Preview-Status |
| POST | /api/projects/{id}/push | Push zu GitHub |
| GET | /api/projects/{id}/roadmap | Roadmap |
| GET | /api/projects/{id}/logs | Logs |
| GET | /api/github/repos | GitHub Repos |
| GET | /api/github/branches | GitHub Branches |
| POST | /api/github/import | Repo importieren |
| GET | /api/ollama/status | Ollama Status |
| POST | /api/ollama/enable | Ollama aktivieren |

## Backlog / Future Tasks

### P1 (High Priority)
- [ ] Echte Docker-Container für Node.js/Python Projekte
- [ ] UI/UX Testing auf höchstem Niveau (Pixel-Perfect)

### P2 (Medium Priority)
- [ ] App.js refactoren (in kleinere Komponenten aufteilen)
- [ ] Tastaturkürzel für häufige Aktionen
- [ ] Projekt-Templates (React, Vue, Node, Python)

### P3 (Low Priority)
- [ ] Mehrere Ollama-Modelle zur Auswahl
- [ ] Projekt-Export als ZIP
- [ ] Versionsverlauf für Dateien

## Changelog

### 27. März 2026
- ✅ "Made with Emergent" Badge entfernt
- ✅ Live-Aktivitätsanzeige implementiert (Agent Activity Feed)
- ✅ Multi-Tab Editor implementiert
- ✅ Ollama Settings UI implementiert
- ✅ Projekt-Zusammenfassung bei Push-Bereitschaft

### 26. März 2026
- ✅ Autonomer Workflow implementiert
- ✅ Chat ohne Auto-Scroll
- ✅ GitHub Import mit Repo/Branch Dropdowns
- ✅ Tooltips auf allen Buttons
- ✅ Live-Preview für HTML/CSS/JS

### 25. März 2026
- ✅ MVP erstellt
- ✅ MongoDB Integration
- ✅ Workspace Split-Pane UI
- ✅ Agent Status Timeline
- ✅ Code Editor mit Prism.js
