"""
Server Migration Script
Migriert schrittweise von server.py zu modularer Architektur
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import alter Server für Backward-Compatibility
try:
    from server import app as legacy_app, api_router as legacy_router
    LEGACY_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Legacy server not available: {e}")
    LEGACY_AVAILABLE = False

# Import neuer modularer Server
from server_v3 import app, config

# Wenn Legacy verfügbar: Routes registrieren
if LEGACY_AVAILABLE:
    print("✅ Mounting legacy routes for backward compatibility")
    app.mount("/api", legacy_app)
else:
    print("⚠️  Running in new-only mode")

if __name__ == "__main__":
    import uvicorn
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ForgePilot v{config.version} - Agentic Delivery OS          ║
║  Running in HYBRID mode (new + legacy)                      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "server_migrated:app",
        host=config.host,
        port=config.port,
        reload=config.reload
    )
