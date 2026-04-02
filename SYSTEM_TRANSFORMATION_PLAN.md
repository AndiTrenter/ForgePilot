# ForgePilot → Agentic Delivery Operating System
## Vollständige System-Transformation

**Datum:** 2026-04-02  
**Status:** PLANUNG  
**Ziel:** Umbau von einem Chat-Interface zu einer professionellen agentischen Entwicklungsplattform

---

## 🎯 EXECUTIVE SUMMARY

**Vision:** ForgePilot soll sich wie eine professionelle Software-Agentur verhalten - nicht wie ein Chatbot, der Code vorschlägt, sondern wie ein autonomes Delivery-System, das Anforderungen analysiert, Architektur entwirft, Umgebungen provisioniert, implementiert, testet und lauffähige Ergebnisse liefert.

**Kernproblem:** Das aktuelle System ist ein Prototyp mit Agentenkonzepten, aber ohne harte systemische Garantien. Es kann "fertig" melden ohne Beweise, hat keine strukturierte Zustandsmaschine, keine zentrale Konfiguration und keine robusten Completion-Gates.

**Zielzustand:** Ein Evidence-Based Delivery System mit:
- Strukturierter Auftragsverarbeitung (Discovery → Design → Planning → Provisioning → Implementation → Verification → Handover)
- Harten Completion-Gates (keine "fertig"-Meldung ohne Build/Test/Lint-Erfolg)
- Zentralem Settings-Center mit Provider-Registry
- Selbstständiger Environment-Provisioning
- Modularer, erweiterbarer Architektur
- Multi-Model-Support mit intelligentem Routing

---

## 📊 IST-ANALYSE

### Aktuelle Architektur

**Frontend (`/app/frontend`):**
- **Hauptdatei:** `App.js` (>3500 Zeilen!) - MONOLITH
- **Komponenten:** Inline in App.js definiert, keine Modularität
- **State Management:** Lokaler React State, keine globale State-Maschine
- **Routing:** Basic React Router
- **UI Library:** Radix UI + Tailwind CSS (gut)
- **API Client:** Axios mit einfachen Wrapper-Funktionen

**Backend (`/app/backend`):**
- **Hauptdatei:** `server.py` (>4000 Zeilen!) - MONOLITH
- **Framework:** FastAPI (gut)
- **Datenbank:** MongoDB mit Motor (async, gut)
- **Agenten-System:** Grundstruktur vorhanden (orchestrator, planner, coder, etc.)
- **System-Prompt:** Riesiger String mit allen Regeln (>1000 Zeilen)
- **Tool-System:** Hartcodierte if/elif-Kette für Tool-Ausführung
- **LLM-Integration:** Nur OpenAI, fest verdrahtet

**Datenbank:**
- MongoDB Collections:
  - `projects` - Projektdaten
  - `messages` - Chat-History
  - `agent_status` - Agent-Zustände
  - `roadmap` - Roadmap-Items
  - `logs` - System-Logs
  - `settings` - Konfiguration
  - `update` - Update-Status

### Kritische Architekturprobleme

#### 1. **MONOLITH-PROBLEM**
- `App.js`: 3500+ Zeilen, alle Komponenten inline
- `server.py`: 4000+ Zeilen, alle Logik in einer Datei
- **Folge:** Unmöglich zu testen, schwer zu warten, keine Modularität

#### 2. **KEINE ZUSTANDSMASCHINE**
- Projekt-Status: nur einfaches String-Feld
- Task-Status: keine strukturierte Verfolgung
- Phasenübergänge: nicht definiert oder erzwungen
- **Folge:** Keine Garantien über Systemzustand

#### 3. **KEINE COMPLETION-GATES**
- `mark_complete` Tool existiert, aber ohne Validierung
- Keine Build/Test/Lint-Prüfung vor "fertig"
- Agenten können beliebig Status setzen
- **Folge:** Falsche "fertig"-Meldungen, ungetesteter Code

#### 4. **KEIN SETTINGS-CENTER**
- Settings verstreut in DB und ENV-Variablen
- Keine UI für zentrale Konfiguration
- Keine Provider-Registry
- Keine Deep-Links zu Key-Erstellungsseiten
- **Folge:** Benutzer muss manuell suchen, keine Selbstbedienung

#### 5. **MONO-MODEL-ARCHITEKTUR**
- Nur OpenAI fest verdrahtet
- Kein Model-Routing
- Keine Fallback-Strategien
- Kein Kosten-/Qualitäts-Balancing
- **Folge:** Inflexibel, teuer, Single Point of Failure

#### 6. **KEINE ENVIRONMENT-PROVISIONING**
- System erwartet vorkonfigurierte Umgebung
- Kann nicht selbst Node/Python/DB/Tools installieren
- Keine Projekt-Template-Engine
- **Folge:** Benutzer muss manuell viel vorbereiten

#### 7. **SCHWACHE EVIDENCE-LAYER**
- Tests werden nicht systematisch erzwungen
- Keine strukturierten Test-Reports
- Keine Screenshot/Browser-Proof-Mechanismen
- **Folge:** Keine Beweise für Funktionalität

#### 8. **TOOL-SYSTEM LIMITIERT**
- Hartcodierte if/elif-Kette
- Keine Tool-Registry
- Keine Tool-Berechtigungen pro Agent
- Keine strukturierten Tool-Results
- **Folge:** Schwer erweiterbar, unsicher

#### 9. **KEINE DELIVERY-PHASEN**
- Discovery/Design/Planning nicht strukturiert
- Kein Acceptance-Criteria-System
- Kein Handover-Prozess
- **Folge:** Ad-hoc-Entwicklung ohne Struktur

#### 10. **SICHERHEIT & ROBUSTHEIT**
- Shell-Kommandos ohne ausreichende Sandbox
- Secrets in Klartext in DB
- Keine Rollback-Mechanismen
- Keine Rate-Limiting
- **Folge:** Sicherheitsrisiken, Stabilitätsprobleme

---

## 🏗️ ZIELARCHITEKTUR

### Neue Modulstruktur

```
/app/
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Zentrale Konfiguration
│   │   ├── database.py            # DB-Abstraktion
│   │   ├── state_machine.py       # Zustandsmaschine
│   │   └── exceptions.py          # Custom Exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py             # Project Model
│   │   ├── task.py                # Task Model
│   │   ├── agent.py               # Agent Model
│   │   ├── evidence.py            # Evidence Model
│   │   ├── settings.py            # Settings Model
│   │   └── provider.py            # Provider Model
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Orchestration Service
│   │   ├── discovery.py           # Discovery Phase
│   │   ├── design.py              # Solution Design
│   │   ├── planning.py            # Delivery Planning
│   │   ├── provisioning.py        # Environment Provisioning
│   │   ├── implementation.py      # Code Implementation
│   │   ├── verification.py        # Testing & QA
│   │   ├── debugging.py           # Debug Loop
│   │   └── handover.py            # Handover & Documentation
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # Base Agent Class
│   │   ├── orchestrator.py
│   │   ├── research.py
│   │   ├── architect.py
│   │   ├── builder.py
│   │   ├── reviewer.py
│   │   ├── tester.py
│   │   ├── debugger.py
│   │   └── release.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py            # Tool Registry
│   │   ├── executor.py            # Safe Tool Execution
│   │   ├── file_ops.py
│   │   ├── search.py
│   │   ├── shell.py
│   │   ├── build.py
│   │   ├── test.py
│   │   ├── lint.py
│   │   ├── git.py
│   │   └── browser.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider_registry.py   # Provider Registry
│   │   ├── router.py              # Model Routing
│   │   ├── providers/
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   ├── google.py
│   │   │   └── ollama.py
│   │   └── cost_tracker.py        # Cost Tracking
│   ├── gates/
│   │   ├── __init__.py
│   │   ├── completion_gate.py     # Hard Completion Gates
│   │   ├── quality_gate.py        # Quality Checks
│   │   └── security_gate.py       # Security Checks
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── collector.py           # Evidence Collection
│   │   ├── storage.py             # Evidence Storage
│   │   └── reporter.py            # Evidence Reporting
│   ├── provisioning/
│   │   ├── __init__.py
│   │   ├── detector.py            # Tech Stack Detection
│   │   ├── installer.py           # Package Installation
│   │   ├── templates/             # Project Templates
│   │   │   ├── web_app.py
│   │   │   ├── browser_game.py
│   │   │   ├── api.py
│   │   │   └── dashboard.py
│   │   └── environment.py         # Environment Setup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py
│   │   │   ├── agents.py
│   │   │   ├── tasks.py
│   │   │   ├── settings.py
│   │   │   ├── providers.py
│   │   │   └── evidence.py
│   │   └── dependencies.py
│   ├── server.py                  # FastAPI Entry Point
│   ├── requirements.txt
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Footer.jsx
│   │   │   ├── project/
│   │   │   │   ├── ProjectCard.jsx
│   │   │   │   ├── ProjectList.jsx
│   │   │   │   └── ProjectWorkspace.jsx
│   │   │   ├── agent/
│   │   │   │   ├── AgentStatus.jsx
│   │   │   │   ├── AgentActivity.jsx
│   │   │   │   └── AgentTimeline.jsx
│   │   │   ├── settings/
│   │   │   │   ├── SettingsCenter.jsx
│   │   │   │   ├── ProviderCard.jsx
│   │   │   │   ├── ModelConfig.jsx
│   │   │   │   └── EnvironmentConfig.jsx
│   │   │   ├── evidence/
│   │   │   │   ├── EvidenceViewer.jsx
│   │   │   │   ├── TestReport.jsx
│   │   │   │   └── BuildLog.jsx
│   │   │   ├── delivery/
│   │   │   │   ├── PhaseIndicator.jsx
│   │   │   │   ├── TaskBoard.jsx
│   │   │   │   └── HandoverSummary.jsx
│   │   │   └── ui/               # Shared UI Components (Radix)
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Workspace.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── Evidence.jsx
│   │   ├── hooks/
│   │   │   ├── useProject.js
│   │   │   ├── useAgent.js
│   │   │   └── useSettings.js
│   │   ├── services/
│   │   │   └── api.js            # API Client
│   │   ├── store/
│   │   │   └── index.js          # State Management (Zustand?)
│   │   ├── utils/
│   │   └── App.jsx               # Clean Entry Point
│   ├── package.json
│   └── vite.config.js
│
├── shared/
│   └── schemas/                  # Shared Type Definitions
│       ├── project.schema.json
│       ├── task.schema.json
│       └── evidence.schema.json
│
└── docs/
    ├── architecture.md
    ├── api.md
    ├── agents.md
    ├── tools.md
    ├── providers.md
    └── deployment.md
```

### Kern-Systeme

#### 1. **ZUSTANDSMASCHINE**

**Projekt-Zustände:**
```python
class ProjectStatus(str, Enum):
    DISCOVERY = "discovery"                    # Anforderungen sammeln
    AWAITING_USER = "awaiting_user"            # Auf Benutzer-Input warten
    SOLUTION_DESIGN = "solution_design"        # Architektur entwerfen
    PLANNING = "planning"                      # Tasks planen
    PROVISIONING = "provisioning"              # Umgebung aufbauen
    IMPLEMENTING = "implementing"              # Code schreiben
    REVIEWING = "reviewing"                    # Code-Review
    TESTING = "testing"                        # Tests ausführen
    DEBUGGING = "debugging"                    # Fehler beheben
    READY_FOR_HANDOVER = "ready_for_handover"  # Bereit zur Übergabe
    COMPLETED = "completed"                    # Abgeschlossen
    FAILED = "failed"                          # Fehlgeschlagen
    PAUSED = "paused"                          # Pausiert
```

**Task-Zustände:**
```python
class TaskStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    UNDER_TEST = "under_test"
    FAILED = "failed"
    PASSED = "passed"
    DONE = "done"
```

**Erlaubte Übergänge:** Definiert in `state_machine.py`

#### 2. **COMPLETION GATES**

**Hard Gates System:**
```python
class CompletionGate:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.checks = []
    
    async def can_complete(self) -> tuple[bool, list[str]]:
        """
        Prüft ob Task als fertig markiert werden darf.
        Returns: (can_complete, failed_checks)
        """
        failed = []
        
        # Gate 1: Build erfolgreich
        if not await self.check_build():
            failed.append("Build failed")
        
        # Gate 2: Lint erfolgreich
        if not await self.check_lint():
            failed.append("Lint failed")
        
        # Gate 3: Tests erfolgreich
        if not await self.check_tests():
            failed.append("Tests failed")
        
        # Gate 4: Akzeptanzkriterien erfüllt
        if not await self.check_acceptance_criteria():
            failed.append("Acceptance criteria not met")
        
        # Gate 5: Evidence vorhanden
        if not await self.check_evidence():
            failed.append("Evidence missing")
        
        return (len(failed) == 0, failed)
```

**Tool-Blockierung:**
```python
@tool("mark_complete")
async def mark_complete(task_id: str) -> dict:
    """Task kann NUR mit Gates-Freigabe completed werden"""
    gate = CompletionGate(task_id)
    can_complete, failed = await gate.can_complete()
    
    if not can_complete:
        raise GateViolationError(
            f"Cannot complete task. Failed checks: {', '.join(failed)}"
        )
    
    # Erst jetzt Status ändern
    await update_task_status(task_id, TaskStatus.DONE)
    return {"success": True, "evidence_saved": True}
```

#### 3. **SETTINGS-CENTER & PROVIDER-REGISTRY**

**Provider-Registry:**
```python
class ProviderMetadata:
    id: str
    name: str
    description: str
    category: str  # llm, database, storage, auth, payment, etc.
    
    # URLs
    homepage_url: str
    docs_url: str
    create_key_url: str         # Exakter Link zur Key-Erstellung
    manage_keys_url: str        # Link zur Key-Verwaltung
    status_page_url: str
    
    # Configuration
    required_fields: list[FieldDefinition]
    optional_fields: list[FieldDefinition]
    env_var_names: dict[str, str]
    validation_rules: dict[str, ValidationRule]
    
    # Capabilities
    capabilities: list[str]
    models: list[ModelDefinition]  # für LLM-Provider
    
    # Integration
    test_connection_handler: Callable
    cost_calculator: Optional[Callable]


# Beispiel: OpenAI Provider
OPENAI_PROVIDER = ProviderMetadata(
    id="openai",
    name="OpenAI",
    description="OpenAI GPT Models for text generation, code generation, and more",
    category="llm",
    homepage_url="https://openai.com",
    docs_url="https://platform.openai.com/docs",
    create_key_url="https://platform.openai.com/api-keys",
    manage_keys_url="https://platform.openai.com/api-keys",
    status_page_url="https://status.openai.com",
    required_fields=[
        FieldDefinition(
            name="api_key",
            label="API Key",
            type="secret",
            description="Your OpenAI API key",
            placeholder="sk-...",
            validation=ValidationRule(
                pattern=r"^sk-[A-Za-z0-9]{48}$",
                message="Must start with 'sk-' followed by 48 characters"
            )
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="organization_id",
            label="Organization ID",
            type="text",
            description="Optional organization ID",
            placeholder="org-..."
        )
    ],
    env_var_names={
        "api_key": "OPENAI_API_KEY",
        "organization_id": "OPENAI_ORG_ID"
    },
    capabilities=["text_generation", "code_generation", "embeddings", "chat"],
    models=[
        ModelDefinition(id="gpt-4o", name="GPT-4o", ...),
        ModelDefinition(id="gpt-4o-mini", name="GPT-4o Mini", ...),
    ],
    test_connection_handler=test_openai_connection
)
```

**Settings-UI:**
- Jede Provider-Karte zeigt:
  - Name + Logo
  - Status (configured / not configured / error)
  - Benötigte Felder mit Validierung
  - "Test Connection"-Button
  - **"Get API Key ↗"** - Link direkt zu `create_key_url`
  - **"Manage Keys ↗"** - Link direkt zu `manage_keys_url`
  - **"Documentation ↗"** - Link zur offiziellen Doku
  - Live-Statusanzeige

#### 4. **MODEL-ROUTING**

**Routing-Strategie:**
```python
class ModelRouter:
    def __init__(self, config: RoutingConfig):
        self.config = config
    
    async def route_request(
        self,
        task_type: TaskType,
        context_size: int,
        priority: Priority,
        budget_constraint: Optional[float]
    ) -> ModelSelection:
        """
        Intelligentes Model-Routing basierend auf:
        - Task-Typ (orchestration, coding, review, etc.)
        - Context-Größe
        - Priorität
        - Budget
        """
        
        # Beispiel-Logik:
        if task_type == TaskType.ORCHESTRATION:
            return self.select_reasoning_model()
        
        elif task_type == TaskType.CODE_GENERATION:
            if context_size > 100_000:
                return self.select_long_context_model()
            elif priority == Priority.HIGH:
                return self.select_best_coding_model()
            else:
                return self.select_cost_effective_model()
        
        elif task_type == TaskType.SIMPLE_COMPLETION:
            return self.select_fast_cheap_model()
        
        # Fallback-Kette
        return self.select_with_fallback()
```

**Konfiguration:**
```yaml
model_routing:
  orchestrator:
    primary: "gpt-4o"
    fallback: ["claude-sonnet-4", "gpt-4o-mini"]
  
  research:
    primary: "claude-sonnet-4"
    fallback: ["gpt-4o"]
  
  coding:
    primary: "gpt-4o"
    fallback: ["claude-sonnet-4"]
  
  review:
    primary: "gpt-4o-mini"
  
  test_summary:
    primary: "gpt-4o-mini"
```

#### 5. **ENVIRONMENT-PROVISIONING**

**Auto-Detection & Setup:**
```python
class EnvironmentProvisioner:
    async def provision_for_project(self, project: Project, requirements: str):
        """
        Analysiert Anforderungen und baut automatisch passende Umgebung
        """
        
        # 1. Tech Stack Detection
        stack = await self.detect_stack(requirements)
        # → "browser-game" → Frontend: Vite+React, No Backend
        
        # 2. Template Selection
        template = await self.select_template(stack)
        
        # 3. Project Scaffold
        await self.create_project_structure(project.workspace_path, template)
        
        # 4. Dependencies Installation
        await self.install_dependencies(project.workspace_path, stack)
        
        # 5. Configuration Files
        await self.create_config_files(project.workspace_path, stack)
        
        # 6. Development Server Setup
        await self.setup_dev_server(project.workspace_path, stack)
        
        # 7. Test Environment
        await self.setup_test_environment(project.workspace_path, stack)
        
        # 8. Build System
        await self.setup_build_system(project.workspace_path, stack)
        
        return ProvisioningResult(
            workspace_path=project.workspace_path,
            stack=stack,
            dev_server_url=f"http://localhost:{port}",
            test_command="npm test",
            build_command="npm run build"
        )
```

**Template-System:**
```python
class BrowserGameTemplate(ProjectTemplate):
    name = "browser-game"
    description = "Modern browser-based game"
    
    stack = {
        "frontend": "vite + react",
        "language": "typescript",
        "styling": "tailwindcss",
        "build": "vite",
        "test": "vitest",
        "e2e": "playwright"
    }
    
    def scaffold(self, workspace: Path) -> list[File]:
        return [
            File("package.json", self.package_json_template()),
            File("vite.config.ts", self.vite_config()),
            File("tsconfig.json", self.ts_config()),
            File("tailwind.config.js", self.tailwind_config()),
            File("src/main.tsx", self.main_tsx()),
            File("src/Game.tsx", self.game_component()),
            File("src/game/engine.ts", self.game_engine()),
            File("tests/setup.ts", self.test_setup()),
        ]
```

#### 6. **EVIDENCE-BASED SYSTEM**

**Evidence Collector:**
```python
class EvidenceCollector:
    async def collect_for_task(self, task: Task) -> Evidence:
        evidence = Evidence(task_id=task.id)
        
        # Build Evidence
        build_result = await run_build(task.project_id)
        evidence.add_artifact(
            type="build_log",
            content=build_result.log,
            status=build_result.success
        )
        
        # Test Evidence
        test_result = await run_tests(task.project_id)
        evidence.add_artifact(
            type="test_report",
            content=test_result.report,
            status=test_result.all_passed,
            metadata={
                "total": test_result.total,
                "passed": test_result.passed,
                "failed": test_result.failed
            }
        )
        
        # Lint Evidence
        lint_result = await run_lint(task.project_id)
        evidence.add_artifact(
            type="lint_report",
            content=lint_result.output,
            status=lint_result.success
        )
        
        # Browser Evidence (für UI-Tasks)
        if task.type == TaskType.UI:
            screenshots = await capture_screenshots(task.project_id)
            for screenshot in screenshots:
                evidence.add_artifact(
                    type="screenshot",
                    content=screenshot.data,
                    metadata={
                        "url": screenshot.url,
                        "viewport": screenshot.viewport
                    }
                )
        
        # Code Diff
        diff = await get_git_diff(task.project_id)
        evidence.add_artifact(
            type="code_diff",
            content=diff,
            metadata={
                "files_changed": count_changed_files(diff),
                "lines_added": count_additions(diff),
                "lines_removed": count_deletions(diff)
            }
        )
        
        return evidence
```

**Evidence Storage:**
- MongoDB Collection: `evidence`
- S3/Local File Storage für Screenshots/Logs
- Strukturierte Metadaten für Queryability

#### 7. **DELIVERY-PHASEN**

**Phase 1: Discovery**
```python
class DiscoveryPhase:
    async def execute(self, user_request: str) -> DiscoveryResult:
        # 1. Anforderungsanalyse
        analysis = await analyze_requirements(user_request)
        
        # 2. Scope-Extraktion
        scope = extract_scope(analysis)
        
        # 3. Kritische Fragen identifizieren
        questions = identify_critical_questions(scope)
        
        # 4. Wenn Fragen vorhanden → User fragen
        if questions:
            return DiscoveryResult(
                status="awaiting_user",
                questions=questions,
                partial_scope=scope
            )
        
        # 5. Annahmen dokumentieren
        assumptions = document_assumptions(scope)
        
        # 6. Discovery-Brief erstellen
        brief = create_discovery_brief(scope, assumptions)
        
        return DiscoveryResult(
            status="complete",
            scope=scope,
            assumptions=assumptions,
            brief=brief
        )
```

**Phase 2: Solution Design**
```python
class SolutionDesignPhase:
    async def execute(self, scope: Scope) -> SolutionDesign:
        # 1. Technische Optionen recherchieren
        options = await research_technical_options(scope)
        
        # 2. Bewertungskriterien anwenden
        evaluated = await evaluate_options(options, criteria=[
            "reliability",
            "maintainability",
            "development_effort",
            "performance",
            "security",
            "cost"
        ])
        
        # 3. Beste Option auswählen
        selected = select_best_option(evaluated)
        
        # 4. Architektur-Dokument erstellen
        architecture = create_architecture_doc(selected)
        
        # 5. Risiken identifizieren
        risks = identify_risks(selected)
        
        return SolutionDesign(
            selected_option=selected,
            architecture=architecture,
            risks=risks,
            decision_log=create_decision_log(evaluated, selected)
        )
```

**Phase 3-8:** Ähnlich strukturiert

---

## 🚀 MIGRATIONSPLAN

### Etappen-Übersicht

**Etappe 1: Foundation (Woche 1-2)**
- Projekt-Struktur Refactoring
- Core-Module anlegen
- Datenbank-Modelle refactoren
- Dependency Injection Setup
- Basis-Tests

**Etappe 2: State Machine (Woche 2-3)**
- Zustandsmaschine implementieren
- Status-Übergänge definieren
- State-Validierung
- Migration bestehender Projekte

**Etappe 3: Settings-Center (Woche 3-4)**
- Provider-Registry Backend
- Settings-API
- Settings-UI mit Provider-Cards
- Deep-Links Integration
- Migration bestehender Settings

**Etappe 4: Completion-Gates (Woche 4-5)**
- Gate-System implementieren
- Tool-Blockierungen
- Evidence-Collector
- Evidence-Storage
- Gate-Tests

**Etappe 5: Model-Routing (Woche 5-6)**
- Provider-Abstraktion
- Multi-Provider-Support
- Routing-Engine
- Fallback-Mechanismen
- Cost-Tracking

**Etappe 6: Environment-Provisioning (Woche 6-8)**
- Template-System
- Auto-Detection
- Installer-Framework
- Dev-Server-Management
- Test-Environment-Setup

**Etappe 7: Delivery-Engine (Woche 8-10)**
- Phasen-Implementierung
- Task-Management
- Agent-Orchestrierung
- Workflow-Engine

**Etappe 8: Frontend-Modernisierung (Woche 10-12)**
- Component-Extraktion
- State-Management
- Settings-UI
- Evidence-Viewer
- Phase-Indicators

**Etappe 9: QA & Hardening (Woche 12-14)**
- Umfassende Tests
- Security-Audit
- Performance-Optimierung
- Dokumentation

**Etappe 10: Migration & Rollout (Woche 14-15)**
- Daten-Migration
- Backward-Compatibility
- Deployment
- Monitoring

---

## 🎯 ERFOLGSKRITERIEN

Das System gilt als erfolgreich umgebaut, wenn:

1. **Autonomie-Test:**
   - Benutzer sagt: "Baue ein Super Mario Jump-and-Run im Browser"
   - System liefert spielbares Spiel ohne manuelle Eingriffe

2. **Quality-Gate-Test:**
   - System kann keinen Task als "fertig" markieren ohne:
     - ✅ Build erfolgreich
     - ✅ Tests erfolgreich
     - ✅ Lint erfolgreich
     - ✅ Evidence vorhanden

3. **Settings-Test:**
   - Für jeden Provider gibt es:
     - ✅ Sofortigen Link zur Key-Erstellung
     - ✅ Validierung
     - ✅ Test-Connection
     - ✅ Status-Anzeige

4. **Evidence-Test:**
   - Jeder abgeschlossene Task hat:
     - ✅ Build-Log
     - ✅ Test-Report
     - ✅ Code-Diff
     - ✅ Screenshots (bei UI)

5. **Modularitäts-Test:**
   - ✅ Keine Datei >500 Zeilen
   - ✅ Klare Modultrenn
ung
   - ✅ Testbare Services
   - ✅ Dependency Injection

---

## ⚠️ RISIKEN & MITIGATION

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Breaking Changes für bestehende Projekte | Hoch | Hoch | Migrations-Scripts + Backward-Compatibility-Layer |
| Performance-Verschlechterung | Mittel | Mittel | Performance-Tests pro Etappe |
| Scope-Creep | Hoch | Hoch | Strikte Etappen-Grenzen, MVP-first |
| Benutzer-Disruption | Mittel | Hoch | Feature-Flags, schrittweises Rollout |
| Test-Overhead | Mittel | Niedrig | Test-Automation, CI/CD |

---

## 📝 NÄCHSTE SCHRITTE

1. **Review & Approval:**
   - Diesen Plan mit Stakeholder reviewen
   - Priorisierung bestätigen
   - Go/No-Go Decision

2. **Etappe 1 Start:**
   - Foundation-Refactoring
   - Erste Module extrahieren
   - Test-Setup

3. **Iteratives Vorgehen:**
   - 2-Wochen-Sprints
   - Nach jeder Etappe: Review + Demo
   - Continuous Integration

---

**Autor:** E1 Agent  
**Version:** 1.0  
**Letzte Aktualisierung:** 2026-04-02
