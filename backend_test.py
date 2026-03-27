#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class ForgePilotAPITester:
    def __init__(self, base_url="https://forged-workflow.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.project_id = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            else:
                self.log_test(name, False, f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}

            details = f"Status: {response.status_code}"
            if not success:
                details += f" (Expected: {expected_status})"
                if response.text:
                    details += f" Response: {response.text[:200]}"

            self.log_test(name, success, details)
            return success, response_data

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test GET /api/"""
        print("\n🔍 Testing Root Endpoint...")
        success, data = self.run_test("Root API", "GET", "/", 200)
        if success and "message" in data:
            print(f"   API Message: {data.get('message')}")
            print(f"   Version: {data.get('version')}")
        return success

    def test_projects_crud(self):
        """Test project CRUD operations"""
        print("\n🔍 Testing Projects CRUD...")
        
        # Test GET /api/projects (empty initially)
        success, projects = self.run_test("Get Projects (Empty)", "GET", "/projects", 200)
        if not success:
            return False

        # Test POST /api/projects (create project)
        project_data = {
            "name": "Test ForgePilot Project",
            "description": "Ein Test-Projekt für die API-Validierung",
            "project_type": "fullstack"
        }
        
        success, project = self.run_test("Create Project", "POST", "/projects", 200, project_data)
        if not success:
            return False
            
        if "id" in project:
            self.project_id = project["id"]
            print(f"   Created Project ID: {self.project_id}")
        else:
            print("   ❌ No project ID returned")
            return False

        # Test GET /api/projects (should have our project)
        success, projects = self.run_test("Get Projects (With Data)", "GET", "/projects", 200)
        if success and len(projects) > 0:
            print(f"   Found {len(projects)} project(s)")

        # Test GET /api/projects/{id}
        success, project_detail = self.run_test(
            "Get Project Detail", "GET", f"/projects/{self.project_id}", 200
        )
        if success:
            print(f"   Project Name: {project_detail.get('name')}")
            print(f"   Project Type: {project_detail.get('project_type')}")

        return success

    def test_messages_api(self):
        """Test messages/chat API"""
        if not self.project_id:
            print("❌ No project ID available for message testing")
            return False

        print("\n🔍 Testing Messages API...")
        
        # Test GET messages (empty initially)
        success, messages = self.run_test(
            "Get Messages (Empty)", "GET", f"/projects/{self.project_id}/messages", 200
        )
        if not success:
            return False

        # Test POST message
        message_data = {
            "project_id": self.project_id,
            "content": "Hallo ForgePilot! Kannst du mir bei diesem Projekt helfen?",
            "role": "user"
        }
        
        success, message = self.run_test(
            "Create Message", "POST", f"/projects/{self.project_id}/messages", 200, message_data
        )
        if success and "id" in message:
            print(f"   Message ID: {message['id']}")

        # Test GET messages (should have our message)
        success, messages = self.run_test(
            "Get Messages (With Data)", "GET", f"/projects/{self.project_id}/messages", 200
        )
        if success and len(messages) > 0:
            print(f"   Found {len(messages)} message(s)")

        return success

    def test_agents_api(self):
        """Test agent status API"""
        if not self.project_id:
            print("❌ No project ID available for agent testing")
            return False

        print("\n🔍 Testing Agents API...")
        
        # Test GET agents
        success, agents = self.run_test(
            "Get Agent Statuses", "GET", f"/projects/{self.project_id}/agents", 200
        )
        if success:
            print(f"   Found {len(agents)} agent(s)")
            for agent in agents:
                print(f"   - {agent.get('agent_type')}: {agent.get('status')}")

        return success

    def test_logs_api(self):
        """Test logs API"""
        if not self.project_id:
            print("❌ No project ID available for logs testing")
            return False

        print("\n🔍 Testing Logs API...")
        
        # Test GET logs
        success, logs = self.run_test(
            "Get Logs", "GET", f"/projects/{self.project_id}/logs", 200
        )
        if success:
            print(f"   Found {len(logs)} log(s)")

        # Test POST log
        log_data = {
            "level": "info",
            "message": "Test log entry from API test",
            "source": "test"
        }
        
        success, log = self.run_test(
            "Create Log Entry", "POST", f"/projects/{self.project_id}/logs", 200, log_data
        )
        if success and "id" in log:
            print(f"   Log ID: {log['id']}")

        return success

    def test_roadmap_api(self):
        """Test roadmap API"""
        if not self.project_id:
            print("❌ No project ID available for roadmap testing")
            return False

        print("\n🔍 Testing Roadmap API...")
        
        # Test GET roadmap (empty initially)
        success, roadmap = self.run_test(
            "Get Roadmap", "GET", f"/projects/{self.project_id}/roadmap", 200
        )
        if success:
            print(f"   Found {len(roadmap)} roadmap item(s)")

        return success

    def test_github_endpoints(self):
        """Test GitHub-related endpoints (without actual import)"""
        print("\n🔍 Testing GitHub Endpoints...")
        
        # Test GitHub import with invalid URL (should fail gracefully)
        github_data = {
            "repo_url": "https://github.com/invalid/nonexistent-repo",
            "branch": "main"
        }
        
        success, response = self.run_test(
            "GitHub Import (Invalid Repo)", "POST", "/github/import", 400, github_data
        )
        # We expect this to fail with 400, so success means it handled the error properly
        
        return True  # GitHub tests are optional for basic functionality

    def test_chat_streaming(self):
        """Test chat streaming endpoint (basic connectivity)"""
        if not self.project_id:
            print("❌ No project ID available for chat testing")
            return False

        print("\n🔍 Testing Chat Streaming...")
        
        # Test chat endpoint (we won't test full streaming, just connectivity)
        chat_data = {
            "project_id": self.project_id,
            "content": "Hallo! Das ist ein Test der Chat-Funktionalität.",
            "role": "user"
        }
        
        try:
            url = f"{self.api_url}/projects/{self.project_id}/chat"
            response = self.session.post(url, json=chat_data, stream=True, timeout=10)
            
            if response.status_code == 200:
                # Check if we get streaming response
                content_type = response.headers.get('content-type', '')
                if 'text/event-stream' in content_type:
                    self.log_test("Chat Streaming Endpoint", True, "SSE stream started")
                    response.close()  # Close the stream
                    return True
                else:
                    self.log_test("Chat Streaming Endpoint", False, f"Wrong content-type: {content_type}")
                    return False
            else:
                self.log_test("Chat Streaming Endpoint", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Chat Streaming Endpoint", False, f"Exception: {str(e)}")
            return False

    def cleanup(self):
        """Clean up test data"""
        if self.project_id:
            print("\n🧹 Cleaning up test data...")
            success, _ = self.run_test(
                "Delete Test Project", "DELETE", f"/projects/{self.project_id}", 200
            )
            if success:
                print("   Test project deleted successfully")

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting ForgePilot API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # Core API tests
        tests = [
            self.test_root_endpoint,
            self.test_projects_crud,
            self.test_messages_api,
            self.test_agents_api,
            self.test_logs_api,
            self.test_roadmap_api,
            self.test_chat_streaming,
            self.test_github_endpoints,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")

        # Cleanup
        self.cleanup()

        # Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 Backend API tests mostly successful!")
            return 0
        else:
            print("⚠️  Backend API has significant issues")
            return 1

def main():
    tester = ForgePilotAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())