#!/usr/bin/env python3
"""
Direct Tool Testing for ForgePilot
Tests tools directly through the execute_tool mechanism.
"""

import requests
import json
import uuid
import time

BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"

def test_direct_tools():
    """Test tools directly"""
    session = requests.Session()
    
    print("🔧 Testing ForgePilot Tools Directly")
    print("=" * 50)
    
    # Create test project
    project_data = {
        "name": f"direct-test-{uuid.uuid4().hex[:8]}",
        "description": "Direct tool testing",
        "project_type": "fullstack"
    }
    
    response = session.post(f"{API_BASE}/projects", json=project_data)
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create project: {response.status_code}")
        return
    
    project = response.json()
    project_id = project["id"]
    print(f"✅ Created test project: {project_id}")
    
    # Test clear_errors tool directly
    print("\n=== Testing clear_errors Tool Directly ===")
    chat_message = {
        "content": "Please use the clear_errors tool with reason 'Testing clear_errors functionality'. This is a direct test of the tool."
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=chat_message,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            clear_errors_found = False
            tool_output = ""
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            print(f"   Tool used: {tool_name}")
                            print(f"   Output: {output[:300]}...")
                            
                            if tool_name == "clear_errors":
                                clear_errors_found = True
                                tool_output = output
                        
                        elif data.get("type") == "content":
                            content = data.get("content", "")
                            if content.strip():
                                print(f"   Content: {content[:200]}...")
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if clear_errors_found:
                if "✓" in tool_output or "cleared" in tool_output.lower():
                    print("✅ clear_errors tool: SUCCESS - Tool executed successfully")
                else:
                    print(f"⚠️  clear_errors tool: EXECUTED - Output: {tool_output}")
            else:
                print("❌ clear_errors tool: NOT FOUND - Tool was not used")
        
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test build_app tool with explicit request
    print("\n=== Testing build_app Tool Directly ===")
    
    # First create a simple package.json
    create_package_message = {
        "content": "Create a package.json file with build script: {\"name\": \"test-app\", \"scripts\": {\"build\": \"echo 'Building app...'\"}}"
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=create_package_message,
            stream=True,
            timeout=30
        )
        
        # Wait for completion
        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        
        # Now test build_app
        build_message = {
            "content": "Use the build_app tool to build this project. The package.json should be in the root directory."
        }
        
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=build_message,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            build_app_found = False
            tool_output = ""
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            print(f"   Tool used: {tool_name}")
                            print(f"   Output: {output[:300]}...")
                            
                            if tool_name == "build_app":
                                build_app_found = True
                                tool_output = output
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if build_app_found:
                if "✓" in tool_output or "build" in tool_output.lower():
                    print("✅ build_app tool: SUCCESS - Tool executed successfully")
                else:
                    print(f"⚠️  build_app tool: EXECUTED - Output: {tool_output}")
            else:
                print("❌ build_app tool: NOT FOUND - Tool was not used")
        
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test install_package tool
    print("\n=== Testing install_package Tool Directly ===")
    install_message = {
        "content": "Use the install_package tool to install 'lodash' with npm. The package.json is in the root directory."
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=install_message,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            install_found = False
            tool_output = ""
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            print(f"   Tool used: {tool_name}")
                            print(f"   Output: {output[:300]}...")
                            
                            if tool_name == "install_package":
                                install_found = True
                                tool_output = output
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if install_found:
                if "✓" in tool_output or "install" in tool_output.lower():
                    print("✅ install_package tool: SUCCESS - Tool executed successfully")
                else:
                    print(f"⚠️  install_package tool: EXECUTED - Output: {tool_output}")
            else:
                print("❌ install_package tool: NOT FOUND - Tool was not used")
        
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Cleanup
    try:
        session.delete(f"{API_BASE}/projects/{project_id}")
        print(f"\n✓ Cleaned up test project: {project_id}")
    except:
        pass
    
    print("\n" + "=" * 50)
    print("🏁 Direct Tool Testing Complete")

if __name__ == "__main__":
    test_direct_tools()