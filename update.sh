#!/bin/bash

# ForgePilot Update Script
# Dieses Script aktualisiert ForgePilot automatisch auf die neueste Version
# 
# Verwendung:
#   ./update.sh           - Normal update
#   ./update.sh --force   - Force update (ignoriert Fehler)
#   ./update.sh --check   - Nur prüfen ob Update verfügbar

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script-Verzeichnis ermitteln
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Compose-Datei ermitteln
if [ -f "docker-compose.unraid.yml" ]; then
    COMPOSE_FILE="docker-compose.unraid.yml"
elif [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
else
    echo -e "${RED}Fehler: Keine docker-compose Datei gefunden!${NC}"
    exit 1
fi

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ForgePilot Update Script           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# Aktuelle Version ermitteln
CURRENT_VERSION="unknown"
if docker exec forgepilot-backend curl -s http://localhost:8001/api/version 2>/dev/null | grep -q "version"; then
    CURRENT_VERSION=$(docker exec forgepilot-backend curl -s http://localhost:8001/api/version 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
fi
echo -e "Aktuelle Version: ${YELLOW}${CURRENT_VERSION}${NC}"

# Neueste Version von GitHub prüfen
echo -e "Prüfe auf Updates..."
LATEST_VERSION=$(curl -s https://raw.githubusercontent.com/AndiTrenter/ForgePilot/main/VERSION 2>/dev/null || echo "unknown")
echo -e "Neueste Version:  ${GREEN}${LATEST_VERSION}${NC}"
echo ""

# Nur Check-Modus?
if [ "$1" == "--check" ]; then
    if [ "$CURRENT_VERSION" == "$LATEST_VERSION" ]; then
        echo -e "${GREEN}✓ ForgePilot ist auf dem neuesten Stand!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Update verfügbar: ${CURRENT_VERSION} → ${LATEST_VERSION}${NC}"
        exit 0
    fi
fi

# Prüfen ob Update nötig
if [ "$CURRENT_VERSION" == "$LATEST_VERSION" ] && [ "$1" != "--force" ]; then
    echo -e "${GREEN}✓ ForgePilot ist bereits auf dem neuesten Stand!${NC}"
    echo -e "  Nutze ${YELLOW}./update.sh --force${NC} um trotzdem zu aktualisieren."
    exit 0
fi

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "Starte Update auf Version ${GREEN}${LATEST_VERSION}${NC}..."
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Schritt 1: Neue Images pullen
echo -e "${BLUE}[1/4]${NC} Lade neue Images herunter..."
docker-compose -f "$COMPOSE_FILE" pull
echo -e "${GREEN}✓ Images heruntergeladen${NC}"
echo ""

# Schritt 2: Alte Container stoppen
echo -e "${BLUE}[2/4]${NC} Stoppe alte Container..."
docker-compose -f "$COMPOSE_FILE" stop
echo -e "${GREEN}✓ Container gestoppt${NC}"
echo ""

# Schritt 3: Alte Container entfernen (aber Volumes behalten!)
echo -e "${BLUE}[3/4]${NC} Entferne alte Container..."
docker-compose -f "$COMPOSE_FILE" rm -f
echo -e "${GREEN}✓ Alte Container entfernt${NC}"
echo ""

# Schritt 4: Neue Container starten
echo -e "${BLUE}[4/4]${NC} Starte neue Container..."
docker-compose -f "$COMPOSE_FILE" up -d
echo -e "${GREEN}✓ Neue Container gestartet${NC}"
echo ""

# Warten bis Backend bereit ist
echo -e "Warte auf Backend..."
for i in {1..30}; do
    if docker exec forgepilot-backend curl -s http://localhost:8001/api/health 2>/dev/null | grep -q "healthy"; then
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Neue Version prüfen
NEW_VERSION=$(docker exec forgepilot-backend curl -s http://localhost:8001/api/version 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
if [ "$NEW_VERSION" == "$LATEST_VERSION" ]; then
    echo -e "${GREEN}✓ Update erfolgreich!${NC}"
    echo -e "  Neue Version: ${GREEN}${NEW_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠ Update abgeschlossen, aber Version konnte nicht verifiziert werden${NC}"
    echo -e "  Erwartete Version: ${LATEST_VERSION}"
    echo -e "  Aktuelle Version: ${NEW_VERSION}"
fi
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Alte Images aufräumen (optional)
echo -e "Räume alte Images auf..."
docker image prune -f 2>/dev/null || true
echo ""

echo -e "${GREEN}ForgePilot ist jetzt unter http://localhost:3000 erreichbar${NC}"
