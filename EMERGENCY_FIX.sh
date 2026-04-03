#!/bin/bash
# EMERGENCY FIX SCRIPT FOR UNRAID v2
# Run this in Unraid Terminal to fix EVERYTHING

echo "🚨 ForgePilot Emergency Fix Script v2"
echo "====================================="
echo ""

# Navigate to directory
cd /mnt/user/appdata/forgepilot || {
    echo "❌ Directory not found!"
    exit 1
}

echo "📍 Current directory: $(pwd)"
echo ""

# Stop containers completely
echo "🛑 Stopping containers and removing networks..."
docker-compose down --remove-orphans --volumes
echo ""

# Pull latest code
echo "📥 Pulling latest code from GitHub..."
git fetch --all
git reset --hard origin/main
echo ""

# Verify scripts exist
echo "📝 Checking scripts..."
if [ -f "update.sh" ]; then
    chmod +x update.sh
    echo "✅ update.sh found and executable"
fi
if [ -f "EMERGENCY_FIX.sh" ]; then
    chmod +x EMERGENCY_FIX.sh
    echo "✅ EMERGENCY_FIX.sh found and executable"
fi
echo ""

# Clean Docker cache
echo "🧹 Cleaning Docker cache..."
docker system prune -f
echo ""

# Rebuild containers
echo "🔨 Rebuilding Docker containers (--no-cache)..."
docker-compose build --no-cache
echo ""

# Start containers
echo "🚀 Starting containers..."
docker-compose up -d
echo ""

# Wait for startup
echo "⏳ Waiting for containers to start..."
sleep 10
echo ""

# Check status
echo "📊 Container Status:"
docker-compose ps
echo ""

# Test backend API
echo "🧪 Testing Backend API..."
sleep 5
BACKEND_RUNNING=$(docker-compose ps | grep forgepilot-backend | grep "Up" || echo "")
if [ -n "$BACKEND_RUNNING" ]; then
    docker exec forgepilot-backend curl -s http://localhost:8001/api/v1/settings/providers | head -20 || echo "⚠️ API not ready yet"
else
    echo "⚠️ Backend container not running yet"
fi
echo ""

echo "✅ Emergency Fix Complete!"
echo ""
echo "🎯 NÄCHSTE SCHRITTE:"
echo "1. Browser öffnen: http://192.168.1.140:3000"
echo "2. Hard Refresh: Ctrl + Shift + R (oder Ctrl + F5)"
echo "3. Zu Settings navigieren - Sie sollten 4 Provider Cards sehen"
echo "4. Wenn immer noch leer: Entwicklertools öffnen (F12) → Console → Fehler prüfen"
echo ""
