"""
Test script for Enhanced Web Search with Retry Logic
Tests the web_search tool with queries that initially yield no/few results
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')

# Import server functions
from server import execute_tool, get_active_llm_provider, generate_alternative_query

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'forgepilot')]

async def test_alternative_query_generation():
    """Test 1: LLM Query Generation"""
    print("\n" + "="*60)
    print("TEST 1: Alternative Query Generation")
    print("="*60)
    
    original_query = "xyz123 nonexistent tech"
    
    print(f"\n🔍 Original Query: '{original_query}'")
    
    for attempt in range(1, 4):
        alternative = await generate_alternative_query(original_query, attempt)
        print(f"   Attempt {attempt}: '{alternative}'")
    
    print("✓ Query generation test completed")

async def test_web_search_with_good_query():
    """Test 2: Web Search with query that should succeed immediately"""
    print("\n" + "="*60)
    print("TEST 2: Web Search - Good Query (should succeed on attempt 1)")
    print("="*60)
    
    # Create test project
    project_id = "test_websearch_good"
    workspace_path = Path("/tmp/test_workspace_good")
    workspace_path.mkdir(exist_ok=True)
    
    # Clean up old project
    await db.projects.delete_many({"_id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    
    # Create project
    await db.projects.insert_one({
        "_id": project_id,
        "name": "Test Web Search Good",
        "status": "active"
    })
    
    print(f"\n🔍 Testing query: 'python best practices 2024'")
    
    result = await execute_tool(
        "web_search",
        {"query": "python best practices 2024", "max_results": 5},
        workspace_path,
        project_id
    )
    
    print(f"\n📊 Result:")
    print(f"   Continue: {result['continue']}")
    print(f"   Output length: {len(result['output'])} chars")
    print(f"\n   Output preview:\n   {result['output'][:300]}...")
    
    # Check logs
    logs = await db.logs.find({"project_id": project_id}).to_list(100)
    print(f"\n📝 Logs generated: {len(logs)}")
    for log in logs:
        print(f"   [{log['level']}] {log['message']}")
    
    assert "Suchergebnisse" in result['output'] or "Ergebnisse" in result['output'], "Should contain results"
    print("\n✓ Good query test passed")

async def test_web_search_with_obscure_query():
    """Test 3: Web Search with obscure query (should trigger retries)"""
    print("\n" + "="*60)
    print("TEST 3: Web Search - Obscure Query (should retry)")
    print("="*60)
    
    # Create test project
    project_id = "test_websearch_obscure"
    workspace_path = Path("/tmp/test_workspace_obscure")
    workspace_path.mkdir(exist_ok=True)
    
    # Clean up old project
    await db.projects.delete_many({"_id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    
    # Create project
    await db.projects.insert_one({
        "_id": project_id,
        "name": "Test Web Search Obscure",
        "status": "active"
    })
    
    # Use a very obscure query that likely has few results
    obscure_query = "xyzabc123 nonexistent framework v99.9"
    print(f"\n🔍 Testing obscure query: '{obscure_query}'")
    
    result = await execute_tool(
        "web_search",
        {"query": obscure_query, "max_results": 5},
        workspace_path,
        project_id
    )
    
    print(f"\n📊 Result:")
    print(f"   Continue: {result['continue']}")
    print(f"   Output length: {len(result['output'])} chars")
    print(f"\n   Output:\n   {result['output'][:500]}...")
    
    # Check logs to verify retry attempts
    logs = await db.logs.find({"project_id": project_id}).to_list(100)
    print(f"\n📝 Logs generated: {len(logs)}")
    
    retry_logs = [log for log in logs if "Versuch" in log['message'] or "alternative" in log['message'].lower()]
    print(f"\n🔄 Retry-related logs: {len(retry_logs)}")
    for log in retry_logs:
        print(f"   [{log['level']}] {log['message']}")
    
    assert len(retry_logs) > 0, "Should have retry logs"
    print("\n✓ Obscure query test passed - retry logic activated")

async def test_web_search_with_narrow_query():
    """Test 4: Web Search with very narrow technical query"""
    print("\n" + "="*60)
    print("TEST 4: Web Search - Narrow Technical Query")
    print("="*60)
    
    # Create test project
    project_id = "test_websearch_narrow"
    workspace_path = Path("/tmp/test_workspace_narrow")
    workspace_path.mkdir(exist_ok=True)
    
    # Clean up old project
    await db.projects.delete_many({"_id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    
    # Create project
    await db.projects.insert_one({
        "_id": project_id,
        "name": "Test Web Search Narrow",
        "status": "active"
    })
    
    narrow_query = "fastapi websocket mongodb best practices"
    print(f"\n🔍 Testing narrow query: '{narrow_query}'")
    
    result = await execute_tool(
        "web_search",
        {"query": narrow_query, "max_results": 5},
        workspace_path,
        project_id
    )
    
    print(f"\n📊 Result:")
    print(f"   Continue: {result['continue']}")
    print(f"   Output length: {len(result['output'])} chars")
    
    # Check logs
    logs = await db.logs.find({"project_id": project_id}).to_list(100)
    print(f"\n📝 Total logs: {len(logs)}")
    
    success_logs = [log for log in logs if log['level'] == 'success']
    warning_logs = [log for log in logs if log['level'] == 'warning']
    
    print(f"   ✓ Success logs: {len(success_logs)}")
    print(f"   ⚠️ Warning logs: {len(warning_logs)}")
    
    print("\n✓ Narrow query test completed")

async def run_all_tests():
    """Run all web search tests"""
    print("\n" + "="*60)
    print("🧪 ForgePilot - Enhanced Web Search Retry Tests")
    print("="*60)
    
    provider = get_active_llm_provider()
    print(f"\n🤖 Active LLM Provider: {provider}")
    
    try:
        # Test 1: Query generation
        await test_alternative_query_generation()
        
        # Test 2: Good query (should succeed immediately)
        await test_web_search_with_good_query()
        
        # Test 3: Obscure query (should trigger retries)
        await test_web_search_with_obscure_query()
        
        # Test 4: Narrow technical query
        await test_web_search_with_narrow_query()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\n📊 Summary:")
        print("   ✓ Alternative query generation working")
        print("   ✓ Web search succeeds with good queries")
        print("   ✓ Retry logic activates for obscure queries")
        print("   ✓ Technical queries handled correctly")
        print("\n🎉 Enhanced Web Search with Retry Logic: OPERATIONAL")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
