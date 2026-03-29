#!/bin/bash

# ForgePilot Updater Service
# Läuft als separater Prozess und wartet auf Update-Befehle
# Wird vom Backend über eine Datei getriggert

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TRIGGER_FILE="/app/workspaces/.update_trigger"
LOG_FILE="/app/workspaces/update.log"

# Compose-Datei ermitteln
if [ -f "$SCRIPT_DIR/docker-compose.unraid.yml" ]; then
    COMPOSE_FILE="$SCRIPT_DIR/docker-compose.unraid.yml"
else
    COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
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

log "Updater Service gestartet"
log "Warte auf Update-Trigger: $TRIGGER_FILE"

# Hauptschleife - wartet auf Trigger-Datei
while true; do
    if [ -f "$TRIGGER_FILE" ]; then
        log "Update-Trigger erkannt!"
        do_update
    fi
    sleep 5
done
