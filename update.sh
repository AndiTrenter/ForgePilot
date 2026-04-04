#!/bin/bash
# ForgePilot Update Script for Unraid & Dev
# Wird vom Update-Button in der UI ausgeführt

echo "🚀 ForgePilot Update gestartet..."
echo ""

# Erkenne Umgebung (Unraid oder Dev)
if [ -d "/mnt/user/appdata/forgepilot" ]; then
    TARGET_DIR="/mnt/user/appdata/forgepilot"
    USE_DOCKER=true
    echo "📍 Umgebung: Unraid Docker"
elif [ -d "/app" ] && [ -f "/app/backend/server.py" ]; then
    TARGET_DIR="/app"
    USE_DOCKER=false
    echo "📍 Umgebung: Development"
else
    echo "❌ Fehler: ForgePilot Verzeichnis nicht gefunden!"
    exit 1
fi

# Gehe zum ForgePilot Verzeichnis
cd "$TARGET_DIR" || {
    echo "❌ Fehler: Verzeichnis nicht erreichbar!"
    exit 1
}

echo "📍 Aktuelles Verzeichnis: $(pwd)"
echo ""

# Git Status prüfen
echo "🔍 Prüfe Git Status..."
git status
echo ""

# Hole neueste Version
echo "📥 Hole Updates von GitHub..."
git fetch origin
echo ""

# Zeige verfügbare Updates
echo "📊 Verfügbare Updates:"
git log HEAD..origin/main --oneline
echo ""

# Bestätige Update
echo "⬇️ Pulling Updates..."
git pull origin main || {
    echo "❌ Git pull fehlgeschlagen!"
    exit 1
}

echo ""
echo "✅ Code erfolgreich aktualisiert!"
echo ""

# Container neu starten (nur bei Docker)
if [ "$USE_DOCKER" = true ]; then
    echo "🔄 Starte Docker Container neu..."
    docker-compose restart backend frontend
    echo ""
    
    echo "⏳ Warte auf Container-Start..."
    sleep 5
    echo ""
    
    # Prüfe Container Status
    echo "📊 Container Status:"
    docker-compose ps
    echo ""
else
    echo "🔄 Starte Services neu (Supervisor)..."
    sudo supervisorctl restart backend frontend
    echo ""
    sleep 3
    echo "📊 Service Status:"
    sudo supervisorctl status backend frontend
    echo ""
fi

echo "✅ Update abgeschlossen!"
echo ""
echo "🎉 ForgePilot wurde erfolgreich aktualisiert!"
echo ""
echo "💡 Hard Refresh im Browser empfohlen: Strg + Shift + R"
