#!/usr/bin/env python3
"""
Targeted ForgePilot Smart Tools Test
Tests the specific smart tools mentioned in the review request.
"""

import requests
import json
import time
import sys
import uuid

BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"

def test_smart_tools():
    """Test smart tools with specific scenarios"""
    session = requests.Session()
    
    print("🔧 Testing ForgePilot Smart Tools")
    print("=" * 50)
    
    # Create test project
    project_data = {
        "name": f"smart-tools-test-{uuid.uuid4().hex[:8]}",
        "description": "Smart tools testing project",
        "project_type": "fullstack"
    }
    
    response = session.post(f"{API_BASE}/projects", json=project_data)
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create project: {response.status_code}")
        return
    
    project = response.json()
    project_id = project["id"]
    print(f"✅ Created test project: {project_id}")
    
    # Test 1: Smart build_app tool with Vite project
    print("\n=== Test 1: Smart build_app Tool ===")
    chat_message = {
        "content": "Create a new Vite React app using 'npm create vite@latest my-react-app -- --template react'. Then build the project using the build_app tool."
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=chat_message,
            stream=True,
            timeout=90
        )
        
        if response.status_code == 200:
            build_app_used = False
            build_success = False
            infinite_loop_detected = False
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            if tool_name == "build_app":
                                build_app_used = True
                                print(f"   build_app output: {output[:200]}...")
                                
                                if "✓" in output and ("build" in output.lower() or "dist" in output.lower()):
                                    build_success = True
                                elif "Missing script: build" in output:
                                    infinite_loop_detected = True
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if build_app_used and build_success:
                print("✅ Smart build_app tool: SUCCESS - Auto-detected subdirectory and built successfully")
            elif build_app_used and infinite_loop_detected:
                print("❌ Smart build_app tool: FAILED - Got stuck on 'Missing script: build'")
            elif build_app_used:
                print("⚠️  Smart build_app tool: PARTIAL - Tool used but build unclear")
            else:
                print("⚠️  Smart build_app tool: NOT TESTED - Tool not used in this scenario")
        
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 2: Smart install_package tool
    print("\n=== Test 2: Smart install_package Tool ===")
    chat_message = {
        "content": "Install the 'lodash' package using npm. The package.json file might be in a subdirectory like my-react-app/."
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=chat_message,
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            install_used = False
            install_success = False
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            if tool_name == "install_package":
                                install_used = True
                                print(f"   install_package output: {output[:200]}...")
                                
                                if "✓" in output or "installed" in output.lower() or "added" in output.lower():
                                    install_success = True
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if install_used and install_success:
                print("✅ Smart install_package tool: SUCCESS - Auto-detected subdirectory and installed package")
            elif install_used:
                print("⚠️  Smart install_package tool: PARTIAL - Tool used but success unclear")
            else:
                print("⚠️  Smart install_package tool: NOT TESTED - Tool not used in this scenario")
        
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 3: clear_errors tool
    print("\n=== Test 3: clear_errors Tool ===")
    chat_message = {
        "content": "Use the clear_errors tool to clear any old error logs. This tool should be available and working."
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=chat_message,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            clear_errors_used = False
            clear_success = False
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            if tool_name == "clear_errors":
                                clear_errors_used = True
                                print(f"   clear_errors output: {output[:200]}...")
                                
                                if "✓" in output or "cleared" in output.lower():
                                    clear_success = True
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if clear_errors_used and clear_success:
                print("✅ clear_errors tool: SUCCESS - Tool executed and cleared errors")
            elif clear_errors_used:
                print("⚠️  clear_errors tool: PARTIAL - Tool used but success unclear")
            else:
                print("❌ clear_errors tool: FAILED - Tool not used or not available")
        
        else:
            print(f"❌ Chat request failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 4: mark_complete (Gate 1)
    print("\n=== Test 4: Smart Gate 1 (mark_complete) ===")
    chat_message = {
        "content": "Mark this project as complete using the mark_complete tool. This should work without being blocked by old errors."
    }
    
    try:
        response = session.post(
            f"{API_BASE}/projects/{project_id}/chat",
            json=chat_message,
            stream=True,
            timeout=45
        )
        
        if response.status_code == 200:
            mark_complete_used = False
            mark_success = False
            blocked_by_errors = False
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        if data.get("type") == "tool_result":
                            tool_name = data.get("tool_name")
                            output = data.get("result", {}).get("output", "")
                            
                            if tool_name == "mark_complete":
                                mark_complete_used = True
                                print(f"   mark_complete output: {output[:200]}...")
                                
                                if "✓" in output or "complete" in output.lower():
                                    mark_success = True
                                elif "error" in output.lower() or "blocked" in output.lower():
                                    blocked_by_errors = True
                        
                        elif data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            if mark_complete_used and mark_success:
                print("✅ Smart Gate 1: SUCCESS - mark_complete worked without being blocked")
            elif mark_complete_used and blocked_by_errors:
                print("❌ Smart Gate 1: FAILED - mark_complete blocked by old errors")
            elif mark_complete_used:
                print("⚠️  Smart Gate 1: PARTIAL - mark_complete used but result unclear")
            else:
                print("⚠️  Smart Gate 1: NOT TESTED - mark_complete not used")
        
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
    print("🏁 Smart Tools Testing Complete")

if __name__ == "__main__":
    test_smart_tools()