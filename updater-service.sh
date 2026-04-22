#!/bin/bash

# ForgePilot Updater & Delivery Service
# Läuft als separater Prozess und wartet auf Update- und Deploy-Befehle
# Wird vom Backend über Trigger-Dateien gesteuert

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TRIGGER_FILE="/app/workspaces/.update_trigger"
DEPLOY_TRIGGER="/app/workspaces/.deploy_trigger"
LOG_FILE="/app/workspaces/update.log"
DEPLOY_LOG="/app/workspaces/deploy.log"

# Compose-Datei ermitteln
if [ -f "$SCRIPT_DIR/docker-compose.unraid.yml" ]; then
    COMPOSE_FILE="$SCRIPT_DIR/docker-compose.unraid.yml"
else
    COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

dlog() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEPLOY_LOG"
}

do_update() {
    log "═══════════════════════════════════════════"
    log "Update gestartet..."
    log "═══════════════════════════════════════════"
    
    cd "$SCRIPT_DIR"
    
    # Neue Images pullen
    log "[1/4] Lade neue Images..."
    docker-compose -f "$COMPOSE_FILE" pull >> "$LOG_FILE" 2>&1
    
    # Container stoppen
    log "[2/4] Stoppe Container..."
    docker-compose -f "$COMPOSE_FILE" stop >> "$LOG_FILE" 2>&1
    
    # Alte Container entfernen
    log "[3/4] Entferne alte Container..."
    docker-compose -f "$COMPOSE_FILE" rm -f >> "$LOG_FILE" 2>&1
    
    # Neue Container starten
    log "[4/4] Starte neue Container..."
    docker-compose -f "$COMPOSE_FILE" up -d >> "$LOG_FILE" 2>&1
    
    log "Update abgeschlossen!"
    log "═══════════════════════════════════════════"
    
    # Trigger-Datei löschen
    rm -f "$TRIGGER_FILE"
    
    # Alte Images aufräumen
    docker image prune -f >> "$LOG_FILE" 2>&1
}

do_deploy() {
    dlog "═══════════════════════════════════════════"
    dlog "Production-Deploy nach User-Freigabe gestartet..."
    dlog "═══════════════════════════════════════════"

    # Payload lesen (project_id, job_id)
    PAYLOAD=$(cat "$DEPLOY_TRIGGER" 2>/dev/null || echo "{}")
    dlog "Payload: $PAYLOAD"

    PROJECT_ID=$(echo "$PAYLOAD" | grep -oE '"project_id"\s*:\s*"[^"]+"' | head -1 | sed -E 's/.*"project_id"\s*:\s*"([^"]+)".*/\1/')
    JOB_ID=$(echo "$PAYLOAD" | grep -oE '"job_id"\s*:\s*"[^"]+"' | head -1 | sed -E 's/.*"job_id"\s*:\s*"([^"]+)".*/\1/')
    PROJECT_DIR="/app/workspaces/$PROJECT_ID"

    if [ -z "$PROJECT_ID" ]; then
        dlog "❌ Kein project_id in Payload gefunden - breche ab."
        rm -f "$DEPLOY_TRIGGER"
        return
    fi

    dlog "Project ID: $PROJECT_ID  /  Job ID: $JOB_ID"
    dlog "Workspace:  $PROJECT_DIR"

    if [ ! -d "$PROJECT_DIR" ]; then
        dlog "❌ Projekt-Verzeichnis existiert nicht: $PROJECT_DIR"
        rm -f "$DEPLOY_TRIGGER"
        return
    fi

    cd "$PROJECT_DIR"

    # 1) Abhängigkeiten installieren, falls package.json / requirements.txt existiert
    if [ -f "package.json" ]; then
        dlog "[deps] package.json gefunden - npm ci …"
        if command -v npm >/dev/null 2>&1; then
            npm ci --no-audit --no-fund >> "$DEPLOY_LOG" 2>&1 \
              || npm install --no-audit --no-fund >> "$DEPLOY_LOG" 2>&1
        else
            dlog "⚠️ npm nicht verfügbar im Updater-Container."
        fi
    fi
    if [ -f "requirements.txt" ]; then
        dlog "[deps] requirements.txt gefunden - pip install …"
        if command -v pip3 >/dev/null 2>&1; then
            pip3 install -r requirements.txt >> "$DEPLOY_LOG" 2>&1 || \
              dlog "⚠️ pip install fehlgeschlagen."
        fi
    fi

    # 2) Wenn Projekt eigene docker-compose mitbringt -> ausrollen
    if [ -f "docker-compose.yml" ] || [ -f "docker-compose.prod.yml" ]; then
        PROJECT_COMPOSE="docker-compose.prod.yml"
        [ ! -f "$PROJECT_COMPOSE" ] && PROJECT_COMPOSE="docker-compose.yml"
        dlog "[deploy] docker-compose up -d via $PROJECT_COMPOSE"
        docker-compose -f "$PROJECT_COMPOSE" pull >> "$DEPLOY_LOG" 2>&1 || true
        docker-compose -f "$PROJECT_COMPOSE" up -d --build >> "$DEPLOY_LOG" 2>&1
        RC=$?
        if [ $RC -eq 0 ]; then
            dlog "✅ Deploy erfolgreich."
        else
            dlog "❌ Deploy fehlgeschlagen (exit=$RC)."
        fi
    elif [ -f "setup.sh" ]; then
        dlog "[deploy] Kein docker-compose - führe setup.sh aus"
        bash setup.sh >> "$DEPLOY_LOG" 2>&1
    else
        dlog "[deploy] Weder docker-compose noch setup.sh gefunden - nichts zu tun."
    fi

    dlog "═══════════════════════════════════════════"
    dlog "Deploy abgeschlossen (Job $JOB_ID)."
    dlog "═══════════════════════════════════════════"

    # Trigger-File konsumieren
    rm -f "$DEPLOY_TRIGGER"

    # Ergebnis markieren, damit Backend den Stage finalisieren kann
    echo "{\"job_id\":\"$JOB_ID\",\"project_id\":\"$PROJECT_ID\",\"finished_at\":\"$(date -Iseconds)\"}" \
        > "/app/workspaces/.deploy_result"
}

log "Updater Service gestartet"
log "Warte auf Update-Trigger: $TRIGGER_FILE"
log "Warte auf Deploy-Trigger: $DEPLOY_TRIGGER"

# Hauptschleife - wartet auf Trigger-Dateien
while true; do
    if [ -f "$TRIGGER_FILE" ]; then
        log "Update-Trigger erkannt!"
        do_update
    fi
    if [ -f "$DEPLOY_TRIGGER" ]; then
        dlog "Deploy-Trigger erkannt!"
        do_deploy
    fi
    sleep 5
done
