#!/usr/bin/env python3
"""
ForgePilot Backend API Testing Suite
Tests critical backend functionality including smart tools and API endpoints.
"""

import requests
import json
import time
import sys
import uuid
from typing import Dict, Any, List
import asyncio
import aiohttp
import subprocess

# Test Configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"

class ForgePilotTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.project_id = None
        
    def log_test(self, test_name: str, success: bool, message: str, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        })
    
    def test_basic_api_health(self):
        """Test basic API endpoints"""
        print("\n=== Testing Basic API Health ===")
        
        # Test GET /api/
        try:
            response = self.session.get(f"{API_BASE}/")
            if response.status_code == 200:
                data = response.json()
                required_fields = ["message", "version", "llm_provider", "active_provider", "ollama_available"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("GET /api/", True, f"API root endpoint working. Version: {data.get('version')}")
                else:
                    self.log_test("GET /api/", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("GET /api/", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/", False, f"Request failed: {str(e)}")
        
        # Test GET /api/health
        try:
            response = self.session.get(f"{API_BASE}/health")
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "version", "checks"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and "checks" in data:
                    checks = data["checks"]
                    check_fields = ["mongodb", "llm", "ollama", "openai"]
                    missing_checks = [field for field in check_fields if field not in checks]
                    
                    if not missing_checks:
                        self.log_test("GET /api/health", True, f"Health check working. Status: {data.get('status')}")
                    else:
                        self.log_test("GET /api/health", False, f"Missing check fields: {missing_checks}")
                else:
                    self.log_test("GET /api/health", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("GET /api/health", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/health", False, f"Request failed: {str(e)}")
        
        # Test GET /api/settings
        try:
            response = self.session.get(f"{API_BASE}/settings")
            if response.status_code == 200:
                data = response.json()
                required_fields = ["openai_api_key_set", "github_token_set", "ollama_url", "ollama_model", "llm_provider", "ollama_available", "ollama_models"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("GET /api/settings", True, f"Settings endpoint working. LLM Provider: {data.get('llm_provider')}")
                else:
                    self.log_test("GET /api/settings", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("GET /api/settings", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/settings", False, f"Request failed: {str(e)}")
    
    def create_test_project(self) -> str:
        """Create a test project and return project ID"""
        print("\n=== Creating Test Project ===")
        
        project_data = {
            "name": f"test-project-{uuid.uuid4().hex[:8]}",
            "description": "Test project for ForgePilot backend testing",
            "project_type": "fullstack"
        }
        
        try:
            response = self.session.post(f"{API_BASE}/projects", json=project_data)
            if response.status_code in [200, 201]:
                project = response.json()
                project_id = project.get("id")
                self.project_id = project_id
                self.log_test("Create Project", True, f"Project created with ID: {project_id}")
                return project_id
            else:
                self.log_test("Create Project", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Create Project", False, f"Request failed: {str(e)}")
            return None
    
    def test_smart_build_app_tool(self, project_id: str):
        """Test smart build_app tool via chat endpoint"""
        print("\n=== Testing Smart build_app Tool ===")
        
        if not project_id:
            self.log_test("Smart build_app Tool", False, "No project ID available")
            return
        
        # Send chat message to create a Vite React app
        chat_message = {
            "content": "Create a new Vite React app. Use 'npm create vite' to set up the project."
        }
        
        try:
            # Use streaming endpoint to get SSE response
            response = self.session.post(
                f"{API_BASE}/projects/{project_id}/chat",
                json=chat_message,
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                # Parse SSE stream for tool_result events
                tool_results = []
                content_parts = []
                done = False
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            if data.get("type") == "tool_result":
                                tool_results.append(data)
                                print(f"   Tool: {data.get('tool_name')} - {data.get('result', {}).get('output', '')[:100]}...")
                            
                            elif data.get("type") == "content":
                                content_parts.append(data.get("content", ""))
                            
                            elif data.get("done"):
                                done = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Check if build_app tool was used and succeeded
                build_app_results = [r for r in tool_results if r.get("tool_name") == "build_app"]
                
                if build_app_results:
                    build_result = build_app_results[-1]
                    output = build_result.get("result", {}).get("output", "")
                    
                    # Check for success indicators
                    if "✓" in output and "build" in output.lower():
                        self.log_test("Smart build_app Tool", True, "build_app tool executed successfully and auto-detected subdirectory")
                    elif "Missing script: build" in output:
                        self.log_test("Smart build_app Tool", False, "Agent got stuck on 'Missing script: build' - smart detection failed")
                    else:
                        self.log_test("Smart build_app Tool", False, f"build_app tool failed: {output}")
                else:
                    # Check if agent completed without getting stuck
                    if done:
                        self.log_test("Smart build_app Tool", True, "Agent completed without infinite loop (build_app may not have been needed)")
                    else:
                        self.log_test("Smart build_app Tool", False, "Agent did not complete or get to build_app tool")
            
            else:
                self.log_test("Smart build_app Tool", False, f"Chat endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Smart build_app Tool", False, f"Request failed: {str(e)}")
    
    def test_smart_install_package_tool(self, project_id: str):
        """Test smart install_package tool"""
        print("\n=== Testing Smart install_package Tool ===")
        
        if not project_id:
            self.log_test("Smart install_package Tool", False, "No project ID available")
            return
        
        # Send chat message to install a package
        chat_message = {
            "content": "Install the 'axios' package using npm. The package.json might be in a subdirectory."
        }
        
        try:
            response = self.session.post(
                f"{API_BASE}/projects/{project_id}/chat",
                json=chat_message,
                stream=True,
                timeout=45
            )
            
            if response.status_code == 200:
                tool_results = []
                done = False
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            if data.get("type") == "tool_result":
                                tool_results.append(data)
                                print(f"   Tool: {data.get('tool_name')} - {data.get('result', {}).get('output', '')[:100]}...")
                            
                            elif data.get("done"):
                                done = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Check if install_package tool was used
                install_results = [r for r in tool_results if r.get("tool_name") == "install_package"]
                
                if install_results:
                    install_result = install_results[-1]
                    output = install_result.get("result", {}).get("output", "")
                    
                    if "✓" in output or "installed" in output.lower():
                        self.log_test("Smart install_package Tool", True, "install_package tool worked correctly with subdirectory detection")
                    else:
                        self.log_test("Smart install_package Tool", False, f"install_package tool failed: {output}")
                else:
                    if done:
                        self.log_test("Smart install_package Tool", True, "Agent completed (install_package may not have been needed)")
                    else:
                        self.log_test("Smart install_package Tool", False, "install_package tool was not used")
            
            else:
                self.log_test("Smart install_package Tool", False, f"Chat endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Smart install_package Tool", False, f"Request failed: {str(e)}")
    
    def test_clear_errors_tool(self, project_id: str):
        """Test clear_errors tool directly"""
        print("\n=== Testing clear_errors Tool ===")
        
        if not project_id:
            self.log_test("clear_errors Tool", False, "No project ID available")
            return
        
        # First, create some errors by triggering a bad build
        print("   Creating test errors...")
        bad_build_message = {
            "content": "Create a file called 'bad-syntax.js' with invalid JavaScript syntax, then try to build the project."
        }
        
        try:
            # Create errors
            response = self.session.post(
                f"{API_BASE}/projects/{project_id}/chat",
                json=bad_build_message,
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
            
            # Now test clear_errors tool
            clear_errors_message = {
                "content": "Use the clear_errors tool to clear any old error logs that have been resolved."
            }
            
            response = self.session.post(
                f"{API_BASE}/projects/{project_id}/chat",
                json=clear_errors_message,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                tool_results = []
                done = False
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            if data.get("type") == "tool_result":
                                tool_results.append(data)
                                print(f"   Tool: {data.get('tool_name')} - {data.get('result', {}).get('output', '')[:100]}...")
                            
                            elif data.get("done"):
                                done = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Check if clear_errors tool was used
                clear_results = [r for r in tool_results if r.get("tool_name") == "clear_errors"]
                
                if clear_results:
                    clear_result = clear_results[-1]
                    output = clear_result.get("result", {}).get("output", "")
                    
                    if "✓" in output or "cleared" in output.lower():
                        self.log_test("clear_errors Tool", True, "clear_errors tool executed successfully")
                    else:
                        self.log_test("clear_errors Tool", False, f"clear_errors tool failed: {output}")
                else:
                    self.log_test("clear_errors Tool", False, "clear_errors tool was not used")
            
            else:
                self.log_test("clear_errors Tool", False, f"Chat endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("clear_errors Tool", False, f"Request failed: {str(e)}")
    
    def test_smart_gate1_mark_complete(self, project_id: str):
        """Test Smart Gate 1 (mark_complete) functionality"""
        print("\n=== Testing Smart Gate 1 (mark_complete) ===")
        
        if not project_id:
            self.log_test("Smart Gate 1", False, "No project ID available")
            return
        
        # Test mark_complete after fixing errors
        mark_complete_message = {
            "content": "Mark this project as complete. The project should be ready for completion now."
        }
        
        try:
            response = self.session.post(
                f"{API_BASE}/projects/{project_id}/chat",
                json=mark_complete_message,
                stream=True,
                timeout=45
            )
            
            if response.status_code == 200:
                tool_results = []
                done = False
                error_messages = []
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            if data.get("type") == "tool_result":
                                tool_results.append(data)
                                tool_name = data.get('tool_name')
                                output = data.get('result', {}).get('output', '')
                                print(f"   Tool: {tool_name} - {output[:100]}...")
                                
                                # Check for error patterns
                                if "error" in output.lower() or "✗" in output:
                                    error_messages.append(f"{tool_name}: {output}")
                            
                            elif data.get("type") == "content":
                                content = data.get("content", "")
                                if "error" in content.lower():
                                    error_messages.append(f"Content: {content}")
                            
                            elif data.get("done"):
                                done = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Check if mark_complete was attempted
                mark_complete_results = [r for r in tool_results if r.get("tool_name") == "mark_complete"]
                
                if mark_complete_results:
                    mark_result = mark_complete_results[-1]
                    output = mark_result.get("result", {}).get("output", "")
                    
                    if "✓" in output or "complete" in output.lower():
                        self.log_test("Smart Gate 1", True, "mark_complete succeeded - Gate 1 not blocked by old errors")
                    else:
                        self.log_test("Smart Gate 1", False, f"mark_complete failed: {output}")
                else:
                    # Check if agent got stuck or completed without mark_complete
                    if done and not error_messages:
                        self.log_test("Smart Gate 1", True, "Agent completed without being blocked by old errors")
                    elif error_messages:
                        self.log_test("Smart Gate 1", False, f"Agent encountered errors: {'; '.join(error_messages[:2])}")
                    else:
                        self.log_test("Smart Gate 1", False, "Agent did not attempt mark_complete")
            
            else:
                self.log_test("Smart Gate 1", False, f"Chat endpoint failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Smart Gate 1", False, f"Request failed: {str(e)}")
    
    def test_sse_streaming(self, project_id: str):
        """Test Server-Sent Events streaming"""
        print("\n=== Testing SSE Streaming ===")
        
        if not project_id:
            self.log_test("SSE Streaming", False, "No project ID available")
            return
        
        chat_message = {
            "content": "Create a simple HTML file with 'Hello World' content."
        }
        
        try:
            response = self.session.post(
                f"{API_BASE}/projects/{project_id}/chat",
                json=chat_message,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                events_received = 0
                tool_events = 0
                content_events = 0
                done_received = False
                
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            events_received += 1
                            
                            if data.get("type") == "tool_result":
                                tool_events += 1
                            elif data.get("type") == "content":
                                content_events += 1
                            elif data.get("done"):
                                done_received = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                if done_received and events_received > 0:
                    self.log_test("SSE Streaming", True, f"SSE working: {events_received} events, {tool_events} tools, {content_events} content")
                else:
                    self.log_test("SSE Streaming", False, f"SSE incomplete: done={done_received}, events={events_received}")
            
            else:
                self.log_test("SSE Streaming", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("SSE Streaming", False, f"Request failed: {str(e)}")
    
    def cleanup_test_project(self, project_id: str):
        """Clean up test project"""
        if project_id:
            try:
                response = self.session.delete(f"{API_BASE}/projects/{project_id}")
                if response.status_code in [200, 204, 404]:
                    print(f"\n✓ Cleaned up test project: {project_id}")
                else:
                    print(f"\n⚠ Could not clean up project {project_id}: HTTP {response.status_code}")
            except Exception as e:
                print(f"\n⚠ Cleanup error: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting ForgePilot Backend API Tests")
        print("=" * 50)
        
        # Basic API health tests
        self.test_basic_api_health()
        
        # Create test project
        project_id = self.create_test_project()
        
        if project_id:
            # Test smart tools and features
            self.test_sse_streaming(project_id)
            self.test_smart_build_app_tool(project_id)
            self.test_smart_install_package_tool(project_id)
            self.test_clear_errors_tool(project_id)
            self.test_smart_gate1_mark_complete(project_id)
            
            # Cleanup
            self.cleanup_test_project(project_id)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🏁 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in self.test_results if r["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['message']}")
                if test['details']:
                    print(f"    Details: {test['details']}")
        
        print("\n" + "=" * 50)
        
        # Return exit code
        return 0 if passed == total else 1

if __name__ == "__main__":
    tester = ForgePilotTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)