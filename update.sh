#!/bin/bash
# ForgePilot Update Script for Unraid
# Wird vom Update-Button in der UI ausgeführt

echo "🚀 ForgePilot Update gestartet..."
echo ""

# Gehe zum ForgePilot Verzeichnis
cd /mnt/user/appdata/forgepilot || {
    echo "❌ Fehler: Verzeichnis nicht gefunden!"
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

# Container neu starten
echo "🔄 Starte Container neu..."
docker-compose restart backend frontend
echo ""

echo "⏳ Warte auf Container-Start..."
sleep 5
echo ""

# Prüfe Container Status
echo "📊 Container Status:"
docker-compose ps
echo ""

echo "✅ Update abgeschlossen!"
echo ""
echo "🎉 ForgePilot wurde erfolgreich aktualisiert!"
echo ""
echo "💡 Hard Refresh im Browser empfohlen: Strg + Shift + R"
