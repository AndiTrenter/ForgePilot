"""
ForgePilot Settings API Tests - Iteration 7
Tests for Settings endpoints: GET, PUT, DELETE for OpenAI key and GitHub token
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://forgepilot-docker.preview.emergentagent.com').rstrip('/')

# Test credentials from review request
TEST_OPENAI_KEY = "sk-test-key-12345"
TEST_GITHUB_TOKEN = "ghp_test_token_12345"


class TestSettingsGet:
    """GET /api/settings - Retrieve current settings status"""
    
    def test_get_settings_returns_200(self):
        """Test GET /api/settings returns 200"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        print(f"✓ GET /api/settings: Status 200")
    
    def test_get_settings_response_structure(self):
        """Test GET /api/settings returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "openai_api_key_set" in data, "Missing openai_api_key_set field"
        assert "github_token_set" in data, "Missing github_token_set field"
        assert "ollama_url" in data, "Missing ollama_url field"
        assert "use_ollama" in data, "Missing use_ollama field"
        
        # Check types
        assert isinstance(data["openai_api_key_set"], bool), "openai_api_key_set should be boolean"
        assert isinstance(data["github_token_set"], bool), "github_token_set should be boolean"
        assert isinstance(data["ollama_url"], str), "ollama_url should be string"
        assert isinstance(data["use_ollama"], bool), "use_ollama should be boolean"
        
        print(f"✓ GET /api/settings response structure valid:")
        print(f"  - openai_api_key_set: {data['openai_api_key_set']}")
        print(f"  - github_token_set: {data['github_token_set']}")
        print(f"  - ollama_url: {data['ollama_url']}")
        print(f"  - use_ollama: {data['use_ollama']}")


class TestSettingsUpdate:
    """PUT /api/settings - Update settings"""
    
    def test_update_openai_key(self):
        """Test PUT /api/settings with openai_api_key"""
        response = requests.put(
            f"{BASE_URL}/api/settings",
            json={"openai_api_key": TEST_OPENAI_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        assert data.get("openai_api_key_set") == True, "Expected openai_api_key_set: true"
        
        print(f"✓ PUT /api/settings (openai_api_key): Success")
        print(f"  - Response: {data}")
    
    def test_update_github_token(self):
        """Test PUT /api/settings with github_token"""
        response = requests.put(
            f"{BASE_URL}/api/settings",
            json={"github_token": TEST_GITHUB_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        assert data.get("github_token_set") == True, "Expected github_token_set: true"
        
        print(f"✓ PUT /api/settings (github_token): Success")
        print(f"  - Response: {data}")
    
    def test_update_ollama_url(self):
        """Test PUT /api/settings with ollama_url"""
        test_url = "http://localhost:11434"
        response = requests.put(
            f"{BASE_URL}/api/settings",
            json={"ollama_url": test_url}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        
        # Verify the change
        get_response = requests.get(f"{BASE_URL}/api/settings")
        get_data = get_response.json()
        assert get_data["ollama_url"] == test_url, f"Expected ollama_url to be {test_url}"
        
        print(f"✓ PUT /api/settings (ollama_url): Success")
    
    def test_update_use_ollama(self):
        """Test PUT /api/settings with use_ollama"""
        response = requests.put(
            f"{BASE_URL}/api/settings",
            json={"use_ollama": True}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        
        # Verify the change
        get_response = requests.get(f"{BASE_URL}/api/settings")
        get_data = get_response.json()
        assert get_data["use_ollama"] == True, "Expected use_ollama to be True"
        
        # Reset back to false
        requests.put(f"{BASE_URL}/api/settings", json={"use_ollama": False})
        
        print(f"✓ PUT /api/settings (use_ollama): Success")
    
    def test_update_multiple_settings(self):
        """Test PUT /api/settings with multiple fields"""
        response = requests.put(
            f"{BASE_URL}/api/settings",
            json={
                "openai_api_key": TEST_OPENAI_KEY,
                "github_token": TEST_GITHUB_TOKEN,
                "use_ollama": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        assert data.get("openai_api_key_set") == True, "Expected openai_api_key_set: true"
        assert data.get("github_token_set") == True, "Expected github_token_set: true"
        
        print(f"✓ PUT /api/settings (multiple): Success")


class TestSettingsDelete:
    """DELETE /api/settings/* - Delete specific settings"""
    
    def test_delete_openai_key(self):
        """Test DELETE /api/settings/openai-key"""
        # First ensure key is set
        requests.put(f"{BASE_URL}/api/settings", json={"openai_api_key": TEST_OPENAI_KEY})
        
        # Delete the key
        response = requests.delete(f"{BASE_URL}/api/settings/openai-key")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/settings")
        get_data = get_response.json()
        assert get_data["openai_api_key_set"] == False, "Expected openai_api_key_set to be False after deletion"
        
        print(f"✓ DELETE /api/settings/openai-key: Success")
    
    def test_delete_github_token(self):
        """Test DELETE /api/settings/github-token"""
        # First ensure token is set
        requests.put(f"{BASE_URL}/api/settings", json={"github_token": TEST_GITHUB_TOKEN})
        
        # Delete the token
        response = requests.delete(f"{BASE_URL}/api/settings/github-token")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success: true"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/settings")
        get_data = get_response.json()
        assert get_data["github_token_set"] == False, "Expected github_token_set to be False after deletion"
        
        print(f"✓ DELETE /api/settings/github-token: Success")


class TestSettingsPersistence:
    """Test that settings persist in MongoDB"""
    
    def test_settings_persist_after_update(self):
        """Test that settings are persisted and can be retrieved"""
        # Set both keys
        update_response = requests.put(
            f"{BASE_URL}/api/settings",
            json={
                "openai_api_key": TEST_OPENAI_KEY,
                "github_token": TEST_GITHUB_TOKEN
            }
        )
        assert update_response.status_code == 200
        
        # Retrieve and verify
        get_response = requests.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["openai_api_key_set"] == True, "OpenAI key should be set"
        assert data["github_token_set"] == True, "GitHub token should be set"
        
        print(f"✓ Settings persistence verified")
        print(f"  - openai_api_key_set: {data['openai_api_key_set']}")
        print(f"  - github_token_set: {data['github_token_set']}")


class TestSettingsCleanup:
    """Cleanup test - restore original settings"""
    
    def test_restore_original_settings(self):
        """Restore original API keys from environment"""
        # The original keys are in backend/.env, restore them
        # Note: This test runs last to restore the original state
        
        # Get current state
        response = requests.get(f"{BASE_URL}/api/settings")
        print(f"✓ Final settings state:")
        print(f"  - {response.json()}")
        
        # Note: The original keys from .env will be loaded on server restart
        # For now, we just verify the API works
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
