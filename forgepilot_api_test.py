#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class ForgePilotNewAPITester:
    def __init__(self, base_url="https://forgepilot-docker.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
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

    def test_api_root_endpoint(self):
        """Test GET /api/ - Should return message, version, llm_provider, active_provider, ollama_available"""
        print("\n🔍 Testing API Root Endpoint...")
        success, data = self.run_test("API Root Endpoint", "GET", "/", 200)
        
        if success:
            required_fields = ["message", "version", "llm_provider", "active_provider", "ollama_available"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
                success = False
            else:
                print(f"   ✅ All required fields present")
                print(f"   Message: {data.get('message')}")
                print(f"   Version: {data.get('version')}")
                print(f"   LLM Provider: {data.get('llm_provider')}")
                print(f"   Active Provider: {data.get('active_provider')}")
                print(f"   Ollama Available: {data.get('ollama_available')}")
        
        return success

    def test_settings_endpoint(self):
        """Test GET /api/settings - Should return comprehensive settings info"""
        print("\n🔍 Testing Settings Endpoint...")
        success, data = self.run_test("Settings Endpoint", "GET", "/settings", 200)
        
        if success:
            required_fields = [
                "openai_api_key_set", "github_token_set", "ollama_url", 
                "ollama_model", "llm_provider", "use_ollama", 
                "settings_from_env", "ollama_available", "ollama_models"
            ]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
                success = False
            else:
                print(f"   ✅ All required fields present")
                print(f"   OpenAI API Key Set: {data.get('openai_api_key_set')}")
                print(f"   GitHub Token Set: {data.get('github_token_set')}")
                print(f"   Ollama URL: {data.get('ollama_url')}")
                print(f"   Ollama Model: {data.get('ollama_model')}")
                print(f"   LLM Provider: {data.get('llm_provider')}")
                print(f"   Use Ollama: {data.get('use_ollama')}")
                print(f"   Settings from Env: {data.get('settings_from_env')}")
                print(f"   Ollama Available: {data.get('ollama_available')}")
                print(f"   Ollama Models: {data.get('ollama_models')}")
        
        return success

    def test_llm_status_endpoint(self):
        """Test GET /api/llm/status - Should return LLM status information"""
        print("\n🔍 Testing LLM Status Endpoint...")
        success, data = self.run_test("LLM Status Endpoint", "GET", "/llm/status", 200)
        
        if success:
            required_fields = [
                "provider", "active_provider", "ollama_available", 
                "ollama_url", "ollama_model", "ollama_models", 
                "openai_available", "auto_fallback_active"
            ]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
                success = False
            else:
                print(f"   ✅ All required fields present")
                print(f"   Provider: {data.get('provider')}")
                print(f"   Active Provider: {data.get('active_provider')}")
                print(f"   Ollama Available: {data.get('ollama_available')}")
                print(f"   Ollama URL: {data.get('ollama_url')}")
                print(f"   Ollama Model: {data.get('ollama_model')}")
                print(f"   Ollama Models: {data.get('ollama_models')}")
                print(f"   OpenAI Available: {data.get('openai_available')}")
                print(f"   Auto Fallback Active: {data.get('auto_fallback_active')}")
        
        return success

    def test_health_check_endpoint(self):
        """Test GET /api/health - Should return health status with checks"""
        print("\n🔍 Testing Health Check Endpoint...")
        success, data = self.run_test("Health Check Endpoint", "GET", "/health", 200)
        
        if success:
            required_fields = ["status", "version", "checks"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
                success = False
            else:
                # Check if checks object has required boolean fields
                checks = data.get('checks', {})
                required_checks = ["mongodb", "llm", "ollama", "openai"]
                missing_checks = []
                
                for check in required_checks:
                    if check not in checks:
                        missing_checks.append(check)
                
                if missing_checks:
                    print(f"   ❌ Missing required checks: {missing_checks}")
                    success = False
                else:
                    print(f"   ✅ All required fields and checks present")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Version: {data.get('version')}")
                    print(f"   MongoDB Check: {checks.get('mongodb')}")
                    print(f"   LLM Check: {checks.get('llm')}")
                    print(f"   Ollama Check: {checks.get('ollama')}")
                    print(f"   OpenAI Check: {checks.get('openai')}")
        
        return success

    def test_update_status_endpoint(self):
        """Test GET /api/update/status - Should return update status information"""
        print("\n🔍 Testing Update Status Endpoint...")
        success, data = self.run_test("Update Status Endpoint", "GET", "/update/status", 200)
        
        if success:
            required_fields = [
                "installed_version", "latest_version", "update_available", 
                "checking", "last_checked_at", "release_notes", 
                "previous_version", "last_update_at", "last_rollback_at"
            ]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
                success = False
            else:
                print(f"   ✅ All required fields present")
                print(f"   Installed Version: {data.get('installed_version')}")
                print(f"   Latest Version: {data.get('latest_version')}")
                print(f"   Update Available: {data.get('update_available')}")
                print(f"   Checking: {data.get('checking')}")
                print(f"   Last Checked At: {data.get('last_checked_at')}")
        
        return success

    def test_update_check_endpoint(self):
        """Test POST /api/update/check - Should check for updates"""
        print("\n🔍 Testing Update Check Endpoint...")
        success, data = self.run_test("Update Check Endpoint", "POST", "/update/check", 200)
        
        if success:
            required_fields = ["success", "installed_version", "latest_version", "update_available"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
                success = False
            else:
                print(f"   ✅ All required fields present")
                print(f"   Success: {data.get('success')}")
                print(f"   Installed Version: {data.get('installed_version')}")
                print(f"   Latest Version: {data.get('latest_version')}")
                print(f"   Update Available: {data.get('update_available')}")
                if data.get('message'):
                    print(f"   Message: {data.get('message')}")
        
        return success

    def test_settings_update_endpoint(self):
        """Test PUT /api/settings with llm_provider field"""
        print("\n🔍 Testing Settings Update Endpoint...")
        
        # Test setting llm_provider to "auto"
        settings_data = {"llm_provider": "auto"}
        success1, data1 = self.run_test("Settings Update (auto)", "PUT", "/settings", 200, settings_data)
        
        if success1:
            if "success" in data1 and data1["success"]:
                print(f"   ✅ Successfully set LLM provider to auto")
                print(f"   Active Provider: {data1.get('active_provider')}")
            else:
                print(f"   ❌ Update failed: {data1}")
                success1 = False
        
        # Test setting llm_provider to "openai"
        settings_data = {"llm_provider": "openai"}
        success2, data2 = self.run_test("Settings Update (openai)", "PUT", "/settings", 200, settings_data)
        
        if success2:
            if "success" in data2 and data2["success"]:
                print(f"   ✅ Successfully set LLM provider to openai")
                print(f"   Active Provider: {data2.get('active_provider')}")
            else:
                print(f"   ❌ Update failed: {data2}")
                success2 = False
        
        # Test setting llm_provider to "ollama"
        settings_data = {"llm_provider": "ollama"}
        success3, data3 = self.run_test("Settings Update (ollama)", "PUT", "/settings", 200, settings_data)
        
        if success3:
            if "success" in data3 and data3["success"]:
                print(f"   ✅ Successfully set LLM provider to ollama")
                print(f"   Active Provider: {data3.get('active_provider')}")
            else:
                print(f"   ❌ Update failed: {data3}")
                success3 = False
        
        # Reset to auto for consistency
        settings_data = {"llm_provider": "auto"}
        self.run_test("Settings Reset (auto)", "PUT", "/settings", 200, settings_data)
        
        return success1 and success2 and success3

    def run_all_tests(self):
        """Run all new API tests"""
        print("🚀 Starting ForgePilot New API Features Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # New API tests
        tests = [
            self.test_api_root_endpoint,
            self.test_settings_endpoint,
            self.test_llm_status_endpoint,
            self.test_health_check_endpoint,
            self.test_update_status_endpoint,
            self.test_update_check_endpoint,
            self.test_settings_update_endpoint,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")

        # Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 ForgePilot new API features tests mostly successful!")
            return 0
        else:
            print("⚠️  ForgePilot new API features have significant issues")
            return 1

def main():
    tester = ForgePilotNewAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())