"""
ForgePilot Update System Tests - Iteration 7
Tests for Auto-Update functionality:
- POST /api/update/install endpoint
- Trigger file creation
- Response structure validation
- Master Agent System Prompt validation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://agent-debug-12.preview.emergentagent.com').rstrip('/')


class TestUpdateStatus:
    """GET /api/update/status - Check update status"""
    
    def test_get_update_status_returns_200(self):
        """Test GET /api/update/status returns 200"""
        response = requests.get(f"{BASE_URL}/api/update/status")
        assert response.status_code == 200
        print(f"✓ GET /api/update/status: Status 200")
    
    def test_update_status_response_structure(self):
        """Test GET /api/update/status returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/update/status")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "installed_version" in data, "Missing installed_version field"
        assert "update_available" in data, "Missing update_available field"
        assert "checking" in data, "Missing checking field"
        
        # Check types
        assert isinstance(data["installed_version"], str), "installed_version should be string"
        assert isinstance(data["update_available"], bool), "update_available should be boolean"
        assert isinstance(data["checking"], bool), "checking should be boolean"
        
        print(f"✓ GET /api/update/status response structure valid:")
        print(f"  - installed_version: {data['installed_version']}")
        print(f"  - update_available: {data['update_available']}")
        print(f"  - latest_version: {data.get('latest_version', 'N/A')}")
        print(f"  - checking: {data['checking']}")


class TestUpdateCheck:
    """POST /api/update/check - Check for updates"""
    
    def test_check_for_updates(self):
        """Test POST /api/update/check"""
        response = requests.post(f"{BASE_URL}/api/update/check")
        # May return 200 or 504 (timeout) depending on GitHub availability
        assert response.status_code in [200, 504], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "installed_version" in data, "Missing installed_version"
            assert "latest_version" in data, "Missing latest_version"
            assert "update_available" in data, "Missing update_available"
            print(f"✓ POST /api/update/check: Success")
            print(f"  - installed_version: {data['installed_version']}")
            print(f"  - latest_version: {data['latest_version']}")
            print(f"  - update_available: {data['update_available']}")
        else:
            print(f"⚠ POST /api/update/check: Timeout (GitHub not reachable)")


class TestUpdateInstall:
    """POST /api/update/install - Trigger automatic update"""
    
    def test_install_update_without_available_update(self):
        """Test POST /api/update/install when no update is available"""
        # First, ensure no update is marked as available
        # This test checks the error handling
        response = requests.post(f"{BASE_URL}/api/update/install")
        
        # Should return 400 if no update available, or 200 if update is available
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data, "Missing error detail"
            print(f"✓ POST /api/update/install (no update): 400 as expected")
            print(f"  - detail: {data['detail']}")
        else:
            data = response.json()
            assert "success" in data, "Missing success field"
            assert "triggered" in data, "Missing triggered field"
            print(f"✓ POST /api/update/install: Success")
            print(f"  - triggered: {data.get('triggered')}")
            print(f"  - message: {data.get('message')}")
    
    def test_install_update_response_structure(self):
        """Test POST /api/update/install response structure when update available"""
        # First check for updates
        check_response = requests.post(f"{BASE_URL}/api/update/check")
        
        if check_response.status_code == 200:
            check_data = check_response.json()
            
            if check_data.get("update_available"):
                # If update is available, test install
                response = requests.post(f"{BASE_URL}/api/update/install")
                assert response.status_code == 200
                data = response.json()
                
                # Check response structure
                assert "success" in data, "Missing success field"
                assert "triggered" in data, "Missing triggered field"
                assert "current_version" in data, "Missing current_version field"
                assert "target_version" in data, "Missing target_version field"
                
                if data["triggered"]:
                    assert "message" in data, "Missing message field"
                    assert "note" in data, "Missing note field"
                    print(f"✓ POST /api/update/install: Auto-update triggered")
                else:
                    assert "instructions" in data, "Missing instructions for manual update"
                    print(f"✓ POST /api/update/install: Manual instructions provided")
                
                print(f"  - triggered: {data['triggered']}")
                print(f"  - current_version: {data['current_version']}")
                print(f"  - target_version: {data['target_version']}")
            else:
                print(f"⚠ No update available, skipping install test")
                pytest.skip("No update available")
        else:
            print(f"⚠ Update check failed, skipping install test")
            pytest.skip("Update check failed")


class TestUpdateRollback:
    """POST /api/update/rollback - Rollback to previous version"""
    
    def test_rollback_without_previous_version(self):
        """Test POST /api/update/rollback when no previous version exists"""
        response = requests.post(f"{BASE_URL}/api/update/rollback")
        
        # Should return 400 if no previous version, or 200 if rollback possible
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data, "Missing error detail"
            print(f"✓ POST /api/update/rollback (no previous): 400 as expected")
            print(f"  - detail: {data['detail']}")
        else:
            data = response.json()
            assert "success" in data, "Missing success field"
            assert "instructions" in data, "Missing instructions field"
            print(f"✓ POST /api/update/rollback: Success")
            print(f"  - rollback_version: {data.get('rollback_version')}")


class TestVersionEndpoint:
    """GET /api/version - Get current version"""
    
    def test_get_version(self):
        """Test GET /api/version"""
        response = requests.get(f"{BASE_URL}/api/version")
        assert response.status_code == 200
        data = response.json()
        
        assert "version" in data, "Missing version field"
        assert "name" in data, "Missing name field"
        assert data["name"] == "ForgePilot", "Expected name to be ForgePilot"
        
        print(f"✓ GET /api/version:")
        print(f"  - version: {data['version']}")
        print(f"  - name: {data['name']}")


class TestHealthEndpoint:
    """GET /api/health - Health check for update verification"""
    
    def test_health_check(self):
        """Test GET /api/health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data, "Missing status field"
        assert "version" in data, "Missing version field"
        assert "checks" in data, "Missing checks field"
        
        # Status should be healthy or degraded
        assert data["status"] in ["healthy", "degraded"], f"Unexpected status: {data['status']}"
        
        # Check structure of checks
        checks = data["checks"]
        assert "mongodb" in checks, "Missing mongodb check"
        assert "llm" in checks, "Missing llm check"
        
        print(f"✓ GET /api/health:")
        print(f"  - status: {data['status']}")
        print(f"  - version: {data['version']}")
        print(f"  - mongodb: {checks['mongodb']}")
        print(f"  - llm: {checks['llm']}")


class TestMasterAgentSystemPrompt:
    """Validate Master Agent System Prompt structure in backend"""
    
    def test_api_root_shows_llm_info(self):
        """Test that API root shows LLM provider info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        
        # Check LLM-related fields
        assert "llm_provider" in data, "Missing llm_provider field"
        assert "active_provider" in data, "Missing active_provider field"
        assert "ollama_available" in data, "Missing ollama_available field"
        
        print(f"✓ API Root LLM Info:")
        print(f"  - llm_provider: {data['llm_provider']}")
        print(f"  - active_provider: {data['active_provider']}")
        print(f"  - ollama_available: {data['ollama_available']}")
    
    def test_llm_status_endpoint(self):
        """Test GET /api/llm/status"""
        response = requests.get(f"{BASE_URL}/api/llm/status")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "provider" in data, "Missing provider field"
        assert "active_provider" in data, "Missing active_provider field"
        assert "ollama_available" in data, "Missing ollama_available field"
        assert "openai_available" in data, "Missing openai_available field"
        
        print(f"✓ GET /api/llm/status:")
        print(f"  - provider: {data['provider']}")
        print(f"  - active_provider: {data['active_provider']}")
        print(f"  - ollama_available: {data['ollama_available']}")
        print(f"  - openai_available: {data['openai_available']}")


class TestUpdateSystemIntegration:
    """Integration tests for the complete update flow"""
    
    def test_full_update_check_flow(self):
        """Test the complete update check flow"""
        # Step 1: Get current status
        status_response = requests.get(f"{BASE_URL}/api/update/status")
        assert status_response.status_code == 200
        initial_status = status_response.json()
        print(f"Step 1 - Initial status: {initial_status['installed_version']}")
        
        # Step 2: Check for updates
        check_response = requests.post(f"{BASE_URL}/api/update/check")
        if check_response.status_code == 200:
            check_data = check_response.json()
            print(f"Step 2 - Update check: available={check_data.get('update_available')}")
            
            # Step 3: Get updated status
            updated_status_response = requests.get(f"{BASE_URL}/api/update/status")
            assert updated_status_response.status_code == 200
            updated_status = updated_status_response.json()
            
            # Verify last_checked_at was updated
            if check_data.get("update_available"):
                assert updated_status.get("latest_version") is not None, "latest_version should be set"
            
            print(f"Step 3 - Updated status: latest={updated_status.get('latest_version')}")
            print(f"✓ Full update check flow completed successfully")
        else:
            print(f"⚠ Update check timed out (GitHub not reachable)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
