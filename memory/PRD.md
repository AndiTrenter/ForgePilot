# ForgePilot - Product Requirements Document

## Project Overview
**Name:** ForgePilot  
**Domain:** Developer Tools / AI Coding Assistant  
**Type:** Local Docker-based Single-User System for Unraid  
**Status:** ✅ FEATURE-COMPLETE & TESTED
**Last Updated:** 27. März 2026

## Original Problem Statement
Ein lokales, Docker-basiertes Single-User-System auf Unraid, das Software-Projekte per Chat plant, recherchiert, programmiert, testet, debuggt, in einer Live-Preview ausführt und in GitHub oder lokal ausgibt. Der Agent soll autonom arbeiten (coden, testen, debuggen) bis er fertig ist oder eine Frage hat.

## Technology Stack
- **Frontend:** React 19, Tailwind CSS, Lucide React Icons, Prism.js
- **Backend:** FastAPI, MongoDB 4.4, httpx, DuckDuckGo Search
- **AI:** OpenAI GPT-4o mit Tool Calling (13 Tools)
- **Deployment:** Docker Compose für Unraid

## ✅ All Implemented Features

### 1. Intelligente Code-Entwicklung
- [x] **Web Research** - Sucht automatisch nach Best Practices
- [x] **Code-Generierung** mit OpenAI Tool Calls
- [x] **Autonomer Workflow** - Agent arbeitet selbstständig
- [x] **13 AI Tools:** create_file, modify_file, read_file, delete_file, list_files, run_command, create_roadmap, update_roadmap_status, web_search, test_code, debug_error, ask_user, mark_complete

### 2. Live-Preview System
- [x] **Echte Live-Preview** im iframe
- [x] Automatische Erkennung von Entry Points
- [x] "Preview öffnen" Button für externe Ansicht
- [x] Refresh bei Dateiänderungen

### 3. GitHub Workflow
- [x] **Repository Dropdown**
- [x] **Branch Dropdown**
- [x] **Ready for Push** Status
- [x] Push-Button wenn Projekt bereit

### 4. User Experience
- [x] **Tooltips auf allen Buttons** (2 Sekunden Verzögerung)
- [x] Chat ohne Auto-Scroll
- [x] File Explorer mit Tree-Struktur
- [x] Code Editor mit Syntax Highlighting
- [x] **Made with Emergent Badge entfernt**
- [x] **Preview-Panel kann geschlossen werden** (X-Button oder Toggle)
- [x] **Chat expandiert wenn Preview geschlossen**
- [x] **Mikrofon-Button für Spracheingabe** (Web Speech API, Deutsch)

### 5. Agent System (7 Agenten)
- [x] Orchestrator, Planner, Coder, Reviewer, Tester, Debugger, Git

### 6. Live-Aktivitätsanzeige
- [x] **Agent Activity Feed** - Echtzeit-Anzeige
- [x] Farbcodierte Agenten
- [x] Zeitstempel für jede Aktion
- [x] Handoff-Anzeige zwischen Agenten

### 7. Multi-Tab Editor
- [x] Mehrere Dateien gleichzeitig öffnen
- [x] Tabs mit Close-Button
- [x] Unsaved-Indicator
- [x] "Alle speichern" Button

### 8. Ollama Settings UI
- [x] Settings Modal mit LLM-Auswahl
- [x] Toggle zwischen OpenAI/Ollama
- [x] Status-Anzeige und Setup-Anleitung

### 9. Projekt-Zusammenfassung
- [x] Erscheint wenn Projekt für Push bereit
- [x] Zeigt Commit-Message und getestete Features
- [x] Direkte Push- und Preview-Buttons

### 10. Scroll-Fix
- [x] **Preview-Panel scrollt NICHT mit beim Chat-Scrollen**
- [x] CSS `overflow: hidden` auf html/body
- [x] Getestet: document.documentElement.scrollTop bleibt 0

### 11. Docker Deployment
- [x] docker-compose.yml für Unraid
- [x] Backend/Frontend Dockerfiles

## Test Results (Iteration 4)

| Kategorie | Ergebnis |
|-----------|----------|
| Backend | 100% Pass |
| Frontend | 100% Pass |
| KRITISCH: Scroll-Fix | ✅ Bestanden |
| KRITISCH: Panel Toggle | ✅ Bestanden |
| KRITISCH: Badge entfernt | ✅ Bestanden |
| KRITISCH: Mikrofon | ✅ Bestanden |

## API Endpoints (Alle getestet ✅)

- GET /api/ - API Status
- GET /api/projects - Projektliste
- POST /api/projects - Neues Projekt
- GET /api/projects/{id} - Projekt-Details
- DELETE /api/projects/{id} - Projekt löschen
- POST /api/projects/{id}/chat - Chat (SSE)
- GET /api/projects/{id}/messages - Nachrichten
- GET /api/projects/{id}/agents - Agent-Status
- GET /api/projects/{id}/files - Dateiliste
- PUT /api/projects/{id}/files - Datei speichern
- GET /api/projects/{id}/preview/{path} - Preview-Dateien
- GET /api/projects/{id}/preview-info - Preview-Status
- POST /api/projects/{id}/push - Push zu GitHub
- GET /api/projects/{id}/roadmap - Roadmap
- GET /api/projects/{id}/logs - Logs
- GET /api/github/repos - GitHub Repos
- GET /api/github/branches - GitHub Branches
- POST /api/github/import - Repo importieren
- GET /api/ollama/status - Ollama Status
- POST /api/ollama/enable - Ollama aktivieren

## Backlog (Future)

### P2 (Medium)
- [ ] App.js refactoren (~1600 Zeilen → kleinere Komponenten)
- [ ] Tastaturkürzel für häufige Aktionen
- [ ] Projekt-Templates (React, Vue, Node, Python)

### P3 (Low)
- [ ] Mehrere Ollama-Modelle zur Auswahl
- [ ] Projekt-Export als ZIP
- [ ] Versionsverlauf für Dateien
- [ ] Echte Docker-Container für Node.js/Python Projekte

## Changelog

### 27. März 2026 - RELEASE
- ✅ Preview-Panel Toggle (schließen/öffnen)
- ✅ Chat expandiert wenn Preview geschlossen
- ✅ Scroll-Fix endgültig gelöst (CSS overflow:hidden)
- ✅ Mikrofon-Button für Spracheingabe
- ✅ Alle Tests bestanden (100% Backend, 100% Frontend)

### 26. März 2026
- ✅ Made with Emergent Badge entfernt
- ✅ Live-Aktivitätsanzeige
- ✅ Multi-Tab Editor
- ✅ Ollama Settings UI
- ✅ Projekt-Zusammenfassung

### 25. März 2026
- ✅ MVP erstellt
- ✅ Workspace Split-Pane UI
- ✅ Agent Status Timeline
- ✅ Code Editor mit Prism.js
