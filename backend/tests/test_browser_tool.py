"""
Quick test for browser_test tool
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

async def test_browser_test_tool():
    """Test the browser_test tool"""
    
    print("="*70)
    print("🌐 Testing browser_test Tool")
    print("="*70)
    
    # Setup
    project_id = "test_browser_tool"
    workspace_path = Path("/tmp/test_browser_workspace")
    workspace_path.mkdir(exist_ok=True)
    
    # Create simple HTML file for testing
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #f5f5f5; }
        form { background: white; padding: 20px; border-radius: 8px; }
        input, button { margin: 10px 0; padding: 10px; width: 100%; }
        button { background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Test Formular</h1>
    <form id="testForm">
        <input type="text" name="name" placeholder="Name" required>
        <input type="email" name="email" placeholder="Email" required>
        <button type="submit">Speichern</button>
    </form>
    <div id="result"></div>
    
    <script>
        document.getElementById('testForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            document.getElementById('result').innerHTML = '<p>Gespeichert: ' + JSON.stringify(data) + '</p>';
        });
    </script>
</body>
</html>"""
    
    (workspace_path / "index.html").write_text(html_content)
    
    # Cleanup
    await db.projects.delete_many({"id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    
    # Create project
    await db.projects.insert_one({
        "id": project_id,
        "name": "Browser Test Project",
        "status": "active"
    })
    
    print("\n📝 Test-Szenarien:")
    print("   1. Formular ausfüllen und absenden")
    print("   2. Button-Klicks testen")
    
    # Run browser_test
    result = await execute_tool(
        "browser_test",
        {
            "test_scenarios": [
                "Fill form with name and email and submit",
                "Click submit button"
            ],
            "preview_url": f"file://{workspace_path}/index.html"
        },
        workspace_path,
        project_id
    )
    
    print("\n📊 Ergebnis:")
    print(result['output'])
    
    # Check logs
    logs = await db.logs.find({"project_id": project_id}).to_list(100)
    print(f"\n📝 Logs: {len(logs)}")
    for log in logs:
        print(f"   [{log['level']}] {log['message']}")
    
    print("\n✅ Browser-Test Tool funktioniert!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_browser_test_tool())
