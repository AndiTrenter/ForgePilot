#!/bin/bash
# EMERGENCY FIX SCRIPT FOR UNRAID
# Run this in Unraid Terminal to fix EVERYTHING

set -e  # Exit on error

echo "🚨 ForgePilot Emergency Fix Script"
echo "=================================="
echo ""

# Navigate to directory
cd /mnt/user/appdata/forgepilot || {
    echo "❌ Directory not found!"
    exit 1
}

echo "📍 Current directory: $(pwd)"
echo ""

# Stop containers
echo "🛑 Stopping containers..."
docker-compose down
echo ""

# Pull latest code
echo "📥 Pulling latest code from GitHub..."
git fetch --all
git reset --hard origin/main
echo ""

# Copy update script
echo "📝 Installing update.sh script..."
if [ -f "update.sh" ]; then
    cp update.sh /mnt/user/appdata/forgepilot/
    chmod +x /mnt/user/appdata/forgepilot/update.sh
    echo "✅ update.sh installed"
else
    echo "⚠️  update.sh not found in repo - will create manually"
fi
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

# Test API
echo "🧪 Testing API v1..."
docker exec forgepilot-backend curl -s http://localhost:8001/api/v1/settings/providers | head -20
echo ""

echo "✅ Emergency Fix Complete!"
echo ""
echo "🎯 NEXT STEPS:"
echo "1. Open browser: http://192.168.1.140:3000"
echo "2. Clear all browser data (Ctrl + Shift + Delete)"
echo "3. Reload page"
echo "4. Open Settings - should show 4 Provider Cards"
echo ""
