# 🏗️ ForgePilot Architecture Documentation

**Version:** 3.0.0  
**Datum:** 2025-04-02  
**Status:** ✅ Vollständig transformiert

---

## 📊 System Overview

ForgePilot ist eine **Agentic Software Delivery Platform** die wie eine professionelle Software-Agentur arbeitet. Das System führt strukturierte Delivery-Phasen aus (Discovery → Design → Planning → Implementation → Verification → Handover) mit harten Quality-Gates.

---

## 🗂️ Project Structure

```
/app/
├── backend/                     # FastAPI Backend
│   ├── server.py               # ✅ AKTIV: Hauptserver mit integrierter API v1
│   ├── server_migrated.py      # 🔄 Hybrid: Kombiniert alte + neue Routen
│   ├── server_v3.py            # 🆕 Komplett modularer Server (zukünftig)
│   │
│   ├── core/                   # ✅ Kern-Systeme
│   │   ├── config.py           # Zentrale Konfiguration
│   │   ├── database.py         # MongoDB Abstraction Layer
│   │   ├── state_machine.py    # Project/Task State Machine
│   │   └── exceptions.py       # Custom Exceptions
│   │
│   ├── models/                 # ✅ Data Models
│   │   ├── project.py          # Project Model
│   │   ├── task.py             # Task Model mit AcceptanceCriteria
│   │   └── provider.py         # Provider Registry (OpenAI, Anthropic, etc.)
│   │
│   ├── gates/                  # ✅ Quality Gates
│   │   └── completion_gate.py  # Erzwingt Build/Test/Lint vor mark_complete
│   │
│   ├── llm/                    # 🔄 LLM Routing (teilweise implementiert)
│   │   └── router.py           # Model Router für intelligente LLM-Auswahl
│   │
│   ├── services/               # 🔄 Business Logic (teilweise)
│   │   ├── discovery.py        # Discovery Phase
│   │   ├── design.py           # Solution Design
│   │   └── planning.py         # Delivery Planning
│   │
│   ├── provisioning/           # 🔄 Environment Setup (teilweise)
│   │   └── detector.py         # Tech Stack Detection
│   │
│   ├── tools/                  # ✅ Tool Registry
│   │   └── registry.py         # Tool Registry mit Permissions
│   │
│   ├── api/                    # ✅ API v1 Endpoints
│   │   ├── dependencies.py     # FastAPI Dependencies
│   │   └── v1/
│   │       ├── settings.py     # Settings & Provider API
│   │       └── tasks.py        # Task Management API
│   │
│   └── tests/                  # Test Suite
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── App.js              # ✅ Haupt-App (3500+ Zeilen, teilweise refactored)
│   │   │
│   │   ├── components/
│   │   │   ├── settings/       # ✅ Settings System
│   │   │   │   └── SettingsCenter.jsx  # Provider-Registry UI
│   │   │   │
│   │   │   ├── delivery/       # ✅ Delivery Phase UI
│   │   │   │   ├── PhaseIndicator.jsx  # Phase-Status-Anzeige
│   │   │   │   └── TaskBoard.jsx       # Task Board mit Status
│   │   │   │
│   │   │   ├── evidence/       # ✅ Evidence Collection UI
│   │   │   │   └── EvidenceViewer.jsx  # Build/Test/Screenshot Viewer
│   │   │   │
│   │   │   ├── modals/         # ✅ Wiederverwendbare Modals
│   │   │   │   └── ConfirmationModal.jsx
│   │   │   │
│   │   │   ├── layout/         # ✅ Layout Komponenten
│   │   │   │   └── Logo.jsx
│   │   │   │
│   │   │   └── ui/             # ✅ UI Komponenten
│   │   │       └── Tooltip.jsx
│   │   │
│   │   ├── DeployModal.js      # Deployment Modal
│   │   └── App.css             # Styles
│   │
│   ├── package.json
│   └── vite.config.js
│
├── docs/                       # Dokumentation
│   ├── ARCHITECTURE.md         # Diese Datei
│   ├── MIGRATION_GUIDE.md      # Migrationsleitfaden
│   ├── SYSTEM_TRANSFORMATION_PLAN.md
│   └── DEPLOYMENT_GUIDE.md
│
└── memory/                     # Persistent Memory
    └── test_credentials.md     # Test-Credentials
```

---

## 🔑 Kern-Konzepte

### 1. **Completion Gates System**

**Zweck:** Verhindert dass Tasks als "fertig" markiert werden ohne Quality-Checks.

**Location:** `/app/backend/gates/completion_gate.py`

**Integration:** In `server.py` bei `mark_complete` Tool aktiviert.

**Checks:**
- ✅ **Gate 1:** Keine Error-Logs in letzten 10 Einträgen
- ✅ **Gate 2:** Mindestens 1 Code-Datei erstellt
- ✅ **Gate 3:** tested_features angegeben

**Aktivierung:** Via `enable_completion_gates` Flag in Config.

```python
# In server.py - mark_complete Tool
if config.enable_completion_gates:
    # Prüfe Gates
    if not gate_checks_passed:
        return "🚨 COMPLETION GATES BLOCKIERT!"
```

---

### 2. **Provider Registry System**

**Zweck:** Zentrale Verwaltung aller externen Service-Provider (OpenAI, Anthropic, GitHub, etc.)

**Location:** `/app/backend/models/provider.py`

**Implementiert:**
- Provider-Metadaten (Name, Kategorie, URLs)
- **Deep-Links:** Direkte Links zu Key-Erstellung Pages
- Field-Definitionen mit Validierung
- Model-Definitionen (für LLM-Provider)

**API Endpoints:**
- `GET /api/v1/settings/providers` - Liste aller Provider
- `GET /api/v1/settings/providers/{id}` - Provider-Details
- `POST /api/v1/settings/providers/{id}/test` - Test Connection
- `POST /api/v1/settings/providers/{id}/configure` - Konfigurieren

**Eingebaute Provider:**
- 🤖 **OpenAI** (GPT-4o, GPT-4o-mini)
- 🧠 **Anthropic** (Claude Sonnet 4, Haiku 4)
- ✨ **Google AI** (Gemini 2.0 Flash)
- 🐙 **GitHub** (Repository Management)

---

### 3. **State Machine**

**Zweck:** Erzwingt gültige Status-Übergänge für Projekte und Tasks.

**Location:** `/app/backend/core/state_machine.py`

**Project States:**
```
discovery → awaiting_user → solution_design → planning → 
provisioning → implementing → reviewing → testing → 
debugging → ready_for_handover → completed
```

**Task States:**
```
queued → in_progress → under_review → under_test → 
passed/failed → done
```

---

### 4. **Settings Center UI**

**Zweck:** Benutzerfreundliche UI zur Provider-Konfiguration.

**Location:** `/app/frontend/src/components/settings/SettingsCenter.jsx`

**Features:**
- Provider-Cards mit Status (configured / not configured)
- **"Get API Key ↗"** Deep-Links direkt zur Provider-Seite
- Test-Connection-Buttons
- Live-Status-Anzeigen

**Integration:** Über Settings-Button im Header aufrufbar.

---

### 5. **Delivery Phase UI**

**Komponenten:**

#### **PhaseIndicator** (`/frontend/src/components/delivery/PhaseIndicator.jsx`)
- Zeigt aktuellen Phase-Status an
- 10 Phasen: Discovery → Completed
- Visuelles Feedback (aktiv, completed, future)

#### **TaskBoard** (`/frontend/src/components/delivery/TaskBoard.jsx`)
- Task-Cards mit Status (queued, in_progress, blocked, done, failed)
- Acceptance Criteria Tracking
- Priority Labels

#### **EvidenceViewer** (`/frontend/src/components/evidence/EvidenceViewer.jsx`)
- Zeigt gesammelte Evidence an
- Build-Logs, Test-Reports, Screenshots, Code-Diffs
- Modal zum Anzeigen von Details

---

## 🔄 API Architecture

### Legacy API (aktiv in server.py)

Alle bestehenden Endpoints unter `/api/`:
- `/api/projects` - CRUD
- `/api/projects/{id}/chat` - Agent Loop
- `/api/settings` - Settings Management
- `/api/github/*` - GitHub Integration
- `/api/update/*` - Update System

### API v1 (neu hinzugefügt)

Neue modulare Endpoints unter `/api/v1/`:
- `/api/v1/settings/providers` - Provider Registry
- `/api/v1/tasks` - Task Management (teilweise)

**Strategie:** Hybrid-Modus - beide APIs laufen parallel.

---

## 🗄️ Database Schema

### **MongoDB Collections:**

#### `projects`
```js
{
  id: "uuid",
  name: "Project Name",
  description: "...",
  project_type: "fullstack|mobile|landing",
  status: "discovery|implementing|completed",
  workspace_path: "/app/workspaces/{id}",
  created_at: "ISO8601",
  updated_at: "ISO8601"
}
```

#### `messages`
```js
{
  id: "uuid",
  project_id: "uuid",
  role: "user|assistant|system",
  content: "...",
  created_at: "ISO8601"
}
```

#### `agent_status`
```js
{
  project_id: "uuid",
  agent: "orchestrator|planner|coder|tester",
  status: "idle|running|completed",
  message: "Current status",
  timestamp: "ISO8601"
}
```

#### `logs`
```js
{
  project_id: "uuid",
  level: "info|success|warning|error",
  message: "...",
  agent: "orchestrator|coder|tester",
  timestamp: "ISO8601"
}
```

#### `evidence` (neu)
```js
{
  task_id: "uuid",
  type: "build|test|lint|screenshot|code_diff|gate_report",
  status: "success|failed",
  content: "...",
  metadata: {
    total: 10,
    passed: 8,
    failed: 2
  },
  timestamp: "ISO8601"
}
```

---

## 🔐 Security & Configuration

### Environment Variables

**Backend (.env):**
```bash
MONGO_URL=mongodb://mongodb:27017
DB_NAME=forgepilot
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
APP_VERSION=3.0.0
ENVIRONMENT=production|development
```

**Frontend (.env):**
```bash
REACT_APP_BACKEND_URL=https://portal-test-issue.preview.emergentagent.com
```

### Feature Flags

Definiert in `/app/backend/core/config.py`:
```python
enable_auto_provisioning = True
enable_completion_gates = True
enable_multi_model = False  # Zukünftig
enable_evidence_collection = True
```

---

## 🚀 Deployment

### Services

**Docker Compose:**
- `forgepilot-backend` - FastAPI auf Port 8001
- `forgepilot-frontend` - React/Nginx auf Port 3000
- `mongodb` - MongoDB auf Port 27017

**Nginx Reverse Proxy:**
- `/api/*` → Backend (Port 8001)
- `/*` → Frontend (Port 3000)

### Supervisor

Services werden von Supervisor verwaltet:
```bash
sudo supervisorctl status
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

---

## 📈 Performance & Scaling

### Optimierungen
- **Connection Pooling:** MongoDB mit min/max pool size
- **Async Operations:** Alle DB-Operationen async
- **Tool-System:** Parallel-Execution wo möglich

### Limits
- Max Iterations: 200 pro Agent Loop
- Max Tool Calls: Unbegrenzt (gestoppt bei mark_complete oder ask_user)
- MongoDB Pool: 10 Connections

---

## 🔧 Development Workflow

### Backend Development
```bash
cd /app/backend
source /root/.venv/bin/activate
python server.py  # Dev-Modus mit Hot Reload
```

### Frontend Development
```bash
cd /app/frontend
yarn install
yarn dev  # Vite Dev Server
```

### Testing
```bash
# Backend
cd /app/backend
pytest tests/

# Frontend
cd /app/frontend
yarn test
```

---

## 📝 Next Steps / Roadmap

### Phase 1: Vollständige Gates-Integration ✅
- [x] Completion Gates in mark_complete integriert
- [x] Error-Log-Check
- [x] File-Check
- [x] tested_features-Check

### Phase 2: Evidence Collection System (teilweise)
- [x] Evidence Models definiert
- [x] EvidenceViewer UI erstellt
- [ ] Automatische Evidence Collection bei Tool-Ausführung
- [ ] Screenshot-Upload-System

### Phase 3: Multi-Model-Routing (TODO)
- [ ] ModelRouter vollständig implementieren
- [ ] Task-Type-basiertes Routing
- [ ] Cost-Tracking-System
- [ ] Fallback-Mechanismen

### Phase 4: Complete Backend Migration (TODO)
- [ ] Alle Routes zu API v1 migrieren
- [ ] server.py deprecaten
- [ ] Nur noch server_v3.py / server_migrated.py

### Phase 5: Frontend Complete Refactoring (teilweise)
- [x] SettingsCenter.jsx extrahiert
- [x] PhaseIndicator, TaskBoard, EvidenceViewer erstellt
- [x] ConfirmationModal, Logo, Tooltip extrahiert
- [ ] App.js vollständig aufteilen (Sidebar, Chat, etc.)
- [ ] State Management (Zustand?)

---

## 🤝 Contributing

**Code Style:**
- Python: PEP 8
- JavaScript: ESLint + Prettier
- Commit Messages: Conventional Commits

**PR Process:**
1. Feature Branch erstellen
2. Änderungen implementieren
3. Tests schreiben
4. PR öffnen
5. Code Review

---

**Autor:** E1 Agent  
**Letzte Aktualisierung:** 2025-04-02  
**Version:** 3.0.0
