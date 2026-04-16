#!/usr/bin/env python3
"""
ForgePilot Backend API Testing Script
Tests all critical backend endpoints as specified in the review request.
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://portal-test-issue.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class BackendTester:
    def __init__(self):
        self.session = None
        self.test_results = []
        self.project_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'Content-Type': 'application/json'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        if response_data and isinstance(response_data, dict):
            print(f"    Response keys: {list(response_data.keys())}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        })
        print()
    
    async def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print("=== TESTING BASIC API ENDPOINTS ===")
        
        # Test GET /api/ (root endpoint)
        try:
            async with self.session.get(f"{API_BASE}/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    required_fields = ['message', 'version', 'llm_provider', 'active_provider', 'ollama_available']
                    missing_fields = [f for f in required_fields if f not in data]
                    
                    if not missing_fields:
                        self.log_test("GET /api/ - Root endpoint", True, 
                                    f"Version: {data.get('version')}, LLM Provider: {data.get('llm_provider')}, Active: {data.get('active_provider')}", data)
                    else:
                        self.log_test("GET /api/ - Root endpoint", False, 
                                    f"Missing required fields: {missing_fields}", data)
                else:
                    self.log_test("GET /api/ - Root endpoint", False, f"HTTP {resp.status}")
        except Exception as e:
            self.log_test("GET /api/ - Root endpoint", False, f"Exception: {str(e)}")
        
        # Test GET /api/health
        try:
            async with self.session.get(f"{API_BASE}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    required_fields = ['status', 'version', 'checks']
                    missing_fields = [f for f in required_fields if f not in data]
                    
                    if not missing_fields and 'checks' in data:
                        checks = data['checks']
                        check_fields = ['mongodb', 'llm', 'ollama', 'openai']
                        missing_checks = [f for f in check_fields if f not in checks]
                        
                        if not missing_checks:
                            self.log_test("GET /api/health", True, 
                                        f"Status: {data.get('status')}, MongoDB: {checks.get('mongodb')}, LLM: {checks.get('llm')}", data)
                        else:
                            self.log_test("GET /api/health", False, 
                                        f"Missing check fields: {missing_checks}", data)
                    else:
                        self.log_test("GET /api/health", False, 
                                    f"Missing required fields: {missing_fields}", data)
                else:
                    self.log_test("GET /api/health", False, f"HTTP {resp.status}")
        except Exception as e:
            self.log_test("GET /api/health", False, f"Exception: {str(e)}")
        
        # Test GET /api/settings
        try:
            async with self.session.get(f"{API_BASE}/settings") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    required_fields = ['openai_api_key_set', 'github_token_set', 'ollama_url', 'ollama_model', 'llm_provider', 'ollama_available', 'ollama_models']
                    missing_fields = [f for f in required_fields if f not in data]
                    
                    if not missing_fields:
                        self.log_test("GET /api/settings", True, 
                                    f"LLM Provider: {data.get('llm_provider')}, Ollama Available: {data.get('ollama_available')}", data)
                    else:
                        self.log_test("GET /api/settings", False, 
                                    f"Missing required fields: {missing_fields}", data)
                else:
                    self.log_test("GET /api/settings", False, f"HTTP {resp.status}")
        except Exception as e:
            self.log_test("GET /api/settings", False, f"Exception: {str(e)}")
        
        # Test GET /api/llm/status
        try:
            async with self.session.get(f"{API_BASE}/llm/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    required_fields = ['provider', 'active_provider', 'ollama_available', 'ollama_url', 'ollama_model', 'ollama_models', 'openai_available', 'auto_fallback_active']
                    missing_fields = [f for f in required_fields if f not in data]
                    
                    if not missing_fields:
                        self.log_test("GET /api/llm/status", True, 
                                    f"Provider: {data.get('provider')}, Active: {data.get('active_provider')}, OpenAI: {data.get('openai_available')}", data)
                    else:
                        self.log_test("GET /api/llm/status", False, 
                                    f"Missing required fields: {missing_fields}", data)
                else:
                    self.log_test("GET /api/llm/status", False, f"HTTP {resp.status}")
        except Exception as e:
            self.log_test("GET /api/llm/status", False, f"Exception: {str(e)}")
    
    async def test_project_management(self):
        """Test project management endpoints"""
        print("=== TESTING PROJECT MANAGEMENT ===")
        
        # Test POST /api/projects (create project)
        project_data = {
            "name": "Test HTML Project",
            "description": "Test project for backend API testing",
            "project_type": "fullstack"
        }
        
        try:
            async with self.session.post(f"{API_BASE}/projects", json=project_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'id' in data:
                        self.project_id = data['id']
                        self.log_test("POST /api/projects - Create project", True, 
                                    f"Created project with ID: {self.project_id}", data)
                    else:
                        self.log_test("POST /api/projects - Create project", False, 
                                    "No project ID in response", data)
                else:
                    response_text = await resp.text()
                    self.log_test("POST /api/projects - Create project", False, 
                                f"HTTP {resp.status}: {response_text}")
        except Exception as e:
            self.log_test("POST /api/projects - Create project", False, f"Exception: {str(e)}")
        
        # Test GET /api/projects (list projects)
        try:
            async with self.session.get(f"{API_BASE}/projects") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        self.log_test("GET /api/projects - List projects", True, 
                                    f"Found {len(data)} projects", {"count": len(data)})
                    else:
                        self.log_test("GET /api/projects - List projects", False, 
                                    "Response is not a list", data)
                else:
                    response_text = await resp.text()
                    self.log_test("GET /api/projects - List projects", False, 
                                f"HTTP {resp.status}: {response_text}")
        except Exception as e:
            self.log_test("GET /api/projects - List projects", False, f"Exception: {str(e)}")
        
        # Test GET /api/projects/{id} (get specific project)
        if self.project_id:
            try:
                async with self.session.get(f"{API_BASE}/projects/{self.project_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'id' in data and data['id'] == self.project_id:
                            self.log_test("GET /api/projects/{id} - Get project", True, 
                                        f"Retrieved project: {data.get('name')}", data)
                        else:
                            self.log_test("GET /api/projects/{id} - Get project", False, 
                                        "Project ID mismatch", data)
                    else:
                        response_text = await resp.text()
                        self.log_test("GET /api/projects/{id} - Get project", False, 
                                    f"HTTP {resp.status}: {response_text}")
            except Exception as e:
                self.log_test("GET /api/projects/{id} - Get project", False, f"Exception: {str(e)}")
        else:
            self.log_test("GET /api/projects/{id} - Get project", False, "No project ID available")
    
    async def test_agent_chat_system(self):
        """Test agent chat system with streaming SSE"""
        print("=== TESTING AGENT CHAT SYSTEM (CRITICAL) ===")
        
        if not self.project_id:
            self.log_test("Agent Chat System", False, "No project ID available for chat testing")
            return
        
        # Test POST /api/projects/{id}/chat with streaming
        chat_message = {
            "content": "Erstelle eine einfache HTML Datei mit Hallo Welt",
            "role": "user"
        }
        
        try:
            # Test streaming SSE response with timeout
            timeout = aiohttp.ClientTimeout(total=15)  # 15 second timeout
            async with self.session.post(
                f"{API_BASE}/projects/{self.project_id}/chat",
                json=chat_message,
                headers={'Accept': 'text/event-stream'},
                timeout=timeout
            ) as resp:
                
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '')
                    if 'text/event-stream' in content_type or 'text/plain' in content_type:
                        # Read streaming response
                        events_received = []
                        tool_calls_found = False
                        done_event_found = False
                        content_found = False
                        
                        try:
                            async for line in resp.content:
                                line_str = line.decode('utf-8').strip()
                                if line_str.startswith('data: '):
                                    try:
                                        event_data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                        events_received.append(event_data)
                                        
                                        # Check for tool events (create_file, etc.)
                                        if 'tool' in event_data:
                                            tool_calls_found = True
                                        
                                        # Check for content events
                                        if 'content' in event_data:
                                            content_found = True
                                        
                                        # Check for done event
                                        if event_data.get('type') == 'done':
                                            done_event_found = True
                                            break
                                            
                                    except json.JSONDecodeError:
                                        # Some lines might not be JSON, that's ok
                                        continue
                                        
                                # Break after reasonable number of events or timeout
                                if len(events_received) > 10:
                                    break
                                    
                        except asyncio.TimeoutError:
                            # Timeout is expected for streaming, that's ok
                            pass
                        
                        # Evaluate the streaming response
                        if events_received:
                            details = f"Received {len(events_received)} events"
                            if tool_calls_found:
                                details += ", tool events found"
                            if content_found:
                                details += ", content events found"
                            
                            # Success if we got tool calls or content (agent is working)
                            success = tool_calls_found or content_found
                            self.log_test("POST /api/projects/{id}/chat - Streaming SSE", success, details, 
                                        {"events_count": len(events_received), "tool_calls": tool_calls_found, "content": content_found})
                        else:
                            self.log_test("POST /api/projects/{id}/chat - Streaming SSE", False, 
                                        "No events received in stream")
                    else:
                        self.log_test("POST /api/projects/{id}/chat - Streaming SSE", False, 
                                    f"Wrong content type: {content_type}")
                else:
                    response_text = await resp.text()
                    self.log_test("POST /api/projects/{id}/chat - Streaming SSE", False, 
                                f"HTTP {resp.status}: {response_text}")
                    
        except asyncio.TimeoutError:
            self.log_test("POST /api/projects/{id}/chat - Streaming SSE", False, "Timeout waiting for response")
        except Exception as e:
            self.log_test("POST /api/projects/{id}/chat - Streaming SSE", False, f"Exception: {str(e)}")
    
    async def test_agent_tool_execution(self):
        """Test agent tool execution results"""
        print("=== TESTING AGENT TOOL EXECUTION ===")
        
        if not self.project_id:
            self.log_test("Agent Tool Execution", False, "No project ID available for tool testing")
            return
        
        # Wait a bit for agent to potentially create files
        await asyncio.sleep(2)
        
        # Test GET /api/projects/{id}/files
        try:
            async with self.session.get(f"{API_BASE}/projects/{self.project_id}/files") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict) and 'tree' in data:
                        # New format: {"type": "directory", "items": [], "tree": [...]}
                        files = data['tree']
                        self.log_test("GET /api/projects/{id}/files", True, 
                                    f"Found {len(files)} files in tree structure", {"files_count": len(files)})
                    elif isinstance(data, list):
                        # Old format: direct list
                        self.log_test("GET /api/projects/{id}/files", True, 
                                    f"Found {len(data)} files", {"files_count": len(data)})
                    elif isinstance(data, dict) and 'files' in data:
                        # Alternative format: {"files": [...]}
                        files = data['files']
                        self.log_test("GET /api/projects/{id}/files", True, 
                                    f"Found {len(files)} files", {"files_count": len(files)})
                    else:
                        self.log_test("GET /api/projects/{id}/files", False, 
                                    "Unexpected response format", data)
                else:
                    response_text = await resp.text()
                    self.log_test("GET /api/projects/{id}/files", False, 
                                f"HTTP {resp.status}: {response_text}")
        except Exception as e:
            self.log_test("GET /api/projects/{id}/files", False, f"Exception: {str(e)}")
        
        # Test GET /api/projects/{id}/preview-info
        try:
            async with self.session.get(f"{API_BASE}/projects/{self.project_id}/preview-info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        self.log_test("GET /api/projects/{id}/preview-info", True, 
                                    "Preview info retrieved", data)
                    else:
                        self.log_test("GET /api/projects/{id}/preview-info", False, 
                                    "Unexpected response format", data)
                else:
                    response_text = await resp.text()
                    self.log_test("GET /api/projects/{id}/preview-info", False, 
                                f"HTTP {resp.status}: {response_text}")
        except Exception as e:
            self.log_test("GET /api/projects/{id}/preview-info", False, f"Exception: {str(e)}")
    
    async def test_settings_update(self):
        """Test settings update functionality"""
        print("=== TESTING SETTINGS UPDATE ===")
        
        # Test PUT /api/settings
        settings_update = {
            "llm_provider": "openai"
        }
        
        try:
            async with self.session.put(f"{API_BASE}/settings", json=settings_update) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'success' in data and data['success']:
                        self.log_test("PUT /api/settings", True, 
                                    f"Settings updated: {data.get('message', '')}", data)
                    else:
                        self.log_test("PUT /api/settings", False, 
                                    "Success flag not true", data)
                else:
                    response_text = await resp.text()
                    self.log_test("PUT /api/settings", False, 
                                f"HTTP {resp.status}: {response_text}")
        except Exception as e:
            self.log_test("PUT /api/settings", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 60)
        print("BACKEND API TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['details']}")
            print()
        
        print("CRITICAL ISSUES:")
        critical_failures = []
        for result in self.test_results:
            if not result['success']:
                if 'chat' in result['test'].lower() or 'streaming' in result['test'].lower():
                    critical_failures.append(f"CRITICAL: {result['test']} - {result['details']}")
                elif 'Exception' in result['details']:
                    critical_failures.append(f"ERROR: {result['test']} - {result['details']}")
        
        if critical_failures:
            for failure in critical_failures:
                print(f"🚨 {failure}")
        else:
            print("✅ No critical issues found")
        
        return passed_tests, failed_tests

async def main():
    """Main test runner"""
    print("ForgePilot Backend API Testing")
    print(f"Testing backend at: {BACKEND_URL}")
    print("=" * 60)
    
    async with BackendTester() as tester:
        # Run all test suites
        await tester.test_basic_endpoints()
        await tester.test_project_management()
        await tester.test_agent_chat_system()
        await tester.test_agent_tool_execution()
        await tester.test_settings_update()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())