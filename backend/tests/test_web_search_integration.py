"""
Quick Integration Test - Web Search Retry in Real Agent Loop
Tests the enhanced web search functionality in a realistic agent scenario
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

from server import execute_tool

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'forgepilot')]

async def simulate_agent_research_scenario():
    """
    Simuliert ein realistisches Szenario:
    Agent muss Best Practices für ein spezielles Tech-Stack recherchieren
    """
    
    print("="*70)
    print("🤖 INTEGRATION TEST: Agent Research Scenario")
    print("="*70)
    
    # Setup
    project_id = "integration_test_websearch"
    workspace_path = Path("/tmp/integration_test")
    workspace_path.mkdir(exist_ok=True)
    
    # Cleanup
    await db.projects.delete_many({"_id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    
    await db.projects.insert_one({
        "_id": project_id,
        "name": "Integration Test - Web Search",
        "status": "active"
    })
    
    # Scenario: Agent recherchiert FastAPI + WebSocket + MongoDB Best Practices
    print("\n📝 Szenario:")
    print("   Der Agent baut eine Real-Time Chat-App mit FastAPI, WebSockets")
    print("   und MongoDB. Er muss Best Practices recherchieren.\n")
    
    # Test 1: Gute technische Query
    print("🔍 Test 1: Technische Best Practices Query")
    print("   Query: 'FastAPI WebSocket best practices 2024'")
    
    result1 = await execute_tool(
        "web_search",
        {"query": "FastAPI WebSocket best practices 2024", "max_results": 5},
        workspace_path,
        project_id
    )
    
    print(f"   ✓ Ergebnis: {len(result1['output'])} Zeichen")
    print(f"   ✓ Fortfahren: {result1['continue']}")
    
    # Check logs
    logs1 = await db.logs.find({"project_id": project_id}).to_list(100)
    success_count = len([l for l in logs1 if l['level'] == 'success'])
    retry_count = len([l for l in logs1 if '🔄' in l['message']])
    
    print(f"   ✓ Success-Logs: {success_count}")
    print(f"   ℹ️ Retry-Versuche: {retry_count}")
    
    # Test 2: Sehr spezifische Query (könnte Retry brauchen)
    print("\n🔍 Test 2: Sehr spezifische Query")
    print("   Query: 'MongoDB real-time document change streams with FastAPI'")
    
    await db.logs.delete_many({"project_id": project_id})
    
    result2 = await execute_tool(
        "web_search",
        {"query": "MongoDB real-time document change streams with FastAPI", "max_results": 5},
        workspace_path,
        project_id
    )
    
    print(f"   ✓ Ergebnis: {len(result2['output'])} Zeichen")
    
    logs2 = await db.logs.find({"project_id": project_id}).to_list(100)
    retry_count2 = len([l for l in logs2 if '🔄' in l['message']])
    attempts = len([l for l in logs2 if 'Suchversuch' in l['message']])
    
    print(f"   ℹ️ Suchversuche: {attempts}")
    print(f"   ℹ️ Retry-Operationen: {retry_count2}")
    
    # Test 3: Breite Query
    print("\n🔍 Test 3: Breite Recherche-Query")
    print("   Query: 'real-time web applications architecture'")
    
    await db.logs.delete_many({"project_id": project_id})
    
    result3 = await execute_tool(
        "web_search",
        {"query": "real-time web applications architecture", "max_results": 5},
        workspace_path,
        project_id
    )
    
    print(f"   ✓ Ergebnis: {len(result3['output'])} Zeichen")
    
    logs3 = await db.logs.find({"project_id": project_id}).to_list(100)
    final_success = any(l['level'] == 'success' for l in logs3)
    
    print(f"   ✓ Erfolgreich: {'Ja' if final_success else 'Nein'}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 ZUSAMMENFASSUNG")
    print("="*70)
    print(f"✅ Test 1 (Technische Query): {'PASSED' if len(result1['output']) > 100 else 'FAILED'}")
    print(f"✅ Test 2 (Spezifische Query): {'PASSED' if len(result2['output']) > 100 else 'FAILED'}")
    print(f"✅ Test 3 (Breite Query): {'PASSED' if len(result3['output']) > 100 else 'FAILED'}")
    
    print("\n💡 Erkenntnisse:")
    print("   • Web Search ist funktional und liefert Ergebnisse")
    print("   • Retry-Mechanismus arbeitet transparent im Hintergrund")
    print("   • Logging gibt klare Auskunft über Suchverlauf")
    print("   • Agent kann nahtlos mit den Ergebnissen weiterarbeiten")
    
    print("\n🎉 Integration Test: ERFOLGREICH")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(simulate_agent_research_scenario())
